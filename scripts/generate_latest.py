import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

RSS_URL = "https://rss.beehiiv.com/feeds/NRMXBlkDdv.xml"


def fetch_rss() -> str:
    # Use a normal browser-like User-Agent so Beehiiv/CDN doesn't 403 us
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    req = Request(RSS_URL, headers=headers)

    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main():
    try:
        xml = fetch_rss()
    except (HTTPError, URLError) as e:
        # If the fetch fails, keep the existing page instead of crashing the workflow
        print(f"Failed to fetch RSS: {e}")
        return

    # Grab the full edition from <content:encoded><![CDATA[ ... ]]>
    m = re.search(
        r"<content:encoded><!\[CDATA\[(.*)\]\]></content:encoded>",
        xml,
        re.DOTALL,
    )

    if m:
        body_html = m.group(1)
    else:
        # Fallback to <description> if content:encoded is missing
        m2 = re.search(
            r"<description><!\[CDATA\[(.*)\]\]></description>",
            xml,
            re.DOTALL,
        )
        body_html = m2.group(1) if m2 else "<p>No content found in RSS.</p>"

    full_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Latest Help My Newsletter Edition</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: #000000;
      color: #ffffff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}
  </style>
</head>
<body>
{body_html}
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_page)


if __name__ == "__main__":
    main()
