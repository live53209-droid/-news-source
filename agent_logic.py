import ollama

def generate_sneaker_post(article_title):
    print("Отправляю заголовок в Hermes для генерации поста...")
    
    # Твоя экспертная инструкция (System Prompt)
    system_instruction = (
        "Ты — ведущий эксперт по кроссовкам и стритвиру. "
        "Твоя задача: написать хайповый, но информативный пост для Telegram-канала на основе заголовка статьи. "
        "Используй эмодзи, добавь призыв к действию и пиши на русском языке."
    )
    
    user_prompt = f"Заголовок статьи: {article_title}"

    response = ollama.generate(
        model='hermes2pro-llama3',
        system=system_instruction,
        prompt=user_prompt
    )
    
    return response['response']

# Пример интеграции:
title_from_scraper = "The Nike Air Lab Is an Interactive Museum With 100+ Prototypes"
final_post = generate_sneaker_post(title_from_scraper)

print("\n--- ГОТОВЫЙ ПОСТ ОТ HERMES ---")
print(final_post)