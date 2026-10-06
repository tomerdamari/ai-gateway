// English texts for the interface (see i18n.js)
window.EN = Object.assign(window.EN || {}, {
  "FireGate · תיעוד": "FireGate · Documentation",
  "תיעוד": "Documentation",
  "בעמוד הזה": "On this page",
});
window.EN_PATTERNS = (window.EN_PATTERNS || []).concat([
]);

// The documentation page: each block of prose replaced whole (CSS selector -> English inner HTML).
// Ids, anchors, code, commands and env names stay exactly as in docs.html.
window.EN_HTML = Object.assign(window.EN_HTML || {}, {
  "main.doc h1": `FireGate documentation`,

  "main.doc .lead": `Everything the system can do, organized by screen. Employees will find the chat screen here, managers the whole admin screen, and IT the installation and connecting apps.`,

  "main.doc .on-page": `
        <h2>On this page</h2>
        <div class="on-page-grid">
          <div><h3>Getting started</h3><ul>
            <li><a href="#about">What the gateway is</a></li>
            <li><a href="#install">Install and run</a></li>
          </ul></div>
          <div><h3>Employees</h3><ul>
            <li><a href="#chat">Chat screen</a></li>
          </ul></div>
          <div><h3>Admin screen</h3><ul>
            <li><a href="#overview">Dashboard</a></li>
            <li class="sub"><a href="#savings">Savings recommendations</a></li>
            <li><a href="#accounts">Users and keys</a></li>
            <li><a href="#teams">Teams and budgets</a></li>
            <li class="sub"><a href="#team-models">Models a team may use</a></li>
            <li><a href="#models">Models</a></li>
            <li class="sub"><a href="#backup">Backup model</a></li>
            <li class="sub"><a href="#auto">Automatic selection</a></li>
            <li class="sub"><a href="#cache">Provider-side cache</a></li>
            <li class="sub"><a href="#local">Models on the company's own server</a></li>
            <li class="sub"><a href="#speed">Speed monitoring</a></li>
            <li><a href="#sources">Knowledge sources</a></li>
            <li class="sub"><a href="#mcp">MCP connections</a></li>
            <li><a href="#reports">Reports</a></li>
            <li class="sub"><a href="#chargeback">Chargeback</a></li>
            <li class="sub"><a href="#summary">Monthly summary by email</a></li>
            <li><a href="#security">Security</a></li>
            <li class="sub"><a href="#policy">Blocking policy</a></li>
            <li class="sub"><a href="#encryption">Encryption and the encryption key</a></li>
            <li><a href="#logs">Logs</a></li>
            <li><a href="#archive">Archive</a></li>
          </ul></div>
          <div><h3>Technical</h3><ul>
            <li><a href="#hardening">Security checklist</a></li>
            <li class="sub"><a href="#security-settings">Server security settings</a></li>
            <li class="sub"><a href="#operator">Server operator checklist</a></li>
            <li><a href="#api">Connecting apps</a></li>
            <li><a href="#settings">Server settings</a></li>
            <li><a href="#limits">Known limitations</a></li>
          </ul></div>
        </div>`,

  "#about": `
        <h2>What the gateway is</h2>
        <p>FireGate is a gateway: a single point that all of the company's AI use passes through, whether it's employees in the chat or apps using a key. The gateway runs on the company's own server, holds the providers' keys (Anthropic, OpenAI, Google) and never hands them out to anyone.</p>
        <p>This is how every question is handled, in order:</p>
        <ol class="flow">
          <li><span><b>Identification:</b> who is asking. An employee is identified when signing in to the chat, an app by the key it was given.</span></li>
          <li><span><b>Permission:</b> whether they are allowed to use this model, and whether the model is turned on.</span></li>
          <li><span><b>Budget and rate:</b> whether they and their team still have budget left this month, and whether they haven't gone over their requests per minute.</span></li>
          <li><span><b>Protection:</b> ID numbers, credit cards and keys are hidden. A question that tries to override the model's instructions is blocked. That is the default, and the admin can change it to "log only" in the Security tab.</span></li>
          <li><span><b>Documents:</b> if the employee asked for it, the gateway searches the company's documents and attaches the relevant passages.</span></li>
          <li><span><b>Sending to the provider:</b> to the chosen model, or to its backup if the provider is unavailable.</span></li>
          <li><span><b>Logging:</b> who, when, which model, how many tokens, what it cost, and the question and answer themselves.</span></li>
        </ol>`,

  "#install": `
        <h2>Install and run</h2>
        <h3>On a server with Docker</h3>
        <pre>cp .env.example .env
docker compose up -d --build</pre>
        <p>Fill in the provider keys in <code>.env</code>. If you have a domain pointing at the server, put it in <code>SITE_ADDRESS</code> and the connection is encrypted automatically (HTTPS). Without a domain the connection is not encrypted and is suitable for the office network only.</p>
        <h3>Without Docker</h3>
        <pre>pip install --require-hashes -r requirements.txt
python gateway.py</pre>
        <p>The first command installs the packages the gateway needs: <code>cryptography</code> for encryption (together with <code>cffi</code> and <code>pycparser</code>, which it needs), and <code>pypdf</code> for reading PDFs. <code>requirements.txt</code> lists an exact version and a fingerprint of the file for each package, and pip refuses to install a file that doesn't match its fingerprint. Without <code>cryptography</code> the gateway doesn't start; without <code>pypdf</code> it starts but can't read PDFs. With Docker this installation happens on its own.</p>
        <p>The gateway reads the <code>.env</code> next to its files and comes up at <code>http://localhost:8080</code>.</p>
        <h3>Sample data and backup</h3>
        <ul>
          <li><code>python seed_demo.py</code> fills an empty system with sample teams, users, 45 days of usage and knowledge sources.</li>
          <li>All data lives in a single file, <code>gateway.db</code>. To copy it while it's running: <code>docker compose exec gateway python -c "import sqlite3; sqlite3.connect('/data/gateway.db').backup(sqlite3.connect('/data/backup.db'))"</code></li>
          <li><code>python test_gateway.py</code> runs all the tests against simulated providers, with no real money spent.</li>
        </ul>`,

  "#chat": `
        <h2>Chat screen</h2>
        <p>At <code>/chat</code>. The employee asks, and the gateway answers word by word.</p>
        <h3>Signing in</h3>
        <ul>
          <li><b>Standard:</b> a username and password given by the admin. After 5 wrong passwords the account is locked for 15 minutes. A sign-in lasts 12 hours, and the password can be changed from the menu.</li>
          <li><b>Open mode</b> (<code>OPEN_ACCESS=1</code>): on the office network there is no sign-in screen. The employee picks their name from the menu, and the browser remembers it. This mode does not work from outside.</li>
        </ul>
        <h3>Choosing a model</h3>
        <ul>
          <li>The list shows only the models the employee is allowed to use and that are turned on.</li>
          <li><b>"Automatic"</b> chooses by itself: a cheap model for short questions, a strong model for code, analysis, comparisons or long text. Next to each answer it says which model answered and why.</li>
          <li>If the chosen model is unavailable and a backup was set for it, the answer notes that the backup model answered.</li>
        </ul>
        <h3>Company documents</h3>
        <p>Below the message box are the sources the employee's team is allowed to search. Tick the ones to use. When an answer relies on documents, it shows "Based on" with the document names underneath.</p>
        <h3>More</h3>
        <ul>
          <li>Conversations are saved in a list on the side, and the employee can go back to them or move them to the archive. An archived conversation leaves the list but is not deleted: the "Archive" link at the top of the list shows it, with a restore button. Writing again in an archived conversation brings it back to the list. The copy in the admin log stays either way.</li>
          <li>At the bottom of the menu: how much of the budget the employee and their team have spent this month, and how much is left.</li>
          <li>An answer that includes a command that could delete data or run code from the internet gets a warning at its end.</li>
          <li>An answer can be stopped midway with the "Stop" button.</li>
        </ul>`,

  "#overview": `
        <h2>Dashboard</h2>
        <p>The gateway's main screen (<code>/</code>, and also <code>/admin</code>). From the office network it opens without a password; from outside only with <code>ADMIN_PASSWORD</code>.</p>
        <ul>
          <li><b>The "To handle" page</b> (in the menu, under the dashboard) gathers what waits for the admin, and the menu shows the number of open items next to it (savings recommendations included). It has three parts:</li>
          <li><b>First steps:</b> shown until the system is ready: connecting a provider, a team, a user and a first question, with a button for each step.</li>
          <li><b>Needs attention:</b> budget overruns (from 80% and from 100%), locked accounts, open security notes, and a provider answering slower than usual (see <a href="#speed">Speed monitoring</a>). When there is nothing, it says "All good".</li>
          <li><b>Savings recommendations:</b> all of them, each with an action button. See <a href="#savings">Savings recommendations</a>.</li>
          <li><b>Four numbers:</b> spend this month, forecast for the end of the month, requests, and active users. Each with the percentage change from the previous week or month.</li>
          <li><b>Charts:</b> daily spend over the last 30 days (hover to see the day), spend split by model, the users who spent the most, and teams against their budget.</li>
          <li><b>Cumulative spend this month:</b> a line that rises day by day, against the previous month and against the total of the team budgets, with a dashed line that continues the current pace to the end of the month.</li>
          <li><b>Budget usage forecast:</b> how many users will finish the month under half of their budget, close to it, or over it. Bars above 100% are colored as a warning.</li>
          <li><b>When people ask:</b> a heat map of requests by day of the week and hour over the last four weeks. Helps you see peak hours and plan rate limits.</li>
          <li><b>Monthly spend by team:</b> the last four months, each month split into the five largest teams and "Other".</li>
        </ul>
        <h3 id="savings">Savings recommendations</h3>
        <p>The gateway looks at the last 30 days for places where the same work could cost less. The dashboard shows the three biggest recommendations and the total that could be saved per month; the "To handle" page shows all of them. Three kinds:</p>
        <ul>
          <li><b>Short questions to a strong model:</b> a team (or an account without a team) sending short questions, up to 2,000 tokens in and 600 out, to a strong, expensive model. The gateway works out what the same questions would have cost on the same provider's cheap model (automatic choice's cheap model if it's from that provider, otherwise the provider's cheapest model that is on), with the same tokens and the same cache prices, and shows the difference per month. It appears only when the saving is at least $5 a month, and only when the team may use the cheap model. The button opens <a href="#auto">automatic choice</a>, which does exactly this in the chat.</li>
          <li><b>A team spending almost everything on the expensive model:</b> more than 80% of the team's spend goes to the provider's most expensive model. The recommendation suggests checking the model one step below; this saving can't be worked out in advance, since not all work suits a simpler model.</li>
          <li><b>A model that is on but unused:</b> on for more than 30 days with no question in the last 30. The button turns it off, after a confirmation. The default model is never listed.</li>
        </ul>
        <p>With less than 30 days of usage, the numbers are scaled up to a full month (under a week counts as a week, so one busy day doesn't look like a month).</p>`,

  "#accounts": `
        <h2>Users and keys</h2>
        <p>Every employee, app or customer is an account. Each account has:</p>
        <ul>
          <li>A <b>team</b>, a <b>monthly budget</b>, <b>allowed models</b> and a <b>requests-per-minute limit</b>.</li>
          <li>A <b>chat password</b> (optional) and/or an <b>API key</b> for apps. The key is shown only once, when it's created. The gateway keeps only a fingerprint of it (SHA-256): a one-way calculation that can't be turned back into the key. A new key can be issued, or a key revoked, in the edit window.</li>
          <li><b>Forecast</b>: how much the account will spend by the end of the month at the current pace. <b>Recommended budget</b>: the higher of the forecast and last month, plus 20%.</li>
          <li>The <b>"Apply"</b> button appears only when the budget needs to go up so the account won't be blocked. Before the change there is a confirmation showing the old and new amounts, and afterwards it can be undone.</li>
          <li><b>Moving to the archive:</b> the account disappears from the lists, its password and key stop working right away, and it is signed out on every device. Its history stays in the log and the reports. Restore it from the <a href="#archive">archive</a>, and the previous password and key work again. A new account can't be created with the name of an archived one: restore it instead.</li>
        </ul>
        <p>You can search by name or team, and sort by name, team, spend or forecast. On a phone each row is shown as a card.</p>
        <h3 id="user-page">A user's page</h3>
        <p>Clicking a user's name (in the users list, in the dashboard's top spenders table, in the token log, or "Details" on an alert about them) opens a page with everything they did:</p>
        <ul>
          <li><b>Numbers:</b> spend this month against the budget, the forecast to the end of the month, and requests and tokens this month.</li>
          <li><b>Charts:</b> daily spend over the last 30 days, and spend by model this month.</li>
          <li><b>Recent activity:</b> the last 100 requests. Clicking a question opens the question and the answer.</li>
          <li><b>Security:</b> their security events and their blocked requests. <b>Change history:</b> what was changed on their account and when. <b>Chats:</b> how many saved chats they have, and the titles of the latest ones.</li>
        </ul>
        <p>An archived user's page opens too, marked as archived. Each user has their own address (<bdi>#user=</bdi> followed by the name), so refresh and the Back button work. Keys and passwords are never shown on this page in any form.</p>`,

  "#teams": `
        <h2>Teams and budgets</h2>
        <ul>
          <li>Each team has a monthly budget. <b>0 = no cap</b> for the team.</li>
          <li>A question is blocked when the personal budget <b>or</b> the team budget runs out.</li>
          <li>On the 1st of each month spending resets to zero; the history stays in the log.</li>
          <li>The teams screen shows the forecast, the recommended budget, and the total of the team members' budgets, so you can see whether the team cap fits them.</li>
          <li><b>Cost center</b> and <b>GL account</b> (optional): they go into the <a href="#chargeback">chargeback</a> file, so accounting knows where to book each team's cost.</li>
          <li><b>Moving to the archive:</b> only for a team with no people in it, so nobody is suddenly left without a team. The team leaves the lists and the choices, and its budget and history are kept. An archived user whose team is archived comes back only after the team does.</li>
        </ul>
        <h3 id="team-models">Models a team may use</h3>
        <p>When editing a team you can check the models the team may use, for example "the legal team works only with Claude". Nothing checked means the team sets no limit. With models checked:</p>
        <ul>
          <li>Everyone in the team can use only models allowed <b>both</b> to them personally <b>and</b> to the team. A model allowed personally but not by the team is blocked (error 403), and the request is recorded on the "Security" tab with the reason "Model not allowed for the team".</li>
          <li>The chat's model list shows only what is really allowed. Automatic choice picks only from those, and a backup model the team may not use is never called: if the provider is down, the question fails instead of moving to another model.</li>
          <li>In a user's edit window, a checked model the team blocks gets a "Blocked by team policy" label.</li>
        </ul>`,

  "#models": `
        <h2>Models</h2>
        <p>All the models the gateway offers are managed from the screen, with no code editing and no restart.</p>
        <ul>
          <li><b>Turning on and off:</b> a model that is turned off is blocked for everyone immediately. Before turning it off you see how many accounts are allowed to use it, and afterwards it can be undone.</li>
          <li><b>Adding and editing:</b> an alias (what apps send), a display name, the provider, the exact name at the provider, and prices per million tokens: input, output, and from the cache.</li>
          <li><b>Default:</b> the model that is ticked for a new user. It can't be turned off or moved to the archive until another one is set.</li>
          <li><b>Connection test:</b> sends the provider a short question and shows whether the key and name work, and how long it took.</li>
          <li><b>Moving to the archive:</b> only when no account is allowed to use the model. An archived model works for no one, not even an app that sends its alias, and it can be restored.</li>
          <li><b>Charts:</b> daily spend by model, and share of requests against share of spend, to spot a model that is expensive per request.</li>
          <li>At the top, each provider shows whether it has a key in the <code>.env</code> file (and the company server: whether an address is saved for it).</li>
        </ul>
        <h3 id="backup">Backup model</h3>
        <p>For each model you can choose a backup model. If the provider is overloaded or not responding (errors 429, 5xx, 529), the question moves to the backup on its own and is charged at the backup's price. The log records that the backup answered, and the models screen shows how many times that happened this month. For apps, the backup only works between models with the same format: Claude with Claude, or GPT with Gemini.</p>
        <h3 id="auto">Automatic selection</h3>
        <p>Set a cheap model and a strong model, and turn it on. A long question (over 1,200 characters), code, analysis, comparison, planning, or a long conversation goes to the strong one; everything else to the cheap one. If the matching model isn't allowed for the employee, the other one is chosen. The screen shows how many questions were routed this month.</p>
        <p><b>"Prefer the fastest suitable model"</b> (off at first): once the cheap or the strong model is picked, the gateway also looks at the models the employee may use whose price (input plus output) is close: at most 2 times more expensive or 2 times cheaper, at any provider. Of those, it picks the one with the lowest median answer time over the last 24 hours. Only models that answered at least 20 times in those 24 hours count; if there are none, the usual choice stays. When a different model is picked for this reason, the employee sees "(the fastest suitable one)" next to the reason.</p>
        <h3 id="cache">Provider-side cache</h3>
        <p>In conversations with Claude, the gateway asks the provider to keep the start of the conversation, and on the next turn it is read at about a tenth of the price. OpenAI and Gemini do this on their own. The cost is calculated using each model's cache price, and the monthly savings are shown on the screen.</p>
        <h3 id="local">Models on the company's own server</h3>
        <p>A model running on the company's own server, with Ollama or vLLM (two programs that run open models such as Llama and Qwen and speak the same language as OpenAI). Questions never leave the company network, and there is no per-token charge.</p>
        <ul>
          <li><b>Connecting:</b> in the "Local model server" card on the Models page, type the server's address, for example <code>http://ollama:11434/v1</code> or <code>http://10.0.0.5:8000/v1</code>, and save. "Check connection" asks the server which models it has and lists them.</li>
          <li><b>Adding:</b> every model in the list has "Add model". It joins the model list with the provider "Company server", at price 0 (you can set an internal price under Edit), and from there you allow it for users and teams like any model. You can also create it by hand with "New model" and the provider "Company server".</li>
          <li><b>Use:</b> in the chat, and for apps through <code>/v1/chat/completions</code> (the OpenAI format), streaming included. Token counts come from the server's answer; a server that doesn't return them gets an estimate, about one token for every four characters, and the log says "estimated".</li>
          <li><b>Access key:</b> if the server needs a key, it goes only into the <code>LOCAL_API_KEY</code> server setting. It isn't stored in the database and isn't shown on screen.</li>
          <li><b>Which addresses are allowed:</b> internal-network addresses are allowed, since that's where the server lives. Link-local addresses (169.254.x.x) and cloud providers' information addresses are always blocked, as is anything that isn't http or https, and an address with a user name and password in it. The machine the gateway runs on (localhost) is blocked unless you set <code>ALLOW_LOCAL_LOOPBACK=1</code>, for example when Ollama is installed on the same machine without Docker. The check runs both when saving and on every connection, against the address the name points to at that moment, and redirects are not followed.</li>
          <li><b>Sensitive data:</b> you can have questions with sensitive data go to this model instead of being masked. See <a href="#policy">Blocking policy</a>.</li>
        </ul>
        <h3 id="speed">Speed monitoring</h3>
        <p>For every question the gateway records how long the whole answer took, and how soon the first word arrived (in a streamed answer; in a regular answer the two times are the same). The time is measured at the gateway, from sending to the provider until the end of the answer, so it includes the trip over the network. Failed questions are recorded with their error code, including a provider that didn't answer at all (502) or stopped answering midway (504).</p>
        <ul>
          <li><b>The "Response speed" card</b> on the Models page: a table per model over the last 24 hours or 7 days: median (half the answers are faster), 95% (only 5 in 100 answers are slower), time to first word, number of requests, and error rate. Next to it, a chart of the median by provider for each hour of the last 48.</li>
          <li><b>Alert:</b> when a model answered at least 10 times in the last hour, and 95% of its answers took more than 2 times the usual (its 95% over the 7 days before that hour), the "To handle" page shows "Provider X is slower than usual", with a link to the Models page, and the model is marked "Slower than usual now" in the table.</li>
          <li>Connection tests from the Models page and document indexing aren't counted.</li>
          <li>For scripts: <code>GET /admin/api/latency</code>, with the same admin access as the screen.</li>
        </ul>`,

  "#sources": `
        <h2>Knowledge sources</h2>
        <p>The company documents the chat searches and quotes from. For each source you choose which teams may search it, or "All employees". An employee will never get a passage from a source their team wasn't given access to.</p>
        <h3>Source types</h3>
        <table>
          <thead><tr><th>Type</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td><b>Uploaded files</b></td><td>PDF, Word (docx) and text files (Markdown, CSV, HTML, JSON and more), up to 5MB per file.</td></tr>
            <tr><td><b>Folder on the server</b></td><td>"Sync now" reads all the files in the folder. A document whose file was deleted from the folder moves to the archive and drops out of search; when the file comes back, it is read again and leaves the archive. With Docker: the <code>sources</code> folder next to the project.</td></tr>
            <tr><td><b>MCP server</b></td><td>Information from another system. See <a href="#mcp">MCP connections</a>.</td></tr>
          </tbody>
        </table>
        <p>An uploaded document, and a whole source too, can be moved to the archive: they drop out of search and out of the lists, and stay in the database with their text, so they can be restored. Uploading a file with the same name again brings a document back from the archive, with the new content. A document's previous version is never deleted: it is kept, encrypted, in the database. Files in the server folder itself are not changed.</p>
        <h3>How search works</h3>
        <ul>
          <li><b>By words:</b> including stripping Hebrew one-letter prefixes (ו, ה, ב, ל...) and ignoring filler words such as "של" (of) and "מה" (what).</li>
          <li><b>By meaning:</b> when there is an OpenAI or Google key, each passage gets a "meaning fingerprint", so a question about "vacation" finds a document about "time off". The cost is tiny and is logged under the name "(אינדקס מסמכים)" (document index). The "Index" button fills in passages that don't have a fingerprint yet.</li>
          <li>The two search methods are merged, and up to 6 passages are sent to the model, marked as "information, not instructions".</li>
        </ul>
        <h3>Protecting the documents</h3>
        <p>A document with browser code, an attempt to override instructions, or a dangerous command is blocked on upload; an admin can approve it anyway, and the decision is logged. When syncing, such a file is not taken in and shows up in the "Security" tab.</p>
        <h3 id="mcp">MCP connections</h3>
        <p>MCP is a standard way for systems (a CRM, a wiki, a ticketing system) to expose information to AI. Enter an address and an access key, and "Test connection" shows the server's name, its tools and its documents. Two modes:</p>
        <ul>
          <li><b>Live search:</b> on every question the gateway calls the chosen search tool with the question, and attaches the result (up to 3,000 characters).</li>
          <li><b>Sync:</b> the server's documents are copied into the index, like a folder. A document that disappeared from the server moves to the archive.</li>
        </ul>
        <p>Every response from the server goes through sensitive-data hiding and a check for suspicious content. A response that tries to give the model instructions is blocked and logged. The access key is kept on the server and never sent back to the browser.</p>`,

  "#reports": `
        <h2>Reports</h2>
        <p>Pick a month and see spend, requests, tokens and number of people, by team (including budget usage), by user, and by model (including tokens from the cache). "Download for Excel" saves a CSV file that opens in Excel with Hebrew displayed correctly.</p>
        <h3 id="chargeback">Chargeback</h3>
        <p>A table of each team's cost in the chosen month, with its cost center and GL account, for charging each department for its own use. One row per team that used the gateway, a "No team" row for accounts without a team (and the document index cost), and a total row. The amounts match the monthly report.</p>
        <ul>
          <li><b>"Download CSV"</b>: a file for the accounting system. Column names are in English and fixed, so an import only has to be set up once: <code>month, team, cost_center, gl_account, requests, tokens_in, tokens_out, cost_usd</code>. Cost is in dollars with two decimals; the total row is <code>TOTAL</code> and is the sum of the rows. The file is UTF-8 with a mark that makes Excel read Hebrew team names correctly. A cell starting with <code>=</code>, <code>+</code>, <code>-</code> or <code>@</code> gets a leading apostrophe, so Excel doesn't run it as a formula.</li>
          <li><b>"Download JSON"</b>: the same data for processing in a program.</li>
          <li>For scripts: <code>GET /admin/api/chargeback?month=2026-09&amp;format=csv</code> (or <code>format=json</code>), with the same admin access as the screen.</li>
          <li>The earlier "Download for Excel" report stays as it is: a file with headings in the interface language, easy to read.</li>
        </ul>
        <h3 id="summary">Monthly summary by email</h3>
        <p>An email to management on the 1st of every month, after 08:00 (server time), about the month before: total spend against the previous month, the five teams and five users who spent the most, spend by model, the savings total and the three biggest recommendations, security events by kind, how many requests were blocked, and who went over budget. The email is in Hebrew, right to left, with a plain-text version for mail readers without HTML.</p>
        <ul>
          <li>On the "Monthly summary by email" card on the reports screen: the recipients' addresses (separated by commas), a switch for automatic sending, "Preview" and "Send now" (for the month chosen at the top of the screen), and a line saying whether a mail server is set up.</li>
          <li>The mail server is set only in the server settings (see <a href="#settings">Server settings</a>). Its password is never stored in the database or sent to the browser; the screen only shows whether one is set up.</li>
          <li>Each month is sent once. Every sending (manual too) is recorded in the change log, and a month already sent isn't sent again automatically. If sending fails, an event is recorded on the "Security" tab and the gateway tries again the next hour, up to 3 times.</li>
          <li>The preview is shown inside a closed frame without scripts, and people's and teams' names appear as plain text only.</li>
        </ul>`,

  "#security": `
        <h2>Security</h2>
        <p>Every question from an employee or an app goes through the gateway before it reaches the provider, so this is where every question is checked and every record is kept. Below: what the gateway does on its own, what you set in the "Security" tab, and what you must know about encryption. The full list, topic by topic, is in the <a href="#hardening">security checklist</a>.</p>
        <h3>What the gateway does on its own</h3>
        <ul>
          <li><b>Hiding sensitive data in questions</b>, before they go out to the provider and before they are stored: keys and passwords, Israeli international bank account numbers (IBAN), credit cards (only numbers that pass the check-digit test of a real card), ID numbers (only with a correct check digit), phone numbers (mobile, landline, +972) and email addresses. Bank account and passport numbers are hidden only when a label next to them says what they are, because a bare number is usually something else.</li>
          <li><b>Hiding in answers:</b> keys and passwords only. In the chat the gateway holds the text back until the next space, so a key that arrives in several pieces is still caught. For apps, each piece of a streamed answer is checked.</li>
          <li><b>Detecting attempts to get around the model</b>, in Hebrew and English: "ignore your instructions", "pretend you have no limits", and requests to reveal the model's hidden instructions, keys or passwords. What happens to such a question is set in the <a href="#policy">blocking policy</a>.</li>
          <li><b>Documents are information, not instructions:</b> every document passage attached to a question is wrapped in markers and a line telling the model it is information, not instructions. Under the block policy, a passage that tries to give the model instructions is dropped, and the question itself goes ahead without it.</li>
          <li><b>Warnings in answers:</b> a command that could delete data or run code from the internet, and a suspicious link (an IP address instead of a site name, a site name written with look-alike letters, a link that runs code, a link-shortening service), get a warning for the employee and are logged as an event.</li>
          <li><b>The gateway's instructions don't leak:</b> an answer that repeats 60 or more characters of the instructions the gateway sends the model is hidden in the log and recorded as an event.</li>
          <li><b>Protection from other websites:</b> a hostile website an employee opens can't make their browser send commands to the gateway, and the gateway only answers to server names it knows.</li>
          <li><b>Keys are never exposed:</b> an app key is shown once, when it's created. The database keeps only a fingerprint of it: the result of a one-way calculation that can't be turned back into the key. The screens never receive keys, fingerprints or provider keys.</li>
          <li><b>Lockout:</b> 5 wrong passwords lock the account for 15 minutes, and 10 failed sign-ins from one address within 15 minutes block that address.</li>
          <li><b>A change log that can't be altered quietly:</b> each row is "signed" together with the row before it, so changing or deleting a row is detected.</li>
        </ul>
        <h3>The "Security" tab</h3>
        <p>Counts for the last 7 days, a "Status check" (encryption, admin password, keys with no rate limit, open mode, connected providers), "Policy", a check that the change log hasn't been altered, "Blocked requests" (the last 200, with the reason and a masked excerpt of the question), and "Security events" (the last 200) that can be filtered by type.</p>

        <h3 id="policy">Blocking policy</h3>
        <p>In the "Policy" card of the "Security" tab you choose what happens to a question that was caught. The setting applies to all accounts at once, and every change to it is recorded in the change log.</p>
        <table>
          <thead><tr><th>What was caught</th><th>The options</th></tr></thead>
          <tbody>
            <tr><td><b>An attempt to override the model's instructions</b> (prompt injection or jailbreak)</td><td><b>Block</b> ("Block the question", the default), or <b>log only</b> ("Send and record in the log").</td></tr>
            <tr><td><b>Sensitive data</b> (ID number, credit card, phone, email, keys and more)</td><td><b>Mask</b> ("Hide the data and send", the default), <b>block</b> ("Block the question"), <b>log only</b> ("Send without hiding and record in the log"), or <b>local model</b> ("Send to the local model").</td></tr>
          </tbody>
        </table>
        <p><b>"Send to the local model"</b> works only when there is a <a href="#local">model on the company's server</a> that is turned on. A question with sensitive data goes to it unmasked, instead of to the model the employee picked, but only if the employee may use it (the models their team may use included). The employee sees "sensitive data: answered by the local model" in the chat, and the "Security" tab records the event "Sensitive data answered by the local model". If the employee has no local model, the data is masked as usual. The unmasked question never reaches an outside provider: if the local model doesn't answer, its backup is used only if it is on the company server too. The log keeps the masked version of the question. Apps on the Claude format (<code>/v1/messages</code>) can't move to the local model, so for them the data is masked.</p>
        <p>A blocked question gets a refusal (code 403), and appears in the "Blocked requests" card with the reason. Questions about code and commands are never blocked, only logged, because employees legitimately ask about them.</p>

        <h3 id="encryption">Encryption and the encryption key</h3>
        <p>The gateway encrypts what is sensitive in the database, using a standard encryption method (AES-256-GCM) that also detects if anyone has altered the encrypted text:</p>
        <ul>
          <li><b>Encrypted:</b> the questions and answers in the log, saved chats (title and messages), knowledge-source settings including the access keys for MCP servers, excerpts from blocked requests, and excerpts in new security events.</li>
          <li><b>Not encrypted:</b> the document search index and its meaning fingerprints, so that search keeps working. Anyone who gets the database file can read the document passages in the index.</li>
        </ul>
        <p><b>Where the key lives:</b> in the <code>FIREGATE_DATA_KEY</code> setting in the <code>.env</code> file. If that is empty, in a file next to the database with the same name and the extension <code>.key</code> (with Docker: <code>/data/gateway.db.key</code>). If neither exists and the database isn't encrypted yet, the gateway creates a new key file and prints a prominent message telling you to back it up.</p>
        <p><b>Creating a key yourself</b> (paste the result into <code>FIREGATE_DATA_KEY</code>):</p>
        <pre>python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"</pre>
        <div class="warn-box" role="note">
          <p><b>Important before you go on</b></p>
          <ul>
            <li>Back up the key <b>separately</b> from the database backups. If the key and the backup are kept in the same place, whoever gets one gets both, and the encryption protects nothing.</li>
            <li><b>A lost key means lost data.</b> There is no back door: without the key the questions, answers and chats can never be read again.</li>
            <li>Once the database holds encrypted data, the gateway <b>refuses to start</b> without the key or with a different key, and prints why. This way a new key can't accidentally "bury" the old data.</li>
            <li>On the first start of the version with encryption, the gateway first copies the whole database to the <code>backups</code> folder next to it, and only then encrypts the existing rows. <b>That copy is not encrypted</b>: keep it somewhere encrypted, like any other backup.</li>
          </ul>
        </div>`,

  "#hardening": `
        <h2>Security checklist</h2>
        <p>Every topic on the security checklist, what the gateway does about it on its own, and what is left for the admin or whoever maintains the server. "—" means there is nothing to do.</p>
        <table>
          <thead><tr><th>Topic</th><th>What the system does</th><th>What the admin needs to do</th></tr></thead>
          <tbody>
            <tr class="group"><th colspan="3">3. Secrets management</th></tr>
            <tr><td>Storing keys and secrets securely</td><td>The provider keys live only in the <code>.env</code> file on the server. App keys are stored only as a fingerprint (SHA-256, a one-way calculation that can't be turned back into the key), and passwords with a deliberately slow method (PBKDF2) so they are hard to guess.</td><td>Keep <code>.env</code> only on the server, readable only by the server's administrator.</td></tr>
            <tr><td>Encryption at rest</td><td>"At rest" means data while it is stored on disk. Questions, answers, chats, source settings and the excerpts in the security logs are encrypted in the database. The search index is not. See <a href="#encryption">Encryption and the encryption key</a>.</td><td>Back up the encryption key separately from the database. Encrypting the server's whole disk (BitLocker, LUKS, or the cloud provider's disk encryption) adds a layer.</td></tr>
            <tr><td>Keeping secrets out of logs</td><td>Keys, passwords and sensitive numbers are hidden before the question is stored. The lines the server prints contain only the address, time, kind of request, the path without its parameters, the result code and the request number: never content, keys or sign-in cookies.</td><td>—</td></tr>
            <tr><td>Keeping secrets off the screens</td><td>The screens never receive keys, fingerprints of keys or passwords, provider keys or MCP access keys. The automated tests check this on every address a screen reads from.</td><td>—</td></tr>
            <tr><td>Rotating and revoking keys</td><td>A new key can be issued, or a key revoked, in the edit window, and given an expiry date: the key works until the end of that day and is refused after it (code 401). A new key starts with no expiry date. The dashboard warns when fewer than 14 days are left, or when a key has been in use for more than 90 days.</td><td>Replace a key when the alert appears. Rotate the provider keys from time to time, and immediately if <code>.env</code> may have leaked.</td></tr>

            <tr class="group"><th colspan="3">4. Gateway and API security</th></tr>
            <tr><td>SQL/NoSQL Injection</td><td>Slipping database commands into text a user sends. The gateway sends the database only fixed queries, with the values passed separately, so text never becomes a command. There is no NoSQL database.</td><td>—</td></tr>
            <tr><td>SSRF</td><td>Making the server contact an internal address on the attacker's behalf. The gateway contacts only the fixed providers, and the MCP servers and local model server an admin configured. Before every call to them the address is resolved to an IP address and checked: the server itself, local addresses and the cloud provider's internal information address are always blocked, and the gateway doesn't follow redirects to another address. (The local model server may be the server itself only with <code>ALLOW_LOCAL_LOOPBACK=1</code>.)</td><td>If all MCP servers are outside the internal network, set <code>ALLOW_PRIVATE_MCP=0</code>.</td></tr>
            <tr><td>Command Injection</td><td>Running operating-system commands through input. The gateway runs no system commands anywhere.</td><td>—</td></tr>
            <tr><td>Path Traversal</td><td>Reading files outside the allowed folder (for example with <code>../</code>). Site files are served from a fixed list. A folder used as a knowledge source must be a full path, inside <code>SOURCE_ROOTS</code> if it's set, and files can't escape it through shortcuts (links).</td><td>Set <code>SOURCE_ROOTS</code> to the document folders only (with Docker: <code>/sources</code>).</td></tr>
            <tr><td>Header Injection</td><td>Inserting a line break into the response headers to add a forged header. The gateway strips line breaks and control characters from every header it sends.</td><td>—</td></tr>
            <tr><td>Request Smuggling</td><td>"Smuggling" a second request inside the first, when the front door and the server disagree about where a request ends. A request with two length declarations, a request sent in pieces (chunked) or an invalid length is refused (code 400); a request that is too large is refused (code 413).</td><td>—</td></tr>
            <tr><td>CORS/CSRF</td><td>Another website making the employee's browser send commands to the gateway. The gateway never allows any other site to read from it (it sends no CORS headers), accepts commands only as JSON, and checks that they came from its own pages (by the Origin and Sec-Fetch-Site headers). It only answers to server names it knows.</td><td>Add every extra name that points at the gateway to <code>ALLOWED_HOSTS</code>.</td></tr>
            <tr><td>Broken Access Control</td><td>Reaching something without permission. An employee sees only their own chats, gets passages only from sources their team may use, and uses only the models allowed to them. An app key doesn't work in the chat. The admin screen from outside requires <code>ADMIN_PASSWORD</code>.</td><td>Set a strong <code>ADMIN_PASSWORD</code>, and turn off <code>OPEN_ACCESS</code> once there are real users.</td></tr>
            <tr><td>Mass Assignment</td><td>Sending extra fields in a request to change something forbidden, such as the spend or the key. Updating an account accepts only a fixed list of fields, and everything else is dropped.</td><td>—</td></tr>
            <tr><td>API Abuse</td><td>Excessive or unusual use of the gateway. Request size is limited, up to 500 messages per request, answers up to 8,192 tokens, up to 4 questions at once per account, a requests-per-minute limit, a budget and a daily quota. See <a href="#security-settings">Server security settings</a>.</td><td>Give every account a requests-per-minute limit and a budget. "Status check" shows keys with no rate limit.</td></tr>

            <tr class="group"><th colspan="3">5. AI-specific security</th></tr>
            <tr><td>Prompt Injection</td><td>Text that tries to make the model ignore its instructions. The gateway detects such attempts in Hebrew and English, and blocks or logs them according to the policy.</td><td>Choose a <a href="#policy">policy</a>. The default is block.</td></tr>
            <tr><td>Indirect Prompt Injection</td><td>The same, but the instructions are hidden in a document or in another system's response rather than in the question. A suspicious document is blocked on upload. Document passages are attached marked "information, not instructions", and a passage that tries to give instructions is dropped (under the block policy). An MCP server response that tries to give instructions is blocked.</td><td>Approve a blocked document only after reading it.</td></tr>
            <tr><td>Jailbreaks</td><td>Trying to talk the model into breaking its safety rules ("pretend you have no limits"). Detected and handled under the same policy.</td><td>—</td></tr>
            <tr><td>Tool/Function Call Abuse</td><td>Making the model trigger tools that take actions. The gateway itself never runs tools the model asks for. For an MCP connection the gateway calls only the tool the admin chose, with only the question, and refuses tools the server marks as changing data. An app that gives the model its own tools runs them on its side.</td><td>Choose a search tool only for each MCP connection.</td></tr>
            <tr><td>Malicious Files/URLs</td><td>A document with browser code, an attempt to override instructions or a dangerous command is blocked on upload (up to 5MB per file). A suspicious link in an answer (an IP address, a disguised site name, a link that runs code, a link shortener) gets a warning and is logged.</td><td>—</td></tr>
            <tr><td>Excessive Agent Permissions</td><td>An AI agent with permissions that are too broad. The gateway's only connection to other systems is MCP, limited to one tool the admin chose. Tools the server marks as changing data are refused, but a tool not marked that way is accepted.</td><td>Give the MCP server an access key with read-only permission, and only to what is needed.</td></tr>
            <tr><td>System Prompt Leakage</td><td>The model revealing the hidden instructions it was given. A request to reveal them is detected as an override attempt. An answer that repeats 60 or more characters of the gateway's instructions is hidden in the log and recorded as an event.</td><td>—</td></tr>
            <tr><td>Attempts to expose credentials</td><td>A request for keys or passwords is detected as an override attempt. The model never receives the gateway's keys. A key or password that appears in an answer is hidden before it reaches the employee, even when it arrives in pieces.</td><td>—</td></tr>

            <tr class="group"><th colspan="3">6. Data leakage</th></tr>
            <tr><td>Leaking PII and sensitive data</td><td>PII means information that identifies a person. ID numbers, credit cards, IBANs, phone numbers, emails and keys are hidden before the question goes out to the provider and before it is stored.</td><td>Choose a <a href="#policy">policy</a>. Use "send without hiding" only with good reason and a suitable agreement with the provider.</td></tr>
            <tr><td>Storing questions and answers</td><td>Kept with no time limit, after hiding, and encrypted. A chat an employee moves to the archive leaves only their list; the chat itself and the copy in the log stay.</td><td>—</td></tr>
            <tr><td>Unauthorized access to data</td><td>The token log is only on the admin screen. An employee sees only their own chats, and knowledge sources are limited by team. The content in the database is encrypted.</td><td>Protect <code>ADMIN_PASSWORD</code>, and never expose the gateway directly to the network (only through Caddy).</td></tr>
            <tr><td>Exposing data through logs</td><td>The excerpts kept from blocked requests and security events are up to 200 characters, after hiding, and encrypted. The lines the server prints contain no content.</td><td>—</td></tr>
            <tr><td>Sending data to AI providers</td><td>The provider receives only the question, after hiding, and the relevant document passages (up to 6). The provider never gets the gateway's keys or details about employees beyond what is written in the question.</td><td>Check each provider's terms on keeping data and using it for training, and choose providers accordingly.</td></tr>
            <tr><td>Complete data deletion</td><td>By the owner's decision, <b>nothing is ever deleted</b>. There is no way to delete questions, answers, logs or the change log. Users, teams, models, knowledge sources, documents and chats aren't deleted either: they move to the <a href="#archive">archive</a>, leave use, and can be restored. Instead of deletion, sensitive data is hidden before it is stored, what is stored is encrypted, and access to it is limited to the admin screen. What is deleted: chat sign-ins that expired or were signed out (they are only proof of sign-in, not data). And uploading a document again under the same name gives it the new content, while the previous version is kept, encrypted, in the database.</td><td>If a law, a customer or an employee requires deletion, know in advance that the system doesn't support it.</td></tr>

            <tr class="group"><th colspan="3">7. Logging and monitoring</th></tr>
            <tr><td>Who did what, when, and with which model</td><td>Every question is recorded: who, team, when, which model answered, tokens, cost and the request number. Every admin action is recorded in the change log.</td><td>—</td></tr>
            <tr><td>Preventing changes to or deletion of the change log</td><td>Each row in the change log has a seal calculated partly from the seal of the row before it, like links in a chain. Changing or deleting a row breaks the chain. The "Security" tab shows whether the chain is intact, the dashboard warns if it isn't, and it can also be checked at <code>GET /admin/api/audit/verify</code>.</td><td>Act on the alert at once. The seal isn't secret: someone who holds the database file and knows what they're doing can recalculate the whole chain. So limit access to the server and keep backups elsewhere, for comparison.</td></tr>
            <tr><td>Keeping sensitive data out of logs</td><td>Hiding before storing, encrypting what is stored, and server lines without content.</td><td>—</td></tr>
            <tr><td>Tracking admin actions</td><td>The change log: creating, updating, archiving and restoring accounts, teams, models, sources and documents, and policy changes, including the before and after values.</td><td>—</td></tr>
            <tr><td>End-to-end request tracing</td><td>Every request gets an ID number, returned to the app in the <code>x-request-id</code> header and stored in the token log and the blocked-requests log. An app can send its own number; it is kept only if it is up to 64 characters of English letters, digits, dot, underscore and hyphen.</td><td>Store the number in the app's own logs too, to find a request on both sides.</td></tr>

            <tr class="group"><th colspan="3">8. Rate limiting and abuse</th></tr>
            <tr><td>Brute Force</td><td>Guessing passwords by force. 5 wrong passwords lock the account for 15 minutes. 10 failed sign-ins from one address within 15 minutes, for any names, block that address (code 429). The response time is the same even for a username that doesn't exist.</td><td>—</td></tr>
            <tr><td>Token Abuse</td><td>Using a stolen key, or using a key excessively. A key can be revoked at once and given an expiry date, and an account can be given a daily token quota (0 = no quota).</td><td>Give apps an expiry date and a daily quota.</td></tr>
            <tr><td>Account Takeover</td><td>Taking over someone else's account. Lockout after wrong passwords; a sign-in lasts 12 hours, in a cookie that code on the page can't read; changing the password signs out every device.</td><td>Give each employee their own password, and turn off <code>OPEN_ACCESS</code> once there are real users.</td></tr>
            <tr><td>Request Flooding</td><td>Flooding with requests. A requests-per-minute limit per account, up to 4 questions at once (beyond that, code 429), and limited request size.</td><td>Give every account a requests-per-minute limit.</td></tr>
            <tr><td>Token/Quota Exhaustion</td><td>One or more questions that use up the quota. Answers are limited to 8,192 tokens, up to 500 messages per request, and a daily quota and budget per account.</td><td>—</td></tr>
            <tr><td>Cost Abuse</td><td>A personal monthly budget and a team budget: an alert at 80%, blocking at 100%. Cost spike: if an account spent more than $5 in the last hour and also more than 5 times its average hour over the week before, an event is recorded and an alert appears on the dashboard, once a day per account.</td><td>Also set a spending limit with each provider.</td></tr>

            <tr class="group"><th colspan="3">9. Infrastructure security</th></tr>
            <tr><td>TLS 1.2/1.3</td><td>Encrypting the connection between the browser and the server. Caddy, the front door installed together with the gateway, gets a certificate automatically and accepts only TLS 1.2 and 1.3. It adds a header telling the browser to use only an encrypted connection for a year (HSTS), plus other protective headers, and hides the server type.</td><td>Set <code>SITE_ADDRESS</code> to a domain. Without a domain there is no encryption.</td></tr>
            <tr><td>Network segmentation</td><td>The gateway and Caddy sit on their own internal network. The gateway's port (8080) is not open to the outside, and only Caddy accepts connections.</td><td>Allow the server outbound access only to the AI providers and the company's MCP servers, and don't connect it to networks it has no reason to reach.</td></tr>
            <tr><td>Firewall</td><td>The gateway doesn't manage the server's firewall.</td><td>Open only 443 and 80. Never open 8080.</td></tr>
            <tr><td>Container security</td><td>The container runs as a user without administrator rights, with a read-only file system (except <code>/data</code>), no extra system privileges, no way to gain privileges later, and memory and process limits.</td><td>Rebuild from time to time to get updates (see the <a href="#operator">checklist</a>).</td></tr>
            <tr><td>IAM and cloud permissions</td><td>The gateway needs no cloud permissions at all.</td><td>Give the server's cloud identity no permissions beyond running itself: no access to storage, permissions or billing.</td></tr>
            <tr><td>Database security</td><td>The database is a single file in the <code>/data</code> folder, which only the gateway's user can access. Its sensitive content is encrypted, and queries are only sent in fixed form.</td><td>Limit who can sign in to the server. Disk encryption adds a layer.</td></tr>
            <tr><td>Backup security</td><td>Before changing the database structure, the gateway backs it up to the <code>backups</code> folder. That backup is not encrypted.</td><td>Encrypt all backups of <code>/data</code>, and keep the encryption key separately from them.</td></tr>
            <tr><td>Vulnerable dependencies</td><td>Few outside packages: pypdf for reading PDFs, and cryptography for encryption with two packages it needs. All of them are checked automatically against lists of known vulnerabilities. pypdf was upgraded from 6.14.2 to 6.19.0, because the old version had 15 known vulnerabilities.</td><td>Rebuild when an update comes out.</td></tr>

            <tr class="group"><th colspan="3">10. Supply chain</th></tr>
            <tr><td>CVEs in dependencies</td><td>A CVE is an official number for a known vulnerability. On every code change, pip-audit checks the Python packages, and Trivy scans the whole container and fails on a critical vulnerability that already has a fix.</td><td>Update when a check fails.</td></tr>
            <tr><td>Outdated dependencies</td><td>Dependabot (a GitHub service) proposes updates once a week: Python packages, Docker images and GitHub actions.</td><td>Approve the updates and rebuild.</td></tr>
            <tr><td>Malicious packages</td><td>Every package is installed at an exact version and checked against a fixed fingerprint of the file. A package someone swapped fails to install.</td><td>—</td></tr>
            <tr><td>Dependency Confusion</td><td>Accidentally installing a package with the same name from another source. The gateway has no internal packages, and every file is checked against its fingerprint, so a different file won't be installed.</td><td>—</td></tr>
            <tr><td>CI/CD security</td><td>CI means the checks that run automatically on GitHub for every change. The actions they use are pinned to an exact version, and the scanning tools are checked against a fingerprint before they run.</td><td>—</td></tr>
            <tr><td>Secrets in Git</td><td>gitleaks scans the code's entire history on every change and fails if it finds a key or password. <code>.env</code>, the key file, the database and the backups never go into git.</td><td>Don't copy secrets into other files in the project.</td></tr>
            <tr><td>Build integrity and signing</td><td>The container's base image is pinned to an exact version by fingerprint. Every build produces a list of everything in the container (SBOM). The container isn't published yet, so it isn't signed either.</td><td>When you start publishing the container, sign it following the instructions in <code>SECURITY.md</code>.</td></tr>
          </tbody>
        </table>

        <h3 id="security-settings">Server security settings</h3>
        <p>In the <code>.env</code> file. All of them can be left empty; the defaults suit most cases.</p>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td><code>FIREGATE_DATA_KEY</code></td><td>None</td><td>The database encryption key. Without it the gateway uses the <code>&lt;db&gt;.key</code> file next to the database, or creates it. See <a href="#encryption">Encryption and the encryption key</a>.</td></tr>
            <tr><td><code>TRUSTED_PROXIES</code></td><td><code>127.0.0.1,::1</code></td><td>Which addresses the gateway believes when they pass on the client's address. With Docker the setting is <code>127.0.0.1,::1,172.28.0.0/24</code>, that is, Caddy's internal network.</td></tr>
            <tr><td><code>MAX_BODY</code></td><td>40MiB</td><td>Maximum size of a document upload and of app requests (which may carry images and PDFs). Caddy is limited to the same size.</td></tr>
            <tr><td><code>MAX_REQUEST_BODY</code></td><td>1MiB</td><td>Maximum size of every other request: chat and admin-screen changes.</td></tr>
            <tr><td><code>MAX_OUTPUT_TOKENS</code></td><td>8192</td><td>The maximum answer length. An app asking for more gets this maximum, which may limit apps that need long answers.</td></tr>
            <tr><td><code>MAX_CONCURRENT</code></td><td>4</td><td>Questions at once per account. Beyond that, code 429.</td></tr>
            <tr><td><code>MAX_MESSAGES</code></td><td>500</td><td>Messages in a single request. Beyond that, code 400.</td></tr>
            <tr><td><code>SOURCE_ROOTS</code></td><td>Not set</td><td>The folders that folder-type knowledge sources may come from, separated by commas. When set, a folder outside them is refused.</td></tr>
            <tr><td><code>ALLOW_LOCAL_LOOPBACK</code></td><td>off</td><td><code>1</code> = the <a href="#local">local model server</a> may be the machine the gateway runs on (localhost). Internal-network addresses are always allowed for it; link-local addresses and the cloud provider's information address are always blocked.</td></tr>
            <tr><td><code>ALLOW_PRIVATE_MCP</code></td><td><code>1</code></td><td><code>0</code> = also block MCP servers at internal-network addresses. The server itself, local addresses and the cloud provider's information address are always blocked, and redirects are never followed.</td></tr>
            <tr><td><code>PUBLIC_DEPLOY</code></td><td>Off</td><td><code>1</code> = the gateway doesn't distinguish the office from outside: the admin screen always asks for the password, and open mode is off. Required if anything sits in front of Caddy (a load balancer, a CDN), or if the gateway can be reached from the internet.</td></tr>
            <tr><td><code>ALLOWED_HOSTS</code></td><td>Empty</td><td>Extra server names the gateway will answer to, separated by commas (the domain in <code>SITE_ADDRESS</code> is already included).</td></tr>
            <tr><td><code>OPEN_ACCESS</code></td><td>Off</td><td><code>1</code> = chat without signing in on the office network, and anyone can pick any name. Turn it off as soon as there are real users.</td></tr>
          </tbody>
        </table>

        <h3 id="operator">Server operator checklist</h3>
        <ul>
          <li>Only 443 and 80 are open in the firewall (Caddy uses 80 to redirect to HTTPS and to get a certificate).</li>
          <li><b>Never open 8080.</b> The gateway believes the client address Caddy passes on, so anyone who reaches it directly from an internal address can pretend to be in the office.</li>
          <li><code>SITE_ADDRESS</code> holds a domain, so the connection is encrypted. <code>:80</code> (no encryption) is only for a closed office network.</li>
          <li>If a load balancer or CDN sits in front of Caddy: <code>PUBLIC_DEPLOY=1</code>.</li>
          <li>Everything the gateway writes is in <code>/data</code>: the database, the key file and the backups. Back it up encrypted, and keep the key separately.</li>
          <li>The server goes out to the internet only to the AI providers (<code>api.anthropic.com</code>, <code>api.openai.com</code>, <code>generativelanguage.googleapis.com</code>) and the company's MCP servers. Everything else is blocked.</li>
          <li>Rotate the provider keys from time to time, and give each one a spending limit at the provider.</li>
          <li>Updating: <code>docker compose build --pull &amp;&amp; docker compose up -d</code></li>
          <li>On every code change, automated checks run on GitHub: the gateway's tests, a search for known vulnerabilities in the packages (pip-audit), a search for leaked keys across the whole code history (gitleaks), a container scan (Trivy), and a list of everything in the container (SBOM).</li>
          <li>Dependabot proposes updates once a week. All versions are pinned, with a fingerprint for every file.</li>
          <li>Found a vulnerability? Report it privately on GitHub (Security → Report a vulnerability), not in a public discussion. Details are in <code>SECURITY.md</code>.</li>
        </ul>`,

  "#logs": `
        <h2>Logs</h2>
        <ul>
          <li><b>Token log:</b> the last 200 questions with who, team, model, tokens, cost, and the full question and answer. Filter by name, team or model. All questions are kept in the database.</li>
          <li><b>Change log:</b> every admin action: creating, updating, archiving and restoring accounts, teams, models, sources and documents, including the before and after values for budget and price changes. An employee moving one of their chats to the archive, or restoring it, is recorded here too.</li>
        </ul>`,

  "#archive": `
        <h2>Archive</h2>
        <p><b>Nothing is ever deleted.</b> Instead of a delete button there is "Move to archive": a user, team, model, knowledge source or document moved to the archive doesn't appear on the screens and doesn't work, but stays in the database with all its history.</p>
        <ul>
          <li>The "Archive" page (in the menu, under "Monitor") shows everything in the archive, with the date, and a "Restore" button for each item.</li>
          <li>The spending of archived items stays in the token log and in the reports of the months it happened in.</li>
          <li>The name of an archived item is taken: creating a user, team, model or source with the same name is refused, with a message to restore it.</li>
          <li>Every move to the archive and every restore is recorded in the change log: what, which item and when.</li>
          <li>Employees archive only their own chats, and restore them from the "Archive" link in the chat.</li>
          <li>From another system: <code>POST /admin/api/archive</code> and <code>POST /admin/api/restore</code> with <code>kind</code> (<code>account</code>, <code>team</code>, <code>model</code>, <code>source</code> or <code>doc</code>) and <code>name</code>; for a document <code>name</code> is the source's name, plus <code>id</code>. The list: <code>GET /admin/api/archive</code>.</li>
        </ul>`,

  "#api": `
        <h2>Connecting apps</h2>
        <p>Create an account with an API key, and in the app change just two things: the address and the key. Everything else stays the same as when talking to the provider directly.</p>
        <pre>client = anthropic.Anthropic(base_url="http://&lt;your-server&gt;", api_key="gw-...")
client.messages.create(model="smart", max_tokens=1000, messages=[...])

client = openai.OpenAI(base_url="http://&lt;your-server&gt;/v1", api_key="gw-...")
client.chat.completions.create(model="gemini-fast", messages=[...])</pre>
        <ul>
          <li>Claude through <code>/v1/messages</code>; GPT, Gemini and <a href="#local">models on the company's server</a> through <code>/v1/chat/completions</code>.</li>
          <li>Streamed answers (<code>stream</code>) are supported, and tokens are counted for them too.</li>
          <li>The <code>x-gateway-model</code> header in the response says which model actually answered (different from the one requested if the backup answered).</li>
          <li>Errors: 401 invalid key, 402 budget used up, 403 model not allowed or turned off, 429 too many requests, 502 provider unavailable.</li>
          <li>When the policy is "Send to the local model", a question with sensitive data is answered by the local model even if the app asked for another one; <code>x-gateway-model</code> shows it.</li>
        </ul>`,

  "#settings": `
        <h2>Server settings</h2>
        <p>In the <code>.env</code> file:</p>
        <table>
          <thead><tr><th>Setting</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td><code>ANTHROPIC_API_KEY</code>, <code>OPENAI_API_KEY</code>, <code>GEMINI_API_KEY</code></td><td>The provider keys. A provider without a key simply won't work.</td></tr>
            <tr><td><code>LOCAL_API_KEY</code></td><td>A key for the company's model server (Ollama or vLLM), if it needs one. Optional. The server's address is set on the Models page. See <a href="#local">Models on the company's own server</a>.</td></tr>
            <tr><td><code>ALLOW_LOCAL_LOOPBACK</code></td><td><code>1</code> = the company's model server may be the gateway's own machine.</td></tr>
            <tr><td><code>ADMIN_PASSWORD</code></td><td>Password for the admin screen from outside. Empty = completely closed from outside.</td></tr>
            <tr><td><code>SITE_ADDRESS</code></td><td>Domain for an automatically encrypted connection.</td></tr>
            <tr><td><code>ALLOWED_HOSTS</code></td><td>Extra server names the gateway will answer to, separated by commas.</td></tr>
            <tr><td><code>OPEN_ACCESS</code></td><td><code>1</code> = chat without signing in on the office network.</td></tr>
            <tr><td><code>EMBEDDINGS</code></td><td>Provider for search by meaning: <code>openai</code>, <code>gemini</code> or <code>off</code>. Default: the first one that has a key.</td></tr>
            <tr><td><code>PORT</code>, <code>GATEWAY_DB</code></td><td>The server port (8080) and the location of the data file.</td></tr>
            <tr><td><code>SMTP_HOST</code>, <code>SMTP_PORT</code></td><td>The mail server that sends the <a href="#summary">monthly summary</a>, and its port (default 587). Without <code>SMTP_HOST</code> no summary is sent.</td></tr>
            <tr><td><code>SMTP_USER</code>, <code>SMTP_PASSWORD</code></td><td>User name and password for the mail server, if it needs them. The password stays in the server settings only.</td></tr>
            <tr><td><code>SMTP_FROM</code></td><td>The address the email is sent from. Empty = <code>SMTP_USER</code>.</td></tr>
            <tr><td><code>SMTP_TLS</code></td><td><code>1</code> (default) = encryption after connecting (STARTTLS, port 587); <code>ssl</code> = encrypted from the start (port 465); <code>0</code> = no encryption, only for a mail server inside the network.</td></tr>
          </tbody>
        </table>
        <p>The security settings (the encryption key, size and rate limits, <code>PUBLIC_DEPLOY</code> and more) are listed in <a href="#security-settings">Server security settings</a>.</p>`,

  "#limits": `
        <h2>Known limitations</h2>
        <ul>
          <li>In open mode, anyone on the network can pick any name and use that person's budget.</li>
          <li>Without a domain the connection is not encrypted.</li>
          <li>Questions and answers are kept with no time limit.</li>
          <li>Nothing is ever deleted: whatever leaves use moves to the <a href="#archive">archive</a> and stays in the database. If something truly has to be deleted (for example by law), there is no button for it.</li>
          <li>A scanned PDF (an image with no text) can't be read.</li>
          <li>The requests-per-minute limit is kept in memory and resets when the gateway restarts.</li>
          <li>Alerts appear only on the admin screen; there are no alerts by email, Teams or Slack yet. Only the <a href="#summary">monthly summary</a> goes out by email.</li>
          <li>Savings recommendations are an estimate: they assume the same short questions would work well on the cheap model, and don't check answer quality.</li>
          <li>Speed monitoring starts with this version: questions from before it have no times. Answer time includes the network trip to the provider, and a long answer naturally takes longer, so comparing models is fair only when they answer similar work.</li>
          <li>A local model server that returns no token counts gets an estimate (about one token for every four characters), so the daily token limit is approximate for it.</li>
        </ul>`,
});
