// End-to-end test of the Worker fetch handler: real Slack signature verification
// and routing, with the archive fetch stubbed (no network).
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import worker from "../src/index.mjs";

const SECRET = "test-signing-secret";
const WORDS = {
  words: [
    { date: "2026-07-16", word: "barattare", url: "https://www.treccani.it/vocabolario/barattare/", definition: "Scambiare." },
    { date: "2026-07-17", word: "eteròclito", url: "https://www.treccani.it/vocabolario/eteroclito/", definition: "Anomalo." },
  ],
};

function signedRequest(text, { secret = SECRET, ts = Math.floor(Date.now() / 1000) } = {}) {
  const body = new URLSearchParams({ command: "/parola", text }).toString();
  const sig = "v0=" + createHmac("sha256", secret).update(`v0:${ts}:${body}`).digest("hex");
  return new Request("https://w/", {
    method: "POST",
    headers: {
      "content-type": "application/x-www-form-urlencoded",
      "x-slack-request-timestamp": String(ts),
      "x-slack-signature": sig,
    },
    body,
  });
}

function withStubbedArchive(fn) {
  const orig = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify(WORDS), { status: 200 });
  return fn().finally(() => (globalThis.fetch = orig));
}

const env = { SLACK_SIGNING_SECRET: SECRET, WORDS_URL: "https://stub/words.json" };

test("valid signature + specific date returns that word in-channel", () =>
  withStubbedArchive(async () => {
    const res = await worker.fetch(signedRequest("2026-07-16"), env);
    const body = await res.json();
    assert.equal(res.status, 200);
    assert.equal(body.response_type, "in_channel");
    assert.ok(body.blocks[1].text.text.includes("barattare"));
  }));

test("unknown date returns ephemeral not-found", () =>
  withStubbedArchive(async () => {
    const body = await (await worker.fetch(signedRequest("2020-01-01"), env)).json();
    assert.equal(body.response_type, "ephemeral");
    assert.ok(body.text.includes("Nessuna parola"));
  }));

test("bad argument returns usage help", () =>
  withStubbedArchive(async () => {
    const body = await (await worker.fetch(signedRequest("pippo"), env)).json();
    assert.ok(body.text.includes("/parola"));
  }));

test("invalid signature is rejected with 401", () =>
  withStubbedArchive(async () => {
    const res = await worker.fetch(signedRequest("oggi", { secret: "wrong-secret" }), env);
    assert.equal(res.status, 401);
  }));

test("stale timestamp is rejected (replay protection)", () =>
  withStubbedArchive(async () => {
    const res = await worker.fetch(signedRequest("oggi", { ts: 100 }), env);
    assert.equal(res.status, 401);
  }));

test("GET is not allowed", async () => {
  const res = await worker.fetch(new Request("https://w/", { method: "GET" }), env);
  assert.equal(res.status, 405);
});
