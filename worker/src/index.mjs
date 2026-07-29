import { resolveDate, findEntry, usageMessage, notFoundMessage, wordMessage } from "./lib.mjs";

const DEFAULT_WORDS_URL =
  "https://cravingpixels.github.io/treccani-parola-del-giorno/data/words.json";
const MAX_SKEW_SECONDS = 60 * 5;

function romeToday() {
  // en-CA formats as YYYY-MM-DD; timeZone handles CET/CEST automatically.
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Rome" }).format(new Date());
}

function json(body) {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

async function verifySlackSignature(secret, timestamp, body, signature) {
  if (!secret || !timestamp || !signature) return false;
  if (Math.abs(Date.now() / 1000 - Number(timestamp)) > MAX_SKEW_SECONDS) return false;

  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(`v0:${timestamp}:${body}`));
  const expected =
    "v0=" + [...new Uint8Array(mac)].map((b) => b.toString(16).padStart(2, "0")).join("");

  // constant-time compare
  if (expected.length !== signature.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= expected.charCodeAt(i) ^ signature.charCodeAt(i);
  return diff === 0;
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

    const raw = await request.text();
    const ok = await verifySlackSignature(
      env.SLACK_SIGNING_SECRET,
      request.headers.get("x-slack-request-timestamp"),
      raw,
      request.headers.get("x-slack-signature"),
    );
    if (!ok) return new Response("invalid signature", { status: 401 });

    const params = new URLSearchParams(raw);
    const date = resolveDate(params.get("text"), romeToday());
    if (!date) return json(usageMessage());

    let words = [];
    try {
      const res = await fetch(env.WORDS_URL || DEFAULT_WORDS_URL, { cf: { cacheTtl: 60 } });
      if (res.ok) words = (await res.json()).words || [];
    } catch {
      return json({ response_type: "ephemeral", text: "Archivio non raggiungibile, riprova." });
    }

    const entry = findEntry(words, date);
    return json(entry ? wordMessage(entry) : notFoundMessage(date));
  },
};
