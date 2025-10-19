"""Telegram channel publisher for sending formatted messages."""

import asyncio
import logging
from typing import Optional, Dict
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
import config
from aiogram.types import InputMediaPhoto
from aiogram.enums import ParseMode
from generator import generate_article_post

class TelegramPublisher:
    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
        self.channel_id = config.CHANNEL_ID
        
    def _chunk_text(self, text: str, max_len: int = 3900) -> list:
        """Split text into chunks safe for Telegram messages."""
        chunks = []
        current = 0
        n = len(text)
        while current < n:
            end = min(current + max_len, n)
            chunks.append(text[current:end])
            current = end
        return chunks

    async def publish_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Publish a message to the Telegram channel.
        
        Args:
            message: The message text to publish
            parse_mode: Parse mode for formatting (Markdown or HTML)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure message is not too long (Telegram limit is 4096 characters)
            if len(message) > 4000:
                message = message[:3900] + "\n\n... (сообщение обрезано)"
            
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=False
            )
            
            print(f"✅ Message published to {self.channel_id}")
            return True
            
        except TelegramAPIError as e:
            print(f"❌ Telegram API error: {e}")
            
            # Try with HTML parse mode if Markdown failed
            if parse_mode == "Markdown":
                print("🔄 Retrying with HTML parse mode...")
                return await self.publish_message(
                    self._convert_markdown_to_html(message), 
                    "HTML"
                )
            
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error publishing message: {e}")
            return False

    async def publish_news_digest(self, news_content: str) -> bool:
        """Publish a news digest to the channel."""
        print("📰 Publishing news digest...")
        return await self.publish_message(news_content)

    async def publish_vacancy(self, vacancy_content: str) -> bool:
        """Publish a vacancy to the channel."""
        print("💼 Publishing vacancy...")
        return await self.publish_message(vacancy_content)

    async def publish_article(self, article: Dict) -> bool:
        """Publish a single article as photo with Russian caption, no links.
        - Enforce Telegram photo caption limit (1024) by truncating.
        - Keep exactly one message per article/hour.
        """
        try:
            post = await generate_article_post(article)
            caption = (post['text'] or '').strip()
            image_url = post.get('image_url')
            CAPTION_LIMIT = 1024
            SHORT_CAPTION_LEN = 1000  # leave space for ellipsis
            if image_url:
                try:
                    if len(caption) <= CAPTION_LIMIT:
                        await self.bot.send_photo(
                            chat_id=self.channel_id,
                            photo=image_url,
                            caption=caption,
                            parse_mode=ParseMode.HTML
                        )
                        return True
                    else:
                        short_caption = caption[:SHORT_CAPTION_LEN] + "…"
                        await self.bot.send_photo(
                            chat_id=self.channel_id,
                            photo=image_url,
                            caption=short_caption,
                            parse_mode=ParseMode.HTML
                        )
                        return True
                except TelegramAPIError as e:
                    print(f"⚠️ Photo upload failed, falling back to text: {e}")
                    # Fallback to text message (single, truncated)
                    text_msg = caption if len(caption) <= 4000 else caption[:3900] + "\n\n…"
                    await self.bot.send_message(chat_id=self.channel_id, text=text_msg, parse_mode=ParseMode.HTML)
                    return True
                except Exception as e:
                    print(f"⚠️ Unexpected photo error, sending text instead: {e}")
                    text_msg = caption if len(caption) <= 4000 else caption[:3900] + "\n\n…"
                    await self.bot.send_message(chat_id=self.channel_id, text=text_msg, parse_mode=ParseMode.HTML)
                    return True
            else:
                # No image: post as a single text message (truncated)
                text_msg = caption if len(caption) <= 4000 else caption[:3900] + "\n\n…"
                await self.bot.send_message(chat_id=self.channel_id, text=text_msg, parse_mode=ParseMode.HTML)
                return True
        except Exception as e:
            print(f"❌ Publish article failed: {e}")
            return False

    async def publish_error_message(self, error_message: str) -> bool:
        """Publish an error message to the channel (for admin notifications)."""
        print("⚠️ Publishing error message...")
        admin_message = f"🔧 **Уведомление администратора**\n\n{error_message}"
        return await self.publish_message(admin_message)

    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """Convert basic Markdown formatting to HTML for Telegram."""
        # Simple conversion for common formatting
        html_text = markdown_text
        
        # Convert **bold** to <b>bold</b>
        import re
        html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_text)
        
        # Convert *italic* to <i>italic</i>
        html_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html_text)
        
        # Convert [text](url) to <a href="url">text</a>
        html_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html_text)
        
        return html_text

    async def test_connection(self) -> bool:
        """Test connection to Telegram and channel access."""
        try:
            # Get bot info
            bot_info = await self.bot.get_me()
            print(f"✅ Bot connected: @{bot_info.username}")
            
            # Try to get chat info (this will fail if bot is not admin)
            try:
                chat_info = await self.bot.get_chat(self.channel_id)
                print(f"✅ Channel access confirmed: {chat_info.title}")
                return True
            except TelegramAPIError as e:
                if "not found" in str(e).lower():
                    print(f"❌ Channel {self.channel_id} not found or bot is not a member")
                else:
                    print(f"❌ Channel access error: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Bot connection failed: {e}")
            return False

    async def close(self):
        """Close the bot session."""
        await self.bot.session.close()

