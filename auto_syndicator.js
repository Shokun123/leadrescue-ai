/**
 * Auto-Syndicator & Indexing Engine - LeadRescue AI
 * Automatiza la distribución, indexación en motores de búsqueda y difusión vía Webhooks.
 */

const https = require('https');
const { exec } = require('child_process');

const SITE_URL = 'https://shokun123.github.io/leadrescue-ai/';
const INDEXNOW_KEY = '7b9a4c1f8e2d3a5b9c0e1f4a8b2c6d7e';
const KEY_LOCATION = `${SITE_URL}${INDEXNOW_KEY}.txt`;

// 1. Notificación a motores de búsqueda vía IndexNow (Bing, Yandex, Seznam, Naver)
function pingIndexNow() {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify({
      host: 'shokun123.github.io',
      key: INDEXNOW_KEY,
      keyLocation: KEY_LOCATION,
      urlList: [
        SITE_URL,
        `${SITE_URL}feed.xml`,
        `${SITE_URL}sitemap.xml`
      ]
    });

    const options = {
      hostname: 'api.indexnow.org',
      port: 443,
      path: '/indexnow',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Length': Buffer.byteLength(payload)
      }
    };

    console.log('[+] Enviando ping a IndexNow (Motores de búsqueda globales)...');
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        console.log(`[✓] IndexNow respondió con código HTTP: ${res.statusCode} (${res.statusCode === 200 || res.statusCode === 202 ? 'Aceptado e Indexado' : 'Pendiente'})`);
        resolve(res.statusCode);
      });
    });

    req.on('error', (err) => {
      console.warn('[-] Error conectando a IndexNow:', err.message);
      resolve(null);
    });

    req.write(payload);
    req.end();
  });
}

// 2. Disparo de Webhooks de distribución automática (Make.com / IFTTT / Zapier / Telegram)
function broadcastToWebhook(webhookUrl, message) {
  if (!webhookUrl) {
    console.log('[i] No se ha configurado URL de webhook externo.');
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const url = new URL(webhookUrl);
    const payload = JSON.stringify({
      content: message,
      title: "LeadRescue AI - Nueva Herramienta en Vivo",
      url: SITE_URL,
      timestamp: new Date().toISOString()
    });

    const options = {
      hostname: url.hostname,
      path: url.pathname + url.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      }
    };

    const req = https.request(options, (res) => {
      console.log(`[✓] Webhook de difusión ejecutado con código: ${res.statusCode}`);
      resolve(res.statusCode);
    });

    req.on('error', (e) => {
      console.warn('[-] Error enviando webhook:', e.message);
      resolve(null);
    });

    req.write(payload);
    req.end();
  });
}

// 3. Ejecución principal
async function run() {
  console.log('==================================================');
  console.log('⚡ INICIANDO MOTOR DE DISTRIBUCIÓN AUTOMÁTICA');
  console.log(`🎯 URL Objetivo: ${SITE_URL}`);
  console.log('==================================================');

  await pingIndexNow();

  // Si se pasa una URL de webhook por variable de entorno o argumento
  const customWebhook = process.env.DISPATCH_WEBHOOK || process.argv[2];
  if (customWebhook && customWebhook.startsWith('http')) {
    await broadcastToWebhook(customWebhook, `Calcula gratis la fuga financiera de leads en: ${SITE_URL}`);
  }

  console.log('[✓] Proceso de distribución y señalización completado.');
}

if (require.main === module) {
  run();
}

module.exports = { pingIndexNow, broadcastToWebhook };
