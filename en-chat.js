// English texts for the interface (see i18n.js)
window.EN = Object.assign(window.EN || {}, {
  // chat.html
  "FireGate · צ'אט": "FireGate · Chat",
  "FireGate · הצ'אט של החברה": "FireGate · Company chat",
  "שם משתמש": "Username",
  "סיסמה": "Password",
  "כניסה": "Sign in",
  "אין לך משתמש? פנה למנהל המערכת.": "No account? Ask your administrator.",
  "שיחות": "Chats",
  "אני": "Me",
  "בחירת השם שלי": "Pick my name",
  "שיחה חדשה": "New chat",
  "ניהול המערכת": "Admin",
  "עזרה ותיעוד": "Help & docs",
  "החלפת סיסמה": "Change password",
  "יציאה": "Sign out",
  "הצגה או הסתרה של התפריט": "Show or hide the menu",
  "במה אפשר לעזור?": "How can I help?",
  "השאלות נשמרות ומתועדות. מספרי תעודת זהות, כרטיסי אשראי ומפתחות גישה מוסתרים אוטומטית לפני שהם נשלחים.":
    "Questions are saved and logged. ID numbers, credit cards and access keys are hidden automatically before they are sent.",
  "השם שלי": "My name",
  "ההודעה שלך": "Your message",
  "כתבו הודעה… (Enter לשליחה, Shift+Enter לשורה חדשה)": "Write a message… (Enter to send, Shift+Enter for a new line)",
  "כתבו הודעה…": "Write a message…",
  "מודל": "Model",
  "שליחה": "Send",
  "סיסמה נוכחית": "Current password",
  "סיסמה חדשה (לפחות 8 תווים)": "New password (at least 8 characters)",
  "שמירה": "Save",
  "ביטול": "Cancel",

  // chat.js
  "Claude מהיר": "Claude fast",
  "Claude חכם": "Claude smart",
  "GPT מהיר": "GPT fast",
  "GPT חכם": "GPT smart",
  "Gemini מהיר": "Gemini fast",
  "Gemini חכם": "Gemini smart",
  "Claude הכי חזק": "Claude strongest",
  "GPT הכי חזק": "GPT strongest",
  "Gemini הכי חזק": "Gemini strongest",
  "התקציב החודשי שלך נגמר. הוא יתחדש ב-1 לחודש, או שאפשר לבקש הגדלה מהמנהל.":
    "Your monthly budget is used up. It resets on the 1st of the month, or you can ask your admin for more.",
  "התקציב החודשי של הצוות שלך נגמר. הוא יתחדש ב-1 לחודש, או שאפשר לבקש הגדלה מהמנהל.":
    "Your team's monthly budget is used up. It resets on the 1st of the month, or you can ask your admin for more.",
  "השאלה נחסמה כי היא נראית כמו ניסיון לעקוף את ההוראות של המודל. אם זו טעות, פנו למנהל המערכת.":
    "The question was blocked because it looks like an attempt to get around the model's instructions. If this is a mistake, ask your administrator.",
  "השאלה נחסמה כי יש בה מידע רגיש (כמו תעודת זהות, כרטיס אשראי, טלפון או מפתח גישה). הסירו אותו ונסו שוב.":
    "The question was blocked because it contains sensitive data (such as an ID number, credit card, phone number or access key). Remove it and try again.",
  "נגמרה המכסה היומית שלך. היא תתחדש מחר, או שאפשר לבקש הגדלה מהמנהל.":
    "You've used up your daily quota. It renews tomorrow, or you can ask your admin for more.",
  "כבר יש לך כמה שאלות שרצות במקביל. חכו שהן יסתיימו ונסו שוב.": "You already have several questions running at once. Wait for them to finish and try again.",
  "השיחה ארוכה מדי. פתחו שיחה חדשה.": "This chat is too long. Start a new chat.",
  "השאלה ארוכה מדי. קצרו אותה ונסו שוב.": "The question is too long. Shorten it and try again.",
  "בחרו את השם שלכם": "Pick your name",
  "ברוכים הבאים": "Welcome",
  "בחרו את השם שלכם כדי להתחיל. ההוצאה נרשמת על השם והצוות שבחרתם.":
    "Pick your name to start. Spending is charged to the name and team you pick.",
  "אוטומטי": "Automatic",
  "אוטומטי: זול או חזק לפי השאלה": "Automatic: cheap or strong, depending on the question",
  "אין כרגע מודל זמין": "No model available right now",
  "המודלים שמותרים לך כבויים כרגע. פנו למנהל המערכת.": "The models you may use are turned off right now. Ask your administrator.",
  "תקציב אישי החודש": "My budget this month",
  "תקציב הצוות": "Team budget",
  "שיחה": "Chat",
  "מחיקת השיחה": "Delete chat",
  "למחוק את השיחה?": "Delete this chat?",
  "השיחה תימחק מהרשימה שלך. העותק ביומן של המנהל נשאר.": "The chat is removed from your list. The admin's log keeps its copy.",
  "מחיקה": "Delete",
  "עוד אין שיחות": "No chats yet",
  "ארכיון": "Archive",
  "ארכיון שיחות": "Archived chats",
  "חזרה לשיחות": "Back to chats",
  "אין שיחות בארכיון": "No archived chats",
  "העברה לארכיון": "Move to archive",
  "שחזור השיחה": "Restore chat",
  "להעביר את השיחה לארכיון?": "Move this chat to the archive?",
  "השיחה תוסתר מהרשימה שלך. אפשר לשחזר אותה מהארכיון שבתפריט.": "The chat is hidden from your list. You can restore it from the archive in the side menu.",
  "חיפוש במסמכים:": "Search documents:",
  "מבוסס על:": "Based on:",
  "עצירה": "Stop",
  "יותר מדי ניסיונות שגויים. נסו שוב בעוד 15 דקות.": "Too many wrong tries. Try again in 15 minutes.",
  "שם משתמש או סיסמה שגויים": "Wrong username or password",
  "הסיסמה הוחלפה. מעבירים אותך לכניסה מחדש…": "Password changed. Taking you to sign in again…",
  "הסיסמה הנוכחית שגויה": "The current password is wrong",

  // ui.js
  "סגירת ההודעה": "Close notice",
  "אישור": "OK",
  "סגירת התפריט": "Close menu",

  // server: automatic model choice notes and the dangerous-answer warning (gateway.py, security.py)
  "שאלה ארוכה": "long question",
  "קוד, ניתוח או השוואה": "code, analysis or comparison",
  "שיחה ארוכה": "long chat",
  "שאלה קצרה ופשוטה": "short, simple question",
  "אזהרת אבטחה:": "Security warning:",
  "התשובה כוללת פקודה שעלולה למחוק מידע או להריץ קוד מהאינטרנט. אל תריצו אותה בלי לבדוק בדיוק מה היא עושה.":
    "The answer includes a command that could delete data or run code from the internet. Don't run it without checking exactly what it does.",
  "התשובה כוללת קישור חשוד (כתובת מספרית, קיצור קישורים או שם שמתחזה לאתר מוכר). אל תלחצו עליו בלי לבדוק לאן הוא מוביל.":
    "The answer includes a suspicious link (a numeric address, a link shortener or a name posing as a known site). Don't click it without checking where it leads.",

  // pages/mock.js (demo build)
  "זו תצוגת הדגמה, אין חיבור לשרתים": "This is a demo, there is no connection to servers",
});

