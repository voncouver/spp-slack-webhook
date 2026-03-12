import imaplib
import email
import re
import json
import os
import urllib.request
from email.header import decode_header
from html.parser import HTMLParser

IMAP_HOST = "imap.zoho.eu"
IMAP_PORT = 993
EMAIL_USER = os.environ["ZOHO_EMAIL"]
EMAIL_PASS = os.environ["ZOHO_APP_PASSWORD"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SPP_SENDER = "rankmenu@es2.serviceprovider.app"


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
        "text": f"*New Order*\nClient: {client}\nOrder #{order_id}\nItem: {service}\nAmount: {amount}"
    }
    data = json.dumps(message).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)


def main():
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("INBOX")

    _, data = mail.search(None, f'(UNSEEN FROM "{SPP_SENDER}")')
    email_ids = data[0].split()

    for eid in email_ids:
        _, msg_data = mail.fetch(eid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        subject_raw = decode_header(msg["Subject"])[0][0]
        subject = subject_raw.decode() if isinstance(subject_raw, bytes) else subject_raw

        match = re.match(r"^(.+) paid (.+) for invoice #([A-Z0-9]+)$", subject)
        if not match:
            continue

        client_name = match.group(1)
        amount = match.group(2)
        order_id = match.group(3)

        service = "Unknown"
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode()
                service = get_service_from_html(html)
                break

        post_to_slack(client_name, order_id, service, amount)
        mail.store(eid, "+FLAGS", "\\Seen")

    mail.logout()


if __name__ == "__main__":
    main()
