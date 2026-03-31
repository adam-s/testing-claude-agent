import { Hono } from 'hono'

const app = new Hono()
let count = 0
const clients = new Set<any>()

app.get('/', (c) =>
  c.html(`<!DOCTYPE html>
<html>
<head><title>Counter</title></head>
<body>
  <h1>Counter: <span id="count">0</span></h1>
  <button id="dec">-</button>
  <button id="inc">+</button>
  <script>
    const ws = new WebSocket('ws://' + location.host + '/ws');
    ws.onmessage = e => {
      document.getElementById('count').textContent = JSON.parse(e.data).count;
    };
    document.getElementById('inc').onclick = () => ws.send('inc');
    document.getElementById('dec').onclick = () => ws.send('dec');
  </script>
</body>
</html>`)
)

Bun.serve({
  port: 4034,
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
      if (message === 'inc') count++
      else if (message === 'dec') count--
      const msg = JSON.stringify({ count })
      // Send to sender immediately, defer others so receivers can set up listeners
      ws.send(msg)
      setImmediate(() => {
        for (const client of clients) {
          if (client !== ws) client.send(msg)
        }
      })
    },
    close(ws) {
      clients.delete(ws)
    },
  },
})

console.log('Server running on port 4034')
