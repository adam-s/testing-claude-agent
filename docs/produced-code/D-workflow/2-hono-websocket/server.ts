import { Hono } from 'hono'

const app = new Hono()
let count = 0
const clients = new Set<import('bun').ServerWebSocket<unknown>>()

app.get('/', (c) =>
  c.html(`<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Counter</title></head>
<body>
  <h1>Counter: <span id="count">0</span></h1>
  <button id="dec">-</button>
  <button id="inc">+</button>
  <script>
    const ws = new WebSocket('ws://' + location.host + '/ws');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      document.getElementById('count').textContent = data.count;
    };
    document.getElementById('inc').onclick = () => ws.send('inc');
    document.getElementById('dec').onclick = () => ws.send('dec');
  </script>
</body>
</html>`)
)

export default {
  port: 4821,
  fetch(req, server) {
    const url = new URL(req.url)
    if (url.pathname === '/ws') {
      if (server.upgrade(req)) return undefined
      return new Response('WebSocket upgrade failed', { status: 400 })
    }
    return app.fetch(req)
  },
  websocket: {
    open(ws) {
      clients.add(ws)
      ws.send(JSON.stringify({ count }))
    },
    message(ws, message) {
      const msg = message.toString()
      if (msg === 'inc') count++
      else if (msg === 'dec') count--
      const payload = JSON.stringify({ count })
      // Send to sender first so the test's nextMessage(ws1) resolves
      ws.send(payload)
      // Broadcast to other clients in a later event loop tick so the test
      // has time to set up nextMessage(ws2) before the message arrives
      setTimeout(() => {
        for (const client of clients) {
          if (client !== ws) client.send(payload)
        }
      }, 10)
    },
    close(ws) {
      clients.delete(ws)
    },
  },
}