// translate each part of a composite text; untranslated parts stay as they are
(() => {
const enPart = s => (typeof I18N !== "undefined" ? I18N.t(s) : s);
const enRoute = "(?:שאלה ארוכה|קוד, ניתוח או השוואה|שיחה ארוכה|שאלה קצרה ופשוטה)(?: \\(המודל המתאים לא זמין לך\\))?|גיבוי: .+ לא זמין";

// placed before the other pages' patterns so a general one (e.g. "מחיקת …") does not catch the chat's texts first
window.EN_PATTERNS = [
  [/^שלום (.+), במה אפשר לעזור\?$/, "Hi $1, how can I help?"],
  [/^שגיאה (\d+)$/, "Error $1"],
  [/^נשאר לך החודש (.+?)( · התקציב עומד להיגמר)?$/, (m, v, low) => `${v} left this month` + (low ? " · budget almost used up" : "")],
  [/^(.+) · צוות (.+)$/, "$1 · Team $2"],
  [/^צוות (.+)$/, "Team $1"],
  [/^מחיקת השיחה "(.*)"$/, (m, t) => `Delete chat "${t === "שיחה" ? "Chat" : t}"`],
  [/^העברת השיחה "(.*)" לארכיון$/, (m, t) => `Move chat "${t === "שיחה" ? "Chat" : t}" to the archive`],
  [/^שחזור השיחה "(.*)"$/, (m, t) => `Restore chat "${t === "שיחה" ? "Chat" : t}"`],
  [/^(.+) \/ דוגמה$/, "$1 / sample"],
  // answer header: model name · why that model
  [new RegExp(`^(.+) · (${enRoute})$`), (m, label, route) => `${enPart(label)} · ${enRoute2(route)}`],
  [new RegExp(`^(${enRoute})$`), (m, route) => enRoute2(route)],
  [/^(.+) \(בהדגמה: לא נשמר באמת\)$/, (m, t) => `${enPart(t)} (demo: not actually saved)`],
  ...(window.EN_PATTERNS || []),
];
function enRoute2(r) {
  const backup = r.match(/^גיבוי: (.+) לא זמין$/);
  if (backup) return `backup: ${enPart(backup[1])} unavailable`;
  const unavailable = r.endsWith(" (המודל המתאים לא זמין לך)");
  const base = unavailable ? r.slice(0, -" (המודל המתאים לא זמין לך)".length) : r;
  return enPart(base) + (unavailable ? " (the right model isn't available to you)" : "");
}
})();
