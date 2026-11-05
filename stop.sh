#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

ROOT="$(pwd)"
PORT="${PORT:-4173}"
PID_FILE="$ROOT/server/server.pid"
STOPPED=0

wait_for_port() {
  for _ in {1..20}; do
    if ! lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "正在关闭青禾（PID ${PID}）…"
    kill "$PID"
    STOPPED=1
  else
    rm -f "$PID_FILE"
  fi
fi

# 兼容旧版本：没有 PID 文件时，仅关闭工作目录确认是青禾的进程
if [[ "$STOPPED" -eq 0 ]] && command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  for PID in $PIDS; do
    CWD="$(lsof -a -p "$PID" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)"
    if [[ "$CWD" == "$ROOT" ]]; then
      echo "正在关闭青禾（PID ${PID}）…"
      kill "$PID"
      STOPPED=1
    else
      echo "端口 ${PORT} 被其他程序占用（PID ${PID}），为避免误杀没有自动关闭。"
      exit 1
    fi
  done
fi

if [[ "$STOPPED" -eq 0 ]]; then
  echo "青禾没有在运行（端口 ${PORT}）。"
  exit 0
fi

if wait_for_port; then
  rm -f "$PID_FILE"
  echo "青禾已关闭。"
  exit 0
fi

echo "进程未在预期时间内退出，请手动检查端口 ${PORT}。" >&2
exit 1
