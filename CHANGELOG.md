# שינויים / Changelog

## 1.2.1 — 2026-10-06

- התפריט הצדדי צפוף יותר ונכנס במסך בלי גלילה, גם במחשב נייד (768 פיקסלים). במסכי מגע השורות נשארות בגודל של אצבע.

---

- The side menu is more compact and fits without scrolling, even on a laptop (768 px high). On touch screens rows stay finger-sized.

## 1.2.0 — 2026-10-06

**חדש: מסך הגדרות** (בתפריט, תחת "מערכת")
- כל ההגדרות של המערכת במקום אחד, ב-13 פרקים, עם חיפוש. כל הגדרה עם הסבר, ברירת מחדל וכפתור "חזרה לברירת מחדל".
- מספרים שהיו קבועים בקוד הם עכשיו הגדרות, עם אותן ברירות מחדל: סף התראה על תקציב, אורך תשובה, בקשות במקביל, נעילת חשבון, ספי התראות והמלצות ועוד.
- מפתחות ספקים וסיסמאות אפשר להזין במסך. הם נשמרים מוצפנים ולא מוצגים שוב. ערך מקובץ ההגדרות בשרת תמיד גובר, ומוצג נעול.
- כל שינוי נרשם ביומן השינויים החתום. שינוי רגיש מבקש אישור עם הערך הישן והחדש.
- הגדרות מיוחדות לצוות: מדיניות מידע רגיש, ניסיונות עקיפה, סוגי מידע רגיש ומילים של הארגון.
- ייצוא וייבוא הגדרות (בלי סודות), עם תצוגה של מה ישתנה לפני שמחילים.
- אפשרויות חדשות: יום איפוס התקציב, מה קורה כשהתקציב נגמר (חסימה, התראה או מעבר למודל זול), יומן בלי תוכן השאלות, כיבוי כל סוג מידע רגיש בנפרד, מילים וביטויים של הארגון להסתרה, שם הארגון, אזור זמן, שפת ברירת מחדל, עמוד הבית, גיבוי עכשיו וגיבוי מתוזמן, ובדיקת עדכונים.
- הכרטיסים שהיו מפוזרים (בחירה אוטומטית, מדיניות אבטחה, שרת מקומי, מייל חודשי) עברו למסך ההגדרות. בעמודים המקוריים נשארה שורה עם קישור.
- אפשרויות של השלבים הבאים (דפדפן, כלי מפתחים, ספקים נוספים) מוצגות "בקרוב".

---

**New: Settings screen** (in the menu, under "System")
- Every setting in one place, in 13 sections, with search. Each setting has an explanation, a default and "Back to default".
- Numbers that were fixed in code are now settings with the same defaults: budget alert threshold, answer length, parallel requests, account lock, alert and savings thresholds and more.
- Provider keys and passwords can be entered in the screen. They are stored encrypted and never shown again. A value in the server's settings file always wins and is shown locked.
- Every change is recorded in the signed change log. A sensitive change asks for confirmation with the old and new value.
- Per-team settings: sensitive-data policy, bypass attempts, sensitive-data types and organization terms.
- Settings export and import (without secrets), with a preview of what will change.
- New options: budget reset day, what happens when a budget runs out (block, alert, or switch to a cheap model), a log without question text, turning off each sensitive-data type, organization terms to hide, organization name, time zone, default language, home page, backup now and scheduled backups, and update check.
- The scattered cards (automatic choice, security policy, local server, monthly email) moved to the settings screen, with a link left on the original pages.
- Options for the next phases (browser, developer tools, more providers) are shown as "Coming soon".

## 1.1.0 — 2026-10-06

**חדש**
- המלצות לחיסכון: שאלות קצרות שנשלחות למודל יקר, צוות שמוציא כמעט הכל על המודל היקר ביותר, ומודל פעיל שאף אחד לא משתמש בו. בלוח הבקרה ובדף "לטיפול", עם כפתור פעולה לכל המלצה.
- סיכום חודשי במייל להנהלה: הוצאה מול החודש הקודם, צוותים ומשתמשים מובילים, הוצאה לפי מודל, חיסכון אפשרי ואירועי אבטחה. נשלח ב-1 לחודש, עם תצוגה מקדימה ושליחה ידנית בדף הדוחות. צריך להגדיר שרת דואר (SMTP_*).
- חיוב פנימי: מרכז עלות וחשבון הנהלת חשבונות לכל צוות, וקובץ חודשי (CSV או JSON) לייבוא להנהלת החשבונות.
- מודלים מותרים לצוות: עובד יכול להשתמש רק במודל שמותר גם לו וגם לצוות שלו, בכל מקום במערכת.
- מודלים בשרת החברה (Ollama או vLLM): חיבור, בדיקה והוספה של מודלים בדף המודלים, ומדיניות חדשה שבה שאלה עם מידע רגיש נענית במודל המקומי ולא יוצאת מהחברה.
- מעקב מהירות: זמן עד המילה הראשונה וזמן תשובה מלא לכל מודל, גרף לפי ספק, התראה כשספק איטי מהרגיל, ואפשרות להעדיף את המודל המהיר בבחירה האוטומטית.

