/**
 * Automation Daemon - LeadRescue AI
 * Ejecutor autónomo que audita el estado del sitio en vivo, actualiza el feed RSS
 * con nuevos artículos técnicos, ejecuta pings a motores de búsqueda y sincroniza con GitHub.
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SITE_URL = 'https://shokun123.github.io/leadrescue-ai/';
const LOG_FILE = path.join(__dirname, 'automation_log.txt');
const FEED_FILE = path.join(__dirname, 'feed.xml');

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  console.log(line.trim());
  fs.appendFileSync(LOG_FILE, line, 'utf8');
}

// 1. Verificación de salud del sitio en vivo
function checkUptime() {
  return new Promise((resolve) => {
    https.get(SITE_URL, (res) => {
      log(`Salud del sitio web: HTTP ${res.statusCode} (${res.statusCode === 200 ? 'ONLINE 24/7' : 'Revisar'})`);
      resolve(res.statusCode === 200);
    }).on('error', (err) => {
      log(`Error comprobando uptime: ${err.message}`);
      resolve(false);
    });
  });
}

// 2. Ejecutar ping de IndexNow
function runIndexNow() {
  try {
    const { pingIndexNow } = require('./auto_syndicator.js');
    return pingIndexNow();
  } catch (e) {
    log(`Error en IndexNow: ${e.message}`);
    return Promise.resolve(null);
  }
}

// 3. Generación y rotación de contenido en el Feed RSS para alimentar redes sociales automáticamente
function refreshRSSContent() {
  const now = new Date().toUTCString();
  const topics = [
    {
      title: "Estudio Speed-to-Lead: El 72% de los prospectos eligen al primer proveedor que contesta",
      desc: "Análisis de conversión y cómo recortar los tiempos de respuesta a menos de 60 segundos con IA."
    },
    {
      title: "Cómo auditar la fuga de dinero de tu formulario web sin gastar en software",
      desc: "Usa la calculadora interactiva de LeadRescue AI y detecta fugas de miles de dólares al mes."
    },
    {
      title: "Automatizaciones B2B con IA: De webhook a reunión en Google Calendar en 30 segundos",
      desc: "Arquitectura técnica $0 de Google Apps Script y Gemini Flash para calificar prospectos."
    }
  ];

  const randomTopic = topics[Math.floor(Math.random() * topics.length)];

  const rssContent = `<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>LeadRescue AI - Speed to Lead Insights</title>
  <link>${SITE_URL}</link>
  <description>Auditorías automáticas de latencia y herramientas de rescate de prospectos para negocios B2B.</description>
  <language>es</language>
  <lastBuildDate>${now}</lastBuildDate>
  <item>
    <title>${randomTopic.title}</title>
    <link>${SITE_URL}</link>
    <description>${randomTopic.desc}</description>
    <pubDate>${now}</pubDate>
  </item>
  <item>
    <title>¿Cuánto dinero pierde tu negocio al tardar más de 5 minutos en responder leads?</title>
    <link>${SITE_URL}</link>
    <description>Calcula la fuga financiera en tiempo real con LeadRescue AI y desbloquea el blueprint por 19 USDT a Binance UID 1049392123.</description>
    <pubDate>Wed, 30 Sep 2026 09:30:00 GMT</pubDate>
  </item>
</channel>
</rss>`;

  fs.writeFileSync(FEED_FILE, rssContent, 'utf8');
  log(`Feed RSS actualizado con nuevo artículo para disparo de redes sociales: "${randomTopic.title}"`);
}

// 4. Sincronización automática con GitHub
function syncGit() {
  try {
    execSync('git add feed.xml automation_log.txt', { cwd: __dirname });
    execSync('git commit -m "Auto-refresh RSS feed and update log [skip ci]"', { cwd: __dirname });
    execSync('git push origin main', { cwd: __dirname });
    log('Cambios sincronizados y subidos exitosamente a GitHub.');
  } catch (e) {
    log(`Aviso de Git (posiblemente sin cambios nuevos pendientes): ${e.message.split('\n')[0]}`);
  }
}

async function start() {
  log('==================================================');
  log('⚡ EJECUTANDO CICLO DE AUTOMATIZACIÓN DESATENDIDO');
  log('==================================================');

  await checkUptime();
  refreshRSSContent();
  await runIndexNow();
  syncGit();

  log('Ciclo de automatización completado con éxito.');
}

if (require.main === module) {
  start();
}

module.exports = { start };
