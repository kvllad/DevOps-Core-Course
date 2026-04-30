export interface Env {
  APP_NAME: string;
  COURSE_NAME: string;
  APP_VERSION: string;
  API_TOKEN: string;
  ADMIN_EMAIL: string;
  SETTINGS: KVNamespace;
}

type EdgeMetadata = {
  colo: string | null;
  country: string | null;
  city: string | null;
  asn: number | null;
  httpProtocol: string | null;
  tlsVersion: string | null;
};

function json(data: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(data, null, 2), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...(init?.headers ?? {}),
    },
    status: init?.status ?? 200,
  });
}

function getEdgeMetadata(request: Request): EdgeMetadata {
  const cf = request.cf as Record<string, unknown> | undefined;
  return {
    colo: typeof cf?.colo === "string" ? cf.colo : null,
    country: typeof cf?.country === "string" ? cf.country : null,
    city: typeof cf?.city === "string" ? cf.city : null,
    asn: typeof cf?.asn === "number" ? cf.asn : null,
    httpProtocol: typeof cf?.httpProtocol === "string" ? cf.httpProtocol : null,
    tlsVersion: typeof cf?.tlsVersion === "string" ? cf.tlsVersion : null,
  };
}

async function readCounter(env: Env): Promise<number> {
  const raw = await env.SETTINGS.get("visits");
  return Number.parseInt(raw ?? "0", 10) || 0;
}

async function incrementCounter(env: Env): Promise<number> {
  const visits = (await readCounter(env)) + 1;
  await env.SETTINGS.put("visits", String(visits));
  return visits;
}

async function handleKv(request: Request, env: Env, key: string): Promise<Response> {
  if (request.method === "GET") {
    const value = await env.SETTINGS.get(key);
    if (value === null) {
      return json({ error: "Not Found", key }, { status: 404 });
    }
    return json({ key, value });
  }

  if (request.method === "POST") {
    const body = await request.json<{ value?: string }>();
    if (!body.value) {
      return json({ error: "Missing value" }, { status: 400 });
    }
    await env.SETTINGS.put(key, body.value);
    return json({ key, value: body.value, stored: true }, { status: 201 });
  }

  return json({ error: "Method Not Allowed" }, { status: 405 });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    console.log("request", {
      method: request.method,
      path: url.pathname,
      colo: request.cf?.colo ?? null,
      country: request.cf?.country ?? null,
    });

    if (url.pathname === "/health") {
      return json({
        status: "ok",
        app: env.APP_NAME,
        version: env.APP_VERSION,
        timestamp: new Date().toISOString(),
      });
    }

    if (url.pathname === "/edge") {
      return json({
        app: env.APP_NAME,
        version: env.APP_VERSION,
        edge: getEdgeMetadata(request),
      });
    }

    if (url.pathname === "/config") {
      return json({
        app: env.APP_NAME,
        course: env.COURSE_NAME,
        version: env.APP_VERSION,
        usesPlaintextVars: true,
        secretsAvailable: {
          apiTokenConfigured: Boolean(env.API_TOKEN),
          adminEmailConfigured: Boolean(env.ADMIN_EMAIL),
        },
      });
    }

    if (url.pathname === "/counter") {
      const visits = await incrementCounter(env);
      return json({ visits, persistedIn: "Workers KV" });
    }

    if (url.pathname.startsWith("/kv/")) {
      const key = url.pathname.replace("/kv/", "");
      return handleKv(request, env, key);
    }

    if (url.pathname === "/") {
      return json({
        app: env.APP_NAME,
        course: env.COURSE_NAME,
        version: env.APP_VERSION,
        routes: [
          "GET /",
          "GET /health",
          "GET /edge",
          "GET /config",
          "GET /counter",
          "GET /kv/:key",
          "POST /kv/:key"
        ],
        notes: [
          "Plaintext vars come from wrangler.jsonc",
          "Secrets come from Wrangler secret bindings",
          "Counter and key-value data are stored in Workers KV",
        ],
      });
    }

    return json({ error: "Not Found", path: url.pathname }, { status: 404 });
  },
};
