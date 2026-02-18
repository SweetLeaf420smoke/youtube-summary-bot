#!/usr/bin/env python3
"""
Telegram-бот: на YouTube-ссылку отвечает кратким саммари (2 абзаца).
Env: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY. Опционально HTTP_PROXY/HTTPS_PROXY или proxy_working.txt.
"""
import html
import logging
import os
import re
from pathlib import Path

LOG_DIR = Path(__file__).parent
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "bot.log", encoding="utf-8"),
    ],
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import asyncio
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

from transcript import fetch_transcript, fetch_transcript_timestamped

# Варианты количества абзацев выжимки
PARAGRAPH_OPTIONS = (2, 4, 8, 10)
DEFAULT_PARAGRAPHS = 2

TOC_BUTTON = "Оглавление"

def get_paragraphs_keyboard():
    keys = [[KeyboardButton(f"{n} абзац" + ("а" if 2 <= n <= 4 else "ов"))] for n in PARAGRAPH_OPTIONS]
    keys.append([KeyboardButton(TOC_BUTTON)])
    return ReplyKeyboardMarkup(keys, resize_keyboard=True, one_time_keyboard=False)

# Лимит символов транскрипта для LLM (контекст)
TRANSCRIPT_MAX_CHARS = 12_000

# Паттерны YouTube: watch?v=, youtu.be/, embed/
YOUTUBE_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})"
)


def extract_video_id(text: str) -> str | None:
    """Извлечь первый YouTube video_id из текста. Иначе None."""
    m = YOUTUBE_PATTERN.search(text)
    return m.group(1) if m else None


def _parse_paragraphs_button(text: str) -> int | None:
    """Если текст — кнопка выбора абзацев, вернуть число, иначе None."""
    for n in PARAGRAPH_OPTIONS:
        btn = f"{n} абзац" + ("а" if 2 <= n <= 4 else "ов")
        if text.strip() == btn:
            return n
    return None


def summarize_with_openai(transcript_text: str, num_paragraphs: int = DEFAULT_PARAGRAPHS) -> str:
    """Саммари на num_paragraphs абзацев через OpenAI."""
    from openai import OpenAI

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return "Не задан OPENAI_API_KEY."
    client = OpenAI(api_key=key)
    if len(transcript_text) > TRANSCRIPT_MAX_CHARS:
        transcript_text = transcript_text[:TRANSCRIPT_MAX_CHARS] + "\n[... обрезано ...]"
    num_str = str(num_paragraphs)
    parts = ["О чём видео, основная тема.", "Главные выводы, советы или идеи."]
    for i in range(3, num_paragraphs + 1):
        parts.append("Дополнительные важные моменты.")
    prompt = f"""Кратко суммаризуй содержание видео по транскрипту. Ответ строго в {num_str} абзацев:
""" + "\n".join(f"{i}) {parts[i-1]}" for i in range(1, num_paragraphs + 1)) + """

Транскрипт:
"""
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Ты делаешь краткие выжимки видео. Пиши только {num_str} абзаца(ов), без заголовков и списков."},
                {"role": "user", "content": prompt + transcript_text},
            ],
            max_tokens=min(500 + (num_paragraphs - 2) * 150, 1000),
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        return f"Ошибка саммари: {e!s}"


TOC_SEGMENTS = 10


def _sec_to_mmss(sec: float) -> str:
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m}:{s:02d}"


def make_toc_with_openai(segments: list[tuple[float, str]]) -> list[str]:
    """По 10 сегментам (start_sec, text) вернуть 10 строк — краткое описание каждого (без таймкода)."""
    from openai import OpenAI

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return [f"Не задан OPENAI_API_KEY."] * len(segments)
    client = OpenAI(api_key=key)
    parts = []
    for start, text in segments:
        chunk = (text[:1500] + "...") if len(text) > 1500 else text
        parts.append(chunk)
    prompt = """По транскрипту ниже даны 10 фрагментов видео по порядку.
Для каждого фрагмента напиши одну короткую строку (3–10 слов) — о чём речь.
Только 10 строк, по одной на фрагмент, в том же порядке. Без нумерации, без таймкодов.

""" + "\n\n---\n\n".join(parts)
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты составляешь оглавление видео. Ответ: 10 строк, только описание каждого фрагмента."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
        )
        raw = (r.choices[0].message.content or "").strip()
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip()][: len(segments)]
        while len(lines) < len(segments):
            lines.append("—")
        return lines[: len(segments)]
    except Exception as e:
        return [f"Ошибка оглавления: {e!s}"]


