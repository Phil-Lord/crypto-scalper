#!/usr/bin/env bash

# Read JSON data that Claude Code sends to stdin
input=$(cat)

# Extract fields using jq
MODEL=$(echo "$input" | jq -r '.model.display_name // "unknown"')

# The "// 0" provides a fallback if the field is null
CONTEXT_USED=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
FIVE_HOUR_USAGE=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // 0' | cut -d. -f1)
SEVEN_DAY_USAGE=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // 0' | cut -d. -f1)

# Pick bar color based on context usage
GREEN='\033[32m'; YELLOW='\033[33m'; RED='\033[31m'; RESET='\033[0m'
if [ "$CONTEXT_USED" -ge 90 ]; then BAR_COLOR="$RED"
elif [ "$CONTEXT_USED" -ge 70 ]; then BAR_COLOR="$YELLOW"
else BAR_COLOR="$GREEN"; fi

FILLED=$((CONTEXT_USED / 10)); EMPTY=$((10 - FILLED))
printf -v FILL "%${FILLED}s"; printf -v PAD "%${EMPTY}s"
BAR="${FILL// /█}${PAD// /░}"

# Output the status line
echo -e "[$MODEL] | ${BAR_COLOR}${BAR}${RESET} ${CONTEXT_USED}% | ${FIVE_HOUR_USAGE}% 5h | ${SEVEN_DAY_USAGE}% 7d"