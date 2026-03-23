# Codebase Structure

**Analysis Date:** 2026-03-23

## Directory Layout

```
/d/Claude/
├── .github/
│   └── workflows/
│       └── check-orders.yml       # GitHub Actions scheduled job
├── .planning/
│   └── codebase/                  # Codebase analysis documents
├── .env                           # Local environment variables (not committed)
├── .gitignore                     # Git exclusions
├── webhook.js                     # Express HTTP server for SPP webhooks
├── email_to_slack.py              # Email ingestion and Slack poster
├── processed_orders.json          # Persisted deduplication state
├── orders.db                      # SQLite database (not currently used)
└── package.json                   # Node.js dependencies and scripts
```

## Directory Purposes

**.github/workflows/:**
- Purpose: CI/CD automation and scheduled tasks
- Contains: GitHub Actions workflow definitions
- Key files: `check-orders.yml` - Cron job triggered every 5 minutes

**.planning/codebase/:**
- Purpose: Architecture and structure documentation
- Contains: Analysis markdown files for future reference
- Not committed initially (created during analysis)

## Key File Locations

**Entry Points:**

- `webhook.js`: HTTP server receiving SPP order webhooks on POST /webhook
  - Runs continuously (started with `npm start`)
  - Depends on: SLACK_WEBHOOK_URL, PORT env vars
  - Language: JavaScript (Node.js 18+)

- `email_to_slack.py`: Email ingestion processor
  - Runs once per 5-minute GitHub Actions interval
  - Depends on: ZOHO_EMAIL, ZOHO_APP_PASSWORD, SLACK_WEBHOOK_URL env vars
  - Language: Python 3
  - Command: `python email_to_slack.py` (or with `--test-fiverr`/`--test-legiit`)

**Configuration:**

- `.env`: Local development environment variables (template - values not in repo)
  - Contains: ZOHO_EMAIL, ZOHO_APP_PASSWORD, SLACK_WEBHOOK_URL, PORT
  - Loaded by: `email_to_slack.py` on startup
  - Not committed: Listed in `.gitignore`

- `package.json`: Node.js project manifest
  - Defines: Dependencies (express ^4.18.2), scripts, Node version requirement
  - Key script: `start` runs `node webhook.js`

- `.github/workflows/check-orders.yml`: GitHub Actions workflow
  - Trigger: Schedule (cron: `*/5 * * * *`) and manual dispatch
  - Steps: Checkout, setup Python 3.11, run email_to_slack.py, commit processed_orders.json
  - Uses secrets: ZOHO_EMAIL, ZOHO_APP_PASSWORD, SLACK_WEBHOOK_URL

**Core Logic:**

- `webhook.js`: Lines 1-34
  - Express setup: `app.use(express.json())`
  - Route: `app.post('/webhook', handler)`
  - Handler: Extract order fields, format message, POST to Slack

- `email_to_slack.py`: Lines 290-314 (main), Lines 119-287 (processors)
  - `main()`: Orchestrates IMAP connection and platform processing
  - `process_spp()`: SPP email processor (lines 119-160)
  - `process_fiverr()`: Fiverr email processor (lines 163-220)
  - `process_legiit()`: Legiit email processor (lines 239-287)

**State Management:**

- `processed_orders.json`: JSON array of order ID strings
  - Format: `["ID1", "ID2", "ID3", ...]`
  - Loaded: By `load_processed()` (line 35-39)
  - Saved: By `save_processed()` (line 42-44)
  - Committed: Yes (tracked in git to preserve state across workflow runs)

**Utilities:**

- `html_to_text()` (lines 79-85): HTML entity decoding and tag stripping
  - Used by: Email body parsers
  - Handles: nbsp, amp, times/× entities, multiple whitespace

- `parse_fiverr_body()` (lines 88-106): Extract order details from Fiverr HTML
  - Returns: (order_id, due_date, service, quantity, total)
  - Uses: Regex on plain text version of HTML

