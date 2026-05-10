#!/usr/bin/env python3
"""
봄 코칭심리연구소 네이버 블로그 RSS → 홈페이지 활동이력 자동 업데이트
'강사의 하루' 카테고리 최신 4개 포스트를 proof-section에 반영합니다.
이미지는 assets/proof/ 에 로컬로 저장해 네이버 CDN 의존성을 제거합니다.
"""
import hashlib
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

RSS_URL = "https://rss.blog.naver.com/bomcoach.xml"
CATEGORY = "강사의 하루"
MAX_ITEMS = 4
HTML_FILE = Path(__file__).parent / "index.html"
PROOF_IMG_DIR = Path(__file__).parent / "assets" / "proof"
MARKER_START = "<!-- PROOF_AUTO_START -->"
MARKER_END = "<!-- PROOF_AUTO_END -->"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://blog.naver.com/",
}


def fetch_url(url: str, binary: bool = False):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read() if binary else resp.read().decode("utf-8")


def download_image(img_url: str) -> str:
    """이미지를 assets/proof/ 에 저장하고 로컬 경로를 반환합니다."""
    if not img_url:
        return ""
    PROOF_IMG_DIR.mkdir(parents=True, exist_ok=True)

    # URL 해시로 파일명 결정 (확장자 추론)
    url_hash = hashlib.md5(img_url.encode()).hexdigest()[:12]
    ext = ".jpg"
    if ".png" in img_url.lower():
        ext = ".png"
    elif ".webp" in img_url.lower():
        ext = ".webp"
    local_path = PROOF_IMG_DIR / f"{url_hash}{ext}"

    if not local_path.exists():
        try:
            data = fetch_url(img_url, binary=True)
            local_path.write_bytes(data)
            print(f"    이미지 저장: {local_path.name}")
        except Exception as e:
            print(f"    이미지 다운로드 실패 ({url_hash}): {e}")
            return ""

    return f"assets/proof/{local_path.name}"


def parse_items(xml_content: str) -> list[dict]:
    root = ET.fromstring(xml_content)
    channel = root.find("channel")
    items = []
    for item in channel.findall("item"):
        cat = item.find("category")
        if cat is None or CATEGORY not in (cat.text or ""):
            continue

        title = item.find("title").text or ""
        link = item.find("link").text or ""
        pub_raw = item.find("pubDate").text or ""

        desc_raw = item.find("description").text or ""
        desc_clean = html.unescape(desc_raw)

        img_match = re.search(r'<img[^>]+src=["\'](https?://[^"\'> ]+)', desc_clean)
        remote_img = img_match.group(1) if img_match else ""

        text = re.sub(r"<[^>]+>", "", desc_clean)
        text = re.sub(r"\s+", " ", text).strip()[:110]
        if text:
            text += "…"

        try:
            dt = parsedate_to_datetime(pub_raw)
            date_str = dt.strftime("%Y.%m")
        except Exception:
            date_str = ""

        items.append({
            "title": title,
            "link": link,
            "remote_img": remote_img,
            "text": text,
            "date": date_str,
        })
        if len(items) >= MAX_ITEMS:
            break

    return items


def render_cards(items: list[dict]) -> str:
    cards = []
    for item in items:
        local_img = item.get("local_img", "")
        img_tag = (
            f'                <img src="{local_img}" alt="{html.escape(item["title"])}" loading="lazy">'
            if local_img
            else ""
        )
        card = f"""\
            <article class="proof-card">
              <a class="proof-link" href="{item['link']}" target="_blank" rel="noreferrer">
{img_tag}
                <div class="proof-copy">
                  <span>{item['date']}</span>
                  <h3>{item['title']}</h3>
                  <p>{item['text']}</p>
                </div>
              </a>
            </article>"""
        cards.append(card)
    return "\n".join(cards)


def update_html(html_path: Path, new_cards: str) -> bool:
    original = html_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}",
        re.DOTALL,
    )
    replacement = f"{MARKER_START}\n{new_cards}\n          {MARKER_END}"
    updated = pattern.sub(replacement, original)
    if updated == original:
        return False
    html_path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    print("RSS 피드 가져오는 중...")
    xml_content = fetch_url(RSS_URL)

    print("포스트 파싱 중...")
    items = parse_items(xml_content)
    print(f"  → {len(items)}개 포스트 확인됨")

    print("이미지 다운로드 중...")
    for item in items:
        item["local_img"] = download_image(item["remote_img"])
        print(f"  [{item['date']}] {item['title']}")

    new_cards = render_cards(items)

    print("index.html 업데이트 중...")
    changed = update_html(HTML_FILE, new_cards)
    if changed:
        print("완료: 활동이력이 업데이트되었습니다.")
    else:
        print("변경 없음: 이미 최신 상태입니다.")


if __name__ == "__main__":
    main()
