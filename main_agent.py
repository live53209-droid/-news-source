import asyncio
import os
import ollama
from playwright.async_api import async_playwright

# Настройки
DB_FILE = "last_url.txt"
CHECK_INTERVAL = 600  # Проверка каждые 10 минут (600 секунд)
BASE_URL = "https://hypebeast.com/footwear"

# --- ФУНКЦИИ ПАМЯТИ ---
def get_last_processed_url():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return f.read().strip()
    return ""

def save_last_url(url):
    with open(DB_FILE, "w") as f:
        f.write(url)

# --- БЛОК 1: ПОИСК НОВИНОК (Discovery) ---
async def get_latest_article_url():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print(f"🔎 Проверяю раздел Footwear...")
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Находим первую ссылку в списке новостей
            first_article = page.locator("a.title").first
            url = await first_article.get_attribute("href")
            title = await first_article.inner_text()
            
            return url, title
        except Exception as e:
            print(f"❌ Ошибка при проверке сайта: {e}")
            return None, None
        finally:
            await browser.close()

# --- БЛОК 2: ПОЛНЫЙ ПАРСИНГ ---
async def scrape_article_data(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            title = await page.inner_text("h1")
            paragraphs = await page.locator(".post-body-content p, article p").all_inner_texts()
            content = "\n\n".join([p.strip() for p in paragraphs if len(p.strip()) > 30])
            return {"title": title, "content": content}
        finally:
            await browser.close()

# --- БЛОК 3: ГЕНЕРАЦИЯ ПРОДАЮЩЕГО ПОСТА (Hermes 3) ---
def generate_sales_post(data):
    print("🧠 Hermes 3 создает продающий пост...")
    
    system_instruction = (
        "Ты — профессиональный контент-менеджер и эксперт по продажам кроссовок. "
        "Твоя цель: перевести статью на грамотный, понятный русский язык и сделать из неё ПРОДАЮЩИЙ пост. "
        "Людям должно быть понятно, почему эта модель крутая и стоит ли её покупать. "
        "Избегай сложного английского сленга, объясняй всё доступно."
    )

    prompt = f"""
    Сделай пост для Telegram на основе этой статьи:
    ЗАГОЛОВОК: {data['title']}
    ТЕКСТ: {data['content']}

    ПЛАН ПОСТА:
    1. 🔥 Яркий заголовок (привлечение внимания).
    2. 📝 Суть новости простыми словами (понятно даже новичку).
    3. 💎 Почему это ценно? (Материалы, дизайн, эксклюзивность).
    4. 💰 Инвестиционная привлекательность (будет ли расти цена, стоит ли брать в коллекцию).
    5. 🚀 Призыв к действию.
    """

    response = ollama.generate(model='hermes3:latest', system=system_instruction, prompt=prompt)
    return response['response']

# --- ГЛАВНЫЙ ЦИКЛ АГЕНТА ---
async def start_agent():
    print("🚀 Автономный агент запущен и готов к работе...")
    
    while True:
        current_url, current_title = await get_latest_article_url()
        last_url = get_last_processed_url()

        if current_url and current_url != last_url:
            print(f"🆕 Найдена новая статья: {current_title}")
            
            # 1. Парсим
            data = await scrape_article_data(current_url)
            
            # 2. Генерируем пост
            if data:
                post_text = generate_sales_post(data)
                
                print("\n" + "🌟" * 20)
                print("ГОТОВЫЙ ПРОДАЮЩИЙ ПОСТ:")
                print(post_text)
                print("🌟" * 20 + "\n")
                
                # 3. Запоминаем ссылку
                save_last_url(current_url)
                print("💾 Ссылка сохранена в память.")
        else:
            print("😴 Новых статей пока нет. Жду...")

        print(f"⏰ Следующая проверка через {CHECK_INTERVAL // 60} минут.")
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(start_agent())
    except KeyboardInterrupt:
        print("\n🛑 Агент остановлен пользователем.")