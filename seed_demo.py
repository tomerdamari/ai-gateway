"""Fills the gateway database with demo teams, users and 45 days of usage, so the screens have something to show.

Run: python seed_demo.py   (users and usage only into an empty database; demo sources only if there are none)
Every demo user's chat password is DEMO_PASSWORD below. Delete gateway.db to start clean.
"""
import json
import os
import random
import sys
import time

import gateway

# a public demo sets DEMO_PASSWORD (Render generates one); the fixed value is for local use only
DEMO_PASSWORD = gateway.os.environ.get("DEMO_PASSWORD") or "demo-pass-1"
TEAMS = {"מכירות": 150, "פיתוח": 600, "שירות לקוחות": 300, "הנהלה": 0}
# name, team, monthly budget, allowed models, how busy (requests per workday, roughly)
PEOPLE = [
    ("דנה כהן", "מכירות", 60, ["fast", "smart"], 9),
    ("רמי לוי", "מכירות", 40, ["fast", "gpt-fast"], 14),
    ("שירן מזרחי", "מכירות", 40, ["fast", "gemini-fast"], 5),
    ("נועה בר", "פיתוח", 200, list(gateway.MODELS), 22),
    ("יוסי אברהם", "פיתוח", 150, ["smart", "gpt-smart", "gemini-smart"], 16),
    ("עומר פרץ", "פיתוח", 120, ["smart", "gpt-smart"], 11),
    ("בוט תמיכה", "שירות לקוחות", 200, ["fast", "gpt-fast"], 60),
    ("מיכל דוד", "שירות לקוחות", 25, ["fast", "gemini-fast"], 8),
    ("אבי גולן", "הנהלה", 80, ["smart", "gpt-smart"], 4),
    ("demo", "פיתוח", 50, list(gateway.MODELS), 3),
]
QUESTIONS = ["סכם לי את הדוח הרבעוני", "נסח מייל ללקוח על עיכוב במשלוח", "תתרגם את המסמך לאנגלית",
             "מה ההבדל בין שתי ההצעות?", "כתוב פונקציה שממיינת רשימה", "תן לי רעיונות לפוסט ללינקדאין",
             "תבדוק את הקוד הזה ותמצא באגים", "נסח תשובה לפנייה של לקוח כועס", "הכן טבלת השוואה בין ספקים"]

DOCS = {
    "חופשה ומחלה.md": """# מדיניות חופשה

כל עובד במשרה מלאה זכאי ל-18 ימי חופשה בשנה. עובד חדש מתחיל לצבור ימי חופשה מהחודש השני.
אפשר להעביר עד 10 ימים שלא נוצלו לשנה הבאה. בקשת חופשה מגישים במערכת הנוכחות לפחות שבועיים מראש.

# ימי מחלה

יום מחלה ראשון ללא תשלום, השני והשלישי ב-50%, ומהרביעי ב-100%. מעל יומיים צריך אישור רופא.""",
    "החזר הוצאות.md": """# החזר הוצאות

נסיעה ברכב פרטי לצורכי עבודה: 2.3 ש"ח לק"מ. ארוחת עבודה עם לקוח: עד 250 ש"ח לאדם.
מגישים קבלות עד ה-5 לחודש העוקב, דרך טופס ההוצאות בפורטל. ההחזר משולם עם המשכורת.""",
    "עבודה מהבית.md": """# עבודה מהבית

אפשר לעבוד מהבית עד יומיים בשבוע, בתיאום עם המנהל הישיר. ימי שלישי הם ימי משרד לכל הצוותים.""",
}
PRICES = {"מחירון 2026.csv": """מוצר,מחיר חודשי,הערות
חבילה בסיסית,49 ש"ח,עד 3 משתמשים
חבילה עסקית,149 ש"ח,עד 20 משתמשים
חבילת ארגון,490 ש"ח,משתמשים ללא הגבלה
הנחה שנתית,15%,בתשלום מראש לשנה"""}
IT_DOCS = {
    "סיסמאות.md": """# מדיניות סיסמאות

סיסמה של לפחות 12 תווים, מתחלפת כל 90 יום. אסור לשתף סיסמאות. חובה אימות דו-שלבי לדואר ולמערכות הכספים.""",
    "ציוד.md": """# ציוד מחשוב

מחשב נייד מוחלף כל 3 שנים. תקלה בציוד מדווחים בפנייה למחלקת IT דרך הפורטל. זמן תגובה: עד יום עבודה.""",
}

