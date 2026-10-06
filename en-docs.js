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

  "main.doc .lead": `Everything the system can do, laid out like the admin screen's menu: screen by screen, under the same names. Employees will find the chat screen here, managers the whole admin screen, and IT staff installation, settings and connecting apps.`,

  "main.doc .on-page": `
        <h2>On this page</h2>
        <div class="on-page-grid">
          <div><h3>Start here</h3><ul>
            <li><a href="#about">What the gateway is</a></li>
            <li><a href="#install">Install and run</a></li>
          </ul></div>
          <div><h3>Main</h3><ul>
            <li><a href="#overview">Dashboard</a></li>
            <li><a href="#todo">To handle</a></li>
            <li class="sub"><a href="#savings">Savings recommendations</a></li>
          </ul></div>
          <div><h3>Manage</h3><ul>
            <li><a href="#accounts">Users and keys</a></li>
            <li class="sub"><a href="#user-page">User screen</a></li>
            <li><a href="#models">Models</a></li>
            <li class="sub"><a href="#local">Models on the company server</a></li>
            <li class="sub"><a href="#speed">Speed monitoring</a></li>
            <li class="sub"><a href="#backup">Backup model</a></li>
            <li class="sub"><a href="#auto">Automatic choice</a></li>
            <li class="sub"><a href="#cache">Provider-side cache</a></li>
            <li><a href="#teams">Teams</a></li>
            <li class="sub"><a href="#team-models">Models a team may use</a></li>
            <li class="sub"><a href="#cost-center">Cost center</a></li>
            <li><a href="#sources">Knowledge sources</a></li>
            <li class="sub"><a href="#mcp">MCP connections</a></li>
          </ul></div>
          <div><h3>Monitor</h3><ul>
            <li><a href="#reports">Reports</a></li>
            <li class="sub"><a href="#summary">Monthly summary by email</a></li>
            <li class="sub"><a href="#chargeback">Chargeback</a></li>
            <li><a href="#security">Security</a></li>
            <li class="sub"><a href="#policy">Blocking policy</a></li>
            <li class="sub"><a href="#encryption">Encryption and the encryption key</a></li>
            <li><a href="#logs">Token log</a></li>
            <li><a href="#audit">Change log</a></li>
            <li><a href="#archive">Archive</a></li>
          </ul></div>
          <div><h3>Employees</h3><ul>
            <li><a href="#chat">Chat screen</a></li>
          </ul></div>
          <div><h3>Technical</h3><ul>
            <li><a href="#hardening">Security checklist</a></li>
            <li class="sub"><a href="#security-settings">Server security settings</a></li>
            <li class="sub"><a href="#operator">Server operator checklist</a></li>
            <li><a href="#api">Connecting apps</a></li>
            <li><a href="#settings">Settings screen</a></li>
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
          <li><span><b>Budget and rate:</b> whether they and their team still have budget left this month, and whether they haven't gone over their requests per minute or their daily token quota.</span></li>
          <li><span><b>Protection:</b> ID numbers, credit cards and keys are hidden, and a question that tries to override the model's instructions is blocked. That is the default; the admin can choose otherwise in the "Policy" card on the "Security" page (see <a href="#policy">Blocking policy</a>).</span></li>
          <li><span><b>Documents:</b> if the employee asked for it, the gateway searches the company's documents and attaches the relevant passages.</span></li>
          <li><span><b>Sending to the provider:</b> to the chosen model, or to its backup if the provider is unavailable.</span></li>
          <li><span><b>Logging:</b> who, when, which model, how many tokens (the units in which the provider counts text and charges for it; a token is roughly a piece of a word), what it cost, and the question and answer themselves.</span></li>
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
          <li><code>python seed_demo.py</code> adds sample data: 10 teams, more than 60 users and apps, 9 models plus one on the company server, 90 days of usage, more than 60 documents, security events, a change log and saved chats. It only adds and never changes anything that exists. The sample users' chat password is the <code>DEMO_PASSWORD</code> setting, or, when that is empty, the password written in the file.</li>
          <li>All data lives in a single file, <code>gateway.db</code>. To copy it while it's running: <code>docker compose exec gateway python -c "import sqlite3; sqlite3.connect('/data/gateway.db').backup(sqlite3.connect('/data/backup.db'))"</code></li>
          <li><code>python test_gateway.py</code> runs all the tests against simulated providers, with no real money spent.</li>
        </ul>`,

  "#chat": `
        <h2>Chat screen</h2>
        <p>At <code>/chat</code>. The employee asks, and the gateway answers word by word.</p>
        <h3>Signing in</h3>
        <ul>
          <li><b>Standard:</b> a username and password given by the admin. Anyone without an account asks the admin. After 5 wrong passwords the account is locked for 15 minutes. A sign-in lasts 12 hours. At the bottom of the menu are "Change password" (at least 8 characters) and "Sign out".</li>
          <li><b>Open mode</b> (<code>OPEN_ACCESS=1</code>): on the office network there is no sign-in screen. The employee picks their name from the menu, and the browser remembers it. This mode does not work from outside.</li>
        </ul>
        <h3>Choosing a model</h3>
        <ul>
          <li>The list shows only the models allowed to the employee (and their team) that are turned on, under their names, for example Claude Sonnet 5.5. At first "Automatic" is selected, or the default model if automatic choice is off. The browser remembers the last choice.</li>
          <li><b>"Automatic"</b> chooses by itself: a cheap model for short questions, a strong model for code, analysis, comparisons or long text. Next to each answer it says which model answered and why.</li>
          <li>If the chosen model is unavailable and a backup was set for it, the answer notes that the backup model answered.</li>
        </ul>
        <h3>Company documents</h3>
        <p>Below the message box, next to "Search documents:", are the sources the employee's team is allowed to search. Tick the ones to use. When an answer relies on documents, it shows "Based on" with the document names underneath.</p>
        <h3>More</h3>
        <ul>
          <li>Conversations are saved in a list on the side, and the employee can go back to them or move them to the archive. An archived conversation leaves the list but is not deleted: the "Archive" link at the top of the list shows it, with a restore button. Writing again in an archived conversation brings it back to the list. The copy in the token log stays either way.</li>
          <li>At the bottom of the menu: "My budget this month" and "Team budget", showing how much of each has been spent. Below the message box it says how much is left, and "budget almost used up" when less than 20% remains.</li>
          <li>An answer that includes a command that could delete data or run code from the internet gets a warning at its end.</li>
          <li>An answer can be stopped midway with the "Stop" button.</li>
          <li>When the policy sends sensitive data to the model on the company server, the answer says "sensitive data: answered by the local model" (see <a href="#policy">Blocking policy</a>).</li>
          <li>The chat menu links to "Admin" and "Help &amp; docs", and the "Archive" link turns into "Back to chats" while the archive is open.</li>
        </ul>`,

  "#overview": `
        <h2>Dashboard</h2>
        <p>The first page of the admin screen, at <code>/</code> (and also <code>/admin</code>). A computer on the office network (that is, with an internal address such as 10.x.x.x or 192.168.x.x) gets in without a password. From outside, the "Sign in from outside" screen asks for the admin password, which is the <code>ADMIN_PASSWORD</code> setting; if it is empty, there is no way in from outside at all. The browser remembers the password only until the tab is closed. With <code>PUBLIC_DEPLOY=1</code> the password is always required, even from the office.</p>
        <ul>
          <li><b>At the top:</b> "Hello, admin" and a "New user" button. The top bar of every screen has "Refresh", which reloads the data, and a button to switch between Hebrew and English.</li>
          <li><b>Four numbers:</b> "Spent this month" and "Requests this month", each with the percentage change from last week to this week; "Projected for the month" against last month; and "Active users", meaning how many of the accounts asked something this month.</li>
          <li><b>Savings recommendations:</b> the three biggest recommendations, and how much could be saved per month in total. "See all recommendations" goes to the <a href="#todo">To handle</a> page.</li>
          <li><b>Daily spend</b> over the last 30 days (hover over a bar to see the day), and <b>spend by model</b> this month.</li>
          <li><b>Cumulative spend this month:</b> a line that rises day by day, against the previous month and against the total of the team budgets, with a dashed line that continues the current pace to the end of the month.</li>
          <li><b>Projected budget use:</b> how many users will finish the month, at the current pace, in each range: up to 50% of their budget, 50–75%, 75–100%, 100–125%, 125–150% and over 150%. The normal bars are grey, and only those who will go over budget carry a warning colour. Accounts without a budget aren't counted.</li>
          <li><b>When people ask:</b> a heat map of requests by day of the week and hour over the last four weeks. Helps you see peak hours and plan rate limits.</li>
          <li><b>Monthly spend by team:</b> the last four months, each month split into the five largest teams and "Other".</li>
          <li><b>Top spenders</b> this month (up to 8), with each one's budget status, and <b>teams vs. budget</b>. Clicking a name opens the <a href="#user-page">user screen</a>.</li>
          <li>The bottom of the admin screen shows the gateway's version number (for example <bdi>v1.0.5</bdi>), so you know which version is installed.</li>
        </ul>`,

  "#accounts": `
        <h2>Users and keys</h2>
        <p>Every employee, app or customer is an account. "New user" (or "Edit" on an existing row) opens a window with three parts:</p>
        <ul>
          <li><b>Who:</b> name and team.</li>
          <li><b>Limits:</b> a monthly budget in dollars, "Requests per minute" and "Tokens per day" (in both, 0 = no limit), and the allowed models, with each one's price. A personal budget of 0 means no personal cap, as for a team. The team's budget still applies.</li>
          <li><b>Access:</b> a chat password (at least 8 characters; empty = no chat), and an API key for apps (the API is how software talks to the gateway). The key is shown only once, in the "The new key" window. The gateway keeps only a fingerprint of it (<bdi>SHA-256</bdi>): a one-way calculation that can't be turned back into the key. When editing there are "New key" (the old one stops working at once) and "Revoke key". A new password in the edit window also releases a locked account.</li>
          <li><b>"Key valid until (empty = no expiry date)":</b> an expiry date for the key. Clicking the field opens a month calendar, with a year view and a "Clear" button. The key works until the end of that day. Empty = no expiry date.</li>
        </ul>
        <p>In the users table, for each account:</p>
        <ul>
          <li><b>Forecast:</b> how much the account will spend by the end of the month at the current pace. <b>Suggested budget:</b> the higher of the forecast and last month's spend, plus 20%, rounded up to $5.</li>
          <li>The <b>"Apply"</b> button appears when the forecast passes 90% of the budget and the suggested budget is higher, meaning the account is about to be blocked. Before the change there is a confirmation showing the old and new amounts, and afterwards it can be undone. When the budget is 4 or more times the suggestion, it says "Could go down to" and the amount.</li>
          <li><b>Moving to the archive:</b> the account disappears from the lists, its password and key stop working right away, and it is signed out on every device. Its history stays in the log and the reports. Restore it from the <a href="#archive">archive</a>, and the previous password and key work again. A new account can't be created with the name of an archived one: restore it instead.</li>
        </ul>
        <p>You can search by name or team, and sort by name, team, spend or forecast. On a phone each row is shown as a card.</p>
        <h3 id="user-page">User screen</h3>
        <p>Clicking a user's name (in the users table, in the dashboard's top spenders table, in the token log, or "Details" on an alert about them) opens a screen with everything they did:</p>
        <ul>
          <li><b>Numbers:</b> spend this month against the budget, the forecast to the end of the month, and requests and tokens this month.</li>
          <li><b>Charts:</b> "Daily spend" over the last 30 days, and "Spend by model" this month.</li>
          <li><b>"Recent activity":</b> the last 100 requests. Clicking a question opens the question and the answer.</li>
          <li><b>"Security":</b> their security events and their blocked requests. <b>"Change history":</b> what was changed on their account and when. <b>"Chats":</b> how many saved chats they have, and the titles of the latest ones.</li>
        </ul>
        <p>An archived user's screen opens too, marked as archived. Each user has their own address (<bdi>#user=</bdi> followed by the name), so refresh and the Back button work, and "Back to users" returns to the table. Keys and passwords are never shown on this screen in any form.</p>`,

  "#teams": `
        <h2>Teams</h2>
        <ul>
          <li>"New team" opens a window with a name, a monthly team budget (<b>0 = no cap</b>), a <a href="#cost-center">cost center</a> and the <a href="#team-models">models the team may use</a>.</li>
          <li>A question is blocked when the personal budget <b>or</b> the team budget runs out. When the team budget runs out, every team member is blocked, even those with personal budget left.</li>
          <li>At the start of each month (the 1st, or the "Budget reset day" set on the settings screen) spending resets to zero; the history stays in the log.</li>
          <li>The teams table shows, for each team, the number of members, spend this month, forecast, suggested budget (with "Apply", as for users), and the total of the members' budgets, so you can see whether the team cap fits them.</li>
          <li><b>Moving to the archive:</b> only for a team with no people in it, so nobody is suddenly left without a team. The team leaves the lists and the choices, and its budget and history are kept. An archived user whose team is archived comes back only after the team does.</li>
        </ul>
        <h3 id="team-models">Models a team may use</h3>
        <p>When editing a team, under "Models the team may use", you can check the models the team may use, for example "the legal team works only with Claude". Nothing checked means the team sets no limit. With models checked:</p>
        <ul>
          <li>Everyone in the team can use only models allowed <b>both</b> to them personally <b>and</b> to the team. A model allowed personally but not by the team is blocked (error 403), and the request is recorded on the "Security" page with the reason "Model not allowed for the team".</li>
          <li>The chat's model list shows only what is really allowed. Automatic choice picks only from those, and a backup model the team may not use is never called: if the provider is down, the question fails instead of moving to another model.</li>
          <li>In a user's edit window, a checked model the team blocks gets a "Blocked by team policy" label. The teams table shows under the team's name how many models it may use.</li>
        </ul>
        <h3 id="cost-center">Cost center</h3>
        <p>When editing a team, under "Chargeback", there are two optional fields of up to 64 characters each: "Cost center" (the department's code in accounting) and "GL account (bookkeeping)" (the expense line the amount is booked to). They show under the team's name in the teams table, and go into the <a href="#chargeback">chargeback</a> table and file, so accounting knows where to book each team's cost.</p>`,

  "#models": `
        <h2>Models</h2>
        <p>All the models the gateway offers are managed from the screen, with no code editing and no restart. A new installation has six models, under their real names: Claude Haiku 4.5 and Claude Sonnet 5.5, GPT-6 Luna and GPT-6.1 Sol, Gemini 3.8 Flash and Gemini 3.1 Pro. The page runs top to bottom: provider status, "Automatic model choice", two charts, "Response speed", the models table and "Local model server".</p>
        <ul>
          <li><b>Provider status:</b> for each provider, whether it has a key in the <code>.env</code> file (and for the company server: whether an address is saved for it).</li>
          <li><b>Turning on and off</b> (the "On" column): a model that is turned off is blocked for everyone immediately. Before turning it off you see how many accounts are allowed to use it, and afterwards it can be undone.</li>
          <li><b>Adding and editing</b> ("New model" or "Edit"): an alias (what apps send in the <code>model</code> field), a display name (what employees see in the chat), the provider, the exact name at the provider, and prices per million tokens: input, output, and from the cache (empty = a tenth of the input price). A display name the admin set is kept across version updates.</li>
          <li><b>Default:</b> the model ticked for a new user, and the model preselected in the chat when automatic choice is off. It can't be turned off or moved to the archive until another one is set.</li>
          <li><b>Connection test</b> ("Test"): sends the provider a short question and shows whether the key and name work, and how long it took. The tiny cost is logged under the name "(בדיקת מודל)" (model test) and isn't counted in reports.</li>
          <li><b>Moving to the archive:</b> only when no account is allowed to use the model. An archived model works for no one, not even an app that sends its alias, and it can be restored.</li>
          <li><b>Usage and charts:</b> for each model, requests and money this month, and how many users may use it. "Daily spend by model" and "Requests vs. spend" (share of requests against share of spend) help spot a model that is expensive per request.</li>
          <li>Every change, including the price before and after, is recorded in the change log.</li>
        </ul>
        <h3 id="local">Models on the company server</h3>
        <p>A model running on the company's own server, with Ollama or vLLM (two programs that run open models such as Llama and Qwen and speak the same language as OpenAI). Questions never leave the company network, and there is no per-token charge.</p>
        <ul>
          <li><b>Connecting:</b> on the <a href="#settings-providers">settings screen</a>, under "Providers and keys", type the server's address, for example <code>http://ollama:11434/v1</code> or <code>http://10.0.0.5:8000/v1</code>, and save. "Test connection" in the "Local model server" card at the bottom of the Models page asks the server which models it has and lists them.</li>
          <li><b>Adding:</b> every model in the list has "Add model". It joins the model list with the provider "Company server", at price 0 (you can set an internal price under Edit), and from there you allow it for users and teams like any model. You can also create it by hand with "New model" and the provider "Company server".</li>
          <li><b>Use:</b> in the chat, and for apps through <code>/v1/chat/completions</code> (the OpenAI format), streaming included. Token counts come from the server's answer; a server that doesn't return them gets an estimate, about one token for every four characters, and the log says "estimated".</li>
          <li><b>Access key:</b> if the server needs a key, it goes only into the <code>LOCAL_API_KEY</code> server setting. It isn't stored in the database and isn't shown on screen.</li>
          <li><b>Which addresses are allowed:</b> internal-network addresses are allowed, since that's where the server lives. Link-local addresses (169.254.x.x) and cloud providers' information addresses are always blocked, as is anything that isn't http or https, and an address with a user name and password in it. The machine the gateway runs on (localhost) is blocked unless you set <code>ALLOW_LOCAL_LOOPBACK=1</code>, for example when Ollama is installed on the same machine without Docker. The check runs both when saving and on every connection, against the address the name points to at that moment, and redirects are not followed.</li>
          <li><b>Sensitive data:</b> you can have questions with sensitive data go to this model instead of being masked. See <a href="#policy">Blocking policy</a>.</li>
        </ul>
        <h3 id="speed">Speed monitoring</h3>
        <p>For every question the gateway records how long the whole answer took, and how soon the first word arrived (in a streamed answer; in a regular answer the two times are the same). The time is measured at the gateway, from sending to the provider until the end of the answer, so it includes the trip over the network. Failed questions are recorded with their error code, including a provider that didn't answer at all (502) or stopped answering midway (504).</p>
        <ul>
          <li><b>The "Response speed" card</b> on the Models page: a table per model over the last 24 hours or 7 days: "Median" (half the answers are faster), "95%" (only 5 in 100 answers are slower), "Time to first word", "Requests" and "Errors". Next to it, a chart of the median by provider for each hour of the last 48.</li>
          <li><b>Alert:</b> when a model answered at least 10 times in the last hour, and 95% of its answers took more than 2 times the usual (its 95% over the 7 days before that hour), the "To handle" page shows "Provider X is slower than usual", with "Details" leading to the Models page, and the model is marked "Slower than usual now" in the table.</li>
          <li>Connection tests from the Models page and document indexing aren't counted.</li>
          <li>For scripts: <code>GET /admin/api/latency</code>, with the same admin access as the screen.</li>
        </ul>
        <h3 id="backup">Backup model</h3>
        <p>When editing a model, under "When the provider is down", choose a "Backup model". If the provider is overloaded or not responding (errors 429, 5xx, 529), the question moves to the backup on its own and is charged at the backup's price. The chat notes next to the answer that the backup answered, the log records it, and the models table shows "Backup:" with the model's name and how many times it answered this month. For apps, the backup only works between models with the same format: Claude with Claude, or GPT with Gemini.</p>
        <h3 id="auto">Automatic choice</h3>
        <p>On the <a href="#settings-models">settings screen</a>, under "Models and routing", pick a "Cheap model" and a "Strong model" and turn on "Automatic choice". The card on the Models page shows the values with a link to change them. From then on the chat offers "Automatic". A long question (over 1,200 characters), code, analysis, comparison, planning, a contract, a legal matter, "why" or "step by step", and also a long conversation (more than 12 messages or more than 8,000 characters) go to the strong one; everything else to the cheap one. The employee sees next to the answer which model answered and why. If the matching model isn't allowed for the employee, the other one is chosen, and the reason says "(the right model isn't available to you)". The card shows how many questions were routed this month.</p>
        <p><b>"Prefer the fastest suitable model"</b> (off at first): once the cheap or the strong model is picked, the gateway also looks at the models the employee may use whose price (input plus output) is close: at most 2 times more expensive or 2 times cheaper, at any provider. Of those, it picks the one with the lowest median answer time over the last 24 hours. Only models that answered at least 20 times in those 24 hours count; if there are none, the usual choice stays. When a different model is picked for this reason, the employee sees "(the fastest suitable one)" next to the reason.</p>
        <h3 id="cache">Provider-side cache</h3>
        <p>A cache is a copy the provider keeps for a short while. In conversations with Claude, the gateway asks the provider to keep the start of the conversation, and on the next turn it is read at about a tenth of the price. OpenAI and Gemini do this on their own. The cost is calculated using each model's cache price. The top of the Models page shows "Cache savings this month", and the table shows how much each model saved.</p>`,

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
        <p>A document with browser code, an attempt to override instructions, or a dangerous command is blocked on upload; an admin can approve it anyway, and the decision is logged. When syncing, such a file is not taken in and shows up on the "Security" page.</p>
        <h3 id="mcp">MCP connections</h3>
        <p>MCP is a standard way for systems (a CRM, a wiki, a ticketing system) to expose information to AI. Enter an address and an access key, and "Test connection" shows the server's name, its tools and its documents. Two modes:</p>
        <ul>
          <li><b>Live search:</b> on every question the gateway calls the chosen search tool with the question, and attaches the result (up to 3,000 characters).</li>
          <li><b>Sync:</b> the server's documents are copied into the index, like a folder. A document that disappeared from the server moves to the archive.</li>
        </ul>
        <p>Every response from the server goes through sensitive-data hiding and a check for suspicious content. A response that tries to give the model instructions is blocked and logged. The access key is kept on the server and never sent back to the browser.</p>`,

  "#reports": `
        <h2>Reports</h2>
        <p>Pick a month in the list at the top of the screen to see summary numbers (spend, requests, tokens, and how many people and apps used it), followed by "By team" (including budget and usage), "By user" and "By model" (including tokens from the cache). "Download for Excel" saves a CSV file (a table in a text file that Excel opens) that opens in Excel with Hebrew displayed correctly. Connection tests from the Models page aren't counted.</p>
        <h3 id="summary">Monthly summary by email</h3>
        <p>An email to management once a month (on the 1st after 08:00, or the day and hour set on the settings screen), about the month before: total spend against the previous month, the five teams and five users who spent the most, spend by model, the savings total and the three biggest recommendations, security events by kind, how many requests were blocked, and who went over budget. The recommendations are worked out from the 30 days before sending, and the overruns against the budgets set at that moment. The email is in Hebrew, right to left, with a plain-text version for mail readers without HTML.</p>
        <ul>
          <li>The recipients (up to 50), automatic sending, the day and the hour are set on the <a href="#settings-alerts">settings screen</a>, under "Alerts and reports". On the "Monthly summary by email" card on the reports screen: a line with the current values, "Preview" and "Send now" (both for the month chosen at the top of the screen), and a line saying whether a mail server is set up.</li>
          <li>The mail server is set on the settings screen or in the server's settings file, which wins (see <a href="#settings">Settings screen</a>). It needs both <code>SMTP_HOST</code> and a sender address (<code>SMTP_FROM</code>, or <code>SMTP_USER</code> when that is empty); without either, nothing is sent. The mail server's password is stored encrypted (if entered on the screen) and never sent to the browser; the screen only shows whether one is set.</li>
          <li>Each month is sent once. Every sending (manual too) is recorded in the change log, and a month already sent isn't sent again automatically. If sending fails, an event is recorded on the "Security" page and the gateway tries again the next hour, up to 3 times.</li>
          <li>The preview is shown inside a closed frame without scripts, and people's and teams' names appear as plain text only.</li>
        </ul>
        <h3 id="chargeback">Chargeback</h3>
        <p>The "Chargeback by team" card: each team's cost in the chosen month, with its <a href="#cost-center">cost center and GL account</a>, for charging each department for its own use. One row per team that used the gateway, a "No team" row for accounts without a team (and the document index cost), and a total row. The amounts match the monthly report.</p>
        <ul>
          <li><b>"Download CSV"</b>: a file for the accounting system. Column names are in English and fixed, so an import only has to be set up once: <code>month, team, cost_center, gl_account, requests, tokens_in, tokens_out, cost_usd</code>. Cost is in dollars with two decimals; the total row is <code>TOTAL</code> and is the sum of the rows. The file is UTF-8 with a mark that makes Excel read Hebrew team names correctly. A cell starting with <code>=</code>, <code>+</code>, <code>-</code> or <code>@</code> gets a leading apostrophe, so Excel doesn't run it as a formula.</li>
          <li><b>"Download JSON"</b>: the same data in a format programs read, for processing in a program.</li>
          <li>For scripts: <code>GET /admin/api/chargeback?month=2026-09&amp;format=csv</code> (or <code>format=json</code>), with the same admin access as the screen.</li>
          <li>"Download for Excel" at the top of the screen stays as it is: a file with headings in the interface language, easy to read.</li>
        </ul>`,

  "#security": `
        <h2>Security</h2>
        <p>Every question from an employee or an app goes through the gateway before it reaches the provider, so this is where every question is checked and every record is kept. Below: what the gateway does on its own, what you set in the "Security" page, and what you must know about encryption. The full list, topic by topic, is in the <a href="#hardening">security checklist</a>.</p>
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
        <h3>The "Security" page</h3>
        <p>Counts for the last 7 days, a "Health check" (an encrypted connection with a domain, an outside admin password of at least 16 characters, keys with no rate limit, open mode, connected providers, and where the encryption key is kept), "Policy", "Change log is intact", "Blocked requests" (the last 200, with the reason and a masked excerpt of the question), and "Security events" (the last 200) that can be filtered by type.</p>

        <h3 id="policy">Blocking policy</h3>
        <p>On the <a href="#settings-security">settings screen</a>, under "Security and policy", you choose what happens to a question that was caught (the "Policy" card on the "Security" page shows the values with a link to change them). The setting applies to all accounts, except a team given a special setting when editing the team, and every change to it is recorded in the change log.</p>
        <table>
          <thead><tr><th>What was caught</th><th>The options</th></tr></thead>
          <tbody>
            <tr><td><b>An attempt to override the model's instructions</b> (prompt injection or jailbreak)</td><td><b>Block</b> ("Block the question", the default), or <b>log only</b> ("Send and record in the log").</td></tr>
            <tr><td><b>Sensitive data</b> (ID number, credit card, phone, email, keys and more)</td><td><b>Mask</b> ("Hide the data and send", the default), <b>block</b> ("Block the question"), <b>log only</b> ("Send without hiding and record in the log"), or <b>local model</b> ("Send to the local model").</td></tr>
          </tbody>
        </table>
        <p><b>"Send to the local model"</b> works only when there is a <a href="#local">model on the company server</a> that is turned on. A question with sensitive data goes to it unmasked, instead of to the model the employee picked, but only if the employee may use it (the models their team may use included). The employee sees "sensitive data: answered by the local model" in the chat, and the "Security" page records the event "Sensitive data answered by the local model". If the employee has no local model, the data is masked as usual. The unmasked question never reaches an outside provider: if the local model doesn't answer, its backup is used only if it is on the company server too. The log keeps the masked version of the question. Apps on the Claude format (<code>/v1/messages</code>) can't move to the local model, so for them the data is masked.</p>
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
            <tr><td>Rotating and revoking keys</td><td>A new key can be issued, or a key revoked, in the edit window, and given an expiry date: the key works until the end of that day and is refused after it (code 401). A new key starts with no expiry date. The "To handle" page warns when fewer than 14 days are left, when the key has expired, or when a key has been in use for more than 90 days.</td><td>Replace a key when the alert appears. Rotate the provider keys from time to time, and immediately if <code>.env</code> may have leaked.</td></tr>

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
            <tr><td>API Abuse</td><td>Excessive or unusual use of the gateway. Request size is limited, up to 500 messages per request, answers up to 8,192 tokens, up to 4 questions at once per account, a requests-per-minute limit, a budget and a daily quota. See <a href="#security-settings">Server security settings</a>.</td><td>Give every account a requests-per-minute limit and a budget. "Health check" shows keys with no rate limit.</td></tr>

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
            <tr><td>Preventing changes to or deletion of the change log</td><td>Each row in the change log has a seal calculated partly from the seal of the row before it, like links in a chain. Changing or deleting a row breaks the chain. The "Security" page shows whether the chain is intact, the "To handle" page warns if it isn't, and it can also be checked at <code>GET /admin/api/audit/verify</code>.</td><td>Act on the alert at once. The seal isn't secret: someone who holds the database file and knows what they're doing can recalculate the whole chain. So limit access to the server and keep backups elsewhere, for comparison.</td></tr>
            <tr><td>Keeping sensitive data out of logs</td><td>Hiding before storing, encrypting what is stored, and server lines without content.</td><td>—</td></tr>
            <tr><td>Tracking admin actions</td><td>The change log: creating, updating, archiving and restoring accounts, teams, models, sources and documents, and policy changes, including the before and after values.</td><td>—</td></tr>
            <tr><td>End-to-end request tracing</td><td>Every request gets an ID number, returned to the app in the <code>x-request-id</code> header and stored in the token log and the blocked-requests log. An app can send its own number; it is kept only if it is up to 64 characters of English letters, digits, dot, underscore and hyphen.</td><td>Store the number in the app's own logs too, to find a request on both sides.</td></tr>

            <tr class="group"><th colspan="3">8. Rate limiting and abuse</th></tr>
            <tr><td>Brute Force</td><td>Guessing passwords by force. 5 wrong passwords lock the account for 15 minutes. 10 failed sign-ins from one address within 15 minutes, for any names, block that address (code 429). The response time is the same even for a username that doesn't exist. Wrong guesses of the admin password from outside count toward this limit too, and every wrong attempt is recorded as a security event.</td><td>Give the admin password at least 16 characters ("Health check" warns about a shorter one).</td></tr>
            <tr><td>Token Abuse</td><td>Using a stolen key, or using a key excessively. A key can be revoked at once and given an expiry date, and an account can be given a daily token quota (0 = no quota).</td><td>Give apps an expiry date and a daily quota.</td></tr>
            <tr><td>Account Takeover</td><td>Taking over someone else's account. Lockout after wrong passwords; a sign-in lasts 12 hours, in a cookie that code on the page can't read; changing the password signs out every device.</td><td>Give each employee their own password, and turn off <code>OPEN_ACCESS</code> once there are real users.</td></tr>
            <tr><td>Request Flooding</td><td>Flooding with requests. A requests-per-minute limit per account, up to 4 questions at once (beyond that, code 429), and limited request size.</td><td>Give every account a requests-per-minute limit.</td></tr>
            <tr><td>Token/Quota Exhaustion</td><td>One or more questions that use up the quota. Answers are limited to 8,192 tokens, up to 500 messages per request, and a daily quota and budget per account.</td><td>—</td></tr>
            <tr><td>Cost Abuse</td><td>A personal monthly budget and a team budget: an alert at 80%, blocking at 100%. Cost spike: if an account spent more than $5 in the last hour and also more than 5 times its average hour over the week before, an event is recorded and an alert appears on the "To handle" page, with a link to that user's screen, once a day per account.</td><td>Also set a spending limit with each provider.</td></tr>

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
          <li>The server goes out to the internet only to the AI providers (<code>api.anthropic.com</code>, <code>api.openai.com</code>, <code>generativelanguage.googleapis.com</code>), the company's MCP servers and model server, and the monthly summary's mail server if one is set. Everything else is blocked.</li>
          <li>Rotate the provider keys from time to time, and give each one a spending limit at the provider.</li>
          <li>Updating: <code>docker compose build --pull &amp;&amp; docker compose up -d</code></li>
          <li>On every code change, automated checks run on GitHub: the gateway's tests, a search for known vulnerabilities in the packages (pip-audit), a search for leaked keys across the whole code history (gitleaks), a container scan (Trivy), and a list of everything in the container (SBOM).</li>
          <li>Dependabot proposes updates once a week. All versions are pinned, with a fingerprint for every file.</li>
          <li>Found a vulnerability? Report it privately on GitHub (Security → Report a vulnerability), not in a public discussion. Details are in <code>SECURITY.md</code>.</li>
        </ul>`,

  "#logs": `
        <h2>Token log</h2>
        <p>The last 200 questions: "When", "Who", "Team", "Model", "Tokens in", "Tokens out" and "Cost". "Question and answer" opens the full question and answer. You can filter by name, team or model, and clicking a name opens the <a href="#user-page">user screen</a>. All questions are kept in the database, including those not shown here, and they count in the reports and on the user screen.</p>`,

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
          <li>In the <code>model</code> field, send the model's alias. In a new installation: <code>fast</code> (Claude Haiku 4.5), <code>smart</code> (Claude Sonnet 5.5), <code>gpt-fast</code> (GPT-6 Luna), <code>gpt-smart</code> (GPT-6.1 Sol), <code>gemini-fast</code> (Gemini 3.8 Flash) and <code>gemini-smart</code> (Gemini 3.1 Pro). The current list is on the <a href="#models">Models page</a>.</li>
          <li>Claude through <code>/v1/messages</code>; GPT, Gemini and <a href="#local">models on the company server</a> through <code>/v1/chat/completions</code>.</li>
          <li>Streamed answers (<code>stream</code>, meaning the answer arrives in pieces as it is written) are supported, and tokens are counted for them too.</li>
          <li>The <code>x-gateway-model</code> header in the response says which model actually answered (different from the one requested if the backup answered). The <code>x-request-id</code> header returns the request number, which is also stored in the token log.</li>
          <li>Errors: 400 invalid request (for example a Claude model through <code>/v1/chat/completions</code>, or more than 500 messages); 401 invalid or expired key; 402 the personal or team budget is used up; 403 model not allowed, turned off or not allowed for the team, or a question blocked by the policy; 413 request too large; 429 too many requests per minute, the daily token quota is used up, or more than 4 questions at once; 502 provider unavailable or didn't answer in time. An error the provider itself returned is passed on to the app as it is, if the backup didn't help either.</li>
          <li>When the policy is "Send to the local model", a question with sensitive data is answered by the local model even if the app asked for another one; <code>x-gateway-model</code> shows it.</li>
          <li><b>Admin addresses for scripts</b> (everything starting with <code>/admin/api/</code>, such as the chargeback report or the archive list): open from the office network. From outside, send the admin password in the <code>x-admin-password</code> header. An app key doesn't open them.</li>
        </ul>`,

  "#settings": `
        <h2>Settings screen</h2>
        <p>Everything that can be adjusted in the gateway is on the admin screen, under "System" &gt; "Settings". At the top there is a search: type "budget" or "email" and see every related setting, from every section. The sections are listed on the side (a drop-down on a phone).</p>
        <ul>
          <li><b>Where a value comes from:</b> a value in the server's settings file (<code>.env</code> or an environment variable) always wins, and is shown locked with an explanation. Next comes the value saved on the screen, then the default. The defaults are how the gateway behaved before the screen existed, so if you change nothing, nothing changes.</li>
          <li><b>Saving:</b> a change marks the setting, and a bar at the bottom says there are unsaved changes. Saving is all or nothing: if one value is invalid nothing is saved and the error shows next to that setting. A sensitive setting (such as turning off the hiding of sensitive data) asks for confirmation with the old and new value. Most settings apply at once.</li>
          <li><b>Log:</b> every change is recorded in the <a href="#audit">change log</a> with the old and new value. Secrets are recorded only as "changed".</li>
          <li><b>Secrets</b> (provider keys, the admin password, the mail password): keep them in the settings file, or enter them on the screen. There they are stored encrypted and never shown again, only "set" and when they were last checked. "Check" sends a short question to the provider, or a test email to an address you type.</li>
          <li><b>Per-team values:</b> the sensitive-data policy, attempts to get around instructions, the kinds of sensitive data and the organization's words can differ for one team. Set them when editing the team, under "Special settings". The screen shows how many teams have their own value.</li>
          <li><b>Export and import:</b> under "System". The export is a JSON file without secrets; the import shows what would change before it applies. There are also "Back up now" (a full copy of the database to a folder next to it; old backups are never deleted) and "Check for updates" (compares with the latest version on GitHub, only when clicked).</li>
          <li>Every screen whose setting moved here (automatic choice, security policy, local server, monthly email) keeps a line with the current value and a "Change in settings" link that opens this screen right at that setting.</li>
        </ul>
        <h3 id="settings-general">General</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Organization name</td><td>Empty</td><td>—</td><td>Shown at the top of the chat screen and in the monthly email's subject. Empty = FireGate only.</td></tr>
            <tr><td>Default language for new visitors</td><td>Hebrew</td><td>—</td><td>The language the screens open in for someone who hasn't picked one in their browser yet.</td></tr>
            <tr><td>Time zone</td><td>Empty</td><td>—</td><td>Sets when a day and a month begin in reports, budgets, the monthly email and backups. Empty = the server's clock.</td></tr>
            <tr><td>Home page of the main address</td><td>Admin screen</td><td>—</td><td>What opens at the gateway's address without a path. The admin screen is always at /admin too.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-access">Sign-in and access</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Chat without a password on the office network <span class="muted">(Asks for confirmation)</span></td><td>Off</td><td><code>OPEN_ACCESS</code></td><td>Anyone on the office network picks their name and goes in. Handy at first, but anyone can use someone else's budget.</td></tr>
            <tr><td>Sign in with the company account <span class="muted">(Coming soon)</span></td><td>Off</td><td>—</td><td>Chat sign-in with the company account (Microsoft or Google), with no separate password.</td></tr>
            <tr><td>Admin password from outside <span class="muted">(Asks for confirmation)</span></td><td>Empty</td><td><code>ADMIN_PASSWORD</code></td><td>From the office network the admin screen opens without a password. From outside it needs this one. Without it the screen is closed from outside. At least 16 characters is recommended.</td></tr>
            <tr><td>Exposure to the internet <span class="muted">(Coming soon)</span></td><td>Office network only</td><td>—</td><td>Where the gateway can be reached from. Needed for Cursor and Copilot for business.</td></tr>
            <tr><td>Hosted in the cloud (no office network) <span class="muted">(Asks for confirmation)</span></td><td>Off</td><td><code>PUBLIC_DEPLOY</code></td><td>When the gateway can't tell the office from outside: the admin screen always needs the password and password-free chat is off.</td></tr>
            <tr><td>Allowed host names</td><td>Empty</td><td><code>ALLOWED_HOSTS</code></td><td>Extra names the gateway answers to (one per line). IP addresses and localhost always work. Stops a hostile site posing as the gateway.</td></tr>
            <tr><td>Trusted proxies <span class="muted">(Asks for confirmation)</span></td><td>127.0.0.1, ::1</td><td><code>TRUSTED_PROXIES</code></td><td>Addresses (or ranges) of servers that pass on the user's address, such as Caddy. Anyone else's claim is ignored.</td></tr>
            <tr><td>Chat sign-in lasts</td><td>12 hours</td><td>—</td><td>How long until an employee has to sign in again.</td></tr>
            <tr><td>Lock an account after</td><td>5 tries</td><td>—</td><td>Wrong passwords in a row before the account locks.</td></tr>
            <tr><td>Lock lasts</td><td>15 minutes</td><td>—</td><td>How long a locked account stays locked.</td></tr>
            <tr><td>Block an address after</td><td>10 failures</td><td>—</td><td>Wrong passwords from one address, across all names (admin password included), before that address is blocked.</td></tr>
            <tr><td>Counting window and block time</td><td>15 minutes</td><td>—</td><td>Over how many minutes failures count, and how long the address waits.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-providers">Providers and keys</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Anthropic key <span class="muted">(Asks for confirmation)</span></td><td>Empty</td><td><code>ANTHROPIC_API_KEY</code></td><td>Stored encrypted and never shown again. A provider without a key doesn't work.</td></tr>
            <tr><td>Address</td><td><code>https://api.anthropic.com/v1/messages</code></td><td><code>ANTHROPIC_URL</code></td><td>Where the gateway sends questions. Change it only when the company routes traffic through its own intermediate server.</td></tr>
            <tr><td>OpenAI key <span class="muted">(Asks for confirmation)</span></td><td>Empty</td><td><code>OPENAI_API_KEY</code></td><td>Stored encrypted and never shown again. A provider without a key doesn't work.</td></tr>
            <tr><td>Address</td><td><code>https://api.openai.com/v1/chat/completions</code></td><td><code>OPENAI_URL</code></td><td>Where the gateway sends questions. Change it only when the company routes traffic through its own intermediate server.</td></tr>
            <tr><td>Google key <span class="muted">(Asks for confirmation)</span></td><td>Empty</td><td><code>GEMINI_API_KEY</code></td><td>Stored encrypted and never shown again. A provider without a key doesn't work.</td></tr>
            <tr><td>Address</td><td><code>https://generativelanguage.googleapis.com/v1beta/openai/chat/completions</code></td><td><code>GEMINI_URL</code></td><td>Where the gateway sends questions. Change it only when the company routes traffic through its own intermediate server.</td></tr>
            <tr><td>Server address</td><td>Empty</td><td>—</td><td>The company's Ollama or vLLM server, e.g. http://ollama:11434/v1. Empty = none. After a check, add its models on the Models page.</td></tr>
            <tr><td>Server key <span class="muted">(Asks for confirmation)</span></td><td>Empty</td><td><code>LOCAL_API_KEY</code></td><td>Only if the server needs a key.</td></tr>
            <tr><td>May connect to this machine itself <span class="muted">(Asks for confirmation)</span></td><td>Off</td><td><code>ALLOW_LOCAL_LOOPBACK</code></td><td>When the local server runs on the gateway's own machine (localhost).</td></tr>
            <tr><td>More providers <span class="muted">(Coming soon)</span></td><td>Empty</td><td>—</td><td>Azure, Bedrock, Vertex, Mistral, DeepSeek, Groq, xAI, OpenRouter, or any OpenAI-compatible server with an address and key.</td></tr>
            <tr><td>Refresh the model list from the provider <span class="muted">(Coming soon)</span></td><td>Manual</td><td>—</td><td>Read which models the provider offers.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-models">Models and routing</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Default chat model</td><td>fast</td><td>—</td><td>The model the chat uses when an employee picked none, and that a new user gets.</td></tr>
            <tr><td>Longest answer</td><td>8,192 tokens</td><td><code>MAX_OUTPUT_TOKENS</code></td><td>An app asking for more gets this number. 0 = by model: no limit (chat with Claude sends 32,000, because Claude needs a number).</td></tr>
            <tr><td>Provider cache in chat</td><td>5 minutes</td><td>—</td><td>Claude re-reads the conversation from its cache at a tenth of the price. An hour costs more to write; worth it for chats with long pauses.</td></tr>
            <tr><td>Backup model when a provider fails</td><td>On</td><td>—</td><td>Off = no model falls back to its backup, even if one is set on the Models page.</td></tr>
            <tr><td>Automatic choice</td><td>On</td><td>—</td><td>An employee who picks "Automatic" in chat: short simple questions go to the cheap model; code, analysis, long text or a long chat to the strong one.</td></tr>
            <tr><td>Cheap model</td><td>fast</td><td>—</td><td>For short simple questions.</td></tr>
            <tr><td>Strong model</td><td>smart</td><td>—</td><td>For code, analysis, comparisons and long text.</td></tr>
            <tr><td>Prefer the fast model</td><td>Off</td><td>—</td><td>Among suitable models at a similar price, at any provider the employee may use: the one that answered fastest lately.</td></tr>
            <tr><td>Similar-price range</td><td>2 times</td><td>—</td><td>How many times higher or lower still counts as a similar price.</td></tr>
            <tr><td>Minimum answers</td><td>20 answers</td><td>—</td><td>A model counts only with at least this many answers in the window.</td></tr>
            <tr><td>Measuring window</td><td>24 hours</td><td>—</td><td>How many hours back speed is measured.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-budgets">Budgets and quotas</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Early warning</td><td>80%</td><td>—</td><td>At what share of the budget a warning shows on the dashboard and on "To handle".</td></tr>
            <tr><td>When the budget runs out <span class="muted">(Asks for confirmation)</span></td><td>Block</td><td>—</td><td>Block: requests are refused. Alert only: requests go through and an event is recorded. Switch to the cheap model: requests go to the automatic choice's cheap model, if allowed; otherwise blocked.</td></tr>
            <tr><td>Budget reset day</td><td>1 of the month</td><td>—</td><td>The day of the month a new budget month starts. Reports and chargeback count from this day too. A change recalculates this month's spending from the log.</td></tr>
            <tr><td>Monthly budget</td><td>Empty</td><td>—</td><td>Prefilled for a new user. Empty = the field starts empty and must be filled.</td></tr>
            <tr><td>Requests per minute</td><td>0</td><td>—</td><td>0 = no limit.</td></tr>
            <tr><td>Tokens per day</td><td>0</td><td>—</td><td>0 = no limit.</td></tr>
            <tr><td>Allowed models</td><td>Empty</td><td>—</td><td>None ticked = the default model only.</td></tr>
            <tr><td>Questions at once per person</td><td>4</td><td><code>MAX_CONCURRENT</code></td><td>More than this at once is refused. Stops a stuck app from draining a budget.</td></tr>
            <tr><td>Most messages in one request</td><td>500</td><td><code>MAX_MESSAGES</code></td><td>A request with more messages is refused.</td></tr>
            <tr><td>Largest request: uploads and apps</td><td>40 MB</td><td><code>MAX_BODY</code></td><td>Uploaded documents, and app requests (which may carry images and PDFs).</td></tr>
            <tr><td>Largest request: everything else</td><td>1 MB</td><td><code>MAX_REQUEST_BODY</code></td><td>Chat questions and admin changes.</td></tr>
            <tr><td>Cost spike: times the usual</td><td>5 times</td><td>—</td><td>Alert when a person's last hour cost this many times their average hour that week.</td></tr>
            <tr><td>Cost spike: minimum</td><td>5 $</td><td>—</td><td>An hour cheaper than this never alerts, even if unusual.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-security">Security and policy</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Attempts to get around the model's instructions <span class="muted">(Can differ per team, Asks for confirmation)</span></td><td>Block</td><td>—</td><td>What happens to a question trying to free the model from its rules.</td></tr>
            <tr><td>Sensitive data in a question <span class="muted">(Can differ per team, Asks for confirmation)</span></td><td>Hide</td><td>—</td><td>Hide: the data is replaced before the question leaves. Local model: answered unmasked on the company's server, if the person has such a model; otherwise hidden.</td></tr>
            <tr><td>Kinds of sensitive data <span class="muted">(Can differ per team, Asks for confirmation)</span></td><td>ID number, Credit card, Secrets and keys, Phone, Email, IBAN, Bank account, Passport</td><td>—</td><td>What is hidden in questions before they leave for the provider, and in the log.</td></tr>
            <tr><td>The organization's words and phrases <span class="muted">(Can differ per team)</span></td><td>Empty</td><td>—</td><td>Project names, customers or codes that must not leave. One per line; hidden like sensitive data.</td></tr>
            <tr><td>What is scanned <span class="muted">(Coming soon)</span></td><td>The whole context</td><td>—</td><td>Only the last message, or the whole context: instructions, tool results and earlier messages.</td></tr>
            <tr><td>Files in a request (images, PDF, audio) <span class="muted">(Coming soon, Can differ per team)</span></td><td>Allow and check PDF text</td><td>—</td><td>What happens to files an employee or app sends to a model.</td></tr>
            <tr><td>Warn about dangerous commands in answers <span class="muted">(Asks for confirmation)</span></td><td>On</td><td>—</td><td>A command that wipes data or runs code from the internet gets a warning for the employee. The event is recorded either way.</td></tr>
            <tr><td>Warn about suspicious links in answers <span class="muted">(Asks for confirmation)</span></td><td>On</td><td>—</td><td>A link to a numeric address, a link shortener or a look-alike name gets a warning. The event is recorded either way.</td></tr>
            <tr><td>Hide keys in answers <span class="muted">(Asks for confirmation)</span></td><td>On</td><td>—</td><td>An access key or password in an answer is hidden before it reaches the employee, the app and the log.</td></tr>
            <tr><td>Internal addresses for MCP servers <span class="muted">(Asks for confirmation)</span></td><td>On</td><td><code>ALLOW_PRIVATE_MCP</code></td><td>MCP servers on the company network may be connected. Off = only servers on the internet.</td></tr>
            <tr><td>Folders allowed for knowledge sources <span class="muted">(Asks for confirmation)</span></td><td>Empty</td><td><code>SOURCE_ROOTS</code></td><td>A server folder connected as a knowledge source must be inside one of these (one per line). Empty = any folder.</td></tr>
            <tr><td>Warn before a key expires</td><td>14 days</td><td>—</td><td>How many days before the expiry date a warning shows.</td></tr>
            <tr><td>Warn about an old key</td><td>90 days</td><td>—</td><td>A key in use longer than this gets a replace recommendation.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-data">Content, storage and encryption</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>What the log keeps</td><td>Question and answer (masked)</td><td>—</td><td>Question and answer (with sensitive data hidden), or data only: who, when, model, tokens and cost, without the text. Applies from now on.</td></tr>
            <tr><td>Files in the log <span class="muted">(Coming soon)</span></td><td>Description only (type, size, fingerprint)</td><td>—</td><td>What is kept about a file sent to a model.</td></tr>
            <tr><td>Automatic backup</td><td>Off</td><td>—</td><td>A full copy of the database. Old backups are never deleted.</td></tr>
            <tr><td>Backup folder</td><td>backups</td><td>—</td><td>A folder name next to the database (letters, digits, dot, dash).</td></tr>
          </tbody>
        </table>
        <h3 id="settings-sources">Knowledge sources</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Searching documents</td><td>Both</td><td>—</td><td>By meaning needs an OpenAI or Google key; without one, search by words remains.</td></tr>
            <tr><td>Provider for search by meaning</td><td>Automatic</td><td><code>EMBEDDINGS</code></td><td>Who turns text into the numbers that make search by meaning work. Automatic = the first one with a key.</td></tr>
            <tr><td>Largest file</td><td>5 MB</td><td>—</td><td>A larger file isn't taken in.</td></tr>
            <tr><td>Passages sent to the model</td><td>6 passages</td><td>—</td><td>At most how many document passages go with each question.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-alerts">Alerts and reports</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Send automatically</td><td>Off</td><td>—</td><td>A summary of last month: spending, teams, users, models, savings recommendations and security.</td></tr>
            <tr><td>Recipients</td><td>Empty</td><td>—</td><td>Email addresses, separated by commas. Up to 50.</td></tr>
            <tr><td>Sending day</td><td>1 of the month</td><td>—</td><td>The day of the month the summary goes out.</td></tr>
            <tr><td>Sending hour</td><td>8:00</td><td>—</td><td>From this hour on, in the chosen time zone.</td></tr>
            <tr><td>Mail server address</td><td>Empty</td><td><code>SMTP_HOST</code></td><td>Empty = no email is sent.</td></tr>
            <tr><td>Port</td><td>587</td><td><code>SMTP_PORT</code></td><td>587 with STARTTLS, 465 with SSL.</td></tr>
            <tr><td>User name</td><td>Empty</td><td><code>SMTP_USER</code></td><td>If the server needs a sign-in.</td></tr>
            <tr><td>Password <span class="muted">(Asks for confirmation)</span></td><td>Empty</td><td><code>SMTP_PASSWORD</code></td><td>Stored encrypted and never shown again.</td></tr>
            <tr><td>Sender address</td><td>Empty</td><td><code>SMTP_FROM</code></td><td>Empty = the user name.</td></tr>
            <tr><td>Encryption</td><td>STARTTLS (port 587)</td><td><code>SMTP_TLS</code></td><td>No encryption only for a mail server inside the network.</td></tr>
            <tr><td>Alert channels <span class="muted">(Coming soon)</span></td><td>Empty</td><td>—</td><td>Email, Slack or Teams: an address the gateway sends a message to.</td></tr>
            <tr><td>Which alerts go out <span class="muted">(Coming soon)</span></td><td>Budget, Security</td><td>—</td><td>What is sent to the channels.</td></tr>
            <tr><td>Slower than usual by</td><td>2 times</td><td>—</td><td>Alert when the last hour's answer time (95% of answers) is this many times the week before.</td></tr>
            <tr><td>Minimum answers in the hour</td><td>10 answers</td><td>—</td><td>Fewer answers than this never alert.</td></tr>
            <tr><td>Short question: tokens in</td><td>2,000 tokens</td><td>—</td><td>Up to how many tokens in a question counts as short.</td></tr>
            <tr><td>Short question: tokens out</td><td>600 tokens</td><td>—</td><td>Up to how many tokens in the answer.</td></tr>
            <tr><td>Smallest saving shown</td><td>5 $</td><td>—</td><td>A recommendation saving less a month isn't shown.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-capabilities">Provider capabilities</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Allowed capabilities <span class="muted">(Coming soon, Can differ per team)</span></td><td>Images, Audio, Files, Batch, Embeddings, Video</td><td>—</td><td>What may be sent to providers.</td></tr>
            <tr><td>Providers' built-in tools <span class="muted">(Coming soon)</span></td><td>Web search, File search, Code execution, MCP</td><td>—</td><td>Tools the model runs by itself.</td></tr>
            <tr><td>Real-time voice <span class="muted">(Coming soon)</span></td><td>Off</td><td>—</td><td>Voice conversation with a model, with minute and connection limits.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-devtools">Developer tools</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Allowed tools <span class="muted">(Coming soon)</span></td><td>Claude Code, Codex, Cursor, Copilot, Gemini CLI</td><td>—</td><td>Developer tools allowed through the gateway.</td></tr>
            <tr><td>Record the tool in the log <span class="muted">(Coming soon)</span></td><td>On</td><td>—</td><td>Which tool made each request.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-browser">Browser</h3>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>In the server file</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td>Browser extension <span class="muted">(Coming soon)</span></td><td>Off</td><td>—</td><td>Watches public AI sites from employees' browsers.</td></tr>
            <tr><td>Watched sites <span class="muted">(Coming soon)</span></td><td>chatgpt.com, claude.ai, gemini.google.com, copilot.microsoft.com, perplexity.ai, chat.deepseek.com</td><td>—</td><td>One per line.</td></tr>
            <tr><td>When sensitive data is found <span class="muted">(Coming soon)</span></td><td>Follow the security policy</td><td>—</td><td>What the extension does.</td></tr>
            <tr><td>What is reported to the gateway <span class="muted">(Coming soon)</span></td><td>Only what was found and done</td><td>—</td><td>How much the extension sends.</td></tr>
            <tr><td>Unapproved sites <span class="muted">(Coming soon)</span></td><td>Empty</td><td>—</td><td>Redirected to the company chat.</td></tr>
            <tr><td>Tell the employee monitoring is on <span class="muted">(Coming soon)</span></td><td>On</td><td>—</td><td>Locked on, as the law requires.</td></tr>
          </tbody>
        </table>
        <h3 id="settings-file">Only in the settings file</h3>
        <p>These are set only in the <code>.env</code> file or as environment variables, and need a restart.</p>
        <table>
          <thead><tr><th>Setting</th><th>Default</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td><code>PORT</code></td><td><code>8080</code></td><td>The port the gateway listens on.</td></tr>
            <tr><td><code>GATEWAY_DB</code></td><td><code>gateway.db</code> in the folder it is started from (with Docker: <code>/data/gateway.db</code>)</td><td>Where the data file lives. The encryption key file and the backups are kept next to it.</td></tr>
            <tr><td><code>FIREGATE_DATA_KEY</code></td><td>Empty = the key file next to the database</td><td>The encryption key. See <a href="#encryption">Encryption and the encryption key</a>.</td></tr>
            <tr><td><code>SITE_ADDRESS</code></td><td>Empty (with Docker: <code>:80</code>, unencrypted)</td><td>Domain for an automatically encrypted connection. The gateway answers to this name.</td></tr>
            <tr><td><code>OPENAI_EMBED_MODEL</code>, <code>GEMINI_EMBED_MODEL</code></td><td><code>text-embedding-3-small</code>, <code>gemini-embedding-001</code></td><td>The model that works out the documents' "meaning fingerprints", at each provider.</td></tr>
            <tr><td><code>SEED_DEMO</code></td><td>Off</td><td><code>1</code> = on every start, fill an empty system with sample data. Meant for a demo on a server whose disk resets (such as Render's free plan).</td></tr>
            <tr><td><code>DEMO_PASSWORD</code>, <code>SEED_SOURCES_DIR</code></td><td>The password written in <code>seed_demo.py</code>; the <code>sources/it</code> folder next to the project</td><td>For sample data only: the chat password of the sample users, and the folder the sample documents are read from.</td></tr>
            <tr><td><code>RENDER_EXTERNAL_HOSTNAME</code></td><td>Set by Render on its own</td><td>The server's name on Render. The gateway adds it to the names it answers to.</td></tr>
          </tbody>
        </table>
        <p>For on/off settings in the file, <code>1</code>, <code>true</code>, <code>yes</code> or <code>on</code> turn it on; anything else turns it off. An empty variable counts as not set. The security settings are also explained in <a href="#security-settings">Server security settings</a>.</p>`,

  "#limits": `
        <h2>Known limitations</h2>
        <ul>
          <li>In open mode, anyone on the network can pick any name and use that person's budget.</li>
          <li>Without a domain the connection is not encrypted.</li>
          <li>Questions and answers are kept with no time limit.</li>
          <li>Nothing is ever deleted: whatever leaves use moves to the <a href="#archive">archive</a> and stays in the database. If something truly has to be deleted (for example by law), there is no button for it.</li>
          <li>A scanned PDF (an image with no text) can't be read.</li>
          <li>The requests-per-minute limit is kept in memory and resets when the gateway restarts.</li>
          <li>The admin password from outside is shared by all admins. Wrong guesses count together with chat passwords: 10 failures from one address within 15 minutes block that address. A long password, at least 16 characters, is still advised.</li>
          <li>Alerts appear only on the admin screen; there are no alerts by email, Teams or Slack yet. Only the <a href="#summary">monthly summary</a> goes out by email.</li>
          <li>The monthly summary assumes a single gateway is running. If several copies of the gateway run on the same database, the same month may be sent twice.</li>
          <li>Savings recommendations are an estimate: they assume the same short questions would work well on the cheap model, and don't check answer quality.</li>
          <li>Questions from before speed monitoring was added have no times. Answer time includes the network trip to the provider, and a long answer naturally takes longer, so comparing models is fair only when they answer similar work.</li>
          <li>A local model server that returns no token counts gets an estimate (about one token for every four characters), so the daily token quota is approximate for it.</li>
        </ul>`,

  "#todo": `
        <h2>To handle</h2>
        <p>The page that gathers everything waiting for the admin. Next to "To handle" in the menu is the number of open items: steps not yet done, alerts and savings recommendations. It has three parts:</p>
        <ul>
          <li><b>Getting started:</b> shown until the system is ready, with four steps: connect a provider (put a key in the <code>.env</code> file and restart the gateway), create a team, create a first user, and ask a first question in the chat. A step not yet done has a "Do it" button.</li>
          <li><b>Needs attention:</b> everything that needs a look, most serious first. Each item has "Details", which leads to the user's screen or the relevant page. When there is nothing, it says "All good". What shows up here:
            <ul>
              <li>A user or team past 80% of their budget, or whose budget has run out. They are then blocked until the 1st of the month or until the budget is raised.</li>
              <li>An account locked after 5 wrong passwords. A new password in the edit window releases it.</li>
              <li>An app key that has expired, will expire within 14 days, or has been in use for more than 90 days.</li>
              <li>Unusual spend by an account in the last hour: more than $5 and also more than 5 times its usual hour.</li>
              <li>Change-log rows that were altered or deleted outside the system.</li>
              <li>A provider answering slower than usual (see <a href="#speed">Speed monitoring</a>).</li>
              <li>Any check that failed in "Health check" on the <a href="#security">Security</a> page, for example an unencrypted connection or keys without a rate limit.</li>
            </ul>
          </li>
          <li><b>Savings recommendations:</b> all of them, each with an action button. This part appears only when there are recommendations.</li>
        </ul>
        <h3 id="savings">Savings recommendations</h3>
        <p>The gateway looks at the last 30 days for places where the same work could cost less. The dashboard shows the three biggest recommendations and the total that could be saved per month; the "To handle" page shows all of them. Three kinds:</p>
        <ul>
          <li><b>Short questions to a strong model:</b> a team (or an account without a team) sending short questions, up to 2,000 tokens in and 600 out, to a strong, expensive model. A model counts as strong if it is automatic choice's strong model, or costs at least 2 times the cheap model. The gateway works out what the same questions would have cost on the same provider's cheap model (automatic choice's cheap model if it's from that provider, otherwise the provider's cheapest model that is on), with the same tokens and the same cache prices, and shows the difference per month. It appears only when the saving is at least $5 a month, and only when the team may use the cheap model. The button ("Turn on automatic choice", or "Automatic choice settings" if it is already on) opens <a href="#auto">automatic choice</a>, which does exactly this in the chat.</li>
          <li><b>A team spending almost everything on the expensive model:</b> more than 80% of the team's spend goes to the provider's most expensive model, and the total is at least $5 a month. The recommendation suggests checking the model one step below (one the team may use); this saving can't be worked out in advance, since not all work suits a simpler model.</li>
          <li><b>A model that is on but unused:</b> on for more than 30 days with no question in the last 30. The "Turn the model off" button turns it off, after a confirmation. The default model is never listed.</li>
        </ul>
        <p>With less than 30 days of usage, the numbers are scaled up to a full month (under a week counts as a week, so one busy day doesn't look like a month). Connection tests, document indexing, and archived users and teams aren't counted.</p>`,

  "#audit": `
        <h2>Change log</h2>
        <p>Every admin action, with "When", "Action" and "Details": creating, updating, archiving and restoring accounts, teams, models, sources and documents; issuing and revoking keys; uploading documents and syncing a folder; the default model, automatic choice and the local model server's address; security policy changes; and the monthly summary's settings and sending. Budget and price changes show the value before and after. An employee moving one of their chats to the archive, or restoring it, is recorded here too.</p>
        <p>There is no way to delete a row from the log. Each row is "signed" together with the row before it, so changing or deleting a row outside the system is detected: the "Change log is intact" card on the <a href="#security">Security</a> page shows whether everything is intact, and the "To handle" page warns if it isn't.</p>`,
});
