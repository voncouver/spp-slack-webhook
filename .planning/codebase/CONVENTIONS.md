# Coding Conventions

**Analysis Date:** 2026-03-23

## Naming Patterns

**Files:**
- Python files: lowercase with underscores (`email_to_slack.py`)
- JavaScript files: lowercase with underscores or camelCase (`webhook.js`)

**Functions (Python):**
- snake_case: `load_processed()`, `save_processed()`, `parse_fiverr_body()`, `post_to_slack()`
- Descriptive verb-noun pattern: `process_spp()`, `process_fiverr()`, `process_legiit()`, `get_service_from_html()`

**Functions (JavaScript):**
- No custom functions defined; using inline route handlers and anonymous functions

**Variables (Python):**
- snake_case for all variables and constants: `IMAP_HOST`, `EMAIL_USER`, `SLACK_WEBHOOK_URL`, `PROCESSED_FILE`
- Uppercase for module-level constants: `IMAP_HOST`, `IMAP_PORT`, `SPP_SENDER`, `FIVERR_SENDER`, `LEGIIT_SENDER`
- lowercase for local variables: `processed`, `cutoff`, `client_name`, `order_id`, `html_body`

**Variables (JavaScript):**
- camelCase for variables: `SLACK_WEBHOOK_URL` (constant), `app`, `client`, `invoice`, `message`
- Uppercase for constants: `SLACK_WEBHOOK_URL`, `PORT`

**Types/Classes:**
- PascalCase for custom classes (Python): `LinkExtractor`

## Code Style

**Formatting:**
- No formal linter or formatter configured
- Python: Uses standard indentation (4 spaces, as shown in `email_to_slack.py`)
- JavaScript: Uses 2-space indentation (as shown in `webhook.js`)

**Linting:**
- Not detected in codebase

## Import Organization

**Python:**
Order:
1. Standard library imports: `imaplib`, `email`, `re`, `json`, `os`, `sys`, `urllib.request`
2. Standard library sub-imports: `from email.header import`, `from email.utils import`, `from html.parser import`
3. Third-party: None used in production code
4. Local imports: Configuration variables and utility functions defined inline

Path usage: Absolute imports from standard library; manual `.env` loading via `Path(__file__).parent`

**JavaScript:**
- Standard: `const express = require('express');` and `const app = express();`
- Environment: `process.env.SLACK_WEBHOOK_URL`, `process.env.PORT`

## Error Handling

**Patterns:**
- Python: Silent exception handling with bare `except` blocks
  - `parse_spp()` (lines 127-134): Bare `except Exception:` to skip invalid email dates
  - `process_fiverr()` (lines 179-186): Same pattern with `test_mode` conditional
  - `process_legiit()` (lines 254-262): Same pattern
  - Returns `None` or sensible defaults on failure: `get_service_from_html()` returns `"Unknown"` if no link found

- JavaScript: No explicit error handling in `webhook.js`
  - Async POST to Slack (line 24-28) has no try-catch
  - Missing error responses for edge cases
  - Returns 200 status regardless of Slack API success

## Logging

**Framework:** console

**Python Patterns:**
- `print()` statements for audit logging in process functions
- Format: `f"Sent {source}: {client} | Order #{order_id} | {service} | {amount}"` (lines 160, 220, 287)
- No structured logging framework

**JavaScript Patterns:**
- `console.log()` on server startup (line 34): `` `Listening on port ${PORT}` ``
- No request/response logging

## Comments

**When to Comment:**
- Minimal commenting observed
- Only appears in configuration section explaining `.env` loading (lines 14-22 in `email_to_slack.py`)
- No JSDoc or TSDoc style documentation

## Function Design

**Size:**
- Python functions range 10-30 lines
- `parse_fiverr_body()` and `parse_legiit_body()` are focused extraction functions (15-17 lines)
- Main processor functions (`process_spp`, `process_fiverr`, `process_legiit`) are 30+ lines, handle email fetching and processing

**Parameters:**
- Python: Explicit parameters passed through call chain
  - `process_spp(mail, processed, cutoff)` - all needed state passed in
  - Parser functions take specific HTML/text input

**Return Values:**
- Python functions return parsed tuples: `parse_fiverr_body()` returns `(order_id, due_date, service, quantity, total)`
- Side effects through mutations: `processed.add(order_id)` to track sent orders
- None or void returns for posting functions

## Module Design

**Exports:**
- Python: Module-level functions used as main entry point via `if __name__ == "__main__":` pattern
- JavaScript: Single Express app instance exported via `require`

**Barrel Files:**
- Not used in this codebase

**Organization (Python - `email_to_slack.py`):**
1. Configuration & constants (lines 1-32)
2. Utility functions: `load_processed()`, `save_processed()` (lines 35-44)
3. HTML parsing class: `LinkExtractor` (lines 47-68)
4. HTML/text extraction: `get_service_from_html()`, `html_to_text()` (lines 70-86)
5. Provider-specific parsers: `parse_fiverr_body()`, `parse_legiit_body()` (lines 88-236)
6. Slack integration: `post_to_slack()` (lines 109-116)
7. Main processors: `process_spp()`, `process_fiverr()`, `process_legiit()` (lines 119-287)
8. Orchestration: `main()` (lines 290-314)

---

*Convention analysis: 2026-03-23*
