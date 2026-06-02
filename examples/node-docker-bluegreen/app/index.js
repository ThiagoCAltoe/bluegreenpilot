const http = require("http");

const slot = process.env.SLOT || "unknown";
const port = Number(process.env.PORT || 3000);

const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, slot }));
    return;
  }

  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end(`BlueGreenPilot demo slot: ${slot}\n`);
});

server.listen(port, () => {
  console.log(`slot ${slot} listening on ${port}`);
});
