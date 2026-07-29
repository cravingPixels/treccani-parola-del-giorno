// Pure, dependency-free helpers for the /parola slash command.
// No I/O here so this module is trivially unit-testable.

const ISO = /^\d{4}-\d{2}-\d{2}$/;
const DMY = /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/;

function isRealDate(iso) {
  const d = new Date(`${iso}T12:00:00Z`);
  return !Number.isNaN(d.getTime()) && iso === d.toISOString().slice(0, 10);
}

export function addDays(iso, n) {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/**
 * Turn the slash-command argument into a YYYY-MM-DD date, relative to `today`
 * (itself a YYYY-MM-DD string in the target timezone). Returns null if unparseable.
 */
export function resolveDate(text, today) {
  const t = (text || "").trim().toLowerCase();
  if (t === "" || t === "oggi" || t === "today") return today;
  if (t === "ieri" || t === "yesterday") return addDays(today, -1);
  if (ISO.test(t)) return isRealDate(t) ? t : null;
  const m = DMY.exec(t);
  if (m) {
    const [, d, mo, y] = m;
    const iso = `${y}-${mo.padStart(2, "0")}-${d.padStart(2, "0")}`;
    return isRealDate(iso) ? iso : null;
  }
  return null;
}

export function findEntry(words, date) {
  return (words || []).find((w) => w.date === date) || null;
}

const USAGE =
  "Uso: `/parola` (oggi), `/parola ieri`, oppure `/parola 2026-07-15` (anche `15/07/2026`).";

export function usageMessage() {
  return { response_type: "ephemeral", text: USAGE };
}

export function notFoundMessage(date) {
  return {
    response_type: "ephemeral",
    text: `Nessuna parola del giorno registrata per *${date}*.`,
  };
}

/** Slack Block Kit payload for a found word. Mirrors the daily post format. */
export function wordMessage(entry) {
  const lines = [`*<${entry.url}|${entry.word}>*`];
  if (entry.definition) lines.push(entry.definition);
  return {
    response_type: "in_channel",
    blocks: [
      { type: "header", text: { type: "plain_text", text: "📖 Parola del giorno", emoji: true } },
      { type: "section", text: { type: "mrkdwn", text: lines.join("\n") } },
      { type: "context", elements: [{ type: "mrkdwn", text: `Treccani · ${entry.date}` }] },
    ],
  };
}
