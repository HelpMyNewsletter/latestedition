import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

RSS_URL = "https://rss.beehiiv.com/feeds/NRMXBlkDdv.xml"
SUBSCRIBE_URL = "https://triage.helpmynewsletter.com/subscribe"
BEEHIIV_AFFILIATE_URL = "https://www.beehiiv.com/?via=JenniferGibbs1"
BOOKING_URL = "https://calendar.app.google/6E3acH7JZZVMDgLaA"


def fetch_rss() -> str:
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


def extract_latest_body(xml: str) -> str:
    item_match = re.search(r"<item[\s\S]*?</item>", xml, flags=re.IGNORECASE)
    search_area = item_match.group(0) if item_match else xml

    content_match = re.search(
        r"<content:encoded><!\[CDATA\[(.*?)\]\]></content:encoded>",
        search_area,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if content_match:
        return content_match.group(1)

    desc_match = re.search(
        r"<description><!\[CDATA\[(.*?)\]\]></description>",
        search_area,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return desc_match.group(1) if desc_match else "<p>No content found.</p>"


def extract_custom_html_blocks(html: str) -> str:
    """
    Keep only beehiiv custom_html blocks.
    This removes native ads, referral blocks, polls, boosts, recommendations,
    and any future beehiiv-native section blocks inserted between custom HTML.
    """

    blocks = []
    lower_html = html.lower()
    search_pos = 0

    while True:
        start_match = re.search(
            r'''<div[^>]*class=["']custom_html["'][^>]*>''',
            html[search_pos:],
            flags=re.IGNORECASE,
        )

        if not start_match:
            break

        start_pos = search_pos + start_match.start()
        i = start_pos
        depth = 0
        end_pos = None

        while i < len(html):
            if html[i:i + 4].lower() == "<div":
                depth += 1
                close_bracket = html.find(">", i)
                if close_bracket == -1:
                    break
                i = close_bracket + 1

            elif html[i:i + 6].lower() == "</div>":
                depth -= 1
                i += 6

                if depth == 0:
                    end_pos = i
                    break

            else:
                i += 1

        if end_pos is None:
            break

        block = html[start_pos:end_pos]
        blocks.append(block)
        search_pos = end_pos

    if blocks:
        return "\n\n".join(blocks)

    return html


def strip_beehiiv_footer(html: str) -> str:
    markers = [
        "powered by beehiiv",
        "published with beehiiv",
        "unsubscribe",
        "manage your subscription",
    ]

    lower_html = html.lower()
    indexes = []

    for marker in markers:
        idx = lower_html.find(marker)
        if idx != -1:
            indexes.append(idx)

    if indexes:
        return html[:min(indexes)]

    return html


def clean_html(html: str) -> str:
    html = extract_custom_html_blocks(html)
    html = strip_beehiiv_footer(html)

    html = re.sub(r"<title>[\s\S]*?</title>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"\n\s*\n\s*\n+", "\n\n", html)
    html = re.sub(r"<p>\s*</p>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<div>\s*</div>", "", html, flags=re.IGNORECASE)

    return html.strip()


def main():
    try:
        xml = fetch_rss()
    except (HTTPError, URLError) as e:
        print(f"Failed to fetch RSS: {e}")
        return

    body_html = extract_latest_body(xml)
    body_html = clean_html(body_html)

    full_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Latest Help My Newsletter Edition</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
  body {{
    margin: 0;
    padding: 0 0 50px 0;
    background: #000000;
    color: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }}

  .hmn-notice {{
    max-width: 600px;
    margin: 20px auto 0 auto;
    padding: 16px 18px;
    background: #151515;
    border: 1px solid #333333;
    border-radius: 14px;
    color: #f5f5f5;
    font-size: 15px;
    line-height: 1.5;
    box-sizing: border-box;
  }}

  .hmn-notice strong {{
    color: #ffffff;
  }}

  .hmn-notice a {{
    color: #D6B943;
    font-weight: 700;
    text-decoration: none;
  }}

  .hmn-shell {{
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
    box-sizing: border-box;
    overflow-x: hidden;
  }}

  .hmn-shell img {{
    max-width: 100% !important;
    width: auto !important;
    height: auto !important;
  }}

  .hmn-shell table {{
    max-width: 100% !important;
  }}

  .hmn-shell iframe,
  .hmn-shell video,
  .hmn-shell embed,
  .hmn-shell object {{
    max-width: 100% !important;
  }}

  .hmn-footer {{
    max-width: 600px;
    margin: 28px auto 0 auto;
    padding: 12px 20px;
    border-top: 1px solid #333333;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-sizing: border-box;
  }}

  .hmn-footer a img {{
    display: block;
    max-height: 64px;
    max-width: 260px;
    width: auto;
    height: auto;
  }}

  @media (max-width: 480px) {{
    .hmn-footer {{
      flex-direction: column;
      gap: 16px;
    }}

    .hmn-footer a img {{
      max-width: 100%;
    }}
  }}
</style>
</head>

<body>

<div class="hmn-notice">
  <strong>Viewing note:</strong> Some interactive newsletter features are disabled in this web preview, including native polls, referral blocks, ads, and other beehiiv-only elements.
  <a href="{SUBSCRIBE_URL}" target="_blank" rel="noopener noreferrer">Subscribe here for the full experience.</a>
</div>

<div class="hmn-shell">
  {body_html}
</div>

<div class="hmn-footer">
  <a href="{BEEHIIV_AFFILIATE_URL}" target="_blank" rel="noopener noreferrer">
    <img
      src="https://beehiiv-images-production.s3.amazonaws.com/uploads/asset/file/de8db07f-5edf-4790-be80-2c28563eede9/Add_a_subheading.png?t=1763656347"
      alt="Start your newsletter on beehiiv">
  </a>

  <a href="{BOOKING_URL}" target="_blank" rel="noopener noreferrer">
    <img
      src="https://beehiiv-images-production.s3.amazonaws.com/uploads/asset/file/f5603471-e469-4bfe-94a6-dd08601cbbd5/Add_a_subheading__1_.png?t=1763656403"
      alt="Book a newsletter consult">
  </a>
</div>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_page)


if __name__ == "__main__":
    main()
