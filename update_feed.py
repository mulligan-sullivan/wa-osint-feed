import json, re, html
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET

FEEDS = {
    # Iranian state media (English only)
    "Fars News English": "https://en.farsnews.ir/rss",
    "Tasnim English": "https://www.tasnimnews.ir/en/rss",
    "Mehr News English": "https://en.mehrnews.com/rss",
    
    # Regional outlets
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Al Arabiya English": "https://english.alarabiya.net/rss",
    "BBC Middle East": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "Anadolu Agency": "https://www.aa.com.tr/en/rss/default?cat=live",
    "AP World": "https://rsshub.app/apnews/topics/world-news",
    "Iran International": "https://www.iranintl.com/en/rss",
    
    # Maritime / military / tanker tracking
    "gCaptain Maritime": "https://feeds.feedburner.com/gcaptain",
    "USNI News": "https://news.usni.org/feed",
    "Defence Blog Maritime": "https://defence-blog.com/category/navy/feed",
    "World Maritime News": "https://feeds.feedburner.com/worldmaritimenews",
    
    # Seismic for missile impact detection
    "USGS Middle East": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
    
    # Twitter/X OSINT feeds via keep.md
    "OSINTdefender Twitter": "https://keep.md/api/x-rss/OSINTdefender.xml?content=posts",
    "UKMTO Twitter": "https://keep.md/api/x-rss/UKMTO.xml?content=posts",
    "IranIntl Twitter": "https://keep.md/api/x-rss/IranIntl.xml?content=posts",
    "Netblocks Twitter": "https://keep.md/api/x-rss/netblocks.xml?content=posts",
    "Hormuz Letter Twitter": "https://keep.md/api/x-rss/HormuzLetter.xml?content=posts",
    "TankerTrackers Twitter": "https://keep.md/api/x-rss/TankerTrackers.xml?content=posts",
    "Kpler Twitter": "https://keep.md/api/x-rss/Kpler.xml?content=posts",
    "Defence_IDA Twitter": "https://keep.md/api/x-rss/Defence_IDA.xml?content=posts",
}

# Stories must contain at least one of these to be included
WAR_KEYWORDS = [
    "iran", "hormuz", "strait", "gulf", "missile", "strike", "strikes",
    "tanker", "base", "war", "military", "drone", "casualt", "intercept", 
    "blockade", "brent", "oil", "sanction", "ceasefire", "escalat", 
    "retaliat", "irgc", "centcom", "jordan", "kuwait", "bahrain", "uae", 
    "saudi", "yemen", "houthi", "ansar", "israel", "gaza", "lebanon", 
    "hezbollah", "syria", "iraq", "trump", "khamenei", "nuclear", "iaea", 
    "refiner", "diesel", "gasoline", "spr", "patriot", "interceptor", 
    "ballistic", "carrier", "naval", "mines", "bombing", "embassy", 
    "mediation", "negotiation", "talks", "embargo", 
    "cargo", "port", "pipeline", "facility", "reserve", 
    "crack", "spread", "futures", "spot", 
    "spike", "plunge", "surge", "panic", "contagion",
    "destroyer", "submarine", "warship", "fleet", "sortie", "bomb", "ordnance",
    "wounded", "killed", "dead", "evacuation", "intercepted", "downed", "captured", "seized",
    "supertanker", "vlcc", "crude", "petroleum", "distillate", "bunker", "fuel oil",
    "enrichment", "centrifuge", "wedding", "mosque", "civilian", "children", "school", "hospital"
]

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
            if not title:
                continue
            combined = (title + " " + desc).lower()
            if not any(kw in combined for kw in WAR_KEYWORDS):
                continue
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
        "<p>Updates every 6 hours. Auto-refresh every 5 minutes.</p>",
        "<h2>Latest Entries</h2>",
    ]
    for e in entries[:200]:
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
