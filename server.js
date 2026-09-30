const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const BINANCE_UID = "1049392123";

const server = http.createServer((req, res) => {
  // Configuración de CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Rutas
  if (req.url === '/' || req.url === '/index.html') {
    const indexPath = path.join(__dirname, 'index.html');
    fs.readFile(indexPath, (err, data) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('Error interno cargando la aplicación.');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(data);
    });
    return;
  }

  // API de información de cobro a Binance
  if (req.url === '/api/payment-info' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({
      binance_uid: BINANCE_UID,
      price_usdt: 19.00,
      supported_networks: ['BNB Smart Chain (BEP20)', 'Polygon'],
      product_name: "LeadRescue AI Suite Pro",
      instant_delivery: true
    }));
    return;
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('Ruta no encontrada');
});

server.listen(PORT, () => {
  console.log(`=======================================================`);
  console.log(`⚡ LeadRescue AI Micro-SaaS corriendo en: http://localhost:${PORT}`);
  console.log(`🟡 Cobros configurados hacia Binance UID: ${BINANCE_UID}`);
  console.log(`=======================================================`);
});
