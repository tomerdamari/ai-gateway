# שינויים / Changelog

## 1.0.0 — 2026-10-05

הגרסה הראשונה של FireGate: שער אחד שכל בקשה לבינה מלאכותית בחברה עוברת דרכו.

**שליטה ועלויות**
- משתמשים, אפליקציות וצוותים, עם תקציב חודשי אישי ותקציב צוות: התראה ב-80%, חסימה ב-100%, איפוס ב-1 לחודש.
- צפי לסוף החודש ותקציב מומלץ לכל משתמש וצוות.
- מכסת טוקנים יומית, מגבלת בקשות לדקה ומגבלת בקשות במקביל.
- דוחות חודשיים לפי צוות, משתמש ומודל, עם הורדה לאקסל.

**מודלים**
- Claude, GPT ו-Gemini מאחורי מפתח אחד של החברה.
- הפעלה וכיבוי של מודלים, מודל ברירת מחדל, בדיקת חיבור.
- מודל גיבוי כשספק לא זמין, בחירה אוטומטית בין מודל זול לחזק, ותמחור נפרד לטקסט מהמטמון של הספק.

**מקורות מידע**
- העלאת מסמכים (כולל PDF ו-Word), תיקייה בשרת, וחיבור לשרתי MCP.
- חיפוש לפי מילים ולפי משמעות, והרשאה לכל מקור לפי צוות.

**אבטחה**
- הצפנה במנוחה של שאלות, תשובות, שיחות והגדרות חיבור.
- הסתרת מידע רגיש לפני שליחה לספק: תעודות זהות, כרטיסי אשראי, סודות, טלפונים, מיילים, חשבונות בנק.
- חסימה של ניסיונות לעקוף את הוראות המודל (המנהל בוחר מדיניות).
- יומן שינויים חתום שמזהה כל שינוי או מחיקה, מספר מעקב לכל בקשה, ויומן בקשות שנחסמו.
- הגנה מניחוש סיסמאות, מקפיצת עלויות ומבקשות לכתובות פנימיות.
- בדיקות אוטומטיות ב-GitHub: בדיקות המערכת, חולשות ידועות, סודות שדלפו לקוד, וסריקת קונטיינר.

**נתונים**
- שום מידע לא נמחק: מה שמוציאים משימוש עובר לארכיון ואפשר לשחזר אותו.

**ממשק**
- מסך ניהול עם לוח בקרה וגרפים, מסך צ'אט לעובדים, ועמוד תיעוד.
- עברית ואנגלית, עם מעבר כיוון מלא, ומצב כהה.
- עיצוב בסגנון Slate.

---

The first release of FireGate: one gateway that every AI request in a company passes through.

**Control and cost**
- Users, apps and teams with personal and team monthly budgets: alert at 80%, block at 100%, reset on the 1st.
- Month-end projection and a suggested budget for every user and team.
- Daily token quota, per-minute rate limit and a cap on parallel requests.
- Monthly reports by team, user and model, with Excel download.

**Models**
- Claude, GPT and Gemini behind one company key.
- Turn models on and off, default model, connection test.
- Backup model when a provider is down, automatic choice between a cheap and a strong model, separate pricing for provider-cached text.

**Knowledge sources**
- Uploaded documents (including PDF and Word), a server folder, and MCP servers.
- Keyword and meaning search, with per-team access to each source.

**Security**
- Encryption at rest for questions, answers, chats and connection settings.
- Sensitive data masked before it reaches a provider: ID numbers, credit cards, secrets, phones, emails, bank accounts.
- Attempts to get around the model's instructions are blocked (the admin picks the policy).
- A hash-chained change log that detects any edit or deletion, a trace id on every request, and a log of blocked requests.
- Protection against password guessing, cost spikes and requests to internal addresses.
- Automatic GitHub checks: tests, known vulnerabilities, secrets leaked into the code, and a container scan.

**Data**
- Nothing is ever deleted: anything taken out of use goes to an archive and can be restored.

**Interface**
- Admin screen with a dashboard and charts, a chat screen for employees, and a documentation page.
- Hebrew and English with full direction switch, and dark mode.
- Slate-style design.