**תיקונים**
- תקציב אישי 0 פירושו בלי תקרה אישית, כמו בצוות (קודם הוא חסם את החשבון).
- ניחושים של סיסמת המנהל מבחוץ נספרים במגבלת הסיסמאות השגויות לכל כתובת.
- הודעת הפתיחה בצ'אט מתאימה לכל מדיניות של מידע רגיש.
- התיעוד עבר בדיקה מלאה ומסודר לפי התפריט של מסך הניהול.

---

**New**
- Savings recommendations: short questions sent to an expensive model, a team spending nearly everything on the priciest model, and an enabled model nobody uses. On the dashboard and the "To handle" page, each with an action button.
- Monthly email summary for management: spend vs last month, top teams and users, spend by model, possible savings and security events. Sent on the 1st, with preview and send-now on the Reports page. Needs a mail server (SMTP_*).
- Chargeback: a cost center and an accounting account per team, and a monthly file (CSV or JSON) for import into accounting.
- Models allowed per team: an employee can use only a model allowed both to them and to their team, everywhere in the system.
- Models on the company's own server (Ollama or vLLM): connect, test and add models on the Models page, and a new policy where a question with sensitive data is answered by the local model and never leaves the company.
- Speed monitoring: time to first word and full answer time for each model, a chart per provider, an alert when a provider is slower than usual, and an option to prefer the faster model in automatic choice.

**Fixes**
- A personal budget of 0 means no personal cap, as for teams (it used to block the account).
- Wrong guesses of the admin password from outside count toward the per-address wrong-password limit.
- The chat's welcome message fits every sensitive-data policy.
- The documentation was fully reviewed and follows the admin menu.

## 1.0.5 — 2026-10-05

- מסך משתמש: לחיצה על שם של משתמש (בטבלת המשתמשים, במובילים בהוצאה, בלוג הטוקנים ובהתראות) פותחת את כל הפעילות שלו: הוצאה מול תקציב, צפי, בקשות וטוקנים, הוצאה יומית ב-30 הימים האחרונים, הוצאה לפי מודל, הבקשות האחרונות עם השאלה והתשובה, אירועי אבטחה ובקשות שנחסמו, היסטוריית שינויים ושיחות שמורות.
- התראה על קפיצה חריגה בהוצאה מובילה עכשיו למסך של אותו משתמש.

---

- User screen: clicking a user's name (in the users table, top spenders, the token log and alerts) opens all of their activity: spend against budget, projection, requests and tokens, daily spend over the last 30 days, spend by model, recent requests with question and answer, security events and blocked requests, change history and saved chats.
- A cost-spike alert now leads to that user's screen.

## 1.0.4 — 2026-10-05

- הלוגו בלי ריבוע: רק השער והלהבה, באדום.

---

- The logo without the square: just the gate and the flame, in red.

## 1.0.3 — 2026-10-05

- הלוגו אדום.
- הצבע הראשי של הגרפים אדום כמו הלוגו, במקום הסגול. שאר הצבעים: ירוק, ענבר, ירוק כהה, ורוד וחום. נבדקו לעיוורי צבעים, בלי כחול ובלי סגול.
- בגרף "צפי ניצול התקציב" העמודות הרגילות אפורות, ורק מי שיחרוג מהתקציב צבוע בצבע אזהרה, כדי שהאדום של הגרפים לא יתבלבל עם חריגה.

---

- The logo is red.
- The main chart colour is red like the logo, instead of violet. The others: green, amber, dark green, pink and brown, checked for colour-blind readers, with no blue and no violet.
- In "Projected budget use" the normal columns are grey and only the ones that will go over budget carry a warning colour, so the charts' red isn't mistaken for an overrun.

## 1.0.2 — 2026-10-05

- צבעי הגרפים בלוח הבקרה חיים יותר, כמו בסלייט, ובלי כחול: סגול, ענבר, ירוק, ורוד, כתום וירוק כהה. הצבעים נבדקו כך שגם עיוורי צבעים מבדילים בין שכנים.
- המקטעים בלוח הבקרה בלי רקע משלהם, כמו בסלייט: האפור של הדף, מסגרת דקה וצל רך.
- "המשתמשים שהוציאו הכי הרבה" ו"צוותים מול תקציב" עברו לתחתית לוח הבקרה.

---

- Livelier dashboard chart colours, as in Slate, with no blue: violet, amber, green, pink, orange and dark green, checked so colour-blind readers can tell neighbours apart.
- Dashboard sections have no fill of their own, as in Slate: the page grey, a thin border and a soft shadow.
- "Top spenders" and "Teams vs. budget" moved to the bottom of the dashboard.

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
