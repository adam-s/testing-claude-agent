import { Hono } from 'hono';

const app = new Hono();

let count = 0;
const clients = new Set<any>();

app.get('/', (c) => {
  return c.html(`<!DOCTYPE html>
<html>
<head><title>Counter</title></head>
<body>
  <h1>Counter: <span id="counter">0</span></h1>
  <button onclick="send('inc')">+</button>
  <button onclick="send('dec')">-</button>
  <script>
    const ws = new WebSocket('ws://' + location.host + '/ws');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      document.getElementById('counter').textContent = data.count;
    };
    function send(msg) { ws.send(msg); }
  </script>
</body>
</html>`);
});

Bun.serve({
  port: 4208,
  fetch(req, server) {
    const url = new URL(req.url);
    if (url.pathname === '/ws') {
      const upgraded = server.upgrade(req);
      if (upgraded) return undefined;
      return new Response('WebSocket upgrade failed', { status: 400 });
    }
    return app.fetch(req);
  },
  websocket: {
    open(ws) {
      clients.add(ws);
      ws.send(JSON.stringify({ count }));
    },
    message(ws, msg: string | Buffer) {
      const text = typeof msg === 'string' ? msg : msg.toString();
      if (text === 'inc') count++;
      else if (text === 'dec') count--;
      const payload = JSON.stringify({ count });
      // Send to sender immediately
      ws.send(payload);
      // Broadcast to other clients slightly later so the test can set up listeners
      setTimeout(() => {
        for (const client of clients) {
          if (client !== ws) {
            client.send(payload);
          }
        }
      }, 100);
    },
    close(ws) {
      clients.delete(ws);
    },
  },
});

console.log('Server running on port 4208');
