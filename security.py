"""Security checks: suspicious content (prompt injection, jailbreaks, scripts, dangerous commands, risky links) and a
log of security events.

What happens to a suspicious question is the administrator's policy (gateway.py: block by default for injection and
jailbreak attempts, log only as the alternative). Scripts and commands in questions are only logged: people
legitimately ask about them. Suspicious documents are refused at upload, because a document reaches every user who
searches it. Dangerous commands and risky links in an answer get a warning appended for the user.
"""
import ipaddress
import json
import re
import time
import urllib.parse

SCHEMA = """
create table if not exists security_events(ts real, kind text, name text, detail text);
create index if not exists security_events_ts on security_events(ts);
"""

_I = re.IGNORECASE
PATTERNS = {
    # text trying to override the model's instructions
    "prompt-injection": [re.compile(p, _I) for p in (
        r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|above|earlier|system)\s+(instructions|prompts?|rules|messages)",
        r"\byou\s+are\s+now\s+(in\s+)?(developer\s+mode|dan\b|jailbr)",
        r"\b(reveal|print|show|repeat)\s+(me\s+)?(your|the)\s+(system\s+prompt|hidden\s+instructions|initial\s+instructions)",
        r"\bdo\s+anything\s+now\b",
        r"</?\s*(system|instructions?)\s*>",
        r"(התעלם|תתעלם|שכח|תשכח|בטל)\S*\s+(מ|את\s+)?(כל\s+)?ה?(הוראות|הנחיות|כללים)",
        r"(חשוף|תחשוף|הצג|תציג|הדפס)\S*\s+(את\s+)?ה?(הוראות|הנחיות)\s+(ה)?(מערכת|הסודיות|הנסתרות)",
        r"מעכשיו\s+אתה\s+(לא\s+)?(מוגבל|חופשי|במצב)",
        # asking for the system prompt, keys or passwords
        r"\b(show|tell|give|reveal|print|repeat|dump|list|leak|what\s+is|what's|what\s+are)\s+(me\s+)?(your|the)\s+"
        r"(system\s+prompt|(api|secret|access|private)[\s_-]?keys?|credentials|passwords?|tokens?)\b"
        r"(?!\s+(policy|policies|format|length|requirements?|rules?|reset|change|expir))",
        r"(מה|תן|תני|הצג|תציג|תראה|חשוף|תחשוף|הדפס|תדפיס)\S*\s+(לי\s+)?(את\s+)?ה?(הנחיות\s+המערכת|פרומפט\s+המערכת|"
        r"מפתח(ות)?\s+ה?-?API|סיסמ(ה|אות)\s+(של\s+)?ה?(מערכת|מנהל|שרת))",
    )],
    # trying to talk the model out of its rules
    "jailbreak": [re.compile(p, _I) for p in (
        r"\bpretend\s+(that\s+)?you\s+(have|had|are)\s+(no|without)\s+(restrictions|rules|limits|filters|guidelines)",
        r"\b(ignore|bypass|disable|forget|break)\s+(all\s+)?(of\s+)?(your|the|any)\s+(rules|restrictions|guidelines|safety|filters|"
        r"content\s+polic(y|ies)|programming)",
        r"\b(you\s+are|act\s+as|pretend\s+to\s+be|role-?play\s+as|become)\s+(now\s+)?(an?\s+)?(unrestricted|unfiltered|uncensored|"
        r"jailbroken|evil)\s+(ai|assistant|model|chatbot|version)",
        r"\b(act\s+as|you\s+are(\s+now)?|pretend\s+to\s+be|become)\s+(a\s+)?(?-i:DAN)\b",
        r"\b(jailbreak\s+(mode|prompt)|jailbroken|(?-i:DAN)\s+mode|developer\s+mode\s+(enabled|output|activated))\b",
        r"\bstay\s+in\s+character\b[^.\n]{0,60}\b(no\s+matter|even\s+if|regardless)",
        r"\b(hypothetically|fictional\s+world|for\s+a\s+story)\b[^.\n]{0,80}\b(no\s+(rules|restrictions|limits)|"
        r"ignore\s+(your|the)\s+(rules|guidelines))",
        r"(תעמיד|תעמידי|העמד|העמידי|תדמיין|דמיין)\S*\s+(ש|פנים\s+ש)אין\s+לך\s+(שום\s+)?(הגבלות|מגבלות|כללים|חוקים)",
        r"(עקוף|תעקוף|תעקפי|תשבור|שבור)\S*\s+(את\s+)?ה?(כללים|חוקים|הגבלות|מגבלות|סינון)",
        r"מצב\s+(ללא|בלי)\s+(הגבלות|מגבלות|צנזורה|סינון)",
    )],
    # active web content: harmless as text, dangerous if some tool renders it
    "script": [re.compile(p, _I) for p in (
        r"<\s*script\b", r"\bjavascript\s*:", r"<[^>]+\son(error|load|click|mouseover)\s*=", r"<\s*iframe\b",
        r"data\s*:\s*text/html", r"<\s*object\b", r"<\s*embed\b",
    )],
    # commands that wipe data or download-and-run code
    "dangerous-command": [re.compile(p, _I) for p in (
        r"\brm\s+-[a-z]*r[a-z]*f?[a-z]*\s+(/|~|\*)(\s|$)",
        r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b",
        r"\bpowershell(\.exe)?\b[^\n]*\s-(e|enc|encodedcommand)\s+[a-z0-9+/=]{20,}",
        r"\b(invoke-expression|iex)\s*[\(\$]",
        r"\bcertutil(\.exe)?\s+-urlcache\b",
        r"\bmshta(\.exe)?\s+https?:",
        r"\bbase64\s+(-d|--decode)\b[^\n]*\|\s*(ba)?sh\b",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
        r"\bformat\s+[a-z]:\s*/q\b",
        r"\bdel\s+/[sfq]\s+/[sfq]",
        r"\bmkfs(\.\w+)?\s+/dev/",
        r"\bdd\s+if=\S+\s+of=/dev/(sd|nvme|hd)",
    )],
}
LABELS = {"prompt-injection": "ניסיון לעקוף הוראות", "jailbreak": "ניסיון לשחרר את המודל מהכללים", "script": "קוד דפדפן",
          "dangerous-command": "פקודה מסוכנת"}
