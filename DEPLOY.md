# Деплой бота на Railway / Render / Fly.io

Секреты (.env) в облако не заливаются — их вводишь в настройках сервиса после создания.

---

## Railway

1. Зайди на [railway.app](https://railway.app), залогинься.
2. **New Project** → **Deploy from GitHub repo**. Если репо нет — создай на GitHub, запушь папку проекта (без .venv и .env).
3. Выбери репозиторий с этим проектом. Корень репо должен содержать `bot.py`, `transcript.py`, `requirements.txt`, `Procfile`.
4. Railway сам подхватит Procfile. Нужен **Worker**, не Web: в настройках сервиса проверь, что запускается команда из Procfile (`worker: python bot.py`). Если создался "Web Service", в **Settings** → **Deploy** смени тип на Worker или добавь процесс Worker.
5. **Variables**: добавь переменные:
   - `TELEGRAM_BOT_TOKEN` = твой токен бота
   - `OPENAI_API_KEY` = твой ключ OpenAI
6. **Deploy** (или деплой запустится сам после пуша). В логах должно быть `Application started`.

---

## Render

1. Зайди на [render.com](https://render.com), залогинься.
2. **New** → **Background Worker**.
3. Подключи GitHub-репозиторий с проектом (корень — там, где `bot.py`, `requirements.txt`).
4. Настройки:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. **Environment** → **Add Environment Variable**:
   - `TELEGRAM_BOT_TOKEN` = токен
   - `OPENAI_API_KEY` = ключ OpenAI
6. **Create Background Worker**. Дождись деплоя, смотри логи.

(Опционально: в корне репо можно оставить `render.yaml` — тогда Render предложит создать сервис по нему.)

---

## Fly.io

1. Установи [flyctl](https://fly.io/docs/hub/installation/) и залогинься: `fly auth login`.
2. В папке проекта (где есть `Dockerfile`, `bot.py`, `requirements.txt`) выполни:
   ```bash
   fly launch --no-deploy
   ```
   Имя приложения введи любое (например `youtube-summary-bot`). Регион выбери ближайший.
3. Секреты:
   ```bash
   fly secrets set TELEGRAM_BOT_TOKEN=твой_токен
   fly secrets set OPENAI_API_KEY=твой_ключ
   ```
4. Деплой:
   ```bash
   fly deploy
   ```
5. Логи: `fly logs`.

---

После деплоя бот работает 24/7 без твоего компа. Проверь в Telegram — отправь боту ссылку на YouTube.
