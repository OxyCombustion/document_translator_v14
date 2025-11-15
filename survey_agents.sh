#!/bin/bash
cd /home/thermodynamics/document_translator_v13
for dir in agents/*/; do
    if [ -d "$dir" ] && [ "$(basename "$dir")" != "__pycache__" ]; then
        count=$(find "$dir" -name "*.py" -type f | wc -l)
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        printf "%-30s %3d files, %s\n" "$(basename "$dir")" "$count" "$size"
    fi
done | sort
