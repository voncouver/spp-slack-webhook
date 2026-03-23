# External Integrations

**Analysis Date:** 2026-03-23

## APIs & External Services

**Order Processing Platforms:**
- Service Provider Pro (SPP) - Email-based order notifications
  - Email sender: `rankmenu@es2.serviceprovider.app`
  - Integration: Email polling via IMAP in `email_to_slack.py` (lines 119-160)
  - Subject pattern: `{client_name} paid {amount} for invoice #{order_id}`

- Fiverr - Gig marketplace order notifications
  - Email sender: `noreply@e.fiverr.com`
  - Integration: Email polling via IMAP in `email_to_slack.py` (lines 163-220)
  - Subject pattern: `Great news: You've received an order from {client_name}`
  - HTML parsing for order details (lines 88-106)

- Legiit - SEO services marketplace order notifications
  - Email sender: `noreply@legiit.com`
  - Integration: Email polling via IMAP in `email_to_slack.py` (lines 239-287)
  - HTML parsing for order details (lines 223-236)

**Messaging:**
- Slack Webhooks - Order notification delivery
  - SDK/Client: None (native HTTP POST via urllib in Python, fetch in Node.js)
  - Auth: `SLACK_WEBHOOK_URL` environment variable
  - Usage: `webhook.js` (lines 24-28), `email_to_slack.py` (lines 110-116)
  - Message format: Plain text with formatting markers (`*bold*`, newlines)

## Data Storage

**Databases:**
- SQLite - Local orders database
  - File: `orders.db` (listed in `.gitignore`)
  - Client: Python sqlite3 (imported but not used in current codebase)
  - Connection: Local filesystem

**File Storage:**
- Local filesystem only
  - Processed orders log: `processed_orders.json` (lines 32, 42-44 in `email_to_slack.py`)
  - Format: JSON array of order IDs

**Caching:**
- None detected

## Authentication & Identity

**Email/IMAP:**
- Provider: Zoho Mail
  - IMAP Server: `imap.zoho.eu` port 993 (SSL)
  - Auth method: Username + App Password
  - Env vars: `ZOHO_EMAIL`, `ZOHO_APP_PASSWORD` (lines 26-27 in `email_to_slack.py`)
  - Implementation: SSL connection in `email_to_slack.py` (line 296)

**Slack Webhooks:**
- Auth: Webhook URL contains embedded authorization
  - Single incoming webhook URL via env var
  - No additional OAuth or API keys required

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Console output via print() statements in `email_to_slack.py`
  - SPP orders: line 160
  - Fiverr orders: line 220
  - Legiit orders: line 287
- No persistent logging framework

## CI/CD & Deployment

**Hosting:**
- Self-hosted (implied)
- Not detected in codebase

**CI Pipeline:**
- None detected

**Execution Model:**
- Express.js server: Long-running HTTP service on port 3000 (or `PORT` env var)
- Python script: Designed for periodic execution (via cron or scheduler)
  - 24-hour lookback window for emails (line 294)
  - Test modes available: `--test-fiverr` and `--test-legiit` flags (lines 291-307)

## Environment Configuration

**Required env vars:**
- `SLACK_WEBHOOK_URL` - Slack incoming webhook endpoint
- `ZOHO_EMAIL` - Zoho Mail account email address
- `ZOHO_APP_PASSWORD` - Zoho Mail app-specific password
- `PORT` (optional) - Express server port, defaults to 3000

**Secrets location:**
- `.env` file (local, not committed to git)
- No other secret management detected

## Webhooks & Callbacks

**Incoming:**
- Express server at `/webhook` endpoint (POST only) in `webhook.js`
  - Expected payload structure: `{ event: string, data: object }`
  - Filters on `event === 'order.created'`
  - Extracts: client name, invoice ID, service, amount (lines 15-22)

**Outgoing:**
- Slack message delivery via incoming webhooks
  - Only outbound integration
  - One-way notification flow

## Data Flow

1. **SPP/Fiverr/Legiit** → Send order notification emails
2. **Email Provider (Zoho)** → Receives and stores emails
3. **Python Script** → Polls IMAP every X minutes/hours
4. **Order Parser** → Extracts relevant fields from email body
5. **Deduplication** → Checks `processed_orders.json` for new orders
6. **Slack Webhook** → Posts formatted message to Slack channel
7. **JSON Store** → Logs processed order ID to prevent duplicates

Alternative flow:
1. **External Service** → POST to `/webhook` endpoint with order data
2. **Express Server** → Validates event type and data structure
3. **Slack Webhook** → Posts formatted message to Slack channel

---

*Integration audit: 2026-03-23*
