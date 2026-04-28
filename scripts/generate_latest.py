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

    if desc_match:
        return desc_match.group(1)

    return "<p>No content found.</p>"


def remove_polls(html: str) -> str:
    patterns = [
        r'''<beehiiv-poll[\s\S]*?</beehiiv-poll>''',
        r'''<div[^>]*data-poll-id[^>]*>[\s\S]*?</div>''',
        r'''<div[^>]*class=["'][^"']*bh-poll[^"']*["'][^>]*>[\s\S]*?</div>''',
        r'''<script[^>]*poll\.beehiiv\.com[^>]*>[\s\S]*?</script>''',
        r'''<script[^>]*poll\.beehiiv\.com[^>]*/>''',
    ]

    for pattern in patterns:
        html = re.sub(pattern, "", html, flags=re.IGNORECASE)

    return html


def remove_native_ads(html: str) -> str:
    patterns = [
        # Custom beehiiv ad elements
        r'''<beehiiv-ad[\s\S]*?</beehiiv-ad>''',
        r'''<beehiiv-ad[^>]*/>''',

        # Data attribute ad markers
        r'''<(?:div|section|aside|article)[^>]*data-sponsorship[^>]*>[\s\S]*?</(?:div|section|aside|article)>''',
        r'''<(?:div|section|aside|article)[^>]*data-ad-[^>]*>[\s\S]*?</(?:div|section|aside|article)>''',
        r'''<(?:div|section|aside|article)[^>]*data-boost[^>]*>[\s\S]*?</(?:div|section|aside|article)>''',

        # Class/id based native blocks
        r'''<(?:div|section|aside|article)[^>]*(class|id)=["'][^"']*(bh-ad|beehiiv-ad|native-ad|ad-wrapper|beehiiv-boost|sponsored)[^"']*["'][^>]*>[\s\S]*?</(?:div|section|aside|article)>''',

        # External beehiiv ad/boost loaders
        r'''<script[^>]*ads\.beehiiv\.com[^>]*>[\s\S]*?</script>''',
        r'''<script[^>]*ads\.beehiiv\.com[^>]*/>''',
        r'''<script[^>]*boosts\.beehiiv\.com[^>]*>[\s\S]*?</script>''',
        r'''<script[^>]*boosts\.beehiiv\.com[^>]*/>''',

        # Beehiiv redirect links
        r'''<a[^>]*href=["']https://(?:track\.)?beehiiv\.com/[^"']*(?:ad|boost|sponsor)[^"']*["'][^>]*>[\s\S]*?</a>''',
    ]

    for pattern in patterns:
        html = re.sub(pattern, "", html, flags=re.IGNORECASE)

    return html


def remove_section_ads(html: str) -> str:
    ad_markers = [
        "utm_source=beehiivads",
        "_bhiiv=opp_",
        "bhcl_id=",
        "turn-ai-into-extra-income",
        "mindstream.news",
    ]

    section_open = re.compile(
        r'''<div[^>]*class=["'][^"']*\bsection\b[^"']*["'][^>]*>''',
        re.IGNORECASE,
    )

    changed = True

    while changed:
        changed = False
        lower_html = html.lower()

        marker_pos = -1

        for marker in ad_markers:
            marker_pos = lower_html.find(marker.lower())
            if marker_pos != -1:
                break

        if marker_pos == -1:
            break

        preceding_html = html[:marker_pos]
        section_matches = list(section_open.finditer(preceding_html))

        if not section_matches:
            break

        start_pos = section_matches[-1].start()

        depth = 0
        i = start_pos
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

        html = html[:start_pos] + html[end_pos:]
        changed = True

    return html


def remove_common_native_blocks(html: str) -> str:
    patterns = [
        # Do not include "beehiiv" here, because the whole RSS body is wrapped in class='beehiiv'
        r'''<div[^>]*(class|id)=["'][^"']*(bh-|poll|referral|recommendation|boost|advertisement|sponsor|survey|subscribe|comment)[^"']*["'][^>]*>[\s\S]*?</div>''',

        # Beehiiv referral/recommendation/boost links
        r'''<a[^>]*href=["'][^"']*beehiiv\.com[^"']*(referral|recommend|boost|subscribe|poll|survey)[^"']*["'][^>]*>[\s\S]*?</a>''',

        # Common native copy blocks
        r'''<p[^>]*>[\s\S]*?(Share this newsletter|Refer a friend|Subscribe to keep reading|Leave a comment|Take the poll|Vote in the poll|Sponsored by|Advertisement)[\s\S]*?</p>''',
        r'''<div[^>]*>[\s\S]*?(Share this newsletter|Refer a friend|Subscribe to keep reading|Leave a comment|Take the poll|Vote in the poll|Sponsored by|Advertisement)[\s\S]*?</div>''',
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

    found_indexes = []

    for marker in markers:
        idx = lower_html.find(marker)
        if idx != -1:
            found_indexes.append(idx)

    if found_indexes:
        return html[:min(found_indexes)]

    return html


def clean_html(html: str) -> str:
    html = remove_polls(html)
    html = remove_native_ads(html)
    html = remove_section_ads(html)
    html = remove_common_native_blocks(html)
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

  .hmn-notice a:hover {{
    text-decoration: underline;
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

  .hmn-shell [class*="bh-ad"],
  .hmn-shell [class*="beehiiv-ad"],
  .hmn-shell [class*="native-ad"],
  .hmn-shell [class*="ad-wrapper"],
  .hmn-shell [class*="beehiiv-boost"],
  .hmn-shell [class*="sponsored"],
  .hmn-shell [data-sponsorship-id],
  .hmn-shell [data-boost],
  .hmn-shell beehiiv-ad {{
    display: none !important;
  }}

  .hmn-shell .section:has(a[href*="beehiivads"]),
  .hmn-shell .section:has(a[href*="_bhiiv=opp_"]),
  .hmn-shell .section:has(a[href*="bhcl_id="]),
  .hmn-shell .section:has(a[href*="mindstream.news"]) {{
    display: none !important;
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
    .hmn-notice,
    .hmn-shell,
    .hmn-footer {{
      max-width: 100%;
    }}

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
