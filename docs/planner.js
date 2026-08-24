/* Shared banner (pixel sage + kamehameha charge bar), calendar, and to-do list.
   Used by the local UI (read-write) and the published dashboard (read-only). */
(function () {
"use strict";

const CSS = `
.kb-wrap { margin-bottom: 20px; }
.kb-banner { position: relative; height: 172px; border-radius: 12px; overflow: hidden;
  background: radial-gradient(1200px 320px at 72% 130%, #182a66 0%, #0c1233 55%, #05070f 100%); }
.kb-stars { position: absolute; width: 1px; height: 1px; border-radius: 50%; background: transparent; }
.kb-canvas { position: absolute; left: 26px; bottom: 0; image-rendering: pixelated; }
.kb-word { position: absolute; top: 10px; left: 16px; font: 700 11px ui-monospace, monospace;
  letter-spacing: 4px; color: #8ea2ff; opacity: .85; user-select: none; }
.kb-fired { position: absolute; top: 8px; right: 14px; color: #ffe97a; font: 700 13px ui-monospace, monospace; }
.kb-beam { position: absolute; width: 0; opacity: 0; border-radius: 24px;
  background: linear-gradient(180deg, rgba(120,199,255,0) 0%, #7cc7ff 12%, #eaf8ff 32%, #ffffff 50%, #eaf8ff 68%, #7cc7ff 88%, rgba(120,199,255,0) 100%);
  filter: drop-shadow(0 0 16px #6cc0ff) drop-shadow(0 0 42px #3f8fe8);
  transition: width .45s cubic-bezier(.2,.8,.3,1), opacity .35s; }
.kb-flash { position: absolute; inset: 0; background: #fff; opacity: 0; pointer-events: none; transition: opacity .5s; }
.kb-banner.kb-shake { animation: kbshake .12s linear infinite; }
@keyframes kbshake { 0%{transform:translate(0,0)} 25%{transform:translate(2px,-2px)}
  50%{transform:translate(-2px,1px)} 75%{transform:translate(1px,2px)} 100%{transform:translate(0,0)} }
.kb-chargewrap { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
.kb-charge { flex: 1; height: 14px; border-radius: 8px; background: var(--track);
  border: 1px solid var(--ring); position: relative; overflow: hidden; }
.kb-charge > i { display: block; height: 100%; width: 0;
  background: linear-gradient(90deg, #ffb02e, #ffe97a 60%, #9fdcff);
  box-shadow: 0 0 10px #ffd75e; transition: width .5s ease; }
.kb-charge::after { content: ""; position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(90deg, transparent 0 calc(10% - 2px), var(--page) calc(10% - 2px) 10%); }
.kb-chargelabel { font-size: 12.5px; color: var(--ink-2); white-space: nowrap; font-variant-numeric: tabular-nums; }

.planner-grid { display: grid; grid-template-columns: 1fr 340px; gap: 14px; align-items: start; }
@media (max-width: 820px) { .planner-grid { grid-template-columns: 1fr; } }
.cal, .todo { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 16px; }
.cal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.cal-head b { font-size: 15px; }
.cal-nav { cursor: pointer; border: 1px solid var(--hairline); background: none; border-radius: 6px;
  color: var(--ink); padding: 2px 10px; font: inherit; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cal-dow { font-size: 11px; color: var(--muted); text-align: center; font-weight: 600; padding: 2px 0; }
.cal-cell { min-height: 64px; border: 1px solid var(--hairline); border-radius: 8px; padding: 4px 5px;
  display: flex; flex-direction: column; gap: 2px; overflow: hidden; }
.cal-cell.dim { opacity: .35; }
.cal-cell.today { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.cal-num { font-size: 11px; color: var(--muted); font-weight: 600; }
.cal-ev { border-radius: 4px; padding: 0 4px; font-size: 10.5px; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.cal-ev.exam { background: rgba(208,59,59,.14); color: var(--critical); font-weight: 600; }
.cal-ev.todo { background: rgba(42,120,214,.14); color: var(--accent-deep); }
.cal-ev.gcal { background: rgba(27,175,122,.14); color: var(--good-text); }
.cal-more { font-size: 10px; color: var(--muted); }

.todo { display: flex; flex-direction: column; gap: 8px; }
.todo h3 { font-size: 15px; }
.todo-row { display: flex; gap: 9px; align-items: center; font-size: 14px; }
.todo-row input[type=checkbox] { width: 16px; height: 16px; accent-color: var(--accent); flex: none; }
.todo-row .box { width: 15px; height: 15px; border: 1.5px solid var(--muted); border-radius: 4px; flex: none;
  display: inline-flex; align-items: center; justify-content: center; font-size: 11px; color: var(--good-text); }
.todo-row.done .box { border-color: var(--good-text); }
.todo-row .t { overflow: hidden; text-overflow: ellipsis; }
.todo-row.done .t { color: var(--muted); text-decoration: line-through; }
.todo-row .due { font-size: 11px; color: var(--accent-deep); border: 1px solid var(--hairline);
  border-radius: 999px; padding: 0 7px; white-space: nowrap; margin-left: auto; }
.todo-row .due.late { color: var(--critical); font-weight: 600; }
.todo-row .del { cursor: pointer; border: none; background: none; color: var(--muted); font-size: 13px; flex: none; }
.todo-add { display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
.todo-empty { color: var(--muted); font-size: 13px; }
`;
const style = document.createElement("style");
style.textContent = CSS;
document.head.appendChild(style);

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

/* ---------- pixel sage ---------- */
const SCALE = 6, THRESHOLD = 10;
const COLORS = { W:"#f4efe2", w:"#ddd3ba", S:"#e8b88a", s:"#c99668", G:"#e8c15a", g:"#a8842f", B:"#7a5230", Y:"#ffe97a" };
const SPRITE = [
"..........www.............",
".........wWWWw............",
".........wWSSw............",
".....Y...wSSSS............",
".....B...wSSSs............",
".....B...WWSSW............",
".....B..WWWWW.............",
".....B..WWWW..............",
".....B.GGWWWG.............",
".....B.wwwwwwwSS..........",
".....B.wwwwwwwwwSS........",
".....B.wwwwwwww...SS......",
".....BGwwwwwwwwwwSS.......",
".....B.wwwwwwww...SS......",
".....B.wwwwwwwwwSS........",
".....B.wwwwwwwSS..........",
".....B..wwwwww............",
".....B..wwwwwww...........",
".....B.Gwwwwwwww..........",
".....B.wwwwwwwwww.........",
".....BGwwwwwwwwwww........",
".....Bwwwwwwwwwwwww.......",
"....gGGGGGGGGGGGGGG.......",
"....gggggggggggggg........",
];
const ORB = { x: 20.5, y: 12 };  // sprite coords of the orb between his hands

function drawSprite() {
  const c = document.createElement("canvas");
  const cols = Math.max(...SPRITE.map(r => r.length));
  c.width = cols * SCALE; c.height = SPRITE.length * SCALE;
  const ctx = c.getContext("2d");
  SPRITE.forEach((row, y) => [...row].forEach((ch, x) => {
    if (COLORS[ch]) { ctx.fillStyle = COLORS[ch]; ctx.fillRect(x * SCALE, y * SCALE, SCALE, SCALE); }
  }));
  return c;
}

const Planner = window.Planner = {};
let B = null;  // banner internals

Planner.mountBanner = function (host, state) {
  host.classList.add("kb-wrap");
  host.innerHTML = `
    <div class="kb-banner">
      <span class="kb-word">STUDYTRACK</span>
      <canvas class="kb-canvas"></canvas>
      <div class="kb-beam"></div>
      <div class="kb-flash"></div>
      <span class="kb-fired" title="kamehamehas fired"></span>
    </div>
    <div class="kb-chargewrap">
      <div class="kb-charge"><i></i></div>
      <span class="kb-chargelabel"></span>
    </div>`;
  const banner = host.querySelector(".kb-banner");
  for (let i = 0; i < 70; i++) {
    const s = document.createElement("i");
    s.className = "kb-stars";
    s.style.left = Math.random() * 100 + "%";
    s.style.top = Math.random() * 100 + "%";
    const glow = Math.random() * 1.6 + 0.4;
    s.style.boxShadow = `0 0 ${glow}px ${glow}px rgba(220,230,255,${Math.random() * .6 + .25})`;
    banner.appendChild(s);
  }
  const canvas = host.querySelector(".kb-canvas");
  const sprite = drawSprite();
  canvas.width = sprite.width; canvas.height = sprite.height;
  B = {
    host, banner, canvas, ctx: canvas.getContext("2d"), sprite,
    beam: host.querySelector(".kb-beam"), flash: host.querySelector(".kb-flash"),
    fired: host.querySelector(".kb-fired"), fill: host.querySelector(".kb-charge > i"),
    label: host.querySelector(".kb-chargelabel"),
    state: { done: 0, fired: 0 }, firing: false, t: 0,
  };
  const orbX = 26 + ORB.x * SCALE;
  const orbY = (172 - canvas.height) + ORB.y * SCALE;
  Object.assign(B.beam.style, { left: orbX + 14 + "px", top: orbY - 23 + "px", height: "46px" });
  B.orb = { x: ORB.x * SCALE, y: ORB.y * SCALE };
  (function loop() { B.t += 1; frame(); requestAnimationFrame(loop); })();
  Planner.setCharge(state.done, { animate: false });
};

function frame() {
  const { ctx, canvas, sprite, orb, state, firing, t } = B;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(sprite, 0, 0);
  const charge = firing ? THRESHOLD : state.done % THRESHOLD;
  const pulse = Math.sin(t / 9) * 2;
  const r = firing ? 20 + pulse : (charge ? 4 + (charge / THRESHOLD) * 12 + pulse : 0);
  if (r > 0) {
    const g = ctx.createRadialGradient(orb.x, orb.y, 0, orb.x, orb.y, r);
    g.addColorStop(0, "#ffffff"); g.addColorStop(.45, "#cfeaff");
    g.addColorStop(.8, "rgba(124,199,255,.75)"); g.addColorStop(1, "rgba(124,199,255,0)");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(orb.x, orb.y, r, 0, 7); ctx.fill();
    for (let i = 0; i < 3; i++) {  // converging sparkles
      const a = Math.random() * 6.28, d = 16 + Math.random() * 26;
      const p = (t % 20) / 20;
      ctx.fillStyle = "rgba(255,233,122," + (0.9 - p * 0.7) + ")";
      ctx.fillRect(orb.x + Math.cos(a) * d * (1 - p), orb.y + Math.sin(a) * d * (1 - p), 2, 2);
    }
  }
}

Planner.setCharge = function (done, opts) {
  const prev = B.state;
  const next = { done, fired: Math.floor(done / THRESHOLD) };
  B.state = next;
  const apply = () => {
    B.fill.style.width = (next.done % THRESHOLD) * (100 / THRESHOLD) + "%";
    B.label.textContent = `${next.done % THRESHOLD}/${THRESHOLD} tasks charged`;
    B.fired.textContent = "⚡ ×" + next.fired;
  };
  if ((opts || {}).animate && next.fired > prev.fired) {
    B.fill.style.width = "100%";
    B.label.textContent = `${THRESHOLD}/${THRESHOLD} — FULL POWER`;
    setTimeout(() => Planner.fire(apply), 450);
  } else apply();
};

Planner.fire = function (after) {
  if (B.firing) { if (after) after(); return; }
  B.firing = true;
  const bannerW = B.banner.clientWidth;
  const beamLeft = parseFloat(B.beam.style.left);
  B.banner.classList.add("kb-shake");
  B.flash.style.transition = "none"; B.flash.style.opacity = ".85";
  requestAnimationFrame(() => { B.flash.style.transition = "opacity .5s"; B.flash.style.opacity = "0"; });
  B.beam.style.opacity = "1";
  B.beam.style.width = Math.max(0, bannerW - beamLeft) + "px";
  setTimeout(() => { B.beam.style.opacity = "0"; B.banner.classList.remove("kb-shake"); }, 1400);
  setTimeout(() => { B.beam.style.width = "0"; B.firing = false; if (after) after(); }, 1800);
};

/* ---------- calendar ---------- */
const fmt = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");

Planner.mountCalendar = function (host, events) {
  if (!host._m) { const n = new Date(); host._m = { y: n.getFullYear(), m: n.getMonth() }; }
  host._events = events;
  const { y, m } = host._m;
  const byDate = {};
  events.forEach(e => (byDate[e.date] = byDate[e.date] || []).push(e));
  const first = new Date(y, m, 1);
  const today = fmt(new Date());
  const monthName = first.toLocaleString("en", { month: "long", year: "numeric" });
  let cells = "";
  const start = new Date(y, m, 1 - first.getDay());
  for (let i = 0; i < 42; i++) {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
    const iso = fmt(d);
    const evs = byDate[iso] || [];
    const shown = evs.slice(0, 2).map(e =>
      `<span class="cal-ev ${e.type}" title="${esc(e.label)}">${esc(e.label)}</span>`).join("");
    const more = evs.length > 2 ? `<span class="cal-more">+${evs.length - 2} more</span>` : "";
    cells += `<div class="cal-cell ${d.getMonth() !== m ? "dim" : ""} ${iso === today ? "today" : ""}">
      <span class="cal-num">${d.getDate()}</span>${shown}${more}</div>`;
  }
  host.innerHTML = `<div class="cal">
    <div class="cal-head">
      <button class="cal-nav" data-nav="-1">‹</button><b>${esc(monthName)}</b><button class="cal-nav" data-nav="1">›</button>
    </div>
    <div class="cal-grid">
      ${["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map(d => `<span class="cal-dow">${d}</span>`).join("")}
      ${cells}
    </div></div>`;
  host.querySelectorAll("[data-nav]").forEach(b => b.onclick = () => {
    const d = new Date(host._m.y, host._m.m + parseInt(b.dataset.nav), 1);
    host._m = { y: d.getFullYear(), m: d.getMonth() };
    Planner.mountCalendar(host, host._events);
  });
};

/* ---------- to-do list ---------- */
Planner.mountTodos = function (host, opts) {
  const { items, readonly, onAdd, onToggle, onDelete } = opts;
  const today = fmt(new Date());
  const sorted = [...items].sort((a, b) => (a.done - b.done) || String(a.due || "9999").localeCompare(String(b.due || "9999")));
  const rows = sorted.map(t => {
    const late = t.due && !t.done && t.due < today;
    const check = readonly
      ? `<span class="box">${t.done ? "✓" : ""}</span>`
      : `<input type="checkbox" data-id="${t.id}" ${t.done ? "checked" : ""}>`;
    return `<div class="todo-row ${t.done ? "done" : ""}">${check}
      <span class="t">${esc(t.title)}</span>
      ${t.due ? `<span class="due ${late ? "late" : ""}">${esc(t.due)}</span>` : ""}
      ${readonly ? "" : `<button class="del" data-del="${t.id}" title="delete">✕</button>`}</div>`;
  }).join("");
  host.innerHTML = `<div class="todo">
    <h3>To-do list</h3>
    ${rows || '<div class="todo-empty">Nothing here — add a task and start charging.</div>'}
    ${readonly ? "" : `<div class="todo-add">
      <input data-new-title placeholder="New task" style="flex:1;min-width:140px">
      <input data-new-due type="date">
      <button class="btn primary" data-add>Add</button></div>`}
  </div>`;
  if (readonly) return;
  host.querySelectorAll("input[type=checkbox]").forEach(cb => cb.onchange = () =>
    onToggle(parseInt(cb.dataset.id), cb.checked));
  host.querySelectorAll("[data-del]").forEach(b => b.onclick = () => onDelete(parseInt(b.dataset.del)));
  const add = () => {
    const title = host.querySelector("[data-new-title]").value.trim();
    if (title) onAdd(title, host.querySelector("[data-new-due]").value || null);
  };
  host.querySelector("[data-add]").onclick = add;
  host.querySelector("[data-new-title]").onkeydown = e => { if (e.key === "Enter") add(); };
};

Planner.THRESHOLD = THRESHOLD;
})();
