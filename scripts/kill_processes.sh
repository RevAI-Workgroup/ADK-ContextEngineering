#!/bin/bash
for i in $(ps aux | grep -E "pnpm|uvi" | grep -vi "node_modules" | grep -v "grep"| awk "{print $ 2}"); do kill $i; done