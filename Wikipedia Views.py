## 68248 page views as of 11/05/2025
import os
import requests
import time
import csv
import random
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from urllib.parse import quote
from tabulate import tabulate
from matplotlib.ticker import FuncFormatter

# Set proper headers to avoid 403 errors
HEADERS = {
    'User-Agent': 'WikipediaPageviewFetcher/1.0 (your_email@example.com)'
}

EXCLUDED_TITLES = {"Storror","Henrietta Swan Leavitt","Oleksiy Torokhtiy","BrowserQuest"}

def get_edited_pages(username):
    """Fetch all unique pages edited by a user with their first edit timestamp."""
    URL = "https://en.wikipedia.org/w/api.php"
    PARAMS = {
        "action": "query",
        "list": "usercontribs",
        "ucuser": username,
        "uclimit": "max",
        "ucprop": "title|timestamp",
        "format": "json"
    }

    contribs = {}
    print(f"Fetching contributions for user: {username}")
    while True:
        R = requests.get(url=URL, params=PARAMS, headers=HEADERS)
        if R.status_code != 200:
            print(f"Error fetching contributions: HTTP {R.status_code}")
            break
        DATA = R.json()
        for contrib in DATA['query']['usercontribs']:
            title = contrib['title']
            timestamp = contrib['timestamp']
            if title not in contribs or timestamp < contribs[title]:
                contribs[title] = timestamp
        if 'continue' in DATA:
            PARAMS.update(DATA['continue'])
            time.sleep(0.5)  # Polite delay
        else:
            break
    return contribs

def fetch_total_pageviews(title, start_date):
    """Fetch total pageviews for a given article since first edit, ensuring full months."""
    base_url = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
    project = "en.wikipedia.org"
    access = "all-access"
    # agent = "user" for just human users
    agent = "all-agents"
    granularity = "daily"

    try:
        # Format dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ")
        end_dt = datetime.now()

        # Ensure end is at least one full month after start
        if start_dt.year == end_dt.year and start_dt.month == end_dt.month:
            # Shift end to next month
            if end_dt.month == 12:
                end_dt = end_dt.replace(year=end_dt.year + 1, month=1)
            else:
                end_dt = end_dt.replace(month=end_dt.month + 1)

        start_fmt = start_dt.strftime("%Y%m01")
        end_fmt = end_dt.strftime("%Y%m01")

        # Encode title safely
        encoded_title = quote(title.replace(" ", "_"), safe='')
        url = f"{base_url}/{project}/{access}/{agent}/{encoded_title}/{granularity}/{start_fmt}/{end_fmt}"

        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            items = res.json().get('items', [])
            return sum(item['views'] for item in items)
        else:
            print(f"❌ HTTP {res.status_code} for '{title}' — URL: {url}")
            return None
    except Exception as e:
        print(f"❌ Exception for '{title}': {e}")
        return None


def output_total_views(username):
    pages = get_edited_pages(username)
    records = []

    for title, timestamp in pages.items():
        if title in EXCLUDED_TITLES:
            continue
        views = fetch_total_pageviews(title, timestamp)
        if views and views > 0:  # Required for log scale
            records.append((title, views))
        else:
            print(f"❌ {title} — Error fetching views")
        time.sleep(0.5)

    records.sort(key=lambda x: x[1], reverse=True)
    print(tabulate(records, headers=["Page Title", "Total Views"], tablefmt="grid"))
    print(f"\n📊 Pages included: {len(records)}")
    print(f"📊 Total combined views: {sum(v for _, v in records):,}")

    # Save to CSV in the same directory as the script
    script_directory = os.path.dirname(os.path.realpath(__file__))
    csv_file_path = os.path.join(script_directory, "pageviews.csv")
    with open(csv_file_path, "w", newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([["Page Title", "Total Views"]] + records)

    # Ask if user wants to show the bar chart
    if input("\nDo you want to show the bar chart (y/n)? ").strip().lower() != 'y':
        return

    # Plot bar chart
    df = pd.DataFrame(records[:20], columns=["Page Title", "Total Views"])
    colors = [f"#{random.randint(0, 0xFFFFFF):06x}" for _ in df.index]

    plt.figure(figsize=(max(12, len(df) * 0.4), 6))
    bars = plt.bar(df["Page Title"], df["Total Views"], color=colors, width=0.25)  # Thinner bars

    # Add value labels on top of bars
    for bar in bars:
        y = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, y, f"{int(y):,}", ha="center", va="bottom", fontsize=8)

    # X-axis styling
    plt.xticks(rotation=90, ha="center", fontsize=8)

    # Y-axis: Log scale with full labels
    plt.yscale("log")
    max_y = df["Total Views"].max()
    log_max = int(np.ceil(np.log10(max_y)))
    ticks = [10 ** i for i in range(0, log_max + 1)]
    plt.yticks(ticks)
    plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))

    plt.title("Wikipedia Pageviews for Edited Pages (Log Scale)")
    plt.xlabel("Page Title")
    plt.ylabel("Total Views (log scale)")
    plt.tight_layout()
    plt.savefig("pageviews_plot.png")
    plt.show()

    # Ask if user wants line graph
    if input("\nDo you want to see a line graph of total views over time (y/n)? ").strip().lower() == 'y':
        # Prepare data for line graph (daily data)
        date_today = datetime.now().strftime('%Y-%m-%d')
        total_views = sum(v for _, v in records)

        # Save line graph data in a separate CSV file
        line_csv_path = os.path.join(script_directory, "line_graph_data.csv")
        with open(line_csv_path, "a", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([date_today, total_views])

        # Plot line graph
        line_df = pd.read_csv(line_csv_path, names=["Date", "Total Views"])
        line_df["Date"] = pd.to_datetime(line_df["Date"])
        plt.figure(figsize=(10, 6))
        plt.plot(line_df["Date"], line_df["Total Views"], marker="o", linestyle='-', color="b")
        plt.title("Total Views Over Time (Daily)")
        plt.xlabel("Date")
        plt.ylabel("Total Views")
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("line_graph.png")
        plt.show()


# === RUN SCRIPT ===
output_total_views("Ajmullen")
