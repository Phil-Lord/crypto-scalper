#!/usr/bin/env bash

# Read JSON data that Claude Code sends to stdin
input=$(cat)

# Colours
GREEN='\033[32m'; YELLOW='\033[33m'; RED='\033[31m'; DIM='\033[2m'; RESET='\033[0m'

# Extract fields using jq
MODEL=$(echo "$input" | jq -r '.model.display_name // "unknown"')
EFFORT=$(echo "$input" | jq -r '.effort.level // "unknown"')

# The "// 0" provides a fallback if the field is null
CONTEXT_USED=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
FIVE_HOUR_USAGE=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // 0' | cut -d. -f1)
SEVEN_DAY_USAGE=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // 0' | cut -d. -f1)

FIVE_HOUR_RESETS_AT=$(echo "$input" | jq -r '
    .rate_limits.five_hour.resets_at 
    | if . then 
        (. | strflocaltime("%l.%M%p")
            | ltrimstr(" ")                                 # Remove leading space from hour (e.g. " 7.00pm" -> "7.00pm")
            | ascii_downcase                                # Convert AM/PM to lowercase (e.g. "7.00PM" -> "7.00pm")
            | gsub("\\."; "")                               # Strip all dots first (7.00p.m. -> 700pm)
            | sub("(?<h>\\d+)(?<m>\\d{2})"; "\(.h).\(.m)")  # Re-insert dot for minutes
            | sub("\\.00"; ""))                             # Remove .00 if it exists
    else 
        "Never" 
    end')

# Pick bar color based on context usage
if [ "$CONTEXT_USED" -ge 90 ]; then BAR_COLOR="$RED"
elif [ "$CONTEXT_USED" -ge 70 ]; then BAR_COLOR="$YELLOW"
else BAR_COLOR="$GREEN"; fi

FILLED=$((CONTEXT_USED / 10)); EMPTY=$((10 - FILLED))
printf -v FILL "%${FILLED}s"; printf -v PAD "%${EMPTY}s"
BAR="${FILL// /█}${PAD// /░}"

# Output the status line
echo -e "$MODEL ${DIM}$EFFORT${RESET} | ${BAR_COLOR}${BAR}${RESET} ${CONTEXT_USED}% | ${FIVE_HOUR_USAGE}% ${DIM}${FIVE_HOUR_RESETS_AT}${RESET} | ${SEVEN_DAY_USAGE}% ${DIM}7d${RESET}"