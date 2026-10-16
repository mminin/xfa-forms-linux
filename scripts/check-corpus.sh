#!/bin/sh
# For each form in corpus/files/: what text extraction without XFA support
# finds on page 1, and what the XFA engine produces (pages, script errors,
# unsupported images). Run scripts/fetch-corpus.sh and scripts/build.sh first.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/_work/corpus"
mkdir -p "$OUT"
export LD_LIBRARY_PATH="$ROOT/_build/poppler:$LD_LIBRARY_PATH"
PDFXFA="$ROOT/_build/poppler/utils/pdfxfa"
PDFTOTEXT="$ROOT/_build/poppler/utils/pdftotext"
TAB=$(printf '\t')
printf 'file\tkind\tpage1_without_xfa\tengine_pages\tscript_errors\tunsupported_images\n' > "$OUT/results.tsv"
tail -n +2 "$ROOT/corpus/forms.tsv" | while IFS="$TAB" read -r file dept title page url sha kind needs; do
    in="$ROOT/corpus/files/$file"
    [ -f "$in" ] || continue
    name=${file%.pdf}
    text=$("$PDFTOTEXT" -l 1 "$in" - 2>/dev/null | tr -s ' \n\t' ' ' | cut -c1-60)
    case "$text" in
        *"Please wait"*|*"requires Adobe Reader"*) page1="fallback message only" ;;
        *) page1="form content" ;;
    esac
    if timeout 120 "$PDFXFA" -log "$in" "$OUT/$name.pdf" > "$OUT/$name.log" 2>&1; then
        pages=$(pdfinfo "$OUT/$name.pdf" 2>/dev/null | awk '/^Pages/ {print $2}')
    else
        pages=failed
    fi
    errors=$(grep -c "script error\|script object" "$OUT/$name.log" || true)
    images=$(grep -o "unsupported image image/[a-z]*" "$OUT/$name.log" | sed 's/.*image\///' | sort -u | paste -sd ' ' -)
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$file" "$kind" "$page1" "$pages" "$errors" "${images:--}" >> "$OUT/results.tsv"
done
column -t -s "$TAB" "$OUT/results.tsv"
echo "rendered forms and logs: $OUT"
