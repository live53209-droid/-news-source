"""
Generate feed.xml for Yandex Dzen from processed articles.

This script creates a clean, production-ready RSS 2.0 feed
compatible with Yandex Dzen requirements.
"""

import json
from datetime import datetime
from pathlib import Path
from email.utils import format_datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

from dzen.config import config
from dzen import feed_config


def get_articles(limit: int = None) -> list[dict]:
    """Load processed articles from dzen_articles/ folder."""
    articles = []
    articles_dir = config.articles_dir

    if not articles_dir.exists():
        return articles

    for article_folder in sorted(articles_dir.iterdir(), reverse=True):
        if not article_folder.is_dir():
            continue

        meta_path = article_folder / "meta.json"
        if not meta_path.exists():
            continue

        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)

            meta["folder"] = article_folder.name
            articles.append(meta)
        except Exception as e:
            print(f"[Feed] Warning: Could not read {meta_path}: {e}")
            continue

    articles.sort(key=lambda x: x.get("pub_date", ""), reverse=True)

    if limit:
        articles = articles[:limit]

    return articles


def build_content_html(article: dict) -> str:
    """Build clean HTML for <content:encoded> section."""
    parts = []

    # Title as H1
    parts.append(f"<h1>{article['title']}</h1>")

    # Main rewritten text
    parts.append(article["dzen_text"])

    # Images gallery
    if article.get("images"):
        parts.append("<h2>Фотографии</h2>")
        for img_name in article["images"]:
            img_url = f"{feed_config.BASE_IMAGE_URL}dzen_articles/{article['folder']}/images/{img_name}"
            parts.append(f'<figure><img src="{img_url}" alt="{article["title"]}" loading="lazy"></figure>')

    return "\n".join(parts)


def build_rss_feed(articles: list[dict]) -> str:
    """Build a clean RSS 2.0 feed for Yandex Dzen."""
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

    channel = ET.SubElement(rss, "channel")

    # Channel info from feed_config
    ET.SubElement(channel, "title").text = feed_config.CHANNEL_TITLE
    ET.SubElement(channel, "link").text = feed_config.CHANNEL_LINK
    ET.SubElement(channel, "description").text = feed_config.CHANNEL_DESCRIPTION
    ET.SubElement(channel, "language").text = feed_config.LANGUAGE
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now())

    # Self link (good practice)
    atom_link = ET.SubElement(channel, "atom:link")
    atom_link.set("href", f"{feed_config.CHANNEL_LINK}/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    for article in articles:
        item = ET.SubElement(channel, "item")

        ET.SubElement(item, "title").text = article["title"]
        ET.SubElement(item, "link").text = article["original_url"]

        guid = ET.SubElement(item, "guid", isPermaLink="false")
        guid.text = article["original_url"]

        # Pub date
        try:
            pub_date = datetime.fromisoformat(article["pub_date"])
            ET.SubElement(item, "pubDate").text = format_datetime(pub_date)
        except:
            ET.SubElement(item, "pubDate").text = format_datetime(datetime.now())

        # Enclosure (main image)
        if article.get("images"):
            first_image = article["images"][0]
            img_url = f"{feed_config.BASE_IMAGE_URL}dzen_articles/{article['folder']}/images/{first_image}"
            enclosure = ET.SubElement(item, "enclosure")
            enclosure.set("url", img_url)
            enclosure.set("type", "image/jpeg")

        # Full content with CDATA
        content_html = build_content_html(article)
        content_elem = ET.SubElement(item, "content:encoded")
        content_elem.text = content_html   # We will wrap in CDATA later

    # Generate pretty XML with proper CDATA
    rough_string = ET.tostring(rss, encoding="utf-8", method="xml")
    reparsed = minidom.parseString(rough_string)

    # Manually ensure CDATA for content:encoded
    for content_elem in reparsed.getElementsByTagName("content:encoded"):
        if content_elem.firstChild and content_elem.firstChild.nodeType == content_elem.TEXT_NODE:
            text = content_elem.firstChild.data
            content_elem.removeChild(content_elem.firstChild)
            cdata = reparsed.createCDATASection(text)
            content_elem.appendChild(cdata)

    return reparsed.toprettyxml(indent="  ")


def main():
    print("[Dzen] Generating feed.xml...")

    articles = get_articles(limit=feed_config.MAX_ARTICLES_IN_FEED)

    if not articles:
        print("[Dzen] No articles found in dzen_articles/. Nothing to generate.")
        return

    print(f"[Dzen] Found {len(articles)} article(s)")

    feed_xml = build_rss_feed(articles)

    feed_path = Path("feed.xml")
    feed_path.write_text(feed_xml, encoding="utf-8")

    print(f"[Dzen] ✅ feed.xml successfully generated: {feed_path.absolute()}")
    print(f"[Dzen] Articles in feed: {len(articles)}")


if __name__ == "__main__":
    main()