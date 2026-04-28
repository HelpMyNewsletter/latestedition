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


def remove_polls(html: str) -> str:
    patterns = [
        r"<beehiiv-poll[\s\S]*?</beehiiv-poll>",
        r"<div[^>]*data-poll-id[^>]*>[\s\S]*?</div>",
        r"<div[^>]*class=[\"'][^\"']*bh-poll[^\"']*[\"'][^>]*>[\s\S]*?</div>",
        r"<script[^>]*poll\.beehiiv\.com[^>]*>[\s\S]*?</script>",
        r"<script[^>]*poll\.beehiiv\.com[^>]*/>",
    ]

    for pattern in patterns:
        html = re.sub(pattern, "", html, flags=re.IGNORECASE)

    return html


def remove_beehiiv_ads(html: str) -> str:
    """
    Remove beehiiv ads even when they are wrapped in generic nested sections.
    This targets the whole ad section from its opening section div through
    the next custom_html block.
    """

    ad_markers = [
        "utm_source=beehiivads",
        "_bhiiv=opp_",
        "bhcl_id",
        "Turn AI Into Extra Income",
        "mindstream.news",
    ]

    for marker in ad_markers:
        while marker.lower() in html.lower():
            lower_html = html.lower()
            marker_idx = lower_html.find(marker.lower())

            section_start = lower_html.rfind("<div", 0, marker_idx)

            while section_start != -1:
                div_open = lower_html[section_start:section_start + 500]
                if "class=" in div_open and "section" in div_open:
                    break
                section_start = lower_html.rfind("<div", 0, section_start)

            if section_start == -1:
                break

            next_custom_html = lower_html.find('<div class="custom_html"', marker_idx)

            if next_custom_html == -1:
                next_custom_html = lower_html.find("<div class='custom_html'", marker_idx)

            if next_custom_html != -1:
                html = html[:section_start] + html[next_custom_html:]
            else:
                section_end = lower_html.find("</div>", marker_idx)

                if section_end == -1:
                    break

                html = html[:section_start] + html[section_end + len("</div>"):]

    return html


def remove_beehiiv_native_blocks(html: str) -> str:
    patterns = [
        r"<beehiiv-[\w-]+[\s\S]*?</beehiiv-[\w-]+>",
        r"<beehiiv-[\w-]+[^>]*/>",

        r"<script[^>]*beehiiv[^>]*>[\s\S]*?</script>",
        r"<script[^>]*beehiiv[^>]*/>",
        r"<iframe[^>]*beehiiv[^>]*>[\s\S]*?</iframe>",
        r"<iframe[^>]*beehiiv[^>]*/>",

        r"<div[^>]*data-[^>]*(poll|referral|recommendation|boost|ad|advertisement|survey|subscribe|comment)[^>]*>[\s\S]*?</div>",

        r"<div[^>]*(class|id)=[\"'][^\"']*(bh-|poll|referral|recommendation|boost|ad|advertisement|sponsor|survey|subscribe|comment)[^\"']*[\"'][^>]*>[\s\S]*?</div>",

        r"<a[^>]*href=[\"'][^\"']*beehiiv\.com[^\"']*(referral|recommend|boost|subscribe|poll|survey)[^\"']*[\"'][^>]*>[\s\S]*?</a>",

        r"<p[^>]*>[\s\S]*?(Share this newsletter|Refer a friend|Subscribe to keep reading|Leave a comment|Take the poll|Vote in the poll|Sponsored by|Advertisement)[\s\S]*?</p>",
        r"<div[^>]*>[\s\S]*?(Share this newsletter|Refer a friend|Subscribe to keep reading|Leave a comment|Take the poll|Vote in the poll|Sponsored by|Advertisement)[\s\S]*?</div>",
    ]

    for pattern in patterns:
        html = re.sub(pattern, "", html, flags=re.IGNORECASE)

    return html


def strip_beehiiv_footer(html: str) -> str:
    markers = [
        "powered by beehiiv",
        "published with beehiiv",
        "unsubscribe",
        "manage your subscription",
    ]

    lower_html = html.lower()

    found_indexes = [
        lower_html.find(marker)
        for marker in markers
        if lower_html.find(marker) != -1
    ]

    if found_indexes:
        return html[:min(found_indexes)]

    return html


def clean_html(html: str) -> str:
    html = remove_polls(html)
    html = remove_beehiiv_ads(html)
    html = remove_beehiiv_native_blocks(html)
    html = strip_beehiiv_footer(html)

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
    max-width: 568px;
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
    max-width: 568px;
    margin: 0 auto;
    padding: 20px;
  }}

  .hmn-footer {{
    max-width: 568px;
    margin: 28px auto 0 auto;
    padding: 12px 20px;
    border-top: 1px solid #333333;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .hmn-footer a img {{
    display: block;
    max-height: 64px;
    width: auto;
  }}

  @media (max-width: 480px) {{
    .hmn-footer {{
      flex-direction: column;
      gap: 16px;
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

  <a href="{BEEHIIV_AFFILIATE_URL}"
     target="_blank" rel="noopener noreferrer">
    <img
      src="https://beehiiv-images-production.s3.amazonaws.com/uploads/asset/file/de8db07f-5edf-4790-be80-2c28563eede9/Add_a_subheading.png?t=1763656347"
      alt="Start your newsletter on beehiiv">
  </a>

  <a href="{BOOKING_URL}"
     target="_blank" rel="noopener noreferrer">
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
