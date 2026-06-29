#!/usr/bin/env python3
"""Export interlinking_progress.json to Google Sheet for client review."""
import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_PATH = os.path.join(SCRIPT_DIR, 'indexchex', 'service_account.json')
PROGRESS_PATH = os.path.join(SCRIPT_DIR, 'interlinking_progress.json')
WORKFILE_PATH = os.path.join(SCRIPT_DIR, 'interlinking_workfile.json')
SHEET_ID = "12Hgpv5ZED9WAeuImcp15pZkWqiqFJTlsQohMYuqDl9g"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=SCOPES)
svc = build("sheets", "v4", credentials=creds).spreadsheets()

with open(PROGRESS_PATH, encoding='utf-8') as f:
    progress = json.load(f)

with open(WORKFILE_PATH, encoding='utf-8') as f:
    workfile = json.load(f)

# Build rows for Structured tab
rows = []
header_row_indices = []
url_row_indices = []
link_cells = []

articles_with_links = 0
articles_no_links = 0
total_links = 0

# Sort by cluster then title
sorted_slugs = sorted(
    progress['done'],
    key=lambda s: (workfile.get(s, {}).get('cluster', 'ZZZ'), workfile.get(s, {}).get('title', s))
)

for slug in sorted_slugs:
    result = progress['results'].get(slug, {})
    links = result.get('new_links', [])
    meta = workfile.get(slug, {})
    title = meta.get('title', slug)
    cluster = meta.get('cluster', 'Unknown')
    existing_count = len(meta.get('existing_links', []))

    url = f"https://www.lido.app/blog/{slug}"
    url_row_indices.append(len(rows))
    link_cells.append((len(rows), 0, url))
    rows.append([f"{title}  [{cluster}]"])

    if links:
        articles_with_links += 1
        header_row_indices.append(len(rows))
        rows.append(["Anchor Text", "Links To", "Paragraph", "Reason"])
        for link in links:
            target_url = f"https://www.lido.app/blog/{link['target_slug']}"
            link_cells.append((len(rows), 1, target_url))
            rows.append([
                link['anchor_text'],
                target_url,
                link.get('paragraph', ''),
                link.get('reason', '')
            ])
            total_links += 1
    else:
        articles_no_links += 1
        rows.append(["No new links recommended" + (f" (already has {existing_count} existing links)" if existing_count else "")])

    rows.append([])

# Build Summary tab
cluster_stats = {}
for slug in progress['done']:
    meta = workfile.get(slug, {})
    cluster = meta.get('cluster', 'Unknown')
    links = progress['results'].get(slug, {}).get('new_links', [])
    if cluster not in cluster_stats:
        cluster_stats[cluster] = {'articles': 0, 'links': 0}
    cluster_stats[cluster]['articles'] += 1
    cluster_stats[cluster]['links'] += len(links)

summary_rows = [
    ["Metric", "Value"],
    ["Articles Reviewed", len(progress['done'])],
    ["Total Articles on Blog", progress.get('total', 376)],
    ["Progress", f"{len(progress['done'])}/{progress.get('total', 376)} ({round(len(progress['done'])/progress.get('total',376)*100)}%)"],
    ["Total New Links Planned", total_links],
    ["Articles Receiving New Links", articles_with_links],
    ["Articles with No New Links", articles_no_links],
    ["Avg New Links per Article (with links)", round(total_links / articles_with_links, 1) if articles_with_links else 0],
    [],
    ["Cluster", "Articles Reviewed", "New Links", "Avg Links"],
]
for cluster, stats in sorted(cluster_stats.items(), key=lambda x: -x[1]['articles']):
    avg = round(stats['links'] / stats['articles'], 1) if stats['articles'] else 0
    summary_rows.append([cluster, stats['articles'], stats['links'], avg])

summary_rows.extend([
    [],
    ["Notes"],
    ["All existing client-added links are preserved unchanged."],
    ["New links use natural anchor text from existing paragraph content."],
    ["Anchor text is varied across articles to avoid over-optimization."],
    ["Orphan articles (0 inbound links) are prioritized as link targets."],
    ["Articles with 9+ existing links receive 0-1 new links to avoid over-linking."],
])

# Write to sheets
existing_sheets = svc.get(spreadsheetId=SHEET_ID).execute()
existing_tabs = {s["properties"]["title"]: s["properties"]["sheetId"] for s in existing_sheets["sheets"]}

