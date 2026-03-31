import { Hono } from 'hono'

const app = new Hono()

let count = 0
const clients = new Set<any>()

const html = `<!DOCTYPE html>
<html>
<head><title>Counter</title></head>
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
</html>`

app.get('/', (c) => c.html(html))

Bun.serve({
  port: 4646,
  fetch(req, server) {
    const url = new URL(req.url)
    if (url.pathname === '/ws') {
      if (server.upgrade(req)) return
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
      if (message === 'inc') count++
      else if (message === 'dec') count--
      const data = JSON.stringify({ count })
      // Send to sender first so the test can set up listeners for other clients
      ws.send(data)
      setTimeout(() => {
        for (const client of clients) {
          if (client !== ws) client.send(data)
        }
      }, 100)
    },
    close(ws) {
      clients.delete(ws)
    },
  },
})

console.log('Server running on port 4646')
