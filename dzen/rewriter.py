"""
Content rewriter using OpenAI (ChatGPT API).

This is the current LLM used for generating Dzen-style articles.
"""

from openai import OpenAI
from dzen.config import config


def get_client() -> OpenAI:
    """Create OpenAI client."""
    return OpenAI(
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
    )


def rewrite_for_dzen(title: str, raw_content: str) -> str:
    """
    Generate a high-quality, expert-style article for Dzen using OpenAI.
    """
    client = get_client()

    system_prompt = (
        "Ты — опытный автор и эксперт в сникер-культуре, уличной моде и lifestyle-тематике. "
        "Твоя задача — написать качественную, интересную и экспертную статью для канала в Яндекс Дзене. "
        "Стиль: спокойный, информативный, экспертный. Избегай хайпа, слов «дроп», «маст-хэв», «огонь», «легендарный», «база», «архив» и подобного. "
        "Пиши грамотным литературным русским языком. Названия брендов и моделей выделяй жирным. "
        "Статья должна быть полезной, с хорошей структурой и контекстом."
    )

    user_prompt = f"""Оригинальный заголовок: {title}

Оригинальный текст:
{raw_content}

Напиши на основе этого материала хорошую статью для Дзена.
Сделай текст более структурированным, добавь полезный контекст и экспертные наблюдения.
Объём — 900–1800 символов. Пиши на русском языке."""

    try:
        response = client.chat.completions.create(
            model=config.llm.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[Rewriter] Ошибка при вызове OpenAI: {e}")
        return f"[Ошибка генерации текста]\n\n{raw_content[:1200]}"


# Quick test
if __name__ == "__main__":
    print("Testing OpenAI rewriting for Dzen (model: gpt-4o-mini)...\n")

    test_title = "Nike Air Max 1 '87 'Sail' возвращается в новой цветовой гамме"
    test_content = """The Nike Air Max 1 '87 returns in a clean Sail colorway with premium leather upper and a gum rubber outsole. 
    This version features subtle tonal details and a comfortable fit."""

    result = rewrite_for_dzen(test_title, test_content)
    print("=== Результат генерации для Дзена ===\n")
    print(result)