# Global publisher instance
_publisher = None

def get_publisher() -> TelegramPublisher:
    """Get or create publisher instance."""
    global _publisher
    if _publisher is None:
        _publisher = TelegramPublisher()
    return _publisher

async def test_publisher():
    """Test publisher functionality."""
    publisher = get_publisher()
    
    # Test connection
    print("Testing Telegram connection...")
    connection_ok = await publisher.test_connection()
    
    if connection_ok:
        # Test message publishing
        test_message = """🧪 **Тестовое сообщение**

Это тестовое сообщение от бота China IT News.

✅ Форматирование работает
🔗 [Ссылки работают](https://example.com)
📅 Дата: сегодня

#Тест #БотРаботает"""
        
        print("Testing message publishing...")
        success = await publisher.publish_message(test_message)
        
        if success:
            print("✅ Test message published successfully!")
        else:
            print("❌ Failed to publish test message")
    
    await publisher.close()

if __name__ == "__main__":
    asyncio.run(test_publisher())


def _chunk_text(text: str, max_len: int = 4000) -> list[str]:
    """Split text into chunks up to max_len, preferably on sentence boundaries."""
    import re
    text = text.strip()
    if len(text) <= max_len:
        return [text]
    # Split by sentences and accumulate
    sentences = re.split(r'(?<=[.!?…])\s+', text)
    chunks, current = [], ''
    for s in sentences:
        if len(s) > max_len:
            # Hard split long sentence by words
            words = s.split()
            buf = ''
            for w in words:
                if len(buf) + len(w) + 1 <= max_len:
                    buf = (buf + ' ' + w).strip()
                else:
                    chunks.append(buf)
                    buf = w
            if buf:
                if len(current) + len(buf) + 1 <= max_len:
                    current = (current + ' ' + buf).strip()
                else:
                    chunks.append(current)
                    current = buf
            continue
        if len(current) + len(s) + 1 <= max_len:
            current = (current + ' ' + s).strip()
        else:
            chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks

async def publish_message(context, chat_id: int, text: str, parse_mode: str = "Markdown"):
    """Publish a text message (with safe length checks)."""
    # Telegram text limit is ~4096, keep some margin
    chunks = _chunk_text(text, max_len=3800)
    for idx, chunk in enumerate(chunks):
        try:
            await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode=parse_mode)
        except Exception as e:
            print(f"Failed to send message chunk {idx+1}/{len(chunks)}: {e}")
            # Try sending without parse mode
            try:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
            except Exception as e2:
                print(f"Fallback send_message failed: {e2}")

async def publish_article(context, chat_id: int, article: dict) -> bool:
    """Publish single article with strict character limit: photo caption or text only."""
    from generator import generate_article_post
    try:
        post = await generate_article_post(article)
        full_text = (post.get('text') or '').strip()
        photo_caption = (post.get('photo_caption') or '').strip()
        image_url = post.get('image_url')

        IDEAL_LIMIT = getattr(config, 'IDEAL_POST_CHAR_LIMIT', 700)

        def truncate(s: str, limit: int) -> str:
            if not s:
                return ''
            if len(s) <= limit:
                return s
            s = s[:limit]
            # avoid cutting in the middle of a word
            s = s.rsplit(' ', 1)[0].rstrip()
            return s + '…'

        if image_url:
            # Use text as caption source, limited by min(ideal, caption limit)
            cap_limit = min(IDEAL_LIMIT, CAPTION_LIMIT)
            caption_source = full_text or photo_caption
            caption = truncate(caption_source, cap_limit)
            try:
                await context.bot.send_photo(chat_id=chat_id, photo=image_url, caption=caption, parse_mode="HTML")
                return True
            except Exception as e:
                print(f"Photo send failed, fallback to text: {e}")
                # Fallback: send truncated text only
                text_to_send = truncate(full_text or photo_caption, IDEAL_LIMIT)
                if text_to_send:
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=text_to_send, parse_mode="HTML")
                        return True
                    except Exception as e2:
                        print(f"Fallback send_message failed: {e2}")
                        return False
                return False
        else:
            # No image: send truncated text only
            text_to_send = truncate(full_text or photo_caption, IDEAL_LIMIT)
            if text_to_send:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=text_to_send, parse_mode="HTML")
                    return True
                except Exception as e:
                    print(f"send_message failed: {e}")
                    return False
            return False
    except Exception as e:
        print(f"publish_article error: {e}")
        return False