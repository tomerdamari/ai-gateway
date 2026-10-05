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
            <li><a href="#accounts">Users and keys</a></li>
            <li><a href="#teams">Teams and budgets</a></li>
            <li><a href="#models">Models</a></li>
            <li class="sub"><a href="#backup">Backup model</a></li>
            <li class="sub"><a href="#auto">Automatic selection</a></li>
            <li class="sub"><a href="#cache">Provider-side cache</a></li>
            <li><a href="#sources">Knowledge sources</a></li>
            <li class="sub"><a href="#mcp">MCP connections</a></li>
            <li><a href="#reports">Reports</a></li>
            <li><a href="#security">Security</a></li>
            <li><a href="#logs">Logs</a></li>
          </ul></div>
          <div><h3>Technical</h3><ul>
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
          <li><span><b>Protection:</b> ID numbers, credit cards and keys are hidden, and suspicious content is logged.</span></li>
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
        <pre>python gateway.py</pre>
        <p>The gateway reads the <code>.env</code> next to its files and comes up at <code>http://localhost:8080</code>. It has no external package dependencies, except <code>pypdf</code> for reading PDFs (optional).</p>
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
          <li>Conversations are saved in a list on the side, and the employee can go back to them or delete them. Deleting removes the conversation from the employee's list; the copy in the admin log stays.</li>
          <li>At the bottom of the menu: how much of the budget the employee and their team have spent this month, and how much is left.</li>
          <li>An answer that includes a command that could delete data or run code from the internet gets a warning at its end.</li>
          <li>An answer can be stopped midway with the "Stop" button.</li>
        </ul>`,

  "#overview": `
        <h2>Dashboard</h2>
        <p>The gateway's main screen (<code>/</code>, and also <code>/admin</code>). From the office network it opens without a password; from outside only with <code>ADMIN_PASSWORD</code>.</p>
        <ul>
          <li><b>First steps:</b> shown until the system is ready: connecting a provider, a team, a user and a first question, with a button for each step.</li>
          <li><b>Needs attention:</b> budget overruns (from 80% and from 100%), locked accounts and open security notes. When there is nothing, it says "All good".</li>
          <li><b>Four numbers:</b> spend this month, forecast for the end of the month, requests, and active users. Each with the percentage change from the previous week or month.</li>
          <li><b>Charts:</b> daily spend over the last 30 days (hover to see the day), spend split by model, the users who spent the most, and teams against their budget.</li>
          <li><b>Cumulative spend this month:</b> a line that rises day by day, against the previous month and against the total of the team budgets, with a dashed line that continues the current pace to the end of the month.</li>
          <li><b>Budget usage forecast:</b> how many users will finish the month under half of their budget, close to it, or over it. Bars above 100% are colored as a warning.</li>
          <li><b>When people ask:</b> a heat map of requests by day of the week and hour over the last four weeks. Helps you see peak hours and plan rate limits.</li>
          <li><b>Monthly spend by team:</b> the last four months, each month split into the five largest teams and "Other".</li>
        </ul>`,

  "#accounts": `
        <h2>Users and keys</h2>
        <p>Every employee, app or customer is an account. Each account has:</p>
        <ul>
          <li>A <b>team</b>, a <b>monthly budget</b>, <b>allowed models</b> and a <b>requests-per-minute limit</b>.</li>
          <li>A <b>chat password</b> (optional) and/or an <b>API key</b> for apps. The key is shown only once, when it's created; the gateway keeps only an encrypted fingerprint of it. A new key can be issued, or a key revoked, in the edit window.</li>
          <li><b>Forecast</b>: how much the account will spend by the end of the month at the current pace. <b>Recommended budget</b>: the higher of the forecast and last month, plus 20%.</li>
          <li>The <b>"Apply"</b> button appears only when the budget needs to go up so the account won't be blocked. Before the change there is a confirmation showing the old and new amounts, and afterwards it can be undone.</li>
        </ul>
        <p>You can search by name or team, and sort by name, team, spend or forecast. On a phone each row is shown as a card.</p>`,

  "#teams": `
        <h2>Teams and budgets</h2>
        <ul>
          <li>Each team has a monthly budget. <b>0 = no cap</b> for the team.</li>
          <li>A question is blocked when the personal budget <b>or</b> the team budget runs out.</li>
          <li>On the 1st of each month spending resets to zero; the history stays in the log.</li>
          <li>The teams screen shows the forecast, the recommended budget, and the total of the team members' budgets, so you can see whether the team cap fits them.</li>
        </ul>`,

  "#models": `
        <h2>Models</h2>
        <p>All the models the gateway offers are managed from the screen, with no code editing and no restart.</p>
        <ul>
          <li><b>Turning on and off:</b> a model that is turned off is blocked for everyone immediately. Before turning it off you see how many accounts are allowed to use it, and afterwards it can be undone.</li>
          <li><b>Adding and editing:</b> an alias (what apps send), a display name, the provider, the exact name at the provider, and prices per million tokens: input, output, and from the cache.</li>
          <li><b>Default:</b> the model that is ticked for a new user. It can't be turned off or deleted until another one is set.</li>
          <li><b>Connection test:</b> sends the provider a short question and shows whether the key and name work, and how long it took.</li>
          <li><b>Deleting:</b> only when no account is allowed to use the model.</li>
          <li><b>Charts:</b> daily spend by model, and share of requests against share of spend, to spot a model that is expensive per request.</li>
          <li>At the top, each provider shows whether it has a key in the <code>.env</code> file.</li>
        </ul>
        <h3 id="backup">Backup model</h3>
        <p>For each model you can choose a backup model. If the provider is overloaded or not responding (errors 429, 5xx, 529), the question moves to the backup on its own and is charged at the backup's price. The log records that the backup answered, and the models screen shows how many times that happened this month. For apps, the backup only works between models with the same format: Claude with Claude, or GPT with Gemini.</p>
        <h3 id="auto">Automatic selection</h3>
        <p>Set a cheap model and a strong model, and turn it on. A long question (over 1,200 characters), code, analysis, comparison, planning, or a long conversation goes to the strong one; everything else to the cheap one. If the matching model isn't allowed for the employee, the other one is chosen. The screen shows how many questions were routed this month.</p>
        <h3 id="cache">Provider-side cache</h3>
        <p>In conversations with Claude, the gateway asks the provider to keep the start of the conversation, and on the next turn it is read at about a tenth of the price. OpenAI and Gemini do this on their own. The cost is calculated using each model's cache price, and the monthly savings are shown on the screen.</p>`,

  "#sources": `
        <h2>Knowledge sources</h2>
        <p>The company documents the chat searches and quotes from. For each source you choose which teams may search it, or "All employees". An employee will never get a passage from a source their team wasn't given access to.</p>
        <h3>Source types</h3>
        <table>
          <thead><tr><th>Type</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td><b>Uploaded files</b></td><td>PDF, Word (docx) and text files (Markdown, CSV, HTML, JSON and more), up to 5MB per file.</td></tr>
            <tr><td><b>Folder on the server</b></td><td>"Sync now" reads all the files in the folder. Files that were deleted drop out of search. With Docker: the <code>sources</code> folder next to the project.</td></tr>
            <tr><td><b>MCP server</b></td><td>Information from another system. See <a href="#mcp">MCP connections</a>.</td></tr>
          </tbody>
        </table>
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
          <li><b>Sync:</b> the server's documents are copied into the index, like a folder.</li>
        </ul>
        <p>Every response from the server goes through sensitive-data hiding and a check for suspicious content. A response that tries to give the model instructions is blocked and logged. The access key is kept on the server and never sent back to the browser.</p>`,

  "#reports": `
        <h2>Reports</h2>
        <p>Pick a month and see spend, requests, tokens and number of people, by team (including budget usage), by user, and by model (including tokens from the cache). "Download for Excel" saves a CSV file that opens in Excel with Hebrew displayed correctly.</p>`,

  "#security": `
        <h2>Security</h2>
        <h3>What the gateway does on its own</h3>
        <ul>
          <li><b>Hiding sensitive data</b> before it goes out to the provider and before it is stored: valid Israeli ID numbers, credit cards and access keys.</li>
          <li><b>Detecting suspicious content</b> in questions, documents and answers: attempts to override instructions (Hebrew and English), browser code, and destructive commands. A suspicious question is logged, not blocked, because employees legitimately ask about code.</li>
          <li><b>Protection from other websites:</b> a hostile website an employee opens can't make their browser send commands to the gateway, and the gateway only answers to addresses it knows.</li>
          <li><b>Secrets stored as encrypted fingerprints:</b> API keys and passwords are not stored as plain text.</li>
          <li><b>Injected code doesn't run:</b> the browser runs only the gateway's own script files.</li>
          <li><b>Lockout</b> after 5 wrong passwords, and the same sign-in time even for a username that doesn't exist.</li>
        </ul>
        <h3>The "Security" tab</h3>
        <p>Counts for the last 7 days, a status check (encryption, admin password, keys with no rate limit, open mode, connected providers), and an event log that can be filtered by type.</p>`,

  "#logs": `
        <h2>Logs</h2>
        <ul>
          <li><b>Question log:</b> the last 200 questions with who, team, model, tokens, cost, and the full question and answer. Filter by name, team or model. All questions are kept in the database.</li>
          <li><b>Change log:</b> every admin action: creating, updating and deleting accounts, teams, models and sources, including the before and after values for budget and price changes.</li>
        </ul>`,

  "#api": `
        <h2>Connecting apps</h2>
        <p>Create an account with an API key, and in the app change just two things: the address and the key. Everything else stays the same as when talking to the provider directly.</p>
        <pre>client = anthropic.Anthropic(base_url="http://&lt;your-server&gt;", api_key="gw-...")
client.messages.create(model="smart", max_tokens=1000, messages=[...])

client = openai.OpenAI(base_url="http://&lt;your-server&gt;/v1", api_key="gw-...")
client.chat.completions.create(model="gemini-fast", messages=[...])</pre>
        <ul>
          <li>Claude through <code>/v1/messages</code>; GPT and Gemini through <code>/v1/chat/completions</code>.</li>
          <li>Streamed answers (<code>stream</code>) are supported, and tokens are counted for them too.</li>
          <li>The <code>x-gateway-model</code> header in the response says which model actually answered (different from the one requested if the backup answered).</li>
          <li>Errors: 401 invalid key, 402 budget used up, 403 model not allowed or turned off, 429 too many requests.</li>
        </ul>`,

  "#settings": `
        <h2>Server settings</h2>
        <p>In the <code>.env</code> file:</p>
        <table>
          <thead><tr><th>Setting</th><th>What it does</th></tr></thead>
          <tbody>
            <tr><td><code>ANTHROPIC_API_KEY</code>, <code>OPENAI_API_KEY</code>, <code>GEMINI_API_KEY</code></td><td>The provider keys. A provider without a key simply won't work.</td></tr>
            <tr><td><code>ADMIN_PASSWORD</code></td><td>Password for the admin screen from outside. Empty = completely closed from outside.</td></tr>
            <tr><td><code>SITE_ADDRESS</code></td><td>Domain for an automatically encrypted connection.</td></tr>
            <tr><td><code>ALLOWED_HOSTS</code></td><td>Extra server names the gateway will answer to, separated by commas.</td></tr>
            <tr><td><code>OPEN_ACCESS</code></td><td><code>1</code> = chat without signing in on the office network.</td></tr>
            <tr><td><code>EMBEDDINGS</code></td><td>Provider for search by meaning: <code>openai</code>, <code>gemini</code> or <code>off</code>. Default: the first one that has a key.</td></tr>
            <tr><td><code>PORT</code>, <code>GATEWAY_DB</code></td><td>The server port (8080) and the location of the data file.</td></tr>
          </tbody>
        </table>`,

  "#limits": `
        <h2>Known limitations</h2>
        <ul>
          <li>In open mode, anyone on the network can pick any name and use that person's budget.</li>
          <li>Without a domain the connection is not encrypted.</li>
          <li>Questions and answers are kept with no time limit.</li>
          <li>A scanned PDF (an image with no text) can't be read.</li>
          <li>The requests-per-minute limit is kept in memory and resets when the gateway restarts.</li>
          <li>Alerts appear only on the admin screen; there's no email, Teams or Slack yet.</li>
        </ul>`,
});
