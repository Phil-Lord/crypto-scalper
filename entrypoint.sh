#!/usr/bin/env bash

# Set strict mode for immediate exit on error
set -euo pipefail

# Validate BOT_IDS is set and non-empty
if [[ -z "${BOT_IDS:-}" ]]; then
    echo "Error: BOT_IDS environment variable is not set or empty." >&2
    exit 1
fi

# Set Internal Field Separator to comma and read BOT_IDS into an array
IFS=',' read -ra IDS <<< "$BOT_IDS"

# Build the base command as an array so each argument is isolated
cmd=(python -m scripts.start_scalping)
has_valid_id=false

for id in "${IDS[@]}"; do
    id="$(echo "$id" | xargs)"  # trim whitespace

    # If the ID is non-empty after trimming, append it as a distinct argument
    if [[ -n "$id" ]]; then
        cmd+=(--bot-id "$id")
        has_valid_id=true
    fi
done

# Validate at least one valid bot ID was parsed
if [[ "$has_valid_id" != "true" ]]; then
    echo "Error: BOT_IDS contains no valid bot IDs" >&2
    exit 1
fi

# Append --dry-run flag if DRY_RUN=true
if [[ "${DRY_RUN:-}" == "true" ]]; then
    cmd+=(--dry-run)
fi

# Log the final command for debugging
printf 'Executing:'
printf ' %q' "${cmd[@]}"
printf '\n'

exec "${cmd[@]}"