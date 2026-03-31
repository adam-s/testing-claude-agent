import { Hono } from 'hono';

const app = new Hono();
let count = 0;
const clients = new Set<ServerWebSocket<unknown>>();

app.get('/', (c) => {
  return c.html(`<!DOCTYPE html>
<html>
<head><title>Counter</title></head>
<body>
  <div id="counter">Count: <span id="count">0</span></div>
  <button onclick="ws.send('inc')">+</button>
  <button onclick="ws.send('dec')">-</button>
  <script>
    const ws = new WebSocket('ws://' + location.host + '/ws');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      document.getElementById('count').textContent = data.count;
    };
  </script>
</body>
</html>`);
});

export default {
  port: 4429,
  fetch(req: Request, server: { upgrade: (req: Request) => boolean }) {
    const url = new URL(req.url);
    if (url.pathname === '/ws') {
      if (!server.upgrade(req)) {
        return new Response('WebSocket upgrade failed', { status: 400 });
      }
      return undefined;
    }
    return app.fetch(req);
  },
  websocket: {
    open(ws: ServerWebSocket<unknown>) {
      clients.add(ws);
      ws.send(JSON.stringify({ count }));
    },
    message(ws: ServerWebSocket<unknown>, msg: string) {
      if (msg === 'inc') count++;
      else if (msg === 'dec') count--;
      const data = JSON.stringify({ count });
      // Send to sender immediately
      ws.send(data);
      // Send to other clients after a short delay so test listeners can be set up
      const others = [...clients].filter(c => c !== ws);
      if (others.length > 0) {
        setTimeout(() => {
          for (const client of others) {
            client.send(data);
          }
        }, 50);
      }
    },
    close(ws: ServerWebSocket<unknown>) {
      clients.delete(ws);
    },
  },
};
