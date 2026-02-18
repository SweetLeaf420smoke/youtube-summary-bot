#!/bin/bash
cd "$(dirname "$0")"
PIDFILE="bot.pid"
if [ ! -f "$PIDFILE" ]; then
  echo "bot.pid не найден — бот не запускался через run_bot_background.sh"
  exit 0
fi
PID=$(cat "$PIDFILE")
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "Бот остановлен (PID $PID)"
else
  echo "Процесс $PID уже не запущен"
fi
rm -f "$PIDFILE"
