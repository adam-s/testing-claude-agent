#!/bin/bash
# Verify challenge 2: start server, run the same test suite the agent was given
PORT=${VERIFY_PORT:-3456}

# Find server file
SERVER_FILE=""
for f in server.ts index.ts server.js index.js src/index.ts src/server.ts; do
    [ -f "$f" ] && SERVER_FILE="$f" && break
done
if [ -z "$SERVER_FILE" ]; then
    echo "FAIL: No server file found"
    echo "RESULT: FAIL"
    exit 0
fi

# Kill anything on the port
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
sleep 1

# Start server
bun run "$SERVER_FILE" > /dev/null 2>&1 &
SERVER_PID=$!
sleep 3

if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "FAIL: Server process died"
    echo "RESULT: FAIL"
    exit 0
fi

# Run test suite
TEST_PORT=$PORT bun test.js 2>&1
EXIT=$?

# Cleanup
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true

if [ $EXIT -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
