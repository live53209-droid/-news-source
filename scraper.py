import asyncio
from playwright.async_api import async_playwright

async def scrape_hypebeast_full_article(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Можно поставить False, чтобы поглазеть
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"Парсим полную статью: {url}")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 1. Забираем заголовок
            title = await page.inner_text("h1")
            
            # 2. Забираем все параграфы текста. 
            # На Hypebeast основной текст обычно лежит в селекторе .post-body-content или просто в p
            # Мы возьмем все p, которые находятся внутри основного тега статьи
            paragraphs = await page.locator(".post-body-content p, article p").all_inner_texts()
            
            # Склеиваем параграфы в один текст
            full_text = "\n\n".join(paragraphs)
            
            print(f"Успех! Получено {len(full_text)} символов текста.")
            return {
                "title": title.strip(),
                "content": full_text.strip()
            }

        except Exception as e:
            print(f"Ошибка: {e}")
            return None
        finally:
            await browser.close()

# Тестируем
test_url = "https://hypebeast.com/2026/4/nike-air-lab-dropcity-milan-design-week-2026-opening-information"
if __name__ == "__main__":
    data = asyncio.run(scrape_hypebeast_full_article(test_url))
    if data:
        print("\n--- ПЕРВЫЕ 200 СИМВОЛОВ ТЕКСТА ---")
        print(data['content'][:200] + "...")