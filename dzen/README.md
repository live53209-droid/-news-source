# Dzen RSS Module (New System)

This is a **completely separate** system for publishing to your Dzen channel (https://dzen.ru/dfd) via RSS.

**Important:**
- This code lives in `dzen/` and does **NOT** touch or depend on the old Telegram bot (`zen_auto_boss.py`).
- Currently using **OpenAI (ChatGPT)** for rewriting articles into Dzen style.
- Goal: Simple, fast, low-risk RSS generation for Dzen.

## Quick Start (MVP)

1. Fill in your SuperGrok credentials in `dzen/config.py` (or use environment variables).
2. Install dependencies:
   ```bash
   pip install -r dzen/requirements.txt
   playwright install chromium
   ```
3. Run the processor on a Hypebeast article:
   ```bash
   python -m dzen.process_article --url "https://hypebeast.com/..."
   ```
4. Generate the feed:
   ```bash
   python -m dzen.generate_feed
   ```
5. Commit & push → GitHub Pages will serve the new `feed.xml`.

## Current Status

This is the early MVP stage. The focus is on getting a working RSS feed as quickly as possible.

See the main plan at the root of the session for the full roadmap.

## Why SuperGrok instead of Hermes 3?

You specifically requested to use your already-connected SuperGrok for higher quality Dzen-style content generation. The new code is designed around an OpenAI-compatible client from the beginning.