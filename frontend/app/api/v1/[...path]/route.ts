import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_PREFIX = "/api/v1";
const IS_DEV = process.env.NODE_ENV !== "production";

function normalizeBaseUrl(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

function getBackendBaseUrl(): string {
  const raw =
    process.env.BACKEND_URL ||
    process.env.POCO_BACKEND_URL ||
    process.env.POCO_API_URL ||
    "http://localhost:8000";
  return normalizeBaseUrl(raw);
}

function stripHopByHopHeaders(headers: Headers): Headers {
  const copied = new Headers(headers);

  // Hop-by-hop headers should not be forwarded.
  [
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
  ].forEach((key) => copied.delete(key));

  return copied;
}

async function proxyRequest(
  request: NextRequest,
  pathSegments: string[],
): Promise<Response> {
  const backendBaseUrl = getBackendBaseUrl();
  const path = pathSegments.join("/");
  const targetUrl = `${backendBaseUrl}${API_PREFIX}/${path}${request.nextUrl.search}`;

  const headers = stripHopByHopHeaders(request.headers);

  const originalHost = request.headers.get("host");
  if (originalHost && !headers.has("x-forwarded-host")) {
    headers.set("x-forwarded-host", originalHost);
  }
  if (!headers.has("x-forwarded-proto")) {
    headers.set("x-forwarded-proto", request.nextUrl.protocol.replace(":", ""));
  }

  const method = request.method.toUpperCase();
  const hasBody = !["GET", "HEAD"].includes(method);

  const init: RequestInit & { duplex?: "half" } = {
    method,
    headers,
    redirect: "manual",
  };

  if (hasBody) {
    init.body = request.body;
    init.duplex = "half";
  }

  const upstream = await fetch(targetUrl, init);

  if (IS_DEV && upstream.status === 404) {
    console.warn(`[API proxy] ${method} ${targetUrl} returned 404`);
  }

  const responseHeaders = stripHopByHopHeaders(upstream.headers);
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

export async function GET(request: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(request, path);
}

export async function POST(request: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(request, path);
}

export async function PUT(request: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(request, path);
}

export async function PATCH(request: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(request, path);
}

export async function DELETE(request: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(request, path);
}

export async function OPTIONS(request: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(request, path);
}
