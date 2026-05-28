import asyncio
import os
import requests
import json
import time
from datetime import datetime
import ollama
from playwright.async_api import async_playwright

# ========================================================
# 1. КОНФИГУРАЦИЯ
# ========================================================
TELEGRAM_TOKEN = "8621328236:AAHKzylJv3jwabyGP_cP7UK1CkhkmwUWGyA"
TELEGRAM_CHAT_ID = "-1003956964604" 
ADMIN_ID = 5560827330 
CHECK_INTERVAL = 3600  
DB_FILE = "last_url_tg.txt"
STATS_FILE = "stats.log"
MODEL_NAME = "hermes3:latest"
BASE_URL = "https://hypebeast.com/footwear"

SIGNATURE = """
Мы доставляем бренды из официальных магазинов Европы и США, подписывайся и заказывай через наши соц.сети:
Наш телеграм - https://t.me/deliveryfromdiscount
Наш ВКонтакте - https://vk.com/deliveryfromdiscount
"""

# Глобальные заголовки
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

FORBIDDEN_KEYWORDS = ["QR", "приложение", "Hypebeast", "App Store", "Google Play", "устройстве"]

# ========================================================
# 2. СЕРВИСНЫЕ ФУНКЦИИ
# ========================================================
def log_post():
    with open(STATS_FILE, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

def get_today_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        if not os.path.exists(STATS_FILE): return 0
        with open(STATS_FILE, "r") as f:
            return sum(1 for line in f if today in line)
    except: return 0

def save_last_url(url):
    with open(DB_FILE, "w", encoding="utf-8") as f: f.write(url)

def get_last_url():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: return f.read().strip()
    return ""

# ========================================================
# 3. ПЕРЕВОД (HERMES 3) — С ЧИСТКОЙ ОТ ШЛАКА
# ========================================================
def translate_content(title, raw_content):
    print(f"🧠 Hermes 3: Перевод...")
    # Твои стоп-слова внедрены прямо в промпт
    system_inst = (
        "Ты профессиональный переводчик и эксперт в сникер-культуре. Твоя задача — перевести текст на грамотный русский язык. "
        "СТРОГО ЗАПРЕЩЕНО использовать слова: база, архив, легендарный, идеальный баланс, эстетика, дроп, маст-хэв, огонь, айтем, ротейшн, Y2K, колорвей. "
        "Пиши сухим экспертным языком. Бренды выделяй <b></b>."
    )
    try:
        response = ollama.generate(
            model=MODEL_NAME, 
            system=system_inst, 
            prompt=f"ЗАГОЛОВОК: {title}\nТЕКСТ: {raw_content[:2500]}",
            options={"num_predict": 1000, "temperature": 0.2}
        )
        return response['response']
    except: return "Ошибка перевода."

# ========================================================
# 4. ГИБРИДНЫЙ СКРАПЕР (ИСПРАВЛЕННЫЙ)
# ========================================================
async def process_and_post(url, is_force=False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Оставляем Retina-фактор для четкости скриншотов
        context = await browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={'width': 1600, 'height': 1200},
            device_scale_factor=3 
        )
        page = await context.new_page()
        
        try:
            print(f"🛠 Обработка: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Активация Lazy Load
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, 0)")

            title = await page.title()
            try:
                h1 = await page.inner_text("h1", timeout=3000)
                if h1: title = h1
            except: pass

            print("📸 Работа с медиа (План А -> План Б)...")
            media_files = {}
            media_group = []
            
            selectors = "article img, .entry-content img, .post-content img, .gallery-item img, picture img"
            image_elements = await page.locator(selectors).all()
            
            count = 0
            # ИСПРАВЛЕНИЕ: Используем глобальный HEADERS вместо context._options
            req_headers = HEADERS.copy()
            req_headers["Referer"] = url
            
            for el in image_elements:
                if count >= 9: break
                
                try:
                    img_url = await el.evaluate("""
                        img => img.srcset ? img.srcset.split(',').pop().trim().split(' ')[0] : (img.dataset.src || img.src)
                    """)
                    
                    img_data = None
                    
                    # План А: Прямое скачивание
                    if img_url and img_url.startswith('http'):
                        try:
                            res = requests.get(img_url, headers=req_headers, timeout=10)
                            if res.status_code == 200 and len(res.content) > 20000:
                                img_data = res.content
                                print(f"  💎 Фото {count+1}: Скачан оригинал.")
                        except: pass

                    # План Б: Retina-скриншот
                    if not img_data:
                        box = await el.bounding_box()
                        if box and box['width'] > 150:
                            await el.scroll_into_view_if_needed()
                            img_data = await el.screenshot(type="jpeg", quality=95)
                            print(f"  📸 Фото {count+1}: Сделан Retina-скриншот.")

                    if img_data:
                        file_name = f"img_{count}.jpg"
                        media_files[file_name] = img_data
                        media_group.append({"type": "photo", "media": f"attach://{file_name}"})
                        count += 1
                        
                except: continue

            if not media_group:
                print("❌ Медиа не найдено.")
                return False

            # Текст и перевод
            paragraphs = await page.locator("p").all_inner_texts()
            clean_p = [p.strip() for p in paragraphs if len(p.strip()) > 50 and not any(k in p for k in FORBIDDEN_KEYWORDS)]
            raw_content = "\n\n".join(clean_p[:10])

            translated = translate_content(title, raw_content)
            final_msg = f"<b>{title}</b>\n\n{translated}\n\n{SIGNATURE}"
            
            # Отправка в Telegram
            r_media = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMediaGroup",
                                    data={"chat_id": TELEGRAM_CHAT_ID, "media": json.dumps(media_group)}, files=media_files)
            
            if r_media.status_code == 200:
                time.sleep(2)
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                              data={"chat_id": TELEGRAM_CHAT_ID, "text": final_msg, "parse_mode": "HTML", "disable_web_page_preview": True})
                if not is_force: save_last_url(url)
                log_post()
                print("✨ Успех!")
                return True
                
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
        finally:
            await browser.close()
    return False

# ========================================================
# 5. УПРАВЛЕНИЕ
# ========================================================
async def telegram_commander():
    offset = 0
    print("🛰 Админ-панель активна.")
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=10").json()
            for update in r.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                if msg.get("from", {}).get("id") == ADMIN_ID:
                    text = msg.get("text", "")
                    if text == "/stats":
                        count = get_today_stats()
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                                      data={"chat_id": ADMIN_ID, "text": f"📊 Сегодня: {count}"})
                    elif text.startswith("/force "):
                        url = text.split(" ")[1]
                        asyncio.create_task(process_and_post(url, is_force=True))
        except: pass
        await asyncio.sleep(2)

async def auto_monitor():
    while True:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=HEADERS["User-Agent"])
            page = await context.new_page()
            try:
                await page.goto(BASE_URL, wait_until="networkidle")
                link = await page.locator("a.title").first.get_attribute("href")
                if link != get_last_url():
                    await process_and_post(link)
            except: pass
            finally: await browser.close()
        await asyncio.sleep(CHECK_INTERVAL)

async def main():
    await asyncio.gather(auto_monitor(), telegram_commander())

if __name__ == "__main__":
    try: asyncio.run(main())
    except: pass