def build_toc_message(snippets: list[tuple[float, str]], video_id: str) -> str:
    """По списку (start_sec, text) и video_id собрать HTML-сообщение с оглавлением (кликабельные ссылки)."""
    if not snippets:
        return ""
    duration = snippets[-1][0] + 30
    seg_len = max(duration / TOC_SEGMENTS, 1)
    segments: list[tuple[float, str]] = []
    for i in range(TOC_SEGMENTS):
        t_start = i * seg_len
        t_end = (i + 1) * seg_len
        texts = [s[1] for s in snippets if t_start <= s[0] < t_end]
        if not texts and segments:
            t_start = segments[-1][0]
        start_sec = t_start if texts else (t_start + t_end) / 2
        segments.append((start_sec, " ".join(texts) if texts else "(нет речи)"))
    descriptions = make_toc_with_openai(segments)
    toc_lines = []
    for (start_sec, _), desc in zip(segments, descriptions):
        url = f"https://www.youtube.com/watch?v={video_id}&t={int(start_sec)}"
        label = f"{_sec_to_mmss(start_sec)} — {desc}"
        toc_lines.append(f'<a href="{html.escape(url)}">{html.escape(label)}</a>')
    return "\n".join(toc_lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать меню и текущую настройку."""
    mode = context.user_data.get("mode", "summary")
    if mode == "toc":
        msg = "Сейчас режим: Оглавление (10 пунктов с таймкодами)."
    else:
        n = context.user_data.get("paragraphs", DEFAULT_PARAGRAPHS)
        msg = f"Сейчас выжимка: {n} абзац(а/ов)."
    await update.message.reply_text(
        msg + " Выбери кнопкой или пришли ссылку на YouTube.",
        reply_markup=get_paragraphs_keyboard(),
    )


async def cmd_toc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Режим «Оглавление» — то же, что кнопка."""
    context.user_data["mode"] = "toc"
    await update.message.reply_text("Режим: Оглавление (~10 пунктов с таймкодами). Пришли ссылку на YouTube.")


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Режим «Выжимка» — то же, что кнопки 2/4/8/10."""
    context.user_data["mode"] = "summary"
    n = context.user_data.get("paragraphs", DEFAULT_PARAGRAPHS)
    await update.message.reply_text(
        f"Режим: Выжимка ({n} абзац(а/ов)). Выбери количество кнопкой или пришли ссылку.",
        reply_markup=get_paragraphs_keyboard(),
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()

    # Режим «Оглавление»
    if text.strip() == TOC_BUTTON:
        context.user_data["mode"] = "toc"
        await update.message.reply_text("Готово. Режим: Оглавление (~10 пунктов с таймкодами). Пришли ссылку на YouTube.")
        return

    # Выбор количества абзацев
    n = _parse_paragraphs_button(text)
    if n is not None:
        context.user_data["mode"] = "summary"
        context.user_data["paragraphs"] = n
        await update.message.reply_text(f"Готово. Выжимка будет в {n} абзац(а/ов). Пришли ссылку на YouTube.")
        return

    video_id = extract_video_id(text)
    if not video_id:
        await update.message.reply_text("Пришли ссылку на YouTube (youtube.com или youtu.be) или выбери режим кнопкой.")
        return

    mode = context.user_data.get("mode", "summary")
    loop = asyncio.get_event_loop()

    if mode == "toc":
        await update.message.reply_text("Скачиваю субтитры и делаю оглавление…")
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_transcript_timestamped, video_id),
                timeout=45.0,
            )
        except asyncio.TimeoutError:
            await update.message.reply_text("Запрос к YouTube занял слишком много времени. Попробуй ещё раз или другую ссылку.")
            return
        snippets, err_msg = result
        if not snippets:
            msg = "У этого видео нет субтитров или они недоступны."
            if err_msg:
                msg += f"\n\nПричина: {err_msg}"
            await update.message.reply_text(msg)
            return
        toc_message = await loop.run_in_executor(None, build_toc_message, snippets, video_id)
        await update.message.reply_text(toc_message, parse_mode="HTML")
        return

    # Режим выжимки (2/4/8/10): сначала оглавление, потом выжимка
    num_paragraphs = context.user_data.get("paragraphs", DEFAULT_PARAGRAPHS)
    await update.message.reply_text("Скачиваю субтитры, делаю оглавление и выжимку…")
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, fetch_transcript_timestamped, video_id),
            timeout=45.0,
        )
    except asyncio.TimeoutError:
        await update.message.reply_text("Запрос к YouTube занял слишком много времени. Попробуй ещё раз или другую ссылку.")
        return
    snippets, err_msg = result
    if not snippets:
        msg = "У этого видео нет субтитров или они недоступны."
        if err_msg:
            msg += f"\n\nПричина: {err_msg}"
        await update.message.reply_text(msg)
        return
    transcript_text = " ".join(s[1] for s in snippets)
    toc_message = await loop.run_in_executor(None, build_toc_message, snippets, video_id)
    summary = await loop.run_in_executor(
        None, summarize_with_openai, transcript_text, num_paragraphs
    )
    await update.message.reply_text(toc_message, parse_mode="HTML")
    await update.message.reply_text("———\n\n" + summary)


async def post_init(app: Application) -> None:
    """Меню-полоска: команды при нажатии на имя бота / иконку меню."""
    await app.bot.set_my_commands([
        ("start", "Меню"),
        ("toc", "Оглавление (10 пунктов)"),
        ("summary", "Выжимка (2/4/8/10 абзацев)"),
    ])


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Задай TELEGRAM_BOT_TOKEN в окружении.")
    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("toc", cmd_toc))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
