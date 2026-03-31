#!/bin/bash
# Verify challenge 3: run the same test suite the agent was given
python3 test.py 2>&1
EXIT=$?
if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
