import http from "node:http";

const port = Number(process.env.PORT ?? "80");
const backendBase = process.env.BACKEND_BASE_URL ?? "http://backend:8000";
const frontendBase = process.env.FRONTEND_BASE_URL ?? "http://frontend:80";

function selectTarget(urlPath) {
  return urlPath.startsWith("/api/") ? backendBase : frontendBase;
}

const server = http.createServer(async (request, response) => {
  try {
    const requestUrl = new URL(request.url ?? "/", "http://localhost");
    const bodyChunks = [];
    for await (const chunk of request) {
      bodyChunks.push(chunk);
    }
    const body = bodyChunks.length > 0 ? Buffer.concat(bodyChunks) : undefined;
    const target = new URL(requestUrl.pathname + requestUrl.search, selectTarget(requestUrl.pathname));

    const upstream = await fetch(target, {
      method: request.method,
      headers: request.headers,
      body
    });

    const headers = {};
    upstream.headers.forEach((value, key) => {
      headers[key] = value;
    });
    response.writeHead(upstream.status, headers);

    if (upstream.body) {
      for await (const chunk of upstream.body) {
        response.write(chunk);
      }
    }
    response.end();
  } catch (error) {
    response.writeHead(502, {
      "Content-Type": "application/json; charset=utf-8"
    });
    response.end(
      JSON.stringify({
        error: "bad_gateway",
        message: error instanceof Error ? error.message : "proxy failed"
      })
    );
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`gateway listening on :${port}`);
});

