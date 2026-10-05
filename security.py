"""Security checks: suspicious content (prompt injection, scripts, dangerous commands) and a log of security events.

Suspicious questions are logged, not blocked: people legitimately ask about scripts and commands.
Suspicious documents are refused at upload, because a document reaches every user who searches it.
Dangerous commands in an answer get a warning appended for the user.
"""
import json
import re
import time

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
LABELS = {"prompt-injection": "ניסיון לעקוף הוראות", "script": "קוד דפדפן", "dangerous-command": "פקודה מסוכנת"}


def scan(text):
    """Names of the suspicious-content categories found in text, in a stable order."""
    if not isinstance(text, str) or not text:
        return []
    return [kind for kind, pats in PATTERNS.items() if any(p.search(text) for p in pats)]


def event(c, kind, name, detail):
    c.execute("insert into security_events values (?,?,?,?)",
              (time.time(), kind, name or "", json.dumps(detail, ensure_ascii=False)))


def answer_warning(categories):
    if "dangerous-command" not in categories:
        return ""
    return ("\n\n⚠️ **אזהרת אבטחה:** התשובה כוללת פקודה שעלולה למחוק מידע או להריץ קוד מהאינטרנט. "
            "אל תריצו אותה בלי לבדוק בדיוק מה היא עושה.")
