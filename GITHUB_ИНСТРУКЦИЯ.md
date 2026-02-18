# Как залить проект на GitHub

## Шаг 1. Создай репозиторий на GitHub

1. Открой **https://github.com/new**
2. **Repository name:** `youtube-summary-bot` (или любое имя)
3. **Public**
4. **НЕ** ставь галочки "Add a README" / "Add .gitignore" — репо должен быть пустой
5. Нажми **Create repository**

## Шаг 2. Отправь код с компа

В терминале (Terminal на Mac или в Cursor) выполни по очереди. Подставь **СВОЙ** логин GitHub и имя репо, если называл иначе:

```bash
cd "/Users/sick/Documents/Cursor/YOUTUBE SUBTITLES"

git remote add origin https://github.com/ТВОЙ_ЛОГИН/youtube-summary-bot.git

git push -u origin main
```

Пример: если логин `sick`, то:
```bash
git remote add origin https://github.com/sick/youtube-summary-bot.git
git push -u origin main
```

При `git push` браузер или терминал может запросить вход в GitHub (логин/пароль или токен). Войди — после этого код загрузится.

## Шаг 3. Деплой на Render

Когда репо появится на GitHub, иди в **https://dashboard.render.com** → New → Background Worker → подключи этот репозиторий и добавь переменные `TELEGRAM_BOT_TOKEN` и `OPENAI_API_KEY` (см. DEPLOY.md).
