# Architecture

**Analysis Date:** 2026-03-23

## Pattern Overview

**Overall:** Multi-source event aggregation with notification distribution

**Key Characteristics:**
- Multiple inbound sources (email services): SPP, Fiverr, Legiit
- Dual integration approach: Python IMAP scraper + Node.js webhook receiver
- Asynchronous event processing with deduplication
- Persistent state tracking via JSON file
- Single outbound notification channel: Slack webhook

## Layers

**Email Ingestion Layer:**
- Purpose: Fetch and parse new order notifications from email providers
- Location: `email_to_slack.py`
- Contains: IMAP connection logic, email parsing, HTML extraction
- Depends on: IMAP4_SSL (Python stdlib), Zoho email service
- Used by: Orchestration layer (main function)

**HTTP Webhook Receiver Layer:**
- Purpose: Accept order events from SPP system webhooks
- Location: `webhook.js`
- Contains: Express server, request routing, event filtering
- Depends on: Express.js, environment configuration
- Used by: External SPP system

**Message Formatting Layer:**
- Purpose: Transform raw order data into Slack-formatted messages
- Location: Lines 155-158 (SPP), 214-218 (Fiverr), 281-285 (Legiit) in `email_to_slack.py`
- Contains: Message templates with order details and emojis
- Depends on: Parsed order data
- Used by: Notification delivery layer

**State Management Layer:**
- Purpose: Track processed orders to prevent duplicates
- Location: `processed_orders.json`, `load_processed()` and `save_processed()` in `email_to_slack.py`
- Contains: Set of processed order IDs persisted to disk
- Depends on: File system
- Used by: Email ingestion layer

**Notification Delivery Layer:**
- Purpose: Post formatted messages to Slack
- Location: `post_to_slack()` in `email_to_slack.py`, fetch call in `webhook.js`
- Contains: HTTP POST requests with JSON payloads
- Depends on: Slack webhook URL
- Used by: Message formatting layer

**Orchestration Layer:**
- Purpose: Coordinate all processing steps
- Location: `main()` in `email_to_slack.py`, `app.listen()` in `webhook.js`
- Contains: IMAP connection setup, processor calls, state persistence
- Depends on: All other layers

## Data Flow

**Email Processing Flow (email_to_slack.py):**

1. Load previously processed order IDs from `processed_orders.json`
2. Establish IMAP4_SSL connection to Zoho email (IMAP_HOST:993)
3. Fetch emails from three sources in sequence:
   - **SPP (Service Provider Pro):** Search INBOX for sender `rankmenu@es2.serviceprovider.app`
     - Parse subject line: `{client} paid {amount} for invoice #{order_id}`
     - Extract service name from HTML body using `LinkExtractor` class
     - Format message with client, order number, service, amount
   - **Fiverr:** Search Newsletter folder for sender `noreply@e.fiverr.com`
     - Parse subject: `Great news: You've received an order from {client}`
     - Extract order_id, due_date, service, quantity, total from HTML
     - Format message with all fields
   - **Legiit:** Search Newsletter folder for sender `noreply@legiit.com`
     - Parse HTML to extract buyer, service, order number, amount
     - Format message with client, order number, service, amount
4. For each new order (not in processed set):
   - POST formatted message to Slack webhook
   - Add order_id to processed set
   - Log to stdout
5. Persist processed orders to `processed_orders.json`
6. Close IMAP connection

**Webhook Processing Flow (webhook.js):**

1. Express server listens on `PORT` (default 3000)
2. POST /webhook receives JSON payload with `{event, data}`
3. Filter: only process `order.created` events
4. Extract: client name, invoice ID, service, amount from data structure
5. Format Slack message
6. POST to Slack webhook
7. Return HTTP 200

**Time-based Filtering:**

- Email processor only processes messages dated within 24 hours (cutoff = now - 24h)
- Timezone normalized to UTC
- Skips malformed/unparseable date headers
- Prevents reprocessing of old emails after recovery from downtime

**State Management:**

- Set-based deduplication prevents duplicate Slack notifications
- Persistent JSON file survives process restarts
- Appended to by email processor, compared by webhook receiver (if integrated)

## Key Abstractions

**LinkExtractor (HTML parser):**
- Purpose: Extract meaningful text from HTML anchor tags
- Examples: `email_to_slack.py` lines 47-68
- Pattern: Subclass of HTMLParser, tracks state during parse, collects link text
- Used by: `get_service_from_html()` to extract service names from SPP emails

**Email Parser Functions:**
- Purpose: Extract structured order data from unstructured email HTML
- Examples: `parse_fiverr_body()` (lines 88-106), `parse_legiit_body()` (lines 223-236)
- Pattern: Take raw HTML, convert to plain text, extract via regex, return tuple
- Used by: Platform-specific processors

**Platform Processor Functions:**
- Purpose: Handle platform-specific email source
- Examples: `process_spp()`, `process_fiverr()`, `process_legiit()` (lines 119-287)
- Pattern: IMAP search + fetch, date filtering, parsing, deduplication, Slack post, state update
- Used by: Orchestration layer (main function)

## Entry Points

**Scheduled Email Processor:**
- Location: `email_to_slack.py` (main entry point)
- Triggers: GitHub Actions cron every 5 minutes (`.github/workflows/check-orders.yml`)
- Responsibilities:
  - Connect to Zoho IMAP
  - Process all three email sources
  - Post to Slack
  - Persist processed orders
  - Exit cleanly

**Direct Email Testing:**
- Triggers: Command line arguments `--test-fiverr` or `--test-legiit`
- Responsibilities: Process single most recent email in test mode (bypasses date filter)

**Webhook HTTP Endpoint:**
- Location: `webhook.js`
- Triggers: POST to `/webhook` from external SPP system
- Responsibilities:
  - Validate event type
  - Parse order data
  - Post to Slack
  - Return HTTP 200

## Error Handling

**Strategy:** Graceful degradation with logging

**Patterns:**

- **Email parsing failures:** Skip emails with unparseable subjects/dates, continue with next
- **Regex match failures:** Return sensible defaults ("Unknown") rather than crashing
- **HTML extraction failures:** Continue with "Unknown" service value
- **Missing order IDs:** Skip record (lines 208-209, 275-276)
- **Date parsing:** Set timezone to UTC if missing, skip if parse fails (lines 129-134)
- **HTTP failures:** Unhandled - would crash on Slack POST failure (potential concern)

## Cross-Cutting Concerns

**Logging:**
- stdout print statements for each successful Slack post with full order details
- Allows tracking in GitHub Actions workflow and local testing
- No error logging for failures (silent skip pattern)

**Validation:**
- Sender address whitelist (3 domains only)
- Event type filtering (order.created only in webhook)
- Order ID presence check (skips records without ID)
- Email date filtering (24-hour window, UTC normalized)

**Deduplication:**
- In-memory set plus JSON persistence
- Loaded at startup, updated after each successful Slack post
- Prevents redundant notifications across restarts

**Configuration:**
- Environment variables only: ZOHO_EMAIL, ZOHO_APP_PASSWORD, SLACK_WEBHOOK_URL
- .env file support for local development (read-only, not committed)
- Fallback PORT 3000 for webhook if not specified

**Secrets:**
- Private credentials in GitHub Actions secrets
- .env in .gitignore for local use
- orders.db in .gitignore (SQLite database, not currently used)

---

*Architecture analysis: 2026-03-23*
