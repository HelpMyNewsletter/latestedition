import re
from urllib.request import urlopen

RSS_URL = "https://rss.beehiiv.com/feeds/NRMXBlkDdv.xml"


def main():
    # Fetch RSS XML
    with urlopen(RSS_URL, timeout=20) as resp:
        xml = resp.read().decode("utf-8", errors="replace")

    # Try to grab the full edition from <content:encoded><![CDATA[ ... ]]>
    m = re.search(
        r"<content:encoded><!\[CDATA\[(.*)\]\]></content:encoded>",
        xml,
        re.DOTALL,
    )

    if m:
        body_html = m.group(1)
    else:
        # Fallback to <description> if content:encoded is missing for some reason
        m2 = re.search(
            r"<description><!\[CDATA\[(.*)\]\]></description>",
            xml,
            re.DOTALL,
        )
        body_html = m2.group(1) if m2 else "<p>No content found in RSS.</p>"

    # Wrap it in a minimal dark HTML shell
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
