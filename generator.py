"""Content generators for news and vacancy posts."""

from typing import List, Dict, Optional
from datetime import datetime
from llm import get_llm_client

class ContentGenerator:
    def __init__(self):
        self.llm_client = get_llm_client()

    async def generate_news_post(self, articles: List[Dict]) -> str:
        """Generate a formatted news post from RSS articles."""
        if not articles:
            return "📰 Сегодня новых статей не найдено."

        try:
            # Generate AI digest
            ai_digest = await self.llm_client.generate_news_digest(articles)
            
            # Add header and footer
            post = f"🇨🇳 **Дайджест IT-новостей из Китая**\n"
            post += f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
            post += ai_digest
            
            # Add source links if digest doesn't include them
            if not any(article['link'] in ai_digest for article in articles):
                post += "\n\n📖 **Источники:**\n"
                for i, article in enumerate(articles[:3], 1):
                    post += f"{i}. [{article['source']}]({article['link']})\n"
            
            return post
            
        except Exception as e:
            print(f"❌ Error generating AI news post: {e}")
            return self._generate_fallback_news_post(articles)

    def _generate_fallback_news_post(self, articles: List[Dict]) -> str:
        """Generate a simple news post without AI when LLM fails."""
        post = f"🇨🇳 **IT-новости из Китая**\n"
        post += f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
        
        for i, article in enumerate(articles[:3], 1):
            post += f"{i}. **{article['title']}**\n"
            post += f"   📰 {article['source']}\n"
            if article.get('description'):
                # Truncate description
                desc = article['description'][:150]
                if len(article['description']) > 150:
                    desc += "..."
                post += f"   📝 {desc}\n"
            post += f"   🔗 [Читать полностью]({article['link']})\n\n"
        
        post += "#КитайТех #IT #Технологии #Новости"
        return post

    async def generate_vacancy_post(self, vacancy_data: Dict, use_ai_polish: bool = True) -> str:
        """Generate a formatted vacancy post."""
        try:
            if use_ai_polish and vacancy_data.get('description'):
                # Use AI to polish the vacancy
                polished_text = await self.llm_client.polish_vacancy(vacancy_data['description'])
                return polished_text
            else:
                # Generate manual format
                return self._generate_manual_vacancy_post(vacancy_data)
        except Exception as e:
            print(f"❌ Error generating AI vacancy post: {e}")
            return self._generate_manual_vacancy_post(vacancy_data)

    def _generate_manual_vacancy_post(self, vacancy_data: Dict) -> str:
        """Generate a manual vacancy format when AI is not used or fails."""
        parts = []
        if vacancy_data.get('position'):
            parts.append(f"🧑‍💻 Позиция: {vacancy_data['position']}")
        if vacancy_data.get('company'):
            parts.append(f"🏢 Компания: {vacancy_data['company']}")
        if vacancy_data.get('location'):
            parts.append(f"📍 Локация: {vacancy_data['location']}")
        if vacancy_data.get('salary'):
            parts.append(f"💰 Зарплата: {vacancy_data['salary']}")
        if vacancy_data.get('experience'):
            parts.append(f"🧪 Опыт: {vacancy_data['experience']}")
        if vacancy_data.get('description'):
            parts.append(f"📝 Описание: {vacancy_data['description']}")
        if vacancy_data.get('requirements'):
            parts.append(f"✅ Требования: {vacancy_data['requirements']}")
        if vacancy_data.get('benefits'):
            parts.append(f"🎁 Условия: {vacancy_data['benefits']}")
        if vacancy_data.get('contact'):
            parts.append(f"📬 Контакт: {vacancy_data['contact']}")
        return "\n".join(parts)

    async def generate_ad_post(self, ad_data: Dict, use_ai_polish: bool = True) -> str:
        """Generate a formatted advertisement post, optionally AI-polished."""
        try:
            if use_ai_polish:
                return await self.llm_client.polish_ad(ad_data)
            else:
                return self._generate_manual_ad_post(ad_data)
        except Exception as e:
            print(f"❌ Error generating AI ad post: {e}")
            return self._generate_manual_ad_post(ad_data)

    def _generate_manual_ad_post(self, ad_data: Dict) -> str:
        """Manual fallback formatting for ads (with emojis and clear sections)."""
        parts = ["📣 **Рекламный пост**\n"]
        title = ad_data.get('title') or ad_data.get('ad_title')
        brand = ad_data.get('brand') or ad_data.get('ad_brand')
        description = ad_data.get('description') or ad_data.get('ad_description')
        offer = ad_data.get('offer') or ad_data.get('ad_offer')
        link = ad_data.get('link') or ad_data.get('ad_link')
        contact = ad_data.get('contact') or ad_data.get('ad_contact')
        if title:
            parts.append(f"🔖 **Заголовок:** {title}")
        if brand:
            parts.append(f"🏷️ **Бренд:** {brand}")
        if description:
            parts.append(f"📝 **Описание:** {description}")
        if offer:
            parts.append(f"🎁 **Оффер:** {offer}")
        if link:
            parts.append(f"🔗 **Ссылка:** {link}")
        if contact:
            parts.append(f"📞 **Контакт:** {contact}")
        return "\n".join(parts)

    async def polish_vacancy_text(self, text: str) -> str:
        """Polish arbitrary vacancy text using LLM vacancy prompt."""
        try:
            return await self.llm_client.polish_vacancy(text)
        except Exception as e:
            print(f"❌ Error polishing freeform vacancy: {e}")
            return text

