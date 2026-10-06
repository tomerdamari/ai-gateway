"""Every setting of the gateway, in one list: the settings screen, the API, the documentation and the code all read it.

A value comes from (first wins): the server's environment / .env file (shown locked on the screen), the value saved on the
screen (the settings table; secrets encrypted), the default below. Defaults are the behaviour before the settings screen
existed, so a gateway nobody configures works exactly as before. Some settings may differ per team (team_settings table).

Standard library only. gateway.py wires in encryption (ENCRYPT/DECRYPT) and the checks that need its data (CHECKS).
"""
import ipaddress
import json
import os
import re

SECTIONS = [
    ("general", "כללי", "General"),
    ("access", "כניסה וגישה", "Sign-in and access"),
    ("providers", "ספקים ומפתחות", "Providers and keys"),
    ("models", "מודלים וניתוב", "Models and routing"),
    ("budgets", "תקציבים ומכסות", "Budgets and quotas"),
    ("security", "אבטחה ומדיניות", "Security and policy"),
    ("data", "תוכן, שמירה והצפנה", "Content, storage and encryption"),
    ("sources", "מקורות מידע", "Knowledge sources"),
    ("alerts", "התראות ודוחות", "Alerts and reports"),
    ("capabilities", "יכולות ספקים", "Provider capabilities"),
    ("devtools", "כלי מפתחים", "Developer tools"),
    ("browser", "דפדפן", "Browser"),
    ("system", "מערכת", "System"),
]
CARDS = {
    "org": ("הארגון", "Organization"), "time": ("שפה ושעה", "Language and time"),
    "chat-login": ("כניסה לצ'אט", "Chat sign-in"), "admin-login": ("כניסה למסך הניהול", "Admin sign-in"),
    "network": ("רשת וכתובות", "Network and addresses"), "lockout": ("סיסמאות שגויות", "Wrong passwords"),
    "anthropic": ("Anthropic ‏(Claude)", "Anthropic (Claude)"), "openai": ("OpenAI ‏(GPT)", "OpenAI (GPT)"),
    "gemini": ("Google ‏(Gemini)", "Google (Gemini)"), "local": ("שרת המודלים של החברה", "The company's model server"),
    "more-providers": ("ספקים נוספים", "More providers"),
    "default": ("ברירת מחדל ותשובות", "Default and answers"), "auto": ("בחירה אוטומטית", "Automatic choice"),
    "budget": ("תקציב", "Budget"), "new-user": ("ברירות מחדל למשתמש חדש", "Defaults for a new user"),
    "limits": ("מגבלות לבקשה", "Request limits"), "spike": ("הוצאה חריגה", "Unusual spending"),
    "policy": ("מדיניות", "Policy"), "masking": ("מידע רגיש", "Sensitive data"), "answers": ("תשובות", "Answers"),
    "connections": ("חיבורים ותיקיות", "Connections and folders"), "keys": ("מפתחות לאפליקציות", "App keys"),
    "log": ("יומן", "Log"), "backup": ("גיבוי", "Backup"),
    "search": ("חיפוש", "Search"), "summary": ("סיכום חודשי במייל", "Monthly summary by email"),
    "smtp": ("שרת דואר", "Mail server"), "outbound": ("התראות החוצה", "Outbound alerts"),
    "speed": ("ספק איטי", "Slow provider"), "savings": ("המלצות לחיסכון", "Savings recommendations"),
    "capabilities": ("יכולות", "Capabilities"), "tools": ("כלים מובנים", "Built-in tools"), "voice": ("קול", "Voice"),
    "devtools": ("כלי מפתחים", "Developer tools"), "browser": ("תוסף הדפדפן", "Browser extension"),
}
MASK_TYPES = [("id", "תעודת זהות", "ID number"), ("card", "כרטיס אשראי", "Credit card"), ("secret", "סודות ומפתחות", "Secrets and keys"),
              ("phone", "טלפון", "Phone"), ("email", "מייל", "Email"), ("iban", "IBAN", "IBAN"), ("bank", "חשבון בנק", "Bank account"),
              ("passport", "דרכון", "Passport")]


def S(key, section, card, type, he, en, help_he, help_en, default, **kw):
    return {"key": key, "section": section, "card": card, "type": type, "label_he": he, "label_en": en, "help_he": help_he,
            "help_en": help_en, "default": default, "env": kw.pop("env", None), "applies": kw.pop("applies", "now"),
            "sensitive": kw.pop("sensitive", False), "team": kw.pop("team", False), "soon": kw.pop("soon", False), **kw}


def O(*opts):
    return [{"value": v, "he": he, "en": en, **({"soon": True} if rest else {})} for v, he, en, *rest in opts]


