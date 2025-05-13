## 68248 page views as of 11/05/2025
import os, requests, time, csv, random
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from urllib.parse import quote
from tabulate import tabulate
from matplotlib.ticker import FuncFormatter

HEADERS = {'User-Agent': 'WikipediaPageviewFetcher/1.0 (your_email@example.com)'}
EXCLUDED_TITLES = {}

def get_edited_pages(username):
    url = "https://en.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "usercontribs", "ucuser": username,
              "uclimit": "max", "ucprop": "title|timestamp", "format": "json"}
    contribs = {}
    print(f"Fetching contributions for user: {username}")
    while True:
        r = requests.get(url=url, params=params, headers=HEADERS)
        if r.status_code != 200:
            print(f"Error fetching contributions: HTTP {r.status_code}")
            break
        for contrib in r.json()['query']['usercontribs']:
            title, timestamp = contrib['title'], contrib['timestamp']
            if title not in contribs or timestamp < contribs[title]:
                contribs[title] = timestamp
        if 'continue' in r.json():
            params.update(r.json()['continue'])
            time.sleep(0.5)
        else:
            break
    return contribs

def fetch_total_pageviews(title, start_date):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ")
        end = datetime.now()
        if start.year == end.year and start.month == end.month:
            end = end.replace(month=end.month % 12 + 1, year=end.year + end.month // 12)
        s_fmt, e_fmt = start.strftime("%Y%m01"), end.strftime("%Y%m01")
        t_enc = quote(title.replace(" ", "_"), safe='')
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/all-agents/{t_enc}/daily/{s_fmt}/{e_fmt}"
        r = requests.get(url, headers=HEADERS)
        return sum(i['views'] for i in r.json().get('items', [])) if r.status_code == 200 else None
    except Exception as e:
        print(f"❌ {title}: {e}")
        return None

def output_total_views(username):
    pages = get_edited_pages(username)
    records = [(t, v) for t, ts in pages.items() if t not in EXCLUDED_TITLES and (v := fetch_total_pageviews(t, ts)) and v > 0]
    time.sleep(0.5)
    records.sort(key=lambda x: x[1], reverse=True)

    print(tabulate(records, headers=["Page Title", "Total Views"], tablefmt="grid"))
    print(f"\n📊 Pages included: {len(records)}\n📊 Total combined views: {sum(v for _, v in records):,}")

    out_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "pageviews.csv")
    with open(out_path, "w", newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([["Page Title", "Total Views"]] + records)

    if input("\nDo you want to show the bar chart (y/n)? ").strip().lower() != 'y':
        return

    df = pd.DataFrame(records[:20], columns=["Page Title", "Total Views"])
    plt.figure(figsize=(10, 8))
    bars = plt.barh(df["Page Title"], df["Total Views"], color=[f"#{random.randint(0, 0xFFFFFF):06x}" for _ in df.index])
    for bar in bars: plt.text(bar.get_width(), bar.get_y() + bar.get_height()/2, f"{int(bar.get_width()):,}", va='center', fontsize=8)
    plt.xscale("log")
    plt.gca().xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    plt.title("Wikipedia Pageviews for Edited Pages (Log Scale)")
    plt.xlabel("Total Views (log scale)")
    plt.ylabel("Page Title")
    plt.tight_layout()
    plt.savefig("pageviews_plot.png")
    plt.show()

    if input("\nDo you want to see a line graph of total views over time (y/n)? ").strip().lower() == 'y':
        date_today, total_views = datetime.now().strftime('%Y-%m-%d'), sum(v for _, v in records)
        line_csv_path = os.path.join(os.path.dirname(__file__), "line_graph_data.csv")
        with open(line_csv_path, "a", newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([date_today, total_views])
        df_line = pd.read_csv(line_csv_path, names=["Date", "Total Views"])
        df_line["Date"] = pd.to_datetime(df_line["Date"])
        plt.figure(figsize=(10, 6))
        plt.plot(df_line["Date"], df_line["Total Views"], marker="o", linestyle='-', color="b")
        plt.title("Total Views Over Time (Daily)")
        plt.xlabel("Date")
        plt.ylabel("Total Views")
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("line_graph.png")
        plt.show()

output_total_views("username")
