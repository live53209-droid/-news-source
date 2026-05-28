"""
Process a single Hypebeast article end-to-end for Dzen.

This is the main processing script for the MVP.
"""

import argparse
import asyncio
import re
from datetime import datetime
from pathlib import Path
import json

from playwright.async_api import async_playwright
import requests

from dzen.config import config
from dzen.rewriter import rewrite_for_dzen


def slugify(text: str, max_length: int = 70) -> str:
    """Create a clean, short URL-friendly slug from text."""
    text = text.lower()
    # Remove common brand words and special characters
    text = re.sub(r'\b(salomon|pas normal|studios|nike|adidas|puma)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    # Remove duplicate dashes
    text = re.sub(r'-+', '-', text)
    return text[:max_length].strip('-')


async def scrape_hypebeast_article(url: str) -> dict | None:
    """Scrape title, text and images from a Hypebeast article."""
    print(f"[Scraper] Loading page: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1600, "height": 1200},
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Title
            title = await page.title()
            try:
                h1 = await page.inner_text("h1", timeout=4000)
                if h1:
                    title = h1.strip()
            except:
                pass

            # Text content
            paragraphs = await page.locator("article p, .post-body-content p").all_inner_texts()
            clean_paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 40]
            raw_text = "\n\n".join(clean_paragraphs[:12])

            # Images (hybrid approach)
            print("[Scraper] Collecting images...")
            image_elements = await page.locator("article img, .post-body-content img, picture img").all()
            images_data = []

            for i, img in enumerate(image_elements[:8]):
                try:
                    img_url = await img.evaluate("""
                        el => el.srcset ? el.srcset.split(',').pop().trim().split(' ')[0] : (el.dataset.src || el.src)
                    """)

                    img_bytes = None

                    # Plan A: Direct download
                    if img_url and img_url.startswith("http"):
                        try:
                            headers = {"User-Agent": context._options.get("user_agent", ""), "Referer": url}
                            res = requests.get(img_url, headers=headers, timeout=12)
                            if res.status_code == 200 and len(res.content) > 15000:
                                img_bytes = res.content
                                print(f"  [Image {i+1}] Downloaded original")
                        except:
                            pass

                    # Plan B: Screenshot
                    if not img_bytes:
                        try:
                            box = await img.bounding_box()
                            if box and box["width"] > 200:
                                await img.scroll_into_view_if_needed()
                                img_bytes = await img.screenshot(type="jpeg", quality=92)
                                print(f"  [Image {i+1}] Screenshot taken")
                        except:
                            pass

                    if img_bytes:
                        images_data.append({
                            "index": i,
                            "bytes": img_bytes,
                            "filename": f"{i+1:02d}.jpg"
                        })
                except:
                    continue

            await browser.close()

            return {
                "title": title,
                "raw_text": raw_text,
                "original_url": url,
                "images": images_data,
            }

        except Exception as e:
            print(f"[Scraper] Error: {e}")
            await browser.close()
            return None


async def process_article(url: str) -> Path | None:
    print(f"\n[Dzen] Processing article: {url}")

    # 1. Scrape
    article_data = await scrape_hypebeast_article(url)
    if not article_data:
        print("[Dzen] Failed to scrape article.")
        return None

    # 2. Generate Dzen text
    print("[Dzen] Rewriting with OpenAI...")
    dzen_text = rewrite_for_dzen(article_data["title"], article_data["raw_text"])

    # 3. Create slug and folder
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(article_data["title"])
    article_dir = config.articles_dir / f"{date_str}-{slug}"
    article_dir.mkdir(parents=True, exist_ok=True)
    images_dir = article_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # 4. Save images
    saved_images = []
    for img in article_data["images"]:
        img_path = images_dir / img["filename"]
        img_path.write_bytes(img["bytes"])
        saved_images.append(img["filename"])

    # 5. Save meta.json
    meta = {
        "title": article_data["title"],
        "dzen_text": dzen_text,
        "original_url": url,
        "pub_date": datetime.now().isoformat(),
        "images": saved_images,
        "model_used": config.llm.model,
    }

    meta_path = article_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[Dzen] Article saved to: {article_dir}")
    print(f"[Dzen] Images saved: {len(saved_images)}")
    print(f"[Dzen] Model used: {config.llm.model}")

    return article_dir


def main():
    parser = argparse.ArgumentParser(description="Process one Hypebeast article for Dzen")
    parser.add_argument("--url", required=True, help="Full Hypebeast article URL")
    args = parser.parse_args()

    result = asyncio.run(process_article(args.url))
    if result:
        print(f"\n✅ Done! Article folder: {result}")


if __name__ == "__main__":
    main()