B = "bool"
REGISTRY = [
    # 1. general
    S("org_name", "general", "org", "text", "שם הארגון", "Organization name",
      "מופיע בראש מסך הצ'אט ובכותרת המייל החודשי. ריק = רק FireGate.",
      "Shown at the top of the chat screen and in the monthly email's subject. Empty = FireGate only.", "", max=80),
    S("default_language", "general", "time", "choice", "שפת ברירת מחדל לעובדים חדשים", "Default language for new visitors",
      "השפה שבה נפתחים המסכים למי שעוד לא בחר שפה בדפדפן שלו.",
      "The language the screens open in for someone who hasn't picked one in their browser yet.", "he",
      options=O(("he", "עברית", "Hebrew"), ("en", "אנגלית", "English"))),
    S("timezone", "general", "time", "timezone", "אזור זמן", "Time zone",
      "לפיו נקבעים תחילת היום והחודש בדוחות, בתקציבים, במייל החודשי ובגיבויים. ריק = השעון של השרת.",
      "Sets when a day and a month begin in reports, budgets, the monthly email and backups. Empty = the server's clock.", ""),
    S("home_page", "general", "org", "choice", "עמוד הבית של הכתובת הראשית", "Home page of the main address",
      "מה נפתח כשנכנסים לכתובת של השער בלי נתיב. מסך הניהול תמיד זמין גם ב-‎/admin.",
      "What opens at the gateway's address without a path. The admin screen is always at /admin too.", "admin",
      options=O(("admin", "מסך הניהול", "Admin screen"), ("chat", "הצ'אט", "Chat"))),

    # 2. sign-in and access
    S("open_access", "access", "chat-login", B, "כניסה לצ'אט בלי סיסמה ברשת המשרד", "Chat without a password on the office network",
      "כל אחד ברשת המשרד בוחר את השם שלו ונכנס. נוח בהתחלה, אבל כל אחד יכול להשתמש בתקציב של אחר.",
      "Anyone on the office network picks their name and goes in. Handy at first, but anyone can use someone else's budget.",
      False, env="OPEN_ACCESS", sensitive=True),
    S("chat_sso", "access", "chat-login", B, "כניסה עם חשבון החברה", "Sign in with the company account",
      "כניסה לצ'אט עם החשבון של החברה (Microsoft או Google), בלי סיסמה נפרדת.",
      "Chat sign-in with the company account (Microsoft or Google), with no separate password.", False, soon=True),
    S("admin_password", "access", "admin-login", "secret", "סיסמת מנהל לכניסה מבחוץ", "Admin password from outside",
      "מתוך רשת המשרד מסך הניהול נפתח בלי סיסמה. מבחוץ צריך את הסיסמה הזו. בלי סיסמה, המסך סגור מבחוץ. מומלץ 16 תווים לפחות.",
      "From the office network the admin screen opens without a password. From outside it needs this one. Without it the "
      "screen is closed from outside. At least 16 characters is recommended.", "", env="ADMIN_PASSWORD", sensitive=True, min=8),
    S("internet_exposure", "access", "network", "choice", "חשיפה לאינטרנט", "Exposure to the internet",
      "מאיפה אפשר להגיע לשער. נדרש ל-Cursor ול-Copilot הארגוני.", "Where the gateway can be reached from. Needed for Cursor and Copilot for business.",
      "office", soon=True, options=O(("office", "רשת המשרד בלבד", "Office network only"), ("internet", "גם מהאינטרנט", "Also from the internet"))),
    S("public_deploy", "access", "network", B, "השרת בענן (בלי רשת משרד)", "Hosted in the cloud (no office network)",
      "כשהשער לא יודע להבדיל בין המשרד לבחוץ: מסך הניהול תמיד דורש סיסמה, והכניסה בלי סיסמה כבויה.",
      "When the gateway can't tell the office from outside: the admin screen always needs the password and password-free chat is off.",
      False, env="PUBLIC_DEPLOY", sensitive=True),
    S("allowed_hosts", "access", "network", "list", "שמות שרת מורשים", "Allowed host names",
      "שמות נוספים שהשער עונה להם (שורה לכל שם). כתובות IP ו-localhost תמיד עובדים. מונע מאתר זר להתחזות לשער.",
      "Extra names the gateway answers to (one per line). IP addresses and localhost always work. Stops a hostile site posing as the gateway.",
      [], env="ALLOWED_HOSTS"),
    S("trusted_proxies", "access", "network", "list", "מתווכים מהימנים", "Trusted proxies",
      "כתובות (או טווחים) של שרתים שמעבירים אלינו את כתובת המשתמש, כמו Caddy. מאחרים לא מאמינים לכתובת שהם שולחים.",
      "Addresses (or ranges) of servers that pass on the user's address, such as Caddy. Anyone else's claim is ignored.",
      ["127.0.0.1", "::1"], env="TRUSTED_PROXIES", sensitive=True),
    S("session_hours", "access", "chat-login", "int", "משך כניסה לצ'אט", "Chat sign-in lasts",
      "אחרי כמה זמן עובד צריך להיכנס שוב.", "How long until an employee has to sign in again.", 12, min=1, max=720,
      unit_he="שעות", unit_en="hours"),
    S("lock_after", "access", "lockout", "int", "נעילת חשבון אחרי", "Lock an account after",
      "סיסמאות שגויות ברצף עד שהחשבון ננעל.", "Wrong passwords in a row before the account locks.", 5, min=1, max=100,
      unit_he="ניסיונות", unit_en="tries"),
    S("lock_minutes", "access", "lockout", "int", "משך הנעילה", "Lock lasts", "כמה זמן חשבון נעול נשאר נעול.",
      "How long a locked account stays locked.", 15, min=1, max=1440, unit_he="דקות", unit_en="minutes"),
    S("login_ip_limit", "access", "lockout", "int", "חסימת כתובת אחרי", "Block an address after",
      "סיסמאות שגויות מאותה כתובת, בכל השמות יחד (כולל סיסמת המנהל), עד שהכתובת נחסמת.",
      "Wrong passwords from one address, across all names (admin password included), before that address is blocked.",
      10, min=1, max=1000, unit_he="כישלונות", unit_en="failures"),
    S("login_ip_minutes", "access", "lockout", "int", "חלון הספירה וזמן החסימה", "Counting window and block time",
      "בכמה דקות נספרים הכישלונות, וכמה זמן הכתובת מחכה.", "Over how many minutes failures count, and how long the address waits.",
      15, min=1, max=1440, unit_he="דקות", unit_en="minutes"),

    # 3. providers and keys
    *[x for p, name, url in (("anthropic", "Anthropic", "https://api.anthropic.com/v1/messages"),
                            ("openai", "OpenAI", "https://api.openai.com/v1/chat/completions"),
                            ("gemini", "Google", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"))
      for x in (
        S(f"{p}_api_key", "providers", p, "secret", f"מפתח {name}", f"{name} key",
          "נשמר מוצפן ולא מוצג שוב. ספק בלי מפתח לא עובד.", "Stored encrypted and never shown again. A provider without a key doesn't work.",
          "", env=f"{p.upper()}_API_KEY", sensitive=True),
        S(f"{p}_url", "providers", p, "url", "כתובת", "Address",
          "לאן השער שולח את השאלות. משנים רק כשהחברה מעבירה את התנועה דרך שרת ביניים משלה.",
          "Where the gateway sends questions. Change it only when the company routes traffic through its own intermediate server.",
          url, env=f"{p.upper()}_URL"))],
    S("local_base_url", "providers", "local", "url", "כתובת השרת", "Server address",
      "שרת Ollama או vLLM של החברה, למשל http://ollama:11434/v1. ריק = אין שרת. אחרי בדיקה, מוסיפים את המודלים שלו בעמוד המודלים.",
      "The company's Ollama or vLLM server, e.g. http://ollama:11434/v1. Empty = none. After a check, add its models on the Models page.",
      "", check="local_url"),
    S("local_api_key", "providers", "local", "secret", "מפתח לשרת", "Server key", "רק אם השרת דורש מפתח.",
      "Only if the server needs a key.", "", env="LOCAL_API_KEY", sensitive=True),
    S("local_loopback", "providers", "local", B, "מותר להתחבר למחשב הזה עצמו", "May connect to this machine itself",
      "כשהשרת המקומי מותקן על אותו מחשב כמו השער (localhost).", "When the local server runs on the gateway's own machine (localhost).",
      False, env="ALLOW_LOCAL_LOOPBACK", sensitive=True),
    S("extra_providers", "providers", "more-providers", "list", "ספקים נוספים", "More providers",
      "Azure, Bedrock, Vertex, Mistral, DeepSeek, Groq, xAI, OpenRouter, או כל שרת תואם-OpenAI עם כתובת ומפתח.",
      "Azure, Bedrock, Vertex, Mistral, DeepSeek, Groq, xAI, OpenRouter, or any OpenAI-compatible server with an address and key.",
      [], soon=True),
    S("models_refresh", "providers", "more-providers", "choice", "רענון רשימת המודלים מהספק", "Refresh the model list from the provider",
      "לקרוא מהספק אילו מודלים קיימים.", "Read which models the provider offers.", "manual", soon=True,
      options=O(("manual", "ידני", "Manual"), ("daily", "יומי", "Daily"))),

    # 4. models and routing
    S("default_model", "models", "default", "model", "מודל ברירת מחדל בצ'אט", "Default chat model",
      "המודל שנבחר בצ'אט כשעובד לא בחר, ומסומן למשתמש חדש.", "The model the chat uses when an employee picked none, and that a new user gets.",
      "fast"),
    S("max_output_tokens", "models", "default", "int", "אורך תשובה מרבי", "Longest answer",
      "אפליקציה שמבקשת יותר מקבלת את המספר הזה. 0 = לפי המודל: לא מגבילים (בצ'אט עם Claude נשלח 32,000, כי Claude דורש מספר).",
      "An app asking for more gets this number. 0 = by model: no limit (chat with Claude sends 32,000, because Claude needs a number).",
      8192, env="MAX_OUTPUT_TOKENS", min=0, max=1_000_000, unit_he="טוקנים", unit_en="tokens"),
    S("chat_cache", "models", "default", "choice", "מטמון של הספק בצ'אט", "Provider cache in chat",
      "Claude קורא שוב את השיחה מהמטמון בעשירית מהמחיר. שעה עולה יותר בכתיבה, וכדאית לשיחות עם הפסקות ארוכות.",
      "Claude re-reads the conversation from its cache at a tenth of the price. An hour costs more to write; worth it for chats with long pauses.",
      "5m", options=O(("off", "כבוי", "Off"), ("5m", "5 דקות", "5 minutes"), ("1h", "שעה", "1 hour"))),
    S("fallback_enabled", "models", "default", B, "מודל גיבוי כשספק נופל", "Backup model when a provider fails",
      "כבוי = אף מודל לא עובר לגיבוי שלו, גם אם הוגדר לו גיבוי בעמוד המודלים.",
      "Off = no model falls back to its backup, even if one is set on the Models page.", True),
    S("auto_enabled", "models", "auto", B, "בחירה אוטומטית", "Automatic choice",
      "עובד שבוחר \"אוטומטי\" בצ'אט: שאלות קצרות ופשוטות הולכות למודל הזול, וקוד, ניתוח, טקסט ארוך או שיחה ארוכה למודל החזק.",
      "An employee who picks \"Automatic\" in chat: short simple questions go to the cheap model; code, analysis, long text or a long chat to the strong one.",
      True),
    S("auto_cheap", "models", "auto", "model", "מודל זול", "Cheap model", "לשאלות קצרות ופשוטות.", "For short simple questions.", "fast"),
    S("auto_strong", "models", "auto", "model", "מודל חזק", "Strong model", "לקוד, ניתוח, השוואה וטקסט ארוך.",
      "For code, analysis, comparisons and long text.", "smart"),
    S("auto_prefer_fast", "models", "auto", B, "להעדיף את המודל המהיר", "Prefer the fast model",
      "בין המודלים המתאימים ובמחיר דומה, אצל כל ספק שמותר לעובד: זה שענה הכי מהר לאחרונה.",
      "Among suitable models at a similar price, at any provider the employee may use: the one that answered fastest lately.", False),
    S("fast_price_range", "models", "auto", "float", "טווח המחיר הדומה", "Similar-price range",
      "פי כמה לכאן או לכאן מחיר נחשב דומה.", "How many times higher or lower still counts as a similar price.", 2.0, min=1, max=20,
      unit_he="פי", unit_en="times"),
    S("fast_min", "models", "auto", "int", "מינימום תשובות", "Minimum answers",
      "מודל נחשב רק אם יש לו לפחות כמה תשובות בחלון.", "A model counts only with at least this many answers in the window.", 20,
      min=1, max=10000, unit_he="תשובות", unit_en="answers"),
    S("fast_window_hours", "models", "auto", "int", "חלון המדידה", "Measuring window", "על כמה שעות אחורה מודדים מהירות.",
      "How many hours back speed is measured.", 24, min=1, max=168, unit_he="שעות", unit_en="hours"),

    # 5. budgets and quotas
    S("soft_limit", "budgets", "budget", "int", "התראה מוקדמת", "Early warning",
      "באיזה אחוז מהתקציב מופיעה התראה בלוח הבקרה ובעמוד \"לטיפול\".", "At what share of the budget a warning shows on the dashboard and on \"To handle\".",
      80, min=1, max=100, unit_he="%", unit_en="%"),
    S("budget_exhausted", "budgets", "budget", "choice", "כשהתקציב נגמר", "When the budget runs out",
      "חסימה: הבקשות נדחות. התראה בלבד: הבקשות עוברות ונרשם אירוע. מעבר למודל זול: הבקשות עוברות למודל הזול של הבחירה האוטומטית, אם מותר; אחרת חסימה.",
      "Block: requests are refused. Alert only: requests go through and an event is recorded. Switch to the cheap model: requests go "
      "to the automatic choice's cheap model, if allowed; otherwise blocked.", "block", sensitive=True,
      options=O(("block", "חסימה", "Block"), ("alert", "התראה בלבד", "Alert only"), ("cheap", "מעבר למודל זול", "Switch to the cheap model"))),
    S("budget_reset_day", "budgets", "budget", "int", "יום איפוס התקציב", "Budget reset day",
      "באיזה יום בחודש מתחיל חודש תקציב חדש. גם הדוחות והחיוב הפנימי נספרים מהיום הזה. שינוי מחשב מחדש את ההוצאה של החודש הנוכחי מהיומן.",
      "The day of the month a new budget month starts. Reports and chargeback count from this day too. A change recalculates this month's spending from the log.",
      1, min=1, max=28, unit_he="בחודש", unit_en="of the month"),
    S("new_user_budget", "budgets", "new-user", "float", "תקציב חודשי", "Monthly budget",
      "מה שממולא מראש במשתמש חדש. ריק = השדה ריק ומחייב מילוי.", "Prefilled for a new user. Empty = the field starts empty and must be filled.",
      None, min=0, max=1_000_000, optional=True, unit_he="$", unit_en="$"),
    S("new_user_rpm", "budgets", "new-user", "int", "בקשות לדקה", "Requests per minute", "0 = ללא הגבלה.", "0 = no limit.", 0,
      min=0, max=100000),
    S("new_user_daily_tokens", "budgets", "new-user", "int", "טוקנים ליום", "Tokens per day", "0 = ללא הגבלה.", "0 = no limit.", 0,
      min=0, max=1_000_000_000),
    S("new_user_models", "budgets", "new-user", "models", "מודלים מותרים", "Allowed models",
      "בלי סימון = מודל ברירת המחדל בלבד.", "None ticked = the default model only.", []),
    S("max_concurrent", "budgets", "limits", "int", "שאלות במקביל לעובד", "Questions at once per person",
      "יותר מזה בבת אחת נדחה. מונע מאפליקציה תקועה לרוקן תקציב.", "More than this at once is refused. Stops a stuck app from draining a budget.",
      4, env="MAX_CONCURRENT", min=1, max=100),
    S("max_messages", "budgets", "limits", "int", "הודעות מרביות בבקשה", "Most messages in one request", "בקשה עם יותר הודעות נדחית.",
      "A request with more messages is refused.", 500, env="MAX_MESSAGES", min=1, max=100000),
    S("max_body", "budgets", "limits", "float", "גודל בקשה מרבי: העלאות ואפליקציות", "Largest request: uploads and apps",
      "מסמכים שמעלים, ובקשות של אפליקציות (שיכולות לכלול תמונות ו-PDF).", "Uploaded documents, and app requests (which may carry images and PDFs).",
      40.0, env="MAX_BODY", env_scale=1024 * 1024, min=1, max=500, unit_he="MB", unit_en="MB"),
    S("max_request_body", "budgets", "limits", "float", "גודל בקשה מרבי: כל השאר", "Largest request: everything else",
      "שאלות בצ'אט ושינויים במסך הניהול.", "Chat questions and admin changes.", 1.0, env="MAX_REQUEST_BODY", env_scale=1024 * 1024,
      min=0.1, max=100, unit_he="MB", unit_en="MB"),
    S("spike_factor", "budgets", "spike", "float", "קפיצת עלות: פי כמה מהרגיל", "Cost spike: times the usual",
      "התראה כשהשעה האחרונה של משתמש עלתה פי כמה מהשעה הממוצעת שלו בשבוע.", "Alert when a person's last hour cost this many times their average hour that week.",
      5.0, min=1, max=1000, unit_he="פי", unit_en="times"),
    S("spike_min", "budgets", "spike", "float", "קפיצת עלות: מינימום", "Cost spike: minimum",
      "שעה זולה מזה לא מתריעה, גם אם היא חריגה.", "An hour cheaper than this never alerts, even if unusual.", 5.0, min=0, max=100000,
      unit_he="$", unit_en="$"),

    # 6. security and policy
    S("policy_injection", "security", "policy", "choice", "ניסיון לעקוף את הוראות המודל", "Attempts to get around the model's instructions",
      "מה קורה לשאלה שמנסה לשחרר את המודל מהכללים שלו.", "What happens to a question trying to free the model from its rules.", "block",
      team=True, sensitive=True, options=O(("block", "חסימה", "Block"), ("log", "רישום בלבד", "Log only"))),
    S("policy_sensitive", "security", "policy", "choice", "מידע רגיש בשאלה", "Sensitive data in a question",
      "הסתרה: המידע מוחלף לפני שהשאלה יוצאת. מודל מקומי: השאלה נענית בלי הסתרה בשרת של החברה, אם יש מודל כזה לעובד; אחרת הסתרה.",
      "Hide: the data is replaced before the question leaves. Local model: answered unmasked on the company's server, if the person "
      "has such a model; otherwise hidden.", "mask", team=True, sensitive=True,
      options=O(("mask", "הסתרה", "Hide"), ("block", "חסימה", "Block"), ("log", "רישום בלבד", "Log only"),
                ("local", "שליחה למודל המקומי", "Send to the local model"))),
    S("mask_types", "security", "masking", "multi", "סוגי מידע רגיש", "Kinds of sensitive data",
      "מה מוסתר בשאלות לפני שהן יוצאות לספק, ובשמירה ביומן.", "What is hidden in questions before they leave for the provider, and in the log.",
      [v for v, _, _ in MASK_TYPES], team=True, sensitive=True, options=O(*MASK_TYPES)),
    S("org_terms", "security", "masking", "list", "מילים וביטויים של הארגון", "The organization's words and phrases",
      "שמות פרויקטים, לקוחות או קודים שאסור שיצאו. שורה לכל ביטוי; מוסתרים כמו מידע רגיש.",
      "Project names, customers or codes that must not leave. One per line; hidden like sensitive data.", [], team=True),
    S("scan_scope", "security", "policy", "choice", "היקף הסריקה", "What is scanned",
      "רק ההודעה האחרונה, או כל ההקשר: הוראות, תוצאות כלים והודעות קודמות.",
      "Only the last message, or the whole context: instructions, tool results and earlier messages.", "all", soon=True,
      options=O(("last", "ההודעה האחרונה", "The last message"), ("all", "כל ההקשר", "The whole context"))),
    S("request_files", "security", "policy", "choice", "קבצים בבקשה (תמונות, PDF, קול)", "Files in a request (images, PDF, audio)",
      "מה קורה לקבצים שעובד או אפליקציה שולחים למודל.", "What happens to files an employee or app sends to a model.", "check", soon=True,
      team=True, options=O(("allow", "לאפשר", "Allow"), ("block", "לחסום", "Block"), ("check", "לאפשר ולבדוק טקסט מתוך PDF", "Allow and check PDF text"))),
    S("warn_dangerous", "security", "answers", B, "אזהרה על פקודות מסוכנות בתשובות", "Warn about dangerous commands in answers",
      "פקודה שמוחקת מידע או מריצה קוד מהאינטרנט מקבלת אזהרה לעובד. האירוע נרשם בכל מקרה.",
      "A command that wipes data or runs code from the internet gets a warning for the employee. The event is recorded either way.", True,
      sensitive=True),
    S("warn_links", "security", "answers", B, "אזהרה על קישורים חשודים בתשובות", "Warn about suspicious links in answers",
      "קישור לכתובת מספרית, קיצור קישורים או שם שמתחזה לאתר מוכר מקבל אזהרה. האירוע נרשם בכל מקרה.",
      "A link to a numeric address, a link shortener or a look-alike name gets a warning. The event is recorded either way.", True,
      sensitive=True),
    S("mask_answer_secrets", "security", "answers", B, "הסתרת מפתחות בתשובות", "Hide keys in answers",
      "מפתח גישה או סיסמה שמופיעים בתשובה מוסתרים לפני שהם מגיעים לעובד, לאפליקציה וליומן.",
      "An access key or password in an answer is hidden before it reaches the employee, the app and the log.", True, sensitive=True),
    S("mcp_private", "security", "connections", B, "כתובות פנימיות לשרתי MCP", "Internal addresses for MCP servers",
      "מותר לחבר שרתי MCP שנמצאים ברשת החברה. כבוי = רק שרתים באינטרנט.",
      "MCP servers on the company network may be connected. Off = only servers on the internet.", True, env="ALLOW_PRIVATE_MCP",
      sensitive=True),
    S("source_roots", "security", "connections", "list", "תיקיות מותרות למקורות מידע", "Folders allowed for knowledge sources",
      "תיקייה בשרת שאפשר לחבר כמקור מידע חייבת להיות בתוך אחת מאלה (שורה לכל תיקייה). ריק = כל תיקייה.",
      "A server folder connected as a knowledge source must be inside one of these (one per line). Empty = any folder.", [],
      env="SOURCE_ROOTS", env_split=True, sensitive=True),
    S("key_expiry_warn_days", "security", "keys", "int", "התראה לפני שמפתח פג", "Warn before a key expires",
      "כמה ימים לפני תאריך התפוגה מופיעה התראה.", "How many days before the expiry date a warning shows.", 14, min=1, max=365,
      unit_he="ימים", unit_en="days"),
    S("key_max_age_days", "security", "keys", "int", "התראה על מפתח ישן", "Warn about an old key",
      "מפתח בשימוש יותר מזה מקבל המלצה להחליף.", "A key in use longer than this gets a replace recommendation.", 90, min=1, max=3650,
      unit_he="ימים", unit_en="days"),

    # 7. content, storage and encryption
    S("log_content", "data", "log", "choice", "מה נשמר ביומן", "What the log keeps",
      "שאלה ותשובה (עם המידע הרגיש מוסתר), או רק נתונים: מי, מתי, מודל, טוקנים ועלות, בלי הטקסט. חל על שאלות מכאן והלאה.",
      "Question and answer (with sensitive data hidden), or data only: who, when, model, tokens and cost, without the text. Applies from now on.",
      "full", options=O(("full", "שאלה ותשובה (מוסתרות)", "Question and answer (masked)"), ("metadata", "רק נתונים, בלי תוכן", "Data only, no content"))),
    S("log_files", "data", "log", "choice", "קבצים ביומן", "Files in the log", "מה נשמר על קובץ שנשלח למודל.",
      "What is kept about a file sent to a model.", "describe", soon=True,
      options=O(("describe", "תיאור בלבד (סוג, גודל, טביעת אצבע)", "Description only (type, size, fingerprint)"),
                ("thumb", "תיאור ותמונה מוקטנת", "Description and a thumbnail"))),
    S("backup_schedule", "data", "backup", "choice", "גיבוי אוטומטי", "Automatic backup",
      "עותק מלא של מסד הנתונים. גיבויים ישנים לא נמחקים לעולם.", "A full copy of the database. Old backups are never deleted.", "off",
      options=O(("off", "כבוי", "Off"), ("daily", "יומי", "Daily"), ("weekly", "שבועי", "Weekly"))),
    S("backup_folder", "data", "backup", "text", "תיקיית הגיבויים", "Backup folder",
      "שם של תיקייה ליד מסד הנתונים (אותיות באנגלית, ספרות, נקודה, מקף).", "A folder name next to the database (letters, digits, dot, dash).",
      "backups", max=64, pattern=r"[A-Za-z0-9._-]+"),

    # 8. knowledge sources
    S("search_mode", "sources", "search", "choice", "חיפוש במסמכים", "Searching documents",
      "לפי משמעות צריך מפתח של OpenAI או Google; בלעדיו נשאר חיפוש לפי מילים.",
      "By meaning needs an OpenAI or Google key; without one, search by words remains.", "both",
      options=O(("words", "לפי מילים", "By words"), ("meaning", "לפי משמעות", "By meaning"), ("both", "שניהם", "Both"))),
    S("embeddings", "sources", "search", "choice", "ספק החיפוש לפי משמעות", "Provider for search by meaning",
      "מי ממיר את הטקסט למספרים שמאפשרים חיפוש לפי משמעות. אוטומטי = הראשון שיש לו מפתח.",
      "Who turns text into the numbers that make search by meaning work. Automatic = the first one with a key.", "auto", env="EMBEDDINGS",
      options=O(("auto", "אוטומטי", "Automatic"), ("openai", "OpenAI", "OpenAI"), ("gemini", "Google", "Google"), ("off", "כבוי", "Off"))),
    S("max_file_mb", "sources", "search", "int", "גודל קובץ מרבי", "Largest file", "קובץ גדול מזה לא נקלט.",
      "A larger file isn't taken in.", 5, min=1, max=100, unit_he="MB", unit_en="MB"),
    S("top_k", "sources", "search", "int", "קטעים שנשלחים למודל", "Passages sent to the model",
      "כמה קטעים מהמסמכים מצורפים לכל שאלה, לכל היותר.", "At most how many document passages go with each question.", 6, min=1,
      max=50, unit_he="קטעים", unit_en="passages"),

    # 9. alerts and reports
    S("summary_enabled", "alerts", "summary", B, "שליחה אוטומטית", "Send automatically",
      "סיכום של החודש שעבר: הוצאה, צוותים, משתמשים, מודלים, המלצות לחיסכון ואבטחה.",
      "A summary of last month: spending, teams, users, models, savings recommendations and security.", False),
    S("summary_recipients", "alerts", "summary", "emails", "נמענים", "Recipients", "כתובות מייל, מופרדות בפסיק. עד 50.",
      "Email addresses, separated by commas. Up to 50.", []),
    S("summary_day", "alerts", "summary", "int", "יום השליחה", "Sending day", "באיזה יום בחודש נשלח הסיכום.",
      "The day of the month the summary goes out.", 1, min=1, max=28, unit_he="בחודש", unit_en="of the month"),
    S("summary_hour", "alerts", "summary", "int", "שעת השליחה", "Sending hour", "מהשעה הזו והלאה, לפי אזור הזמן.",
      "From this hour on, in the chosen time zone.", 8, min=0, max=23, unit_he=":00", unit_en=":00"),
    S("smtp_host", "alerts", "smtp", "text", "כתובת שרת הדואר", "Mail server address", "ריק = לא נשלח מייל.",
      "Empty = no email is sent.", "", env="SMTP_HOST", max=255),
    S("smtp_port", "alerts", "smtp", "int", "פורט", "Port", "587 עם STARTTLS, ‏465 עם SSL.", "587 with STARTTLS, 465 with SSL.", 587,
      env="SMTP_PORT", min=1, max=65535),
    S("smtp_user", "alerts", "smtp", "text", "שם משתמש", "User name", "אם השרת דורש כניסה.", "If the server needs a sign-in.", "",
      env="SMTP_USER", max=255),
    S("smtp_password", "alerts", "smtp", "secret", "סיסמה", "Password", "נשמרת מוצפנת ולא מוצגת שוב.", "Stored encrypted and never shown again.",
      "", env="SMTP_PASSWORD", sensitive=True),
    S("smtp_from", "alerts", "smtp", "text", "כתובת השולח", "Sender address", "ריק = שם המשתמש.", "Empty = the user name.", "",
      env="SMTP_FROM", max=255),
    S("smtp_tls", "alerts", "smtp", "choice", "הצפנה", "Encryption", "בלי הצפנה רק לשרת דואר בתוך הרשת.",
      "No encryption only for a mail server inside the network.", "1", env="SMTP_TLS",
      options=O(("1", "STARTTLS (פורט 587)", "STARTTLS (port 587)"), ("ssl", "SSL (פורט 465)", "SSL (port 465)"), ("0", "בלי הצפנה", "None"))),
    S("alert_channels", "alerts", "outbound", "list", "ערוצי התראה", "Alert channels",
      "מייל, Slack או Teams: כתובת שאליה השער שולח הודעה.", "Email, Slack or Teams: an address the gateway sends a message to.", [], soon=True),
    S("alert_kinds", "alerts", "outbound", "multi", "אילו התראות לשלוח החוצה", "Which alerts go out", "מה נשלח לערוצים.",
      "What is sent to the channels.", ["budget", "security"], soon=True,
      options=O(("budget", "תקציב", "Budget"), ("security", "אבטחה", "Security"), ("spike", "קפיצת עלות", "Cost spike"),
                ("slow", "ספק איטי", "Slow provider"), ("key", "מפתח פג", "Key expiring"))),
    S("slow_factor", "alerts", "speed", "float", "איטי פי כמה מהרגיל", "Slower than usual by",
      "התראה כשזמן התשובה בשעה האחרונה (95% מהתשובות) ארוך פי כמה מהשבוע שלפני.",
      "Alert when the last hour's answer time (95% of answers) is this many times the week before.", 2.0, min=1, max=100,
      unit_he="פי", unit_en="times"),
    S("slow_min", "alerts", "speed", "int", "מינימום תשובות בשעה", "Minimum answers in the hour", "פחות תשובות מזה לא מתריעות.",
      "Fewer answers than this never alert.", 10, min=1, max=100000, unit_he="תשובות", unit_en="answers"),
    S("simple_tokens_in", "alerts", "savings", "int", "שאלה קצרה: טוקנים נכנסים", "Short question: tokens in",
      "עד כמה טוקנים נכנסים שאלה נחשבת קצרה.", "Up to how many tokens in a question counts as short.", 2000, min=1, max=1_000_000,
      unit_he="טוקנים", unit_en="tokens"),
    S("simple_tokens_out", "alerts", "savings", "int", "שאלה קצרה: טוקנים יוצאים", "Short question: tokens out",
      "עד כמה טוקנים בתשובה.", "Up to how many tokens in the answer.", 600, min=1, max=1_000_000, unit_he="טוקנים", unit_en="tokens"),
    S("savings_min", "alerts", "savings", "float", "חיסכון מינימלי להצגה", "Smallest saving shown", "המלצה שחוסכת פחות בחודש לא מוצגת.",
      "A recommendation saving less a month isn't shown.", 5.0, min=0, max=100000, unit_he="$", unit_en="$"),

    # 10-12. coming with the gateway plan's phases
    S("capabilities", "capabilities", "capabilities", "multi", "יכולות מותרות", "Allowed capabilities", "מה מותר לשלוח לספקים.",
      "What may be sent to providers.", ["images", "audio", "files", "batch", "embeddings", "video"], soon=True, team=True,
      options=O(("images", "תמונות", "Images"), ("audio", "קול", "Audio"), ("files", "קבצים", "Files"), ("batch", "עיבוד במנות", "Batch"),
                ("embeddings", "הטמעות", "Embeddings"), ("video", "וידאו", "Video"))),
    S("builtin_tools", "capabilities", "tools", "multi", "כלים מובנים של הספקים", "Providers' built-in tools", "כלים שהמודל מפעיל בעצמו.",
      "Tools the model runs by itself.", ["web_search", "file_search", "code", "mcp"], soon=True,
      options=O(("web_search", "חיפוש באינטרנט", "Web search"), ("file_search", "חיפוש בקבצים", "File search"), ("code", "הרצת קוד", "Code execution"),
                ("mcp", "MCP", "MCP"), ("computer", "שליטה במחשב", "Computer use"))),
    S("realtime_voice", "capabilities", "voice", B, "קול בזמן אמת", "Real-time voice", "שיחה קולית עם מודל, עם מגבלת דקות וחיבורים.",
      "Voice conversation with a model, with minute and connection limits.", False, soon=True),
    S("dev_tools", "devtools", "devtools", "multi", "כלים מותרים", "Allowed tools", "כלי מפתחים שמותר להם לעבור דרך השער.",
      "Developer tools allowed through the gateway.", ["claude-code", "codex", "cursor", "copilot", "gemini-cli"], soon=True,
      options=O(("claude-code", "Claude Code", "Claude Code"), ("codex", "Codex", "Codex"), ("cursor", "Cursor", "Cursor"),
                ("copilot", "Copilot", "Copilot"), ("gemini-cli", "Gemini CLI", "Gemini CLI"))),
    S("dev_tool_detect", "devtools", "devtools", B, "זיהוי הכלי ביומן", "Record the tool in the log", "באיזה כלי השתמשו בכל בקשה.",
      "Which tool made each request.", True, soon=True),
    S("browser_extension", "browser", "browser", B, "תוסף הדפדפן", "Browser extension",
      "מעקב אחרי אתרי בינה מלאכותית ציבוריים מהדפדפן של העובדים.", "Watches public AI sites from employees' browsers.", False, soon=True),
    S("browser_sites", "browser", "browser", "list", "אתרים במעקב", "Watched sites", "שורה לכל אתר.", "One per line.",
      ["chatgpt.com", "claude.ai", "gemini.google.com", "copilot.microsoft.com", "perplexity.ai", "chat.deepseek.com"], soon=True),
    S("browser_action", "browser", "browser", "choice", "כשנמצא מידע רגיש", "When sensitive data is found", "מה התוסף עושה.",
      "What the extension does.", "policy", soon=True,
      options=O(("mask", "הסתרה", "Hide"), ("warn", "אזהרה", "Warn"), ("block", "חסימה", "Block"), ("policy", "לפי מדיניות האבטחה", "Follow the security policy"))),
    S("browser_report", "browser", "browser", "choice", "מה מדווח לשער", "What is reported to the gateway", "כמה פרטים התוסף שולח.",
      "How much the extension sends.", "found", soon=True,
      options=O(("found", "רק מה נמצא ומה נעשה", "Only what was found and done"), ("text", "גם הטקסט כשחוק הופעל", "Also the text when a rule fired"))),
    S("browser_unapproved", "browser", "browser", "list", "אתרים לא מאושרים", "Unapproved sites", "מפנים לצ'אט של החברה.",
      "Redirected to the company chat.", [], soon=True),
    S("browser_notice", "browser", "browser", B, "להציג לעובד שהניטור פעיל", "Tell the employee monitoring is on",
      "נעול על פעיל בגלל דרישות החוק.", "Locked on, as the law requires.", True, soon=True),
]
BY_KEY = {d["key"]: d for d in REGISTRY}
LIST_TYPES = ("list", "emails", "multi", "models")
TRUE = ("1", "true", "yes", "on")
ENCRYPT = DECRYPT = lambda s: s  # gateway.py puts its own encryption here
CHECKS = {}  # name -> fn(value) returning the value or raising ValueError; gateway.py fills: "local_url", "model", "enabled_model"
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
HOST = re.compile(r"^(?=.{1,253}$)[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$")

_cache = {"db": {}, "teams": {}, "loaded": False}


class Invalid(ValueError):
    def __init__(self, code, **info):
        super().__init__(code)
        self.info = {"code": code, **info}


def env_value(d):
    """The value the server's environment / .env sets for this setting, or None. An empty variable counts as not set."""
    raw = os.environ.get(d["env"], "").strip() if d["env"] else ""
    if not raw:
        return None
    t = d["type"]
    try:
        if t == B:
            return raw.lower() in TRUE
        if t == "int":
            return int(raw)
        if t == "float":
            return float(raw) / d.get("env_scale", 1)
        if t in LIST_TYPES:
            parts = raw.replace(os.pathsep, ",").split(",") if d.get("env_split") else raw.split(",")
            return [p.strip() for p in parts if p.strip()]
        if d["key"] == "smtp_tls":
            return "ssl" if raw.lower() == "ssl" else "0" if raw.lower() in ("0", "false", "no", "off") else "1"
        if t == "choice":
            return raw.lower() if raw.lower() in [o["value"] for o in d["options"]] else None
        return raw
    except ValueError:
        return None  # unreadable: the screen or the default decides


def to_db(d, v):
    if d["type"] == B:
        return "1" if v else "0"
    if d["type"] in LIST_TYPES:
        return json.dumps(v, ensure_ascii=False)
    if d["type"] == "secret":
        return ENCRYPT(v) if v else ""
    return "" if v is None else str(v)


def from_db(d, raw):
    t = d["type"]
    if t == B:
        return raw.strip().lower() in TRUE
    if t == "int":
        return int(float(raw))
    if t == "float":
        return None if raw == "" and d.get("optional") else float(raw)
    if t in LIST_TYPES:  # JSON; the older monthly-summary recipients were saved as "a, b"
        return json.loads(raw) if raw.startswith("[") else [x.strip() for x in raw.split(",") if x.strip()]
    if t == "secret":
        return DECRYPT(raw) if raw else ""
    return raw


def refresh(c):
    """Reload the saved values (one query each for global and team values). gateway.db() calls it on every connection."""
    keys = list(BY_KEY)
    rows = c.execute(f"select key, value from settings where value is not null and key in ({','.join('?' * len(keys))})", keys).fetchall()
    got = {}
    for k, raw in rows:
        try:
            got[k] = from_db(BY_KEY[k], raw)
        except (ValueError, TypeError):
            pass  # unreadable: the default decides
    teams = {}
    for team, k, raw in c.execute("select team, key, value from team_settings where value is not null"):
        if k in BY_KEY and BY_KEY[k]["team"]:
            try:
                teams[(team, k)] = from_db(BY_KEY[k], raw)
            except (ValueError, TypeError):
                pass
    _cache.update(db=got, teams=teams, loaded=True)


def lookup(key, team=None):
    """(value, source): source is "env", "team", "db" or "default"."""
    d = BY_KEY[key]
    v = env_value(d)
    if v is not None:
        return v, "env"
    if team and d["team"] and (team, key) in _cache["teams"]:
        return _cache["teams"][(team, key)], "team"
    if key in _cache["db"]:
        return _cache["db"][key], "db"
    return (list(d["default"]) if isinstance(d["default"], list) else d["default"]), "default"


def get(c, key, team=None):
    """The value in effect: the environment, else the team's own value (if the setting allows one), else the saved value,
    else the default. c (a database connection) is used only to load the values the first time."""
    if not _cache["loaded"] and c is not None:
        refresh(c)
    return lookup(key, team)[0]


def team_overrides():
    """{(team, key): value} for the team values in effect."""
    return dict(_cache["teams"])


def validate(d, v):
    """The value cleaned up, or Invalid(code, ...) saying why not (the screen turns the code into a sentence)."""
    t = d["type"]
    if t == B:
        if not isinstance(v, bool):
            raise Invalid("type")
        return v
    if t in ("int", "float"):
        if d.get("optional") and (v is None or v == ""):
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float, str)):
            raise Invalid("number")
        try:
            n = float(v)
        except ValueError:
            raise Invalid("number")
        if t == "int":
            if n != int(n):
                raise Invalid("integer")
            n = int(n)
        if n != n or n in (float("inf"), float("-inf")):
            raise Invalid("number")
        if "min" in d and n < d["min"]:
            raise Invalid("min", min=d["min"])
        if "max" in d and n > d["max"]:
            raise Invalid("max", max=d["max"])
        return n
    if t == "choice":
        opts = {o["value"]: o for o in d["options"]}
        if v not in opts or opts[v].get("soon"):
            raise Invalid("choice")
        return v
    if t in LIST_TYPES:
        if isinstance(v, str):
            v = [x for x in re.split(r"[,;\s]+" if t == "emails" else r"\n", v)]
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            raise Invalid("list")
        v = list(dict.fromkeys(x.strip() for x in v if x.strip()))
        if len(v) > (50 if t == "emails" else 200):
            raise Invalid("too_many", max=50 if t == "emails" else 200)
        for x in v:
            if len(x) > 254:
                raise Invalid("too_long", item=x[:40])
            if t == "emails" and not EMAIL.match(x):
                raise Invalid("email", item=x)
            if t == "multi" and x not in [o["value"] for o in d["options"]]:
                raise Invalid("choice", item=x)
            if t == "models":
                _check("model", x, item=x)
        if d["key"] == "allowed_hosts":
            v = [x.lower() for x in v]
            bad = next((x for x in v if not HOST.match(x)), None)
            if bad:
                raise Invalid("host", item=bad)
        if d["key"] == "trusted_proxies":
            for x in v:
                try:
                    ipaddress.ip_network(x, strict=False)
                except ValueError:
                    raise Invalid("network", item=x)
        if d["key"] == "source_roots":
            bad = next((x for x in v if not os.path.isabs(x)), None)
            if bad:
                raise Invalid("absolute", item=bad)
        return v
    if not isinstance(v, str):
        raise Invalid("type")
    v = v.strip()
    if t == "secret":
        if not v:
            raise Invalid("required")
        if len(v) < d.get("min", 1):
            raise Invalid("short", min=d["min"])
        if len(v) > 4096 or re.search(r"[\x00-\x1f]", v):
            raise Invalid("type")
        return v
    if len(v) > d.get("max", 2048):
        raise Invalid("length", max=d.get("max", 2048))
    if d.get("pattern") and not re.fullmatch(d["pattern"], v):
        raise Invalid("pattern")
    if t == "url" and v and not re.match(r"^https?://[^\s/]+", v):
        raise Invalid("url")
    if t == "timezone" and v:
        try:
            import zoneinfo
            zoneinfo.ZoneInfo(v)
        except (ValueError, KeyError, OSError, ImportError):  # unknown name, or no time zone data on this server
            raise Invalid("timezone")
    if d["key"] == "smtp_from" and v and not EMAIL.match(v):
        raise Invalid("email", item=v)
    if t == "model":
        _check("enabled_model" if d["key"] == "default_model" else "model", v)
    if d.get("check"):
        v = _check(d["check"], v)
    return v


def _check(name, v, **info):
    try:
        return CHECKS[name](v) if name in CHECKS else v
    except ValueError as e:
        raise Invalid(name, message=str(e), **info)


def public(d, value, source):
    """One setting as the screen gets it. A secret's value is never included: only whether it is set."""
    out = {k: v for k, v in d.items() if k not in ("check", "pattern", "env_scale", "env_split")}
    if d["type"] == "secret":
        out["default"] = None
        out["value"] = {"set": bool(value), "source": source}
    else:
        out["value"] = value
    out.update(source=source, card_he=CARDS[d["card"]][0], card_en=CARDS[d["card"]][1],
               changed=source == "db" and (bool(value) if d["type"] == "secret" else value != d["default"]))
    return out


if __name__ == "__main__":  # self-check: every setting is complete and its default passes its own validation
    for d in REGISTRY:
        assert d["section"] in [s[0] for s in SECTIONS] and d["card"] in CARDS, d["key"]
        assert all(d[k] for k in ("label_he", "label_en", "help_he", "help_en")), d["key"]
        if d["type"] not in ("secret", "model") and not d.get("check"):
            assert validate(d, d["default"]) == d["default"], d["key"]
    print("ok", len(REGISTRY))
