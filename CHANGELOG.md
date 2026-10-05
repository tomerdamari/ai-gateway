# שינויים / Changelog

## 1.0.1 — 2026-10-05

- רשימות נפתחות בעיצוב חדש: חץ משלנו, ורשימה פתוחה ככרטיס מעוגל עם סימון ✓ (בכרום ובאדג').
- דף חדש "לטיפול" מתחת ללוח הבקרה: צעדים ראשונים ודורש טיפול, עם מספר הפריטים הפתוחים בתפריט.
- שמות המודלים האמיתיים (Claude Opus 5.5, GPT-6.1 Sol, Gemini 3.1 Pro…) במקום "Claude מהיר" / "Claude חכם". שם שהמנהל נתן בעצמו נשמר.
- "יומן שאלות" נקרא עכשיו "לוג טוקנים".
- כל הכפתורים באותו גובה, כולל כפתור השפה, שקיבל אייקון של גלובוס.
- התיעוד ברוחב מסך מלא.
- בלי צבע ברקע כשעוברים עם העכבר על שורות בטבלה.
- שדות שמתאימים את הכיוון לשפת ההקלדה מיושרים לימין כשהם ריקים.
- שורת "שאלו את הבינה" בלוח הבקרה מוסתרת בינתיים.
- בחירת תאריך בסגנון Slate: שדה עם אייקון לוח שנה, חלון חודש עם ימים עגולים, סימון היום, תצוגת שנים וכפתור ניקוי.
- בשדה קלט שבפוקוס רק צבע המסגרת מתכהה, בלי טבעת מסביב.
- סמן של יד במעבר מעל תיבות סימון.

---

- Redesigned dropdowns: our own arrow, and the open list as a rounded card with a ✓ mark (Chrome and Edge).
- New "To handle" page under the dashboard: getting started and needs attention, with the number of open items in the menu.
- Real model names (Claude Opus 5.5, GPT-6.1 Sol, Gemini 3.1 Pro…) instead of "Claude fast" / "Claude smart". A name the admin set is kept.
- "Question log" is now "Token log".
- All buttons share one height, including the language button, which got a globe icon.
- Documentation at full screen width.
- No background colour on table rows under the mouse.
- Fields that follow the typed language sit on the page's side while empty.
- The "Ask the AI" bar on the dashboard is hidden for now.
- Slate-style date picker: a field with a calendar icon, a month panel with round days, today marked, a year view and a clear button.
- A focused field only darkens its border, with no ring around it.
- A hand pointer over checkboxes.

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
