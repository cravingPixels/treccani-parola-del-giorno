import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveDate, addDays, findEntry, wordMessage, usageMessage, notFoundMessage } from "../src/lib.mjs";

const TODAY = "2026-07-17";

test("resolveDate: empty / oggi / today -> today", () => {
  for (const t of ["", "  ", "oggi", "Today", "OGGI"]) assert.equal(resolveDate(t, TODAY), TODAY);
});

test("resolveDate: ieri / yesterday -> previous day", () => {
  assert.equal(resolveDate("ieri", TODAY), "2026-07-16");
  assert.equal(resolveDate("yesterday", TODAY), "2026-07-16");
});

test("resolveDate: ISO date passes through", () => {
  assert.equal(resolveDate("2026-07-15", TODAY), "2026-07-15");
});

test("resolveDate: Italian DD/MM/YYYY and DD-MM-YYYY", () => {
  assert.equal(resolveDate("15/07/2026", TODAY), "2026-07-15");
  assert.equal(resolveDate("5-3-2026", TODAY), "2026-03-05");
});

test("resolveDate: yesterday crosses month boundary", () => {
  assert.equal(resolveDate("ieri", "2026-08-01"), "2026-07-31");
  assert.equal(addDays("2026-01-01", -1), "2025-12-31");
});

test("resolveDate: rejects nonsense and impossible dates", () => {
  assert.equal(resolveDate("banana", TODAY), null);
  assert.equal(resolveDate("2026-13-40", TODAY), null);
  assert.equal(resolveDate("32/01/2026", TODAY), null);
});

test("findEntry finds by date, else null", () => {
  const words = [{ date: "2026-07-16", word: "a" }, { date: "2026-07-17", word: "b" }];
  assert.equal(findEntry(words, "2026-07-17").word, "b");
  assert.equal(findEntry(words, "2026-07-01"), null);
  assert.equal(findEntry([], "2026-07-17"), null);
});

test("wordMessage is in_channel and includes link + definition", () => {
  const msg = wordMessage({
    date: "2026-07-17", word: "eteròclito",
    url: "https://www.treccani.it/vocabolario/eteroclito/", definition: "Anomalo.",
  });
  assert.equal(msg.response_type, "in_channel");
  const text = msg.blocks[1].text.text;
  assert.ok(text.includes("eteròclito") && text.includes("eteroclito/") && text.includes("Anomalo."));
});

test("usage and not-found are ephemeral", () => {
  assert.equal(usageMessage().response_type, "ephemeral");
  assert.equal(notFoundMessage("2026-07-17").response_type, "ephemeral");
});