- `parse_legiit_body()` (lines 223-236): Extract order details from Legiit HTML
  - Returns: (order_id, client, service, amount)
  - Uses: Regex on plain text version

- `LinkExtractor` class (lines 47-68): HTML parser for anchor text extraction
  - Used by: `get_service_from_html()` for SPP emails
  - State: Tracks current link context during parse

- `post_to_slack()` (lines 109-116): Unified Slack webhook poster
  - Used by: All three processor functions
  - Implementation: urllib.request with JSON encoding

## Naming Conventions

**Files:**

- Root-level entry point files: lowercase with underscore (`email_to_slack.py`, `webhook.js`)
- Configuration: common names (`.env`, `package.json`, `.gitignore`)
- State files: lowercase plural nouns (`processed_orders.json`)

**Functions:**

- Platform processors: `process_{platform}()` (e.g., `process_spp`, `process_fiverr`)
- Parsers: `parse_{platform}_body()` or `html_to_text()`
- Data loaders: `load_processed()`, save functions: `save_processed()`
- Extraction: `get_service_from_html()`
- Utilities: `post_to_slack()`

**Variables:**

- Email/order fields: snake_case (`client_name`, `order_id`, `service`, `email_pass`)
- Configuration: UPPERCASE (SLACK_WEBHOOK_URL, IMAP_HOST, EMAIL_USER)
- Local state: lowercase (`processed`, `cutoff`, `mail`, `html_body`)

**Types:**

- Classes (Python): PascalCase (`LinkExtractor`)
- Constants: UPPERCASE_SNAKE_CASE
- No TypeScript/JSDoc type annotations in current code

## Where to Add New Code

**New Freelance Platform Email Source:**

- Processor function: Add `process_newplatform()` in `email_to_slack.py` after line 287
  - Follow pattern: IMAP search → fetch → date filter → parse body → check dedup → post to Slack → state update
  - Add sender constant: `NEWPLATFORM_SENDER = "..."` at top with other senders
  - Add to main() function: Call in appropriate location (before/after existing processors)

- Parsing logic: Add `parse_newplatform_body(html)` function before processor
  - Extract using regex: `html_to_text(html)` then `re.search()` patterns
  - Return tuple: `(order_id, client, service, amount, [optional_fields])`

- Message template: Update post_to_slack() call in processor with platform emoji and fields

**New HTTP Webhook Event Type:**

- Handler: Add conditional in `webhook.js` after line 11
  - Check event type: `if (event !== 'order.created') { ... }`
  - Extract fields from data structure
  - Format message with emoji and fields
  - POST to Slack

**New Notification Channel (Non-Slack):**

- Abstraction: Create `post_to_{channel}()` function parallel to `post_to_slack()`
  - Takes formatted text and destination config
  - Handles auth and POST logic

- Integration: Update message posting code to call both functions or use strategy pattern

**Utilities/Helpers:**

- Shared helpers: Add to root level as `utils.py` or `utils.js`
- HTML parsing: Extend `LinkExtractor` or add specialized parser
- Regex patterns: Consider extracting to constants dict at top of file if reused

## Special Directories

**node_modules/:**
- Purpose: NPM package dependencies
- Generated: Yes (by `npm install`)
- Committed: No (listed in .gitignore)

**.git/:**
- Purpose: Version control metadata
- Generated: Yes (by `git init`)
- Committed: No (excluded by default)

**.env file:**
- Purpose: Local development configuration
- Generated: Manually by developer
- Committed: No (listed in .gitignore)
- Template values: ZOHO_EMAIL, ZOHO_APP_PASSWORD, SLACK_WEBHOOK_URL, optional PORT

**orders.db:**
- Purpose: SQLite database (legacy - not currently used)
- Generated: Potentially by future code
- Committed: No (listed in .gitignore)

**processed_orders.json:**
- Purpose: Deduplication state persistence across runs
- Generated: Created by email_to_slack.py on first run
- Committed: Yes (committed to preserve state)
- Recovery: GitHub Actions automatically commits after each run

---

*Structure analysis: 2026-03-23*
