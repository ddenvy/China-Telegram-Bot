import asyncio
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from publisher import get_publisher

async def main():
    pub = get_publisher()
    dummy_article = {
        "title": "Baidu представила новую платформу для разработчиков AI",
        "source": "SCMP Tech",
        "description": "Компания Baidu анонсировала инструменты для создания и развертывания моделей ИИ, нацеленные на ускорение разработки в экосистеме Китая.",
        # Use a reliable JPEG for Telegram fetching
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Baidu_Building_2006.jpg/640px-Baidu_Building_2006.jpg",
        "link": "https://example.com/baidu-ai-platform"
    }
    ok = await pub.publish_article(dummy_article)
    await pub.close()
    print(f"Publish dummy article: {'success' if ok else 'failed'}")

if __name__ == "__main__":
    asyncio.run(main())