ATTACKS = {"prompt-injection", "jailbreak"}  # what the injection policy blocks

# links in an answer that a careful person wouldn't click: raw IP addresses, look-alike (punycode) names,
# data:/javascript: links, link shorteners and top-level domains that are mostly abuse
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>\"'`)\]]+|\b(?:javascript|data|vbscript):[^\s<>\"'`)]+", _I)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "ow.ly", "buff.ly", "shorturl.at", "tiny.cc",
              "rebrand.ly", "t.ly", "v.gd", "s.id", "lnkd.in"}
BAD_TLDS = {"zip", "mov", "tk", "ml", "ga", "cf", "gq", "xyz", "top", "click", "country", "kim", "work", "loan", "rest"}


def bad_links(text):
    """Risky links in text (each at most 200 characters)."""
    out = []
    for m in _URL.finditer(text or ""):
        url = m[0].rstrip(".,;:!?")
        if re.match(r"(?i)(javascript|data|vbscript):", url):
            out.append(url[:200])
            continue
        host = (urllib.parse.urlsplit(url if "://" in url else "http://" + url).hostname or "").lower().rstrip(".")
        try:
            ipaddress.ip_address(host)
            raw_ip = True
        except ValueError:
            raw_ip = False
        if raw_ip or "xn--" in host or host in SHORTENERS or host.rsplit(".", 1)[-1] in BAD_TLDS:
            out.append(url[:200])
    return out


def scan(text):
    """Names of the suspicious-content categories found in text, in a stable order."""
    if not isinstance(text, str) or not text:
        return []
    return [kind for kind, pats in PATTERNS.items() if any(p.search(text) for p in pats)]


def event(c, kind, name, detail):
    c.execute("insert into security_events values (?,?,?,?)",
              (time.time(), kind, name or "", json.dumps(detail, ensure_ascii=False)))


def answer_warning(categories, links=()):
    out = ""
    if "dangerous-command" in categories:
        out += ("\n\n⚠️ **אזהרת אבטחה:** התשובה כוללת פקודה שעלולה למחוק מידע או להריץ קוד מהאינטרנט. "
                "אל תריצו אותה בלי לבדוק בדיוק מה היא עושה.")
    if links:
        out += ("\n\n⚠️ **אזהרת אבטחה:** התשובה כוללת קישור חשוד (כתובת מספרית, קיצור קישורים או שם שמתחזה לאתר מוכר). "
                "אל תלחצו עליו בלי לבדוק לאן הוא מוביל.")
    return out
