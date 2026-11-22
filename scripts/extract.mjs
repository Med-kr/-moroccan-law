// Extract positioned text lines from a PDF with pdf.js.
// Output: one JSON object per page on stdout: {p, lines:[{t,h,y,x0,x1,mark?}]}
// `mark` is set on a line that opens with small raised numbers, i.e. the first line of a
// footnote: it lists those numbers (several when one note serves several marks) and they are
// left out of `t`.
//
// pdf.js returns glyph runs in content-stream order, which is NOT always the
// reading order. Each line is therefore rebuilt from geometry:
//   1. runs are grouped into lines by baseline;
//   2. inside a line, runs are ordered by position (right-to-left when the line
//      is mostly Arabic, left-to-right otherwise);
//   3. in a right-to-left line, neighbouring left-to-right runs that belong
//      together (Latin words, or the two halves of one number) are put back in
//      left-to-right order;
//   4. a space is inserted when the gap between two neighbours is wide enough;
//   5. small raised digit runs become footnote references: [^12];
//   6. a run drawn twice at almost the same place (fake bold) is kept once;
//   7. a left-to-right line drawn twice letter by letter (shadowed headings), which pdf.js
//      returns as overlapping two-letter runs, is read in stream order with each doubled
//      letter kept once.
import { getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs';
import fs from 'fs';

const file = process.argv[2];
if (!file) { console.error('usage: node extract.mjs file.pdf'); process.exit(2); }
const data = new Uint8Array(fs.readFileSync(file));
const doc = await getDocument({ data, useSystemFonts: true, verbosity: 0 }).promise;

const AR = /[؀-ۿﭐ-﷿ﹰ-﻿]/;
const LATIN = /[A-Za-zÀ-ɏ]/;
const NUMERIC = /^[\d.,\/-]+$/;

// A shadowed heading: every letter is drawn twice, a hair apart. In stream order the runs
// then spell each letter twice in a row ("T", "TI", "IT", ... -> "TTIITT..."). Returns the
// line text with the doubles removed, or null when the line is not of that kind.
function shadowedLine(items) {
  const body = items.filter(i => !i.sup);
  if (!body.some(i => i.str.trim().length >= 2)) return null;
  const letters = body.map(i => i.str).join('').replace(/\s+/g, '');
  if (letters.length < 4 || letters.length % 2) return null;
  for (let k = 0; k < letters.length; k += 2) if (letters[k] !== letters[k + 1]) return null;
  if (AR.test(letters)) return null;
  let t = '';
  const sups = new Set();
  for (const it of items) {
    if (it.sup) { const n = it.str.trim(); if (!sups.has(n)) { sups.add(n); t += `[^${n}]`; } continue; }
    t += it.str;
  }
  return t.replace(/([^\s\[\]^])\1/g, '$1');
}

function buildLine(items) {
  // drop fake-bold duplicates
  const uniq = [];
  for (const it of items) {
    if (uniq.some(u => u.str === it.str && Math.abs(u.x - it.x) < 2 && Math.abs(u.y - it.y) < 2)) continue;
    uniq.push(it);
  }
  const base = uniq.filter(i => !i.sup);
  const h = Math.max(...base.map(i => i.h));
  const arabic = base.filter(i => AR.test(i.str)).reduce((n, i) => n + i.str.length, 0);
  const latin = base.filter(i => LATIN.test(i.str)).reduce((n, i) => n + i.str.length, 0);
  const rtl = arabic >= latin;
  // visual order: from the reading start edge
  const vis = [...uniq].sort((a, b) => rtl ? (b.x + b.w) - (a.x + a.w) : a.x - b.x);
  // footnote text: the line opens with small raised number(s)
  const mark = [];
  const full = base.filter(i => i.h >= h * 0.95);
  if (full.length) {
    const baseY = full[0].y;
    let k = 0;
    while (k < vis.length && /^[\d\s-]+$/.test(vis[k].str) && vis[k].h < h * 0.8 && vis[k].y > baseY + h * 0.15) k++;
    const nums = vis.slice(0, k).flatMap(i => i.str.match(/\d+/g) || []).map(Number);
    if (nums.length && k < vis.length) { mark.push(...nums.sort((a, b) => a - b)); vis.splice(0, k); }
  }
  const gapBetween = (a, b) => Math.max(b.x - (a.x + a.w), a.x - (b.x + b.w));
  const wide = (a, b) => gapBetween(a, b) > Math.min(a.h, b.h, h) * 0.12;

  // group left-to-right runs that belong together inside a right-to-left line
  const groups = [];
  for (let vi = 0; vi < vis.length; vi++) {
    const it = vis[vi];
    const last = groups[groups.length - 1];
    const prev = last && last[last.length - 1];
    let join = false;
    if (rtl && prev && !it.sup && !prev.sup && it.dir === 'ltr' && prev.dir === 'ltr') {
      const bothNumeric = NUMERIC.test(it.str.trim()) && NUMERIC.test(prev.str.trim());
      const latinPair = (LATIN.test(it.str) || LATIN.test(prev.str)) && !AR.test(it.str) && !AR.test(prev.str);
      // "9 [gap] - 647": a dash or slash set a little apart from the digits before it still
      // links them to the digits that follow it
      const nextIt = vis[vi + 1];
      const linked = /^\d+$/.test(prev.str.trim()) && /^[-\/]$/.test(it.str.trim())
        && nextIt && nextIt.dir === 'ltr' && /^\d/.test(nextIt.str.trim()) && !wide(it, nextIt)
        && gapBetween(prev, it) < Math.min(prev.h, it.h) * 0.45;
      join = (bothNumeric && !wide(prev, it)) || linked || latinPair;
    }
    if (join) last.push(it); else groups.push([it]);
  }
  let t = '';
  let prevItem = null;
  const shadow = shadowedLine(items);
  if (shadow !== null) t = shadow;
  else for (const g of groups) {
    let seq = g.length > 1 ? [...g].reverse() : g;   // back to left-to-right inside the group
    // the full stop that ends the sentence is drawn at the left of a number that ends a
    // right-to-left sentence: "." "647-9" reads "647-9."
    if (rtl && seq.length > 1 && /^[.,;:]$/.test(seq[0].str.trim()) && /\d/.test(seq[1].str)
        && seq.every(i => NUMERIC.test(i.str.trim()))) seq = [...seq.slice(1), seq[0]];
    for (const it of seq) {
      if (it.sup) { t += `[^${it.str.trim()}]`; prevItem = it; continue; }
      if (prevItem && !prevItem.sup && wide(prevItem, it) && !t.endsWith(' ') && !it.str.startsWith(' ')) t += ' ';
      t += it.str;
      prevItem = it;
    }
  }
  return {
    ...(mark.length ? { mark } : {}),
    t: t.replace(/\s+/g, ' ').trim(),
    h: +h.toFixed(1),
    y: +base[0].y.toFixed(1),
    x0: +Math.min(...base.map(i => i.x)).toFixed(1),
    x1: +Math.max(...base.map(i => i.x + i.w)).toFixed(1),
  };
}

function groupLines(items) {
  // items in content-stream order -> lines (runs on one baseline)
  const lines = [];
  let cur = null;   // {y, h, items}
  const flush = () => {
    if (cur && cur.items.some(i => !i.sup && i.str.trim())) {
      const l = buildLine(cur.items.filter(i => i.sup || i.str.trim() || i.w > 0));
      if (l.t) lines.push(l);
    }
    cur = null;
  };
  for (const it of items) {
    // footnote reference: a short digit run raised above the baseline of the current line
    if (cur && it.y > cur.y + cur.h * 0.18 && it.y < cur.y + cur.h * 0.9 && it.h <= cur.h && /^\s*\d{1,4}\s*$/.test(it.str)) {
      it.sup = true; cur.items.push(it); continue;
    }
    if (cur && Math.abs(it.y - cur.y) > Math.max(it.h, cur.h) * 0.5) flush();
    if (!cur) cur = { y: it.y, h: it.h, items: [] };
    cur.h = Math.max(cur.h, it.h);
    cur.items.push(it);
  }
  flush();
  return lines;
}

// Two-column pages (the Bulletin officiel layout): a vertical gutter in the middle third of
// the page that almost no run crosses, with text on both sides. Returns [x0, x1] or null.
function findGutter(items, width) {
  const text = items.filter(i => i.str.trim());
  const total = text.reduce((n, i) => n + i.str.length, 0);
  if (text.length < 40 || !width) return null;
  const bins = new Array(Math.ceil(width) + 1).fill(0);
  for (const i of text) for (let x = Math.max(0, Math.floor(i.x)); x <= Math.min(width, Math.ceil(i.x + i.w)); x++) bins[x]++;
  let best = null;
  for (let x = Math.floor(width * 0.33); x <= Math.ceil(width * 0.67); x++) {
    if (bins[x] > text.length * 0.04) continue;
    let e = x;
    while (e + 1 < bins.length && bins[e + 1] <= text.length * 0.04) e++;
    if (e - x >= 10 && (!best || e - x > best[1] - best[0])) best = [x, e];
    x = e;
  }
  if (!best) return null;
  const left = text.filter(i => i.x + i.w <= best[0]).reduce((n, i) => n + i.str.length, 0);
  const right = text.filter(i => i.x >= best[1]).reduce((n, i) => n + i.str.length, 0);
  // each column has lines of its own (a wide space inside justified lines, or a cover page
  // with a few words on each side, is no column)
  const rows = side => new Set(text.filter(side).map(i => Math.round(i.y / 2))).size;
  const nl = rows(i => i.x + i.w <= best[0]);
  const nr = rows(i => i.x >= best[1]);
  return left > total * 0.2 && right > total * 0.2 && nl >= 8 && nr >= 8 ? best : null;
}

for (let p = 1; p <= doc.numPages; p++) {
  const page = await doc.getPage(p);
  const tc = await page.getTextContent();
  const items = [];
  for (const raw of tc.items) {
    if (!raw.str || (raw.width === 0 && !raw.str.trim())) continue;
    items.push({ str: raw.str, dir: raw.dir, x: raw.transform[4], y: raw.transform[5], w: raw.width,
                 h: raw.height || Math.abs(raw.transform[3]), sup: false });
  }
  const [vx0, , vx1] = page.view;
  const gutter = findGutter(items, vx1 - vx0);
  let lines;
  if (!gutter) {
    lines = groupLines(items);
  } else {
    // full-width runs (titles, page header) split the page into bands; in each band the
    // right column is read before the left one (Arabic) — the left one first for a page
    // that is mostly Latin
    const crosses = i => i.x < gutter[0] && i.x + i.w > gutter[1];
    const mid = (gutter[0] + gutter[1]) / 2;
    const full = groupLines(items.filter(crosses));
    const right = groupLines(items.filter(i => !crosses(i) && i.x + i.w / 2 >= mid));
    const left = groupLines(items.filter(i => !crosses(i) && i.x + i.w / 2 < mid));
    const arabic = items.filter(i => AR.test(i.str)).length >= items.filter(i => LATIN.test(i.str)).length;
    const seps = full.map(l => l.y).sort((a, b) => b - a);
    const band = l => seps.filter(y => y > l.y).length;
    let o = 0;
    lines = [];
    for (let b = 0; b <= seps.length; b++) {
      const cols = arabic ? [right, left] : [left, right];
      for (const col of cols) {
        const ls = col.filter(l => band(l) === b);
        if (ls.length) { o++; for (const l of ls) lines.push({ ...l, o }); }
      }
      if (b < seps.length) { o++; for (const l of full.filter(l => l.y === seps[b])) lines.push({ ...l, o }); }
    }
  }
  process.stdout.write(JSON.stringify({ p, lines, ...(gutter ? { columns: gutter } : {}) }) + '\n');
}
