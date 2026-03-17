import imaplib
import email
import re
import json
import os
import sys
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
FIVERR_SENDER = "noreply@e.fiverr.com"
LEGIIT_SENDER = "noreply@legiit.com"
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


def html_to_text(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&times;|&#215;', '×', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_fiverr_body(html):
    text = html_to_text(html)

    order_match = re.search(r'Order #(\S+) is due (\w+ \d+, \d+)', text)
    order_id = order_match.group(1) if order_match else None
    due_date = order_match.group(2) if order_match else "Unknown"

    service_match = re.search(r'Price\s+(.+?)\s*:?\s*[×x]\s*(\d+)', text, re.DOTALL)
    if service_match:
        service = re.sub(r'^I will \w+ ', '', service_match.group(1).strip().rstrip(':').strip())
        quantity = service_match.group(2)
    else:
        service = "Unknown"
        quantity = "?"

    total_match = re.search(r'Total:\s*\$?([\d,]+(?:\.\d+)?)', text)
    total = f"${total_match.group(1)}" if total_match else "Unknown"

    return order_id, due_date, service, quantity, total


def post_to_slack(message_text):
    data = json.dumps({"text": message_text}).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)


def process_spp(mail, processed, cutoff):
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

        client_name, amount, order_id = match.group(1), match.group(2), match.group(3)

        if order_id in processed:
            continue

        service = "Unknown"
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode()
                service = get_service_from_html(html)
                break

        post_to_slack(
            f"*📝 New Order on Service Provider Pro!*\n\n"
            f"Client: {client_name}\nOrder #{order_id}\nService: {service}\nAmount: {amount}"
        )
        processed.add(order_id)
        print(f"Sent SPP: {client_name} | Order #{order_id} | {service} | {amount}")


def process_fiverr(mail, processed, cutoff, test_mode=False):
    mail.select("Newsletter")
    _, data = mail.search(None, f'(FROM "{FIVERR_SENDER}")')
    email_ids = data[0].split()

    if not email_ids:
        return

    if test_mode:
        email_ids = [email_ids[-1]]

    for eid in email_ids:
        _, msg_data = mail.fetch(eid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        if not test_mode:
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

        fiverr_match = re.match(r"^Great news: You've received an order from (.+)$", subject)
        if not fiverr_match:
            continue

        client_name = fiverr_match.group(1).strip()

        html_body = None
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True).decode()
                break

        if not html_body:
            continue

        order_id, due_date, service, quantity, total = parse_fiverr_body(html_body)

        if not order_id:
            continue

        if not test_mode and order_id in processed:
            continue

        post_to_slack(
            f"*📝 New Order on Fiverr!*\n\n"
            f"Client: {client_name}\nOrder #{order_id}\nService: {service}\n"
            f"Quantity: {quantity}\nTotal Price: {total}\nDue Date: {due_date}"
        )
        processed.add(order_id)
        print(f"Sent Fiverr: {client_name} | Order #{order_id} | {service} | Qty:{quantity} | {total} | Due:{due_date}")


def parse_legiit_body(html):
    text = html_to_text(html)

    buyer_match = re.search(r'Buyer:\s*(\S+)', text)
    service_match = re.search(r'Service:\s*(.+?)\s*(?:Package\s*:|Total Amount:)', text)
    amount_match = re.search(r'Total Amount:\s*(\$[\d.]+)', text)
    order_match = re.search(r'Order Number:\s*(\S+)', text)

    client = buyer_match.group(1).strip() if buyer_match else "Unknown"
    service = service_match.group(1).strip() if service_match else "Unknown"
    amount = amount_match.group(1) if amount_match else "Unknown"
    order_id = order_match.group(1).strip() if order_match else None

    return order_id, client, service, amount


def process_legiit(mail, processed, cutoff, test_mode=False):
    mail.select("Newsletter")
    _, data = mail.search(None, f'(FROM "{LEGIIT_SENDER}")')
    email_ids = data[0].split()

    if not email_ids:
        return

    if test_mode:
        email_ids = [email_ids[-1]]

    for eid in email_ids:
        _, msg_data = mail.fetch(eid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        if not test_mode:
            try:
                msg_date = parsedate_to_datetime(msg["Date"])
                if msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)
                if msg_date < cutoff:
                    continue
            except Exception:
                continue

        html_body = None
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True).decode()
                break

        if not html_body:
            continue

        order_id, client, service, amount = parse_legiit_body(html_body)

        if not order_id:
            continue

        if not test_mode and order_id in processed:
            continue

        post_to_slack(
            f"*📝 New Order on Legiit!*\n\n"
            f"Client: {client}\nOrder Number: {order_id}\n"
            f"Service: {service}\nTotal Amount: {amount}"
        )
        processed.add(order_id)
        print(f"Sent Legiit: {client} | Order {order_id} | {service} | {amount}")


def main():
    test_fiverr = "--test-fiverr" in sys.argv
    test_legiit = "--test-legiit" in sys.argv
    processed = load_processed()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASS)

    if not test_fiverr and not test_legiit:
        mail.select("INBOX")
        process_spp(mail, processed, cutoff)
        process_fiverr(mail, processed, cutoff)
        process_legiit(mail, processed, cutoff)
    elif test_fiverr:
        process_fiverr(mail, processed, cutoff, test_mode=True)
    elif test_legiit:
        process_legiit(mail, processed, cutoff, test_mode=True)

    save_processed(processed)
    mail.logout()


if __name__ == "__main__":
    main()
