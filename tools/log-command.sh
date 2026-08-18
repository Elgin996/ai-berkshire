#!/bin/bash
# 记录用户指令到日志文件
# 由 user_prompt_submit hook 调用，stdin 接收用户输入

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${AI_BERKSHIRE_LOG_DIR:-$ROOT/logs}"
LOG_FILE="$LOG_DIR/command-log.jsonl"
COUNTER_FILE="$LOG_DIR/.counter"

mkdir -p "$LOG_DIR"

PROMPT=$(cat)
[ -z "$PROMPT" ] && exit 0

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

printf '%s' "$PROMPT" | python3 -c '
import json, sys
ts, path = sys.argv[1], sys.argv[2]
prompt = sys.stdin.read()[:200].replace("\n", " ")
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps({"time": ts, "prompt": prompt}, ensure_ascii=False) + "\n")
' "$TIMESTAMP" "$LOG_FILE"

if [ -f "$COUNTER_FILE" ]; then
    COUNT=$(cat "$COUNTER_FILE")
else
    COUNT=0
fi
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"

if [ $((COUNT % 10)) -eq 0 ]; then
    TOTAL=$(wc -l < "$LOG_FILE" | tr -d ' ')
    echo "[指令日志] 已累计记录 ${TOTAL} 条指令。建议运行 /command-log 补充近期指令的背景摘要。"
fi
