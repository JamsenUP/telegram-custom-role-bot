# Пошаговая инструкция: Бесплатный запуск бота 24/7 в облаке

Чтобы бот работал круглые сутки, даже когда ваш компьютер выключен, его можно разместить на одном из бесплатных облачных сервисов.

---

## 🏆 Вариант 1: Koyeb (Рекомендуется — 100% бесплатно 24/7)

**Koyeb** предоставляет постоянный бесплатный инстанс (Free Nano), который **не засыпает** и работает 24/7.

### Инструкция:
1. Загрузите код бота в свой **GitHub** репозиторий:
   - Зайдите на [github.com](https://github.com/) и создайте новый приватный или публичный репозиторий.
   - Загрузите все файлы из папки `custom_role_telegram_bot` (кроме файла `.env` с личными ключами!).
2. Зарегистрируйтесь на [koyeb.com](https://www.koyeb.com/) (можно войти через GitHub).
3. Нажмите **"Create App"** / **"Create Service"**.
4. Выберите **GitHub** в качестве источника и укажите ваш репозиторий.
5. В разделе **"Environment Variables"** (Переменные окружения) добавьте:
   - `TELEGRAM_BOT_TOKEN` = `ваш_токен`
   - `OPENAI_API_KEY` = `ваш_ключ`
   - `OPENAI_BASE_URL` = `(если нужен сторонний провайдер)`
   - `LLM_MODEL` = `(например, gpt-4o-mini)`
6. Нажмите **"Deploy"**.
7. Бот соберется и начнет работать 24/7.

---

## 🥈 Вариант 2: Render.com (Бесплатный Web Service)

**Render** — очень популярный бесплатный сервис.

### Инструкция:
1. Загрузите код в репозиторий на [github.com](https://github.com/).
2. Зарегистрируйтесь на [render.com](https://render.com/).
3. Нажмите **"New +"** -> **"Web Service"** и подключите ваш репозиторий.
4. Укажите:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
5. В разделе **"Environment Variables"** укажите ваши ключи (`TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `LLM_MODEL`).
6. Нажмите **"Create Web Service"**.
7. *Чтобы Render не усыплял бесплатный сервис после 15 минут неактивности:*
   - Скопируйте URL созданного веб-сервиса (например, `https://my-bot.onrender.com`).
   - Зайдите на бесплатный сервис [cron-job.org](https://cron-job.org/) или [uptimerobot.com](https://uptimerobot.com/) и настройте пинг этого адреса каждые 10 минут.

---

## 🥉 Вариант 3: Hugging Face Spaces (Docker)

1. Зайдите на [huggingface.co/spaces](https://huggingface.co/spaces).
2. Нажмите **"Create new Space"**.
3. Выберите **Space SDK: Docker** (Blank).
4. Загрузите все файлы проекта в Space.
5. В настройках Space (Settings -> Variables and secrets) добавьте ваши секретные переменные (`TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`).
6. Бот запустится в изолированном контейнере 24/7.
