import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const backendUrl = (process.env.BACKEND_URL || "http://localhost:8002").replace(/\/$/, "");

  let upstream: Response;
  try {
    upstream = await fetch(`${backendUrl}/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    return new Response(JSON.stringify({ detail: "Backend unreachable" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!upstream.ok) {
    const errorText = await upstream.text();
    return new Response(errorText, { status: upstream.status });
  }

  if (!upstream.body) {
    return new Response(JSON.stringify({ detail: "Empty response from backend" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
