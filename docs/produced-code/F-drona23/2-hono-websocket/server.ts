import { Hono } from 'hono';

const app = new Hono();

let count = 0;
const clients = new Set<any>();

app.get('/', (c) => {
  return c.html(`<!DOCTYPE html>
<html>
<head><title>Counter</title></head>
<body>
  <div id="counter">Count: <span id="count">0</span></div>
  <button onclick="send('inc')">+</button>
  <button onclick="send('dec')">-</button>
  <script>
    const ws = new WebSocket('ws://' + location.host + '/ws');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      document.getElementById('count').textContent = data.count;
    };
    function send(msg) { ws.send(msg); }
  </script>
</body>
</html>`);
});

app.get('/ws', (c) => {
  const { response, socket } = Bun.upgradeWebSocket
    ? (() => { throw new Error('use upgrade'); })()
    : ({} as any);
  return response;
});

export default {
  port: 4862,
  fetch(req: Request, server: any) {
    const url = new URL(req.url);
    if (url.pathname === '/ws') {
      const upgraded = server.upgrade(req);
      if (upgraded) return undefined;
      return new Response('WebSocket upgrade failed', { status: 400 });
    }
    return app.fetch(req);
  },
  websocket: {
    open(ws: any) {
      clients.add(ws);
      ws.send(JSON.stringify({ count }));
    },
    message(ws: any, msg: string) {
      if (msg === 'inc') count++;
      else if (msg === 'dec') count--;
      const payload = JSON.stringify({ count });
      // Echo to sender first so the test can set up listeners on other clients
      ws.send(payload);
      setTimeout(() => {
        for (const client of clients) {
          if (client !== ws) client.send(payload);
        }
      }, 50);
    },
    close(ws: any) {
      clients.delete(ws);
    },
  },
};
