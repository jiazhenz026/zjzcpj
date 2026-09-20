#!/bin/bash
# usage: clone.sh repos.txt
LIST=$(realpath "$1")
cd /tmp/claude-0/-home-user-zjzcpj/56dabd89-f253-58f3-bb91-f7e189b0a41c/scratchpad/repos
while read -r r; do
  [ -z "$r" ] && continue
  d=$(echo "$r" | tr '/' '__')
  if [ -d "$d/.git" ]; then echo "SKIP $r"; continue; fi
  if timeout 180 git clone -q "https://github.com/$r" "$d" 2>/tmp/clone_err.txt; then
    echo "OK   $r"
  else
    echo "FAIL $r : $(tail -1 /tmp/clone_err.txt)"
  fi
done < "$LIST"
