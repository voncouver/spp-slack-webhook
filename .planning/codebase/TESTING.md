# Testing Patterns

**Analysis Date:** 2026-03-23

## Test Framework

**Runner:**
- Not detected - no test framework configured

**Assertion Library:**
- Not used

**Run Commands:**
- No test commands defined in `package.json`
- No pytest configuration in Python project

## Test File Organization

**Location:**
- Not applicable - no test files detected

**Naming:**
- Not applicable - no test files in codebase

**Structure:**
- Not applicable

## Testing Coverage

**Current State:**
- No automated test suite exists
- Code relies on manual testing and CLI invocation

**Manual Testing Approach:**
- Python: Command-line arguments for test mode
  - `python email_to_slack.py --test-fiverr` - tests Fiverr processor in isolation
  - `python email_to_slack.py --test-legiit` - tests Legiit processor in isolation
  - Uses `test_mode=False` parameter to control behavior in `process_fiverr()` (line 163) and `process_legiit()` (line 239)
  - In test mode: processes only most recent email instead of all matching
    ```python
    if test_mode:
        email_ids = [email_ids[-1]]
    ```

## Coverage

**Requirements:** None enforced

**Untested Paths:**
- Error handling: All bare `except Exception:` blocks (lines 127-134 in `email_to_slack.py`)
- SPP processor: `process_spp()` has no test mode flag - cannot be tested in isolation
- Slack posting failures: No error handling for failed webhook calls in either file
- IMAP connection failures: No recovery logic for connection issues
- HTML parsing edge cases: No test coverage for malformed emails
- Concurrent requests: `webhook.js` has no concurrency handling

**Testability Gaps:**
- `post_to_slack()` (line 109) is not mockable - uses `urllib.request.urlopen()` directly
- IMAP login credentials hardcoded to environment variables - no injection point for test mocks
- Slack webhook URL loaded at module initialization - cannot be overridden for tests
- Email parsing logic coupled to IMAP operations - difficult to test parsers independently

## Known Testing Issues

**Issue 1: No Error Handling for Slack API Failures**
- Files: `webhook.js` (line 24-28), `email_to_slack.py` (line 109-116)
- Problem: Webhook requests have no error handling or timeout
- Impact: Failed Slack posts silently succeed in webhook response
- Suggested fix: Wrap `urllib.request.urlopen()` in try-except; add `await` error handling in Express

**Issue 2: SPP Processor Not Test-Mode Aware**
- File: `email_to_slack.py` (line 119-160)
- Problem: `process_spp()` has no test mode parameter unlike Fiverr/Legiit
- Impact: Cannot safely test SPP ordering without processing all recent emails
- Suggested fix: Add `test_mode=False` parameter matching other processors

**Issue 3: Hardcoded Test Email Selection**
- Files: `email_to_slack.py` (line 172, 248 in Fiverr/Legiit)
- Problem: Test mode selects last email by index - assumes emails exist and are in order
- Impact: Test mode fails silently if no emails present
- Suggested fix: Validate `email_ids` length before indexing

**Issue 4: No Integration Tests**
- Problem: Real email parsing logic untested against actual email structures
- Impact: Format changes in order emails break silently
- Suggested fix: Create test emails or fixtures for each provider

## Mocking

**Framework:** None configured

**Patterns:**
- Manual parameter passing: `test_mode` flag controls behavior
- Environment variable isolation via `.env` file (manual setup per test run)

**What Could Be Mocked (if framework added):**
- `imaplib.IMAP4_SSL()` for offline testing
- `urllib.request.urlopen()` for Slack webhook verification
- Email parsing libraries for edge case testing

## Fixtures and Factories

**Test Data:**
- Not applicable - no fixtures defined

**Location:**
- Not applicable

## Test Types

**Unit Tests:**
- Not present in codebase
- Candidate functions for unit testing:
  - `html_to_text()`: Pure function, highly testable
  - `parse_fiverr_body()`: Pure text parsing, testable with fixtures
  - `parse_legiit_body()`: Pure text parsing, testable with fixtures
  - `get_service_from_html()`: HTML parsing, needs sample emails

**Integration Tests:**
- Implicit manual testing only
- Developers must run script with `--test-fiverr` or `--test-legiit` flags

**E2E Tests:**
- Not configured
- Manual workflow: Script connects to real Zoho email, reads orders, posts to Slack

## Recommendations for Adding Tests

**Step 1: Unit Tests (High Priority)**
- Add pytest for Python (`email_to_slack.py`)
- Test pure functions: `html_to_text()`, parsing functions
- Use sample HTML email bodies as fixtures
- Example test structure:
  ```python
  def test_parse_fiverr_body_extracts_order_id():
      html = "<sample HTML with order ID>"
      order_id, _, _, _, _ = parse_fiverr_body(html)
      assert order_id == "12345"
  ```

**Step 2: Integration Tests**
- Mock IMAP connection to avoid real email access
- Mock Slack webhook to verify posting
- Test full email processing pipeline with sample emails

**Step 3: JavaScript Testing**
- Add Jest or Vitest to `package.json`
- Test Express route `/webhook` with mock POST bodies
- Verify error handling when Slack webhook fails

---

*Testing analysis: 2026-03-23*
