#!/usr/bin/env bash
set -euo pipefail

# count_tokens.sh -- Exact token count via Anthropic API.
# Usage: ./count_tokens.sh <path-to-file>
# Returns: JSON with total count and per-section breakdown.
# Requires: ANTHROPIC_API_KEY, curl, jq

readonly FILE="${1:?Usage: count_tokens.sh <path-to-file>}"
readonly API="https://api.anthropic.com/v1/messages/count_tokens"
readonly MODEL="claude-sonnet-4-20250514"

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo '{"error": "ANTHROPIC_API_KEY not set"}' >&2
    exit 1
fi

if ! command -v jq &>/dev/null; then
    echo '{"error": "jq not installed (apt install jq)"}' >&2
    exit 1
fi

if [[ ! -f "$FILE" ]]; then
    echo "{\"error\": \"File not found: $FILE\"}" >&2
    exit 1
fi

# -- Total file count --

total_tokens=$(
    jq -Rs '{
        model: "'"$MODEL"'",
        messages: [{role: "user", content: .}]
    }' "$FILE" \
    | curl -s -w '\n%{http_code}' "$API" \
        -H "x-api-key: $ANTHROPIC_API_KEY" \
        -H "content-type: application/json" \
        -H "anthropic-version: 2023-06-01" \
        -d @- \
    | {
        body=$(sed '$d')
        code=$(tail -1)
        if [[ "$code" != "200" ]]; then
            echo "{\"error\": \"API returned HTTP $code\", \"body\": $body}" >&2
            exit 1
        fi
        echo "$body" | jq '.input_tokens'
    }
)

# -- Per-section counts --
# Split file by markdown headers, count each section separately.

sections_json=$(
    awk '
    BEGIN { section="(preamble)"; buf="" }
    /^#/ {
        if (buf != "") {
            print section "\t" buf
        }
        section = $0
        gsub(/^#+[[:space:]]*/, "", section)
        buf = ""
        next
    }
    { buf = (buf == "" ? $0 : buf "\n" $0) }
    END {
        if (buf != "") print section "\t" buf
    }
    ' "$FILE" | while IFS=$'\t' read -r header body; do
        sec_tokens=$(
            echo "$body" | jq -Rs '{
                model: "'"$MODEL"'",
                messages: [{role: "user", content: .}]
            }' | curl -s "$API" \
                -H "x-api-key: $ANTHROPIC_API_KEY" \
                -H "content-type: application/json" \
                -H "anthropic-version: 2023-06-01" \
                -d @- \
            | jq '.input_tokens'
        )
        jq -n --arg h "$header" --argjson t "$sec_tokens" \
            '{section: $h, tokens: $t}'
    done | jq -s '.'
)

# -- Zone classification --

zone=$(echo "$total_tokens" | awk '{
    if ($1 < 500)        print "GREEN"
    else if ($1 < 2000)  print "YELLOW"
    else if ($1 < 5000)  print "ORANGE"
    else if ($1 < 10000) print "RED"
    else                 print "CRITICAL"
}')

# -- Output --

jq -n \
    --arg file "$FILE" \
    --argjson total "$total_tokens" \
    --arg zone "$zone" \
    --arg method "anthropic_api" \
    --arg accuracy "exact" \
    --argjson sections "$sections_json" \
    '{
        file: $file,
        total_tokens: $total,
        zone: $zone,
        method: $method,
        accuracy: $accuracy,
        sections: $sections
    }'