for tab in ["Structured", "Summary"]:
    if tab not in existing_tabs:
        svc.batchUpdate(
            spreadsheetId=SHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
        ).execute()
        existing_sheets = svc.get(spreadsheetId=SHEET_ID).execute()
        existing_tabs = {s["properties"]["title"]: s["properties"]["sheetId"] for s in existing_sheets["sheets"]}

struct_sid = existing_tabs["Structured"]
sum_sid = existing_tabs["Summary"]

# Clear everything first
print("Clearing existing data...")
svc.values().clear(spreadsheetId=SHEET_ID, range="'Structured'!A:Z").execute()
svc.values().clear(spreadsheetId=SHEET_ID, range="'Summary'!A:Z").execute()

# Clear all formatting on both tabs
svc.batchUpdate(
    spreadsheetId=SHEET_ID,
    body={"requests": [
        {
            "repeatCell": {
                "range": {"sheetId": struct_sid},
                "cell": {"userEnteredFormat": {}},
                "fields": "userEnteredFormat",
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": sum_sid},
                "cell": {"userEnteredFormat": {}},
                "fields": "userEnteredFormat",
            }
        },
    ]},
).execute()

# Write data
print(f"Writing {len(rows)} rows to Structured tab...")
CHUNK = 5000
for i in range(0, len(rows), CHUNK):
    chunk = rows[i:i+CHUNK]
    start_row = i + 1
    svc.values().update(
        spreadsheetId=SHEET_ID, range=f"'Structured'!A{start_row}",
        valueInputOption="USER_ENTERED", body={"values": chunk},
    ).execute()

print("Writing Summary tab...")
svc.values().update(
    spreadsheetId=SHEET_ID, range="'Summary'!A1",
    valueInputOption="RAW", body={"values": summary_rows},
).execute()

# Format requests
format_requests = []

# Article title rows: bold blue text
for row_idx in url_row_indices:
    format_requests.append({
        "repeatCell": {
            "range": {
                "sheetId": struct_sid,
                "startRowIndex": row_idx,
                "endRowIndex": row_idx + 1,
                "startColumnIndex": 0,
                "endColumnIndex": 4,
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 0.06, "green": 0.36, "blue": 0.72},
                        "underline": True,
                    },
                }
            },
            "fields": "userEnteredFormat(textFormat)",
        }
    })

# Header rows: bold + light gray fill
for row_idx in header_row_indices:
    format_requests.append({
        "repeatCell": {
            "range": {
                "sheetId": struct_sid,
                "startRowIndex": row_idx,
                "endRowIndex": row_idx + 1,
                "startColumnIndex": 0,
                "endColumnIndex": 4,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                    "textFormat": {"bold": True},
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }
    })

# Summary header
format_requests.append({
    "repeatCell": {
        "range": {"sheetId": sum_sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 4},
        "cell": {
            "userEnteredFormat": {
                "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.7},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            }
        },
        "fields": "userEnteredFormat(backgroundColor,textFormat)",
    }
})

# Auto-resize columns
format_requests.append({
    "autoResizeDimensions": {
        "dimensions": {"sheetId": struct_sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 4},
    }
})
format_requests.append({
    "autoResizeDimensions": {
        "dimensions": {"sheetId": sum_sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 4},
    }
})

# Hyperlinks
for row_idx, col_idx, url in link_cells:
    format_requests.append({
        "updateCells": {
            "range": {
                "sheetId": struct_sid,
                "startRowIndex": row_idx,
                "endRowIndex": row_idx + 1,
                "startColumnIndex": col_idx,
                "endColumnIndex": col_idx + 1,
            },
            "rows": [{
                "values": [{
                    "textFormatRuns": [{
                        "startIndex": 0,
                        "format": {"link": {"uri": url}}
                    }]
                }]
            }],
            "fields": "textFormatRuns",
        }
    })

# Send format requests in batches
BATCH_SIZE = 100
print(f"Applying {len(format_requests)} format requests...")
for i in range(0, len(format_requests), BATCH_SIZE):
    chunk = format_requests[i:i + BATCH_SIZE]
    svc.batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"requests": chunk},
    ).execute()

print(f"\nDone!")
print(f"  {len(progress['done'])} articles exported")
print(f"  {total_links} new links")
print(f"  {articles_with_links} articles with links, {articles_no_links} with none")
print(f"  https://docs.google.com/spreadsheets/d/{SHEET_ID}")