c = gateway.db()
seed_people = not c.execute("select count(*) from accounts").fetchone()[0] or "--force" in sys.argv
if not c.execute("select count(*) from sources").fetchone()[0]:
    folder = os.environ.get("SEED_SOURCES_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources", "it")
    os.makedirs(folder, exist_ok=True)
    for name, text in IT_DOCS.items():
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write(text)
    with c:
        for team in TEAMS:  # the source access lists reference teams
            c.execute("insert or ignore into teams(name, budget, month) values (?,?,?)", (team, TEAMS[team], time.strftime("%Y-%m")))
        c.execute("insert into sources(name, description, kind, teams) values (?,?,?,?)",
                  ("נהלי החברה", "חופשה, מחלה, החזר הוצאות ועבודה מהבית", "upload", "*"))
        c.execute("insert into sources(name, description, kind, teams) values (?,?,?,?)",
                  ("מחירון", "מחירי החבילות והנחות", "upload", "מכירות,הנהלה"))
        c.execute("insert into sources(name, description, kind, path, teams) values (?,?,?,?,?)",
                  ("נהלי IT", "סיסמאות וציוד מחשוב", "folder", folder, "*"))
        for name, text in DOCS.items():
            gateway.sources.add_doc(c, "נהלי החברה", name, text)
        for name, text in PRICES.items():
            gateway.sources.add_doc(c, "מחירון", name, text)
        gateway.sources.sync_folder(c, "נהלי IT", folder)
    print("demo sources added: נהלי החברה (everyone), מחירון (sales + management), נהלי IT (folder, everyone)")
if not seed_people:
    if __name__ == "__main__":
        sys.exit("the database already has accounts; skipped demo users and usage (delete gateway.db, or run with --force)")
else:

    random.seed(7)
    now = time.time()
    month_start, _ = gateway.month_bounds()
    month = time.strftime("%Y-%m")
    pw_hash = gateway.hash_password(DEMO_PASSWORD)
    with c:
        for team, budget in TEAMS.items():
            c.execute("insert or ignore into teams(name, budget, month) values (?,?,?)", (team, budget, month))
            gateway.audit(c, "team-save", {"name": team, "budget": budget})
        for name, team, budget, models, _ in PEOPLE:
            c.execute("insert or ignore into accounts(name, team, models, budget, month, pw_hash) values (?,?,?,?,?,?)",
                      (name, team, ",".join(models), budget, month, pw_hash))
            gateway.audit(c, "create", {"name": name, "team": team, "budget": budget, "models": ",".join(models), "password": True})
        gateway.new_key(c, "בוט תמיכה")

        for day in range(45, -1, -1):
            when = now - day * 86400
            weekday = time.localtime(when).tm_wday  # Friday=4, Saturday=5: quiet days in Israel
            load = 0.15 if weekday in (4, 5) else 1.0
            for name, team, _, models, busy in PEOPLE:
                for _ in range(random.randint(0, round(busy * load * 1.6))):
                    alias = random.choice(models)
                    _, real, price_in, price_out = gateway.MODELS[alias]
                    t_in, t_out = random.randint(400, 9000), random.randint(150, 2500)
                    cost = (t_in * price_in + t_out * price_out) / 1e6
                    ts = when - random.randint(0, 9 * 3600)
                    if ts > now:
                        continue
                    q = random.choice(QUESTIONS)
                    c.execute("insert into logs(ts, name, team, model, tokens_in, tokens_out, cost, request, response) values (?,?,?,?,?,?,?,?,?)",
                              (ts, name, team, real, t_in, t_out, cost,
                               json.dumps([{"role": "user", "content": q}], ensure_ascii=False), "תשובת דוגמה לשאלה: " + q))
                    if ts >= month_start:
                        c.execute("update accounts set spent = spent + ? where name = ?", (cost, name))
                        c.execute("update teams set spent = spent + ? where name = ?", (cost, team))

        # a few budget situations worth seeing: one user near the limit, one blocked
        for name, ratio in (("רמי לוי", 0.86), ("מיכל דוד", 1.02)):
            spent = c.execute("select spent from accounts where name = ?", (name,)).fetchone()[0]
            if spent:
                c.execute("update accounts set budget = ? where name = ?", (round(spent / ratio, 2), name))

        for q in QUESTIONS[:4]:
            c.execute("insert into conversations values (?,?,?,?,?)",
                      (gateway.secrets.token_hex(8), "demo", q, now - random.randint(0, 5 * 86400),
                       json.dumps([{"role": "user", "content": q}, {"role": "assistant", "content": "תשובת דוגמה.", "model": "fast"}], ensure_ascii=False)))

    print(f"done: {len(TEAMS)} teams, {len(PEOPLE)} users, "
          f"{c.execute('select count(*) from logs').fetchone()[0]} logged requests. Chat login: any user name above, password in this file.")
