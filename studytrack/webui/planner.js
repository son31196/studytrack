/* Shared calendar and to-do list.
   Used by the local UI (read-write) and the published dashboard (read-only). */
(function () {
"use strict";

const CSS = `
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
const fmt = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");

const Planner = window.Planner = {};

/* ---------- calendar ---------- */
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
    ${rows || '<div class="todo-empty">Nothing here yet — add a task.</div>'}
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
})();
