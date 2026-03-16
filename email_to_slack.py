import imaplib
import email
import re
import json
import os
import urllib.request
from email.header import decode_header
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Load .env file (local use only)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

IMAP_HOST = "imap.zoho.eu"
IMAP_PORT = 993
EMAIL_USER = os.environ["ZOHO_EMAIL"]
EMAIL_PASS = os.environ["ZOHO_APP_PASSWORD"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SPP_SENDER = "rankmenu@es2.serviceprovider.app"
PROCESSED_FILE = Path(__file__).parent / "processed_orders.json"


def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(processed), f)


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links_text = []
        self._in_link = False
        self._current_text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._in_link = True
            self._current_text = ""

    def handle_data(self, data):
        if self._in_link:
            self._current_text += data.strip()

    def handle_endtag(self, tag):
        if tag == "a" and self._in_link:
            if self._current_text:
                self.links_text.append(self._current_text)
            self._in_link = False


def get_service_from_html(html_body):
    parser = LinkExtractor()
    parser.feed(html_body)
    for text in parser.links_text:
        if len(text) > 5 and not text.startswith("http"):
            return text
    return "Unknown"


def post_to_slack(client, order_id, service, amount):
    message = {
        "text": f"*📝 New Order on Service Provider Pro!*\n\nClient: {client}\nOrder #{order_id}\nService: {service}\nAmount: {amount}"
    }
    data = json.dumps(message).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)


def main():
    processed = load_processed()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("INBOX")

    _, data = mail.search(None, f'(FROM "{SPP_SENDER}")')
    email_ids = data[0].split()

    for eid in email_ids:
        _, msg_data = mail.fetch(eid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        try:
            msg_date = parsedate_to_datetime(msg["Date"])
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            if msg_date < cutoff:
                continue
        except Exception:
            continue

        subject_raw = decode_header(msg["Subject"])[0][0]
        subject = subject_raw.decode() if isinstance(subject_raw, bytes) else subject_raw

        match = re.match(r"^(.+) paid (.+) for invoice #([A-Z0-9]+)$", subject)
        if not match:
            continue

        client_name = match.group(1)
        amount = match.group(2)
        order_id = match.group(3)

        if order_id in processed:
            continue

        service = "Unknown"
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode()
                service = get_service_from_html(html)
                break

        post_to_slack(client_name, order_id, service, amount)
        processed.add(order_id)
        print(f"Sent: {client_name} | Order #{order_id} | {service} | {amount}")

    save_processed(processed)
    mail.logout()


if __name__ == "__main__":
    main()
