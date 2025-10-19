"""Unified LLM client supporting multiple providers."""

import asyncio
from typing import List, Dict, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Import LLM libraries
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import openai
except ImportError:
    openai = None

try:
    import httpx
except ImportError:
    httpx = None
from typing import Optional, Dict

class LLMClient:
    def __init__(self):
        self.provider = config.LLM_PROVIDER.lower()
        self.setup_client()

    def setup_client(self):
        """Initialize the appropriate LLM client based on provider."""
        if self.provider == "gemini":
            if not genai or not config.GEMINI_API_KEY:
                raise ValueError("Gemini configuration missing")
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(config.GEMINI_MODEL)
            
        elif self.provider == "openai":
            if not openai or not config.OPENAI_API_KEY:
                raise ValueError("OpenAI configuration missing")
            self.client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            
        elif self.provider == "deepseek":
            if not httpx or not config.DEEPSEEK_API_KEY:
                raise ValueError("DeepSeek configuration missing")
            # DeepSeek uses OpenAI-compatible API
            self.client = openai.AsyncOpenAI(
                api_key=config.DEEPSEEK_API_KEY,
                base_url=config.DEEPSEEK_BASE_URL
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def generate_news_digest(self, articles: List[Dict]) -> str:
        """Generate a news digest from collected articles."""
        if not articles:
            return "Сегодня новых статей не найдено."

        # Prepare articles summary for prompt
        articles_text = ""
        for i, article in enumerate(articles[:5], 1):  # Limit to 5 articles
            articles_text += f"{i}. {article['title']}\n"
            articles_text += f"   Источник: {article['source']}\n"
            if article.get('description'):
                articles_text += f"   Описание: {article['description'][:200]}...\n"
            articles_text += f"   Ссылка: {article['link']}\n\n"

        prompt = f"""Создай краткий дайджест новостей о технологиях и IT в Китае на русском языке.

Исходные статьи:
{articles_text}

Требования к дайджесту:
- Объем: 150-200 слов
- Язык: русский
- Стиль: информативный, профессиональный
- Структура: краткое введение + основные тренды/новости + заключение
- Включи 2-3 самые важные новости
- Добавь релевантные хештеги в конце (#КитайТех #IT #Технологии)
- НЕ включай прямые ссылки в текст

Дайджест:"""

        try:
            return await self._generate_text(prompt)
        except Exception as e:
            print(f"❌ Error generating news digest: {e}")
            return self._fallback_news_digest(articles)

    async def polish_vacancy(self, description: str) -> str:
        """Polish the vacancy description to be more professional and attractive."""
        prompt = f"""Преобразуй описание вакансии в профессиональный и привлекательный текст на русском языке.

Исходный текст:
{description}

Требования:
- Ясная структура: роль, задачи, требования, условия, контакт
- Тон: деловой, дружелюбный, без клише
- Объем: 120-180 слов
- Без эмодзи и хештегов

Выведи только финальный текст вакансии:"""
        try:
            return await self._generate_text(prompt)
        except Exception as e:
            print(f"❌ Error polishing vacancy: {e}")
            return description

    async def polish_ad(self, ad_data: Dict) -> str:
        """Polish advertisement data into a persuasive, well-structured post (RU).
        ad_data keys: title, brand, description, offer, link, contact
        """
        title = (ad_data.get("title") or ad_data.get("ad_title") or "").strip()
        brand = (ad_data.get("brand") or ad_data.get("ad_brand") or "").strip()
        description = (ad_data.get("description") or ad_data.get("ad_description") or "").strip()
        offer = (ad_data.get("offer") or ad_data.get("ad_offer") or "").strip()
        link = (ad_data.get("link") or ad_data.get("ad_link") or "").strip()
        contact = (ad_data.get("contact") or ad_data.get("ad_contact") or "").strip()
        prompt = f"""Сформируй убедительный рекламный пост на русском языке.

Исходные данные:
Заголовок: {title}
Бренд: {brand}
Описание: {description}
Оффер: {offer}
Ссылка: {link}
Контакт: {contact}

Требования к тексту:
- Короткий цепляющий лид, далее 2–3 абзаца
- Ясная структура: что это, выгоды/оффер, призыв к действию
- Тон: дружелюбный, профессиональный, без чрезмерных клише
- Объем: 90–140 слов
- Без эмодзи и хештегов

Выведи только финальный текст поста:"""
        try:
            return await self._generate_text(prompt)
        except Exception as e:
            print(f"❌ Error polishing ad: {e}")
            # Fallback: compose a minimal ad text
            parts = []
            if title:
                parts.append(f"{title}.")
            if brand:
                parts.append(f"Бренд: {brand}.")
            if description:
                parts.append(description)
            if offer:
                parts.append(f"Предложение: {offer}.")
            if link:
                parts.append(f"Ссылка: {link}")
            if contact:
                parts.append(f"Контакт: {contact}")
            return " " .join(parts).strip()

    async def normalize_vacancy_freeform(self, raw_text: str) -> str:
        """Normalize a free-form vacancy text into a unified template.
        Extract fields (позиция, компания, локация, зарплата, опыт, описание/задачи,
        требования, условия, контакт) and append a detected URL as a link line.
        Output must follow the same labeled format used in generator manual fallback.
        """
        prompt = f"""Ты структурируешь вакансии из свободного текста.

Исходный текст вакансии:
{raw_text}

Задача:
- Извлеки ключевые поля: Позиция, Компания, Локация, Зарплата, Опыт, Описание/задачи, Требования, Условия, Контакт
- Найди URL (http/https) в тексте и добавь в конце строку: "🔗 Ссылка: <url>"
- Если URL не найден, НЕ добавляй строку "Ссылка"
- Пиши по-русски, деловой тон, без воды и клише
- Формат вывода ДОЛЖЕН строго соответствовать меткам:
  🧑‍💻 Позиция: ...
  🏢 Компания: ...
  📍 Локация: ...
  💰 Зарплата: ...
  🧪 Опыт: ...
  📝 Описание: ...
  ✅ Требования: ...
  🎁 Условия: ...
  📬 Контакт: ...
  🔗 Ссылка: ...   (только если нашёл URL)
- Опускай пустые разделы, если данных нет
- Не добавляй никаких других комментариев или заголовков

Выведи только финальный структурированный текст в указанном формате."""
        try:
            return await self._generate_text(prompt)
        except Exception as e:
            print(f"❌ Error normalizing free-form vacancy: {e}")
            # Fallback: try to extract a URL and return raw text + link line
            import re
            m = re.search(r'https?://\S+', raw_text)
            link_line = f"\n🔗 Ссылка: {m.group(0)}" if m else ""
            return raw_text.strip() + link_line

    async def generate_article_summary(self, article: Dict, max_chars: Optional[int] = None) -> str:
        """Generate a Russian post for a single article with optional character limit.
        When max_chars is set, the model is asked to produce a cohesive text
        up to that character count and end on a complete sentence.
        """
        title = article.get('title', '')
        source = article.get('source', '')
        description = article.get('description', '')
        base_text = f"Заголовок: {title}\nИсточник: {source}\nОписание: {description[:800]}"
        length_req = "Объем: 10–15 предложений" if not max_chars else (
            f"Объем: до {max_chars} символов (не превышай лимит)."
        )
        end_req = "Заверши на полном предложении, без обрыва."
        prompt = f"""Переведи и переформулируй новость на русский язык, сделай развернутый пост.

Исходные данные:
{base_text}

Требования к тексту:
- Язык: русский (если исходные данные на английском — переведи)
- {length_req}
- Стиль: информативный, нейтральный, без клише и воды
- Сохраняй факты, цифры, названия компаний, дат и продуктов
- Дай краткий контекст и объясни значимость для китайского IT-рынка
- Без прямых ссылок, без хештегов, без эмодзи
- НЕ добавляй заголовки разделов
- {end_req}

Выведи только сам текст поста (без префиксов и комментариев)."""
        try:
            # Rough token estimate: 1 token ≈ 3.5 chars (for OpenAI). Add margin.
            max_tokens = None
            if max_chars and self.provider in ["openai", "deepseek"]:
                est = int(max_chars / 3.5) + 40
                max_tokens = max(200, min(est, 1200))
            return await self._generate_text(prompt, max_tokens=max_tokens)
        except Exception as e:
            print(f"❌ Error generating article summary: {e}")
            # Fallback: sentence-aware trim of description or title
            def trim_sentencewise(txt: str, limit: int) -> str:
                import re
                txt = (txt or '').strip()
                if not txt:
                    return ''
                if not limit:
                    return txt
                parts = re.split(r'(?<=[.!?…])\s+', txt)
                out = ''
                for p in parts:
                    if len(out) + len(p) + 1 <= limit:
                        out = (out + ' ' + p).strip()
                    else:
                        break
                return out or txt[:limit]
            if description:
                return trim_sentencewise(description.strip(), max_chars or 1200)
            return trim_sentencewise(title, max_chars or 400)

    async def _generate_text(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate text using the configured LLM provider."""
        if self.provider == "gemini":
            response = await self._generate_gemini(prompt)
        elif self.provider in ["openai", "deepseek"]:
            response = await self._generate_openai_compatible(prompt, max_tokens=max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        return response.strip()

    async def _generate_openai_compatible(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Use OpenAI-compatible chat completions (OpenAI/DeepSeek)."""
        try:
            result = await self.client.chat.completions.create(
                model=(config.OPENAI_MODEL if self.provider == "openai" else config.DEEPSEEK_MODEL),
                messages=[
                    {"role": "system", "content": "Ты помощник, который пишет информативные русскоязычные тексты без ссылок и эмодзи."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=(max_tokens or 1200)
            )
            return result.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI-compatible error: {e}")

    def _fallback_news_digest(self, articles: List[Dict]) -> str:
        """Fallback news digest when LLM fails."""
        if not articles:
            return "📰 Сегодня новых статей не найдено."
        
        digest = "📰 **Дайджест новостей IT в Китае**\n\n"
        
        for i, article in enumerate(articles[:3], 1):
            digest += f"{i}. **{article['title']}**\n"
            digest += f"   🔗 [{article['source']}]({article['link']})\n\n"
        
        digest += "#КитайТех #IT #Технологии"
        return digest

# Global LLM client instance
_llm_client = None

def get_llm_client() -> LLMClient:
    """Get or create LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

async def test_llm():
    """Test LLM client functionality."""
    client = get_llm_client()
    
    # Test news generation
    test_articles = [
        {
            "title": "Chinese AI startup raises $100M",
            "source": "TechNode",
            "description": "A new AI company in Beijing secured major funding",
            "link": "https://example.com/1"
        }
    ]
    
    print("Testing news digest generation...")
    digest = await client.generate_news_digest(test_articles)
    print(f"Generated digest:\n{digest}")
    
    # Test vacancy polishing
    test_vacancy = "Ищем Python разработчика в Шанхай. Зарплата хорошая. Опыт 3+ года."
    print("\nTesting vacancy polishing...")
    polished = await client.polish_vacancy(test_vacancy)
    print(f"Polished vacancy:\n{polished}")

if __name__ == "__main__":
    asyncio.run(test_llm())