import json, re, html
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET

FEEDS = {
    "Fars News": "https://www.farsnews.ir/rss",
    "IRNA": "https://www.irna.ir/rss",
    "Tasnim": "https://www.tasnimnews.com/fa/rss",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Anadolu Agency": "https://www.aa.com.tr/en/rss/default?cat=live",
    "AP World": "https://rsshub.app/apnews/topics/world-news",
    "USGS Middle East": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
}

def fetch_rss(url):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None

def parse_rss(xml_bytes, source, max_items=8):
    items = []
    if not xml_bytes:
        return items
    try:
        root = ET.fromstring(xml_bytes)
        for item in root.iter("item"):
            title = item.findtext("title", default="")
            desc = item.findtext("description", default="")
            pub = item.findtext("pubDate", default="")
            link = item.findtext("link", default="")
            if title:
                items.append({
                    "source": source,
                    "time": pub or datetime.now(timezone.utc).isoformat(),
                    "title": html.escape(title),
                    "text": html.escape(re.sub(r"<[^>]+>", "", desc))[:400],
                    "link": link or ""
                })
            if len(items) >= max_items:
                break
    except Exception:
        pass
    return items

def fetch_usgs():
    try:
        req = Request(FEEDS["USGS Middle East"], headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        quakes = []
        for f in data.get("features", [])[:10]:
            props = f["properties"]
            coords = f["geometry"]["coordinates"]
            if 24 < coords[1] < 42 and 34 < coords[0] < 60:
                quakes.append({
                    "source": "USGS Seismic",
                    "time": datetime.fromtimestamp(props["time"]/1000, tz=timezone.utc).isoformat(),
                    "title": f"M{props['mag']} - {props['place']}",
                    "text": f"Depth: {coords[2]}km",
                    "link": props["url"]
                })
        return quakes
    except Exception:
        return []

def build_html(entries):
    entries.sort(key=lambda x: x["time"], reverse=True)
    lines = [
        "<!DOCTYPE html><html><head>",
        '<meta charset="UTF-8">',
        '<meta http-equiv="refresh" content="300">',
        "<title>OSINT Feed</title>",
        "<style>body{font-family:monospace;max-width:900px;margin:20px auto;padding:10px;background:#111;color:#eee}h1{color:#0f0}h2{color:#ff0;border-bottom:1px solid #444;padding-bottom:4px}.entry{margin:10px 0;padding:10px;background:#222;border-left:4px solid #0f0}.meta{color:#888;font-size:0.85em}.src{color:#0ff;font-weight:bold}</style>",
        "</head><body>",
        f"<h1>OSINT Feed - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</h1>",
        "<p>Updates daily. Auto-refresh every 5 minutes.</p>",
        "<h2>Latest Entries</h2>",
    ]
    for e in entries[:60]:
        lines.append(f'<div class="entry">')
        lines.append(f'<div class="meta"><span class="src">{e["source"]}</span> | {e["time"]}</div>')
        lines.append(f'<div><b>{e["title"]}</b></div>')
        if e["text"]:
            lines.append(f'<div>{e["text"]}</div>')
        if e["link"]:
            lines.append(f'<div><a href="{e["link"]}" style="color:#0f0">{e["link"]}</a></div>')
        lines.append('</div>')
    lines.append("</body></html>")
    return "\n".join(lines)

def main():
    all_entries = []
    for name, url in FEEDS.items():
        if "USGS" in name:
            continue
        xml = fetch_rss(url)
        all_entries.extend(parse_rss(xml, name))
    all_entries.extend(fetch_usgs())
    
    html_out = build_html(all_entries)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Wrote {len(all_entries)} entries to index.html")

if __name__ == "__main__":
    main()
  
