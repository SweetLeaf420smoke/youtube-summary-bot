#!/bin/bash
# Запуск бота в фоне: переживёт закрытие терминала.
# Остановка: ./stop_bot.sh или kill $(cat bot.pid)

cd "$(dirname "$0")"
PIDFILE="bot.pid"
LOGFILE="bot_stdout.log"

if [ -f "$PIDFILE" ]; then
  OLD=$(cat "$PIDFILE")
  if kill -0 "$OLD" 2>/dev/null; then
    echo "Бот уже запущен (PID $OLD). Сначала останови: ./stop_bot.sh"
    exit 1
  fi
  rm -f "$PIDFILE"
fi

nohup .venv/bin/python bot.py >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "Бот запущен в фоне. PID: $(cat $PIDFILE)"
echo "Лог: $LOGFILE. Остановить: ./stop_bot.sh"
