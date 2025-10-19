# China IT News Telegram Bot 🇨🇳

Автоматический Telegram-бот для публикации новостей IT и вакансий в Китае с использованием AI-генерации контента.

## 🚀 Возможности

- **Автоматический сбор новостей** из RSS-лент китайских IT-источников
- **AI-генерация контента** с поддержкой Gemini, DeepSeek и OpenAI
- **Ежедневная публикация** дайджестов новостей
- **Интерактивное добавление вакансий** через Telegram-бота
- **Умное форматирование** и улучшение текстов с помощью AI
- **Дедупликация** новостей для избежания повторов

## 📋 Требования

- Python 3.8+
- Telegram Bot Token
- API ключ для одного из LLM провайдеров (Gemini/DeepSeek/OpenAI)
- Telegram канал с правами администратора для бота

## 🛠️ Установка

1. **Клонируйте проект:**
```bash
git clone <repository-url>
cd China-Telegram-Bot
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Настройте окружение:**
```bash
cp .env.example .env
```

4. **Заполните .env файл:**
```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@your_channel_username

# LLM Provider (gemini, deepseek, openai)
LLM_PROVIDER=gemini

# API Keys (заполните для выбранного провайдера)
GEMINI_API_KEY=your_gemini_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

## 🔧 Настройка Telegram

1. **Создайте бота:**
   - Напишите @BotFather в Telegram
   - Используйте `/newbot` и следуйте инструкциям
   - Сохраните полученный токен

2. **Создайте канал:**
   - Создайте публичный канал
   - Добавьте бота как администратора с правами публикации

3. **Получите ID канала:**
   - Для публичных каналов: `@channel_username`
   - Для приватных: используйте числовой ID

## 🚀 Запуск

```bash
python bot.py
```

## 🐳 Деплой через Docker и GitHub Actions

1. Подготовьте секреты в репозитории GitHub (Settings → Secrets and variables → Actions):
   - `DEPLOY_HOST` — адрес сервера
   - `DEPLOY_USER` — пользователь для SSH
   - `DEPLOY_SSH_KEY` — приватный ключ (PEM) для SSH
   - `DEPLOY_TARGET_DIR` — каталог на сервере (например, `/opt/china-bot`)
   - `GHCR_PAT` — токен с правами `read:packages` для GHCR

2. На сервере установите Docker (включая Docker Compose plugin) и создайте `.env` в `${DEPLOY_TARGET_DIR}` со значениями:

```env
BOT_TOKEN=... 
CHANNEL_ID=... 
LLM_PROVIDER=openai
OPENAI_API_KEY=...
# При необходимости другие ключи и флаги
TIMEZONE=Asia/Shanghai
AI_POLISH_ENABLE_VACANCY=true
AI_POLISH_ENABLE_AD=true
```

3. Пушите в ветку `main`. GitHub Actions:
   - соберёт образ из `Dockerfile`
   - запушит в `ghcr.io/<owner>/<repo>:latest`
   - подключится по SSH к серверу, создаст `docker-compose.yml` (если нет), выполнит `docker pull` и `docker compose up -d`.

Локальная сборка:
```bash
docker build -t china-telegram-bot:local .
docker run --rm -e BOT_TOKEN=... -e CHANNEL_ID=@... china-telegram-bot:local
```

## 📊 Источники новостей

Бот автоматически собирает новости из:
- **TechNode** - Китайские технологические новости
- **36Kr Global** - Стартапы и инвестиции
- **Pandaily** - IT и бизнес новости
- **SCMP Tech** - South China Morning Post Technology
- **The China Project Tech** - Технологические тренды

## 🤖 LLM Провайдеры

### Gemini (рекомендуется)
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-1.5-flash
```

### DeepSeek
```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key
DEEPSEEK_MODEL=deepseek-chat
```

### OpenAI
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
```

## 📱 Команды бота

- `/start` - Начать работу с ботом
- `/help` - Справка по командам
- `/post_vacancy` - Добавить новую вакансию
- `/status` - Проверить статус системы
- `/post_now` - Принудительно опубликовать новости (только админы)

## 📝 Добавление вакансий

1. Используйте команду `/post_vacancy`
2. Заполните 9 полей по очереди:
   - Позиция
   - Компания
   - Локация
   - Зарплата
   - Опыт
   - Описание
   - Требования
   - Условия
   - Контакт
3. Выберите улучшение с AI или оставьте как есть
4. Подтвердите публикацию

## ⏰ Расписание

- **Сбор новостей:** каждый час
- **Публикация дайджеста:** ежедневно в 10:00 МСК
- **Максимум статей:** 5 в день

## 🗂️ Структура проекта

```
China-Telegram-Bot/
├── bot.py              # Основной файл бота
├── config.py           # Конфигурация
├── rss_collector.py    # Сбор RSS новостей
├── generator.py        # Генерация контента
├── publisher.py        # Публикация в Telegram
├── rss_sources.py      # Источники RSS
├── llm/
│   ├── __init__.py
│   └── client.py       # LLM клиент
├── data/               # Данные (создается автоматически)
├── requirements.txt    # Зависимости
├── .env.example       # Пример конфигурации
└── README.md          # Документация
```

## 🔍 Тестирование

Тестирование отдельных компонентов:

```bash
# Тест RSS сборщика
python rss_collector.py

# Тест LLM клиента
python llm/client.py

# Тест генератора контента
python generator.py

# Тест публикации
python publisher.py
```

## 🛡️ Безопасность

- Никогда не коммитьте `.env` файл
- Используйте переменные окружения для секретов
- Регулярно обновляйте API ключи
- Ограничьте доступ к админским командам

## 🚨 Устранение неполадок

### Бот не запускается
- Проверьте BOT_TOKEN в .env
- Убедитесь, что все зависимости установлены

### Не публикуются сообщения
- Проверьте CHANNEL_ID
- Убедитесь, что бот добавлен как админ канала
- Проверьте права бота на публикацию

### Ошибки LLM
- Проверьте API ключ для выбранного провайдера
- Убедитесь в наличии интернет-соединения
- Проверьте лимиты API

### Нет новостей
- Проверьте доступность RSS источников
- Убедитесь в корректности URL в rss_sources.py

## 📈 Будущие улучшения

- [ ] Веб-интерфейс для управления
- [ ] Аналитика и статистика
- [ ] Поддержка изображений
- [ ] Интеграция с базой данных
- [ ] Мультиязычность
- [ ] A/B тестирование заголовков
- [ ] Фильтрация по ключевым словам

## 📄 Лицензия

MIT License

## 🤝 Поддержка

Для вопросов и предложений создавайте Issues в репозитории.

---

**Создано с ❤️ для IT-сообщества в Китае**