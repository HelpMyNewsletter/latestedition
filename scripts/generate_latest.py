import re
from datetime import datetime
from email.utils import parsedate_to_datetime
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


def get_tag_value(item_html: str, tag_name: str) -> str:
    match = re.search(
        rf"<{tag_name}[^>]*>([\s\S]*?)</{tag_name}>",
        item_html,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    value = match.group(1).strip()
    value = re.sub(r"^<!\[CDATA\[", "", value)
    value = re.sub(r"\]\]>$", "", value)

    return value.strip()


def parse_item_date(date_text: str):
    if not date_text:
        return None

    try:
        return parsedate_to_datetime(date_text)
    except Exception:
        pass

    try:
        return datetime.fromisoformat(date_text.replace("Z", "+00:00"))
    except Exception:
        return None


def get_item_date(item_html: str):
    date_text = (
        get_tag_value(item_html, "pubDate")
        or get_tag_value(item_html, "atom:published")
        or get_tag_value(item_html, "atom:updated")
    )

    return parse_item_date(date_text)


def extract_items(xml: str) -> list[str]:
    return re.findall(r"<item[\s\S]*?</item>", xml, flags=re.IGNORECASE)


def extract_latest_item(xml: str) -> str:
    items = extract_items(xml)

    if not items:
        return xml

    dated_items = []

    for item in items:
        item_date = get_item_date(item)
        if item_date:
            dated_items.append((item_date, item))

    if dated_items:
        dated_items.sort(key=lambda pair: pair[0], reverse=True)
        return dated_items[0][1]

    return items[0]


def extract_latest_body(xml: str) -> str:
    latest_item = extract_latest_item(xml)

    content_match = re.search(
        r"<content:encoded><!\[CDATA\[([\s\S]*?)\]\]></content:encoded>",
        latest_item,
        flags=re.IGNORECASE,
    )

    if content_match:
        return content_match.group(1)

    desc_match = re.search(
        r"<description><!\[CDATA\[([\s\S]*?)\]\]></description>",
        latest_item,
        flags=re.IGNORECASE,
    )

    if desc_match:
        return desc_match.group(1)

    return "<p>No content found.</p>"


def extract_custom_html_blocks(html: str) -> str:
    blocks = []
    search_pos = 0

    while True:
        start_match = re.search(
            r'''<div[^>]*class=["'][^"']*\bcustom_html\b[^"']*["'][^>]*>''',
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

        blocks.append(html[start_pos:end_pos])
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


def remove_native_beehiiv_leftovers(html: str) -> str:
    ad_markers = [
        "utm_source=beehiivads",
        "_bhiiv=opp_",
        "bhcl_id=",
        "turn-ai-into-extra-income",
        "mindstream.news",
    ]

    for marker in ad_markers:
        while marker.lower() in html.lower():
            lower_html = html.lower()
            marker_pos = lower_html.find(marker.lower())

            section_start = lower_html.rfind("<div", 0, marker_pos)
            section_end = lower_html.find("</div>", marker_pos)

            if section_start == -1 or section_end == -1:
                break

            html = html[:section_start] + html[section_end + 6:]

    return html


def constrain_email_tables(html: str) -> str:
    html = re.sub(
        r'width=["\']600["\']',
        'width="100%"',
        html,
        flags=re.IGNORECASE,
    )

    html = re.sub(
        r"width:600px;max-width:600px;",
        "width:100%;max-width:100%;",
        html,
        flags=re.IGNORECASE,
    )

    html = re.sub(
        r"width:\s*600px",
        "width:100%",
        html,
        flags=re.IGNORECASE,
    )

    html = re.sub(
        r"max-width:\s*600px",
        "max-width:100%",
        html,
        flags=re.IGNORECASE,
    )

    return html


def protect_header_logo(html: str) -> str:
    html = re.sub(
        r'(<img[^>]+alt=["\']Help My Newsletter["\'][^>]*)(>)',
        r'\1 class="hmn-header-logo"\2',
        html,
        count=1,
        flags=re.IGNORECASE,
    )

    return html


def clean_html(html: str) -> str:
    html = extract_custom_html_blocks(html)
    html = remove_native_beehiiv_leftovers(html)
    html = strip_beehiiv_footer(html)

    html = re.sub(r"<title>[\s\S]*?</title>", "", html, flags=re.IGNORECASE)
    html = constrain_email_tables(html)
    html = protect_header_logo(html)

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
  *, *::before, *::after {{
    box-sizing: border-box;
  }}

  body {{
    margin: 0;
    padding: 0 0 50px 0;
    background: #000000;
    color: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }}

  .hmn-notice {{
    width: min(600px, calc(100% - 32px));
    margin: 20px auto 0 auto;
    padding: 16px 18px;
    background: #151515;
    border: 1px solid #333333;
    border-radius: 14px;
    color: #f5f5f5;
    font-size: 15px;
    line-height: 1.5;
  }}

  .hmn-notice strong {{
    color: #ffffff;
  }}

  .hmn-notice a {{
    color: #D6B943;
    font-weight: 700;
    text-decoration: none;
  }}

  .hmn-notice a:hover {{
    text-decoration: underline;
  }}

  .hmn-shell {{
    width: min(600px, calc(100% - 32px));
    margin: 0 auto;
    padding: 20px 0;
    overflow-x: hidden;
  }}

  .hmn-shell .custom_html,
  .hmn-shell .custom_html > table,
  .hmn-shell table {{
    width: 100% !important;
    max-width: 100% !important;
  }}

  .hmn-shell td {{
    max-width: 100% !important;
  }}

  .hmn-shell img {{
    max-width: 100% !important;
    height: auto !important;
  }}

  .hmn-shell img.hmn-header-logo,
  .hmn-shell img[alt="Help My Newsletter"] {{
    width: 56px !important;
    max-width: 56px !important;
    height: 56px !important;
    max-height: 56px !important;
    object-fit: contain !important;
  }}

  .hmn-shell iframe,
  .hmn-shell video,
  .hmn-shell embed,
  .hmn-shell object {{
    max-width: 100% !important;
  }}

  .hmn-footer {{
    width: min(600px, calc(100% - 32px));
    margin: 28px auto 0 auto;
    padding: 12px 0;
    border-top: 1px solid #333333;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
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
