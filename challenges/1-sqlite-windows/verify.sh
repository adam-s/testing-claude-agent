#!/bin/bash
# Verify challenge 1: run the same test suite the agent was given
[ -d node_modules ] || npm install --silent 2>/dev/null
node test.js 2>&1
EXIT=$?
if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
