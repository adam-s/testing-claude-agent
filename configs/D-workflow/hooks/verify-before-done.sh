#!/bin/bash
# PreToolUse hook: remind agent to verify before declaring done
# This is a soft reminder, not a hard gate
echo "Reminder: Have you run and verified the output before finishing?"
exit 0