# Global generator instance
_generator = None

def get_generator() -> ContentGenerator:
    """Get or create content generator instance."""
    global _generator
    if _generator is None:
        _generator = ContentGenerator()
    return _generator

async def test_generator():
    """Test content generator functionality."""
    generator = get_generator()
    
    # Test news generation
    test_articles = [
        {
            "title": "Китайский стартуп привлек $100M инвестиций",
            "source": "TechNode",
            "description": "Новая AI-компания в Пекине получила крупное финансирование от венчурных фондов",
            "link": "https://example.com/1"
        },
        {
            "title": "Baidu запускает новую платформу для разработчиков",
            "source": "36Kr",
            "description": "Китайский поисковый гигант представил инструменты для AI-разработки",
            "link": "https://example.com/2"
        }
    ]
    
    print("Testing news post generation...")
    news_post = await generator.generate_news_post(test_articles)
    print(f"Generated news post:\n{news_post}\n")
    
    # Test vacancy generation
    test_vacancy = {
        "position": "Senior Python Developer",
        "company": "TechCorp China",
        "location": "Шанхай",
        "salary": "25,000-35,000 RMB",
        "experience": "3+ года",
        "description": "Разработка backend-систем для финтех проектов",
        "requirements": "Python, Django, PostgreSQL, опыт с микросервисами",
        "benefits": "Релокация, медстраховка, обучение китайскому языку",
        "contact": "@hr_techcorp"
    }
    
    print("Testing vacancy post generation...")
    vacancy_post = await generator.generate_vacancy_post(test_vacancy, use_ai_polish=False)
    print(f"Generated vacancy post:\n{vacancy_post}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_generator())


from typing import Dict
from llm.client import get_llm_client
import config

aSYNC = False
async def generate_article_post(article: Dict) -> Dict:
    """Return a per-article post payload:
    - full text (RU, logically complete) constrained by IDEAL_POST_CHAR_LIMIT
    - short photo caption derived from the text
    - image url if available
    """
    llm = get_llm_client()
    limit = getattr(config, 'IDEAL_POST_CHAR_LIMIT', 700)
    try:
        text = await llm.generate_article_summary(article, max_chars=limit)
    except Exception as e:
        # Fallback: compose a multi-sentence Russian text and trim sentence-wise to limit
        title = (article.get('title') or '').strip()
        source = (article.get('source') or '').strip()
        description = (article.get('description') or article.get('summary') or '').strip()
        import re
        base = []
        if title:
            base.append(f"Новость: {title}.")
        if description:
            raw = [s.strip() for s in re.split(r'(?<=[.!?…])\s+', description.replace("\n", " ")) if s.strip()]
            for s in raw[:10]:
                base.append(s)
        if source:
            base.append(f"Источник: {source}.")
        base.append("Тема важна для китайского IT-рынка; подробно в оригинале.")
        # Sentence-wise trim
        out, cur_len = '', 0
        for s in base:
            if cur_len + len(s) + 1 <= limit:
                out = (out + ' ' + s).strip()
                cur_len = len(out)
            else:
                break
        text = out or (description[:limit] if description else title[:limit])
    # Build a photo-friendly short caption from the first sentences
    def build_photo_caption(full: str, limit_cap: int = 300) -> str:
        import re
        parts = re.split(r'(?<=[.!?…])\s+', full)
        caption = ''
        for p in parts:
            if len(caption) + len(p) + 1 <= limit_cap:
                caption = (caption + ' ' + p).strip()
            else:
                break
        if not caption:
            caption = full[:limit_cap]
        if len(caption) > limit_cap:
            caption = caption[:limit_cap].rsplit(' ', 1)[0]
        if len(caption) < len(full):
            caption = caption.rstrip() + '…'
        return caption
    photo_caption = build_photo_caption(text)
    image_url = article.get('image_url') or article.get('image') or article.get('thumbnail')
    return {
        'text': text.strip(),
        'photo_caption': photo_caption.strip(),
        'image_url': image_url
    }


async def generate_vacancy_from_freeform(raw_text: str) -> str:
    """Normalize free-form vacancy text to a unified format using LLM.
    Returns final post text ready for publishing.
    """
    llm = get_llm_client()
    try:
        return await llm.normalize_vacancy_freeform(raw_text)
    except Exception as e:
        # Fallback handled inside llm method; but double-guard
        import re
        m = re.search(r'https?://\S+', raw_text)
        link_line = f"\n🔗 Ссылка: {m.group(0)}" if m else ""
        return raw_text.strip() + link_line