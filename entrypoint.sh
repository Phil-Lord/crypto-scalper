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

# Construct command-line flags for each bot ID
BOT_ID_FLAGS=""
for id in "${IDS[@]}"; do
    id="$(echo "$id" | xargs)"  # trim whitespace
    
    # If the ID is non-empty after trimming, append it to the flags
    if [[ -n "$id" ]]; then
        BOT_ID_FLAGS="$BOT_ID_FLAGS --bot-id $id"
    fi
done

# Validate at least one valid bot ID was parsed
if [[ -z "$BOT_ID_FLAGS" ]]; then
    echo "Error: BOT_IDS contains no valid bot IDs" >&2
    exit 1
fi

# Build the base command
CMD="python -m scalper.scripts.start_scalping$BOT_ID_FLAGS"

# Append --dry-run flag if DRY_RUN=true
if [[ "${DRY_RUN:-}" == "true" ]]; then
    CMD="$CMD --dry-run"
fi

# Log the final command for debugging
echo "Executing: $CMD"
exec $CMD