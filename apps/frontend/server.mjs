import http from "node:http";
import { createReadStream, existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.join(__dirname, "dist");
const indexFile = path.join(distDir, "index.html");
const port = Number(process.env.PORT ?? "80");

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".ico": "image/x-icon"
};

function sendFile(response, filePath) {
  const extension = path.extname(filePath).toLowerCase();
  response.writeHead(200, {
    "Content-Type": mimeTypes[extension] ?? "application/octet-stream"
  });
  createReadStream(filePath).pipe(response);
}

const server = http.createServer(async (request, response) => {
  const requestUrl = new URL(request.url ?? "/", "http://localhost");
  const cleanedPath = requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname;
  const targetPath = path.join(distDir, cleanedPath);

  if (existsSync(targetPath) && !targetPath.endsWith(path.sep)) {
    sendFile(response, targetPath);
    return;
  }

  response.writeHead(200, {
    "Content-Type": "text/html; charset=utf-8"
  });
  response.end(await readFile(indexFile, "utf-8"));
});

server.listen(port, "0.0.0.0", () => {
  console.log(`frontend server listening on :${port}`);
});
