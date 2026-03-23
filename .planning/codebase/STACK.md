# Technology Stack

**Analysis Date:** 2026-03-23

## Languages

**Primary:**
- Python 3.x - Email polling and integration logic in `email_to_slack.py`
- JavaScript (Node.js) - Webhook server in `webhook.js`

**Secondary:**
- JSON - Configuration and data serialization in `processed_orders.json`

## Runtime

**Environment:**
- Node.js 18+ (specified in `package.json`)
- Python 3.x (inferred from standard library usage)

**Package Manager:**
- npm (for Node.js dependencies)
- pip (for Python dependencies)
- Lockfile: `package.json` present; no `package-lock.json` or `requirements.txt` detected

## Frameworks

**Core:**
- Express.js ^4.18.2 - HTTP server framework for webhook endpoint in `webhook.js`

**Runtime Support:**
- Node.js built-in `imaplib` (Python standard library) - IMAP email protocol in `email_to_slack.py`
- Python standard library modules: `email`, `urllib`, `json`, `re`, `os`, `sys`

## Key Dependencies

**Critical:**
- Express.js ^4.18.2 - HTTP request handling for Slack webhook ingestion in `webhook.js`

**Infrastructure:**
- Zoho Mail IMAP - Email access via `imaplib.IMAP4_SSL` in `email_to_slack.py` (lines 24-25, 296)
- Slack Webhook API - Message posting via HTTP POST in both `webhook.js` (line 24) and `email_to_slack.py` (lines 110-116)

## Configuration

**Environment:**
- `.env` file present (listed in `.gitignore`)
- Environment variables loaded in `email_to_slack.py` (lines 14-22)
- Key env vars: `SLACK_WEBHOOK_URL`, `ZOHO_EMAIL`, `ZOHO_APP_PASSWORD`, `PORT`

**Build:**
- No build configuration detected
- Entry points: `webhook.js` (main Express server), `email_to_slack.py` (scheduled email poller)

## Platform Requirements

**Development:**
- Node.js 18 or higher
- Python 3.6+ (for f-strings and standard library compatibility)

**Production:**
- Linux/Unix environment (Zoho Mail IMAP access)
- Network access to: `imap.zoho.eu:993` (Zoho Mail), Slack webhook endpoint
- `.env` file with required credentials

---

*Stack analysis: 2026-03-23*
