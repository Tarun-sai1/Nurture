/* Nurture — front end. Plain JS, no framework: one small file, instant page switches.
   State lives in the URL hash (#/doctor?day=…&v=…&tab=…) so refresh and back/forward work. */
"use strict";

const $app = document.getElementById("app");
const $bar = document.getElementById("bar");

/* ------------------------------------------------------------------ API + cache */
const cache = new Map();
let inflight = 0;
function loading(on) {
  inflight += on ? 1 : -1;
  $bar.style.width = inflight > 0 ? "70%" : "100%";
  if (inflight <= 0) setTimeout(() => { if (inflight <= 0) $bar.style.width = "0"; }, 200);
}
async function api(path, body) {
  if (!body && cache.has(path)) return cache.get(path);
  const p = (async () => {
    loading(true);
    try {
      const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
      return await res.json();
    } finally { loading(false); }
  })();
  if (!body) { cache.set(path, p); p.catch(() => cache.delete(path)); }
  return p;
}
function invalidate(fragment) { for (const k of [...cache.keys()]) if (k.includes(fragment)) cache.delete(k); }
function prefetch(paths) {
  const run = () => { const p = paths.shift(); if (!p) return; if (!cache.has(p)) api(p).finally(() => setTimeout(run, 30)); else run(); };
  (window.requestIdleCallback || setTimeout)(run);
}

/* ------------------------------------------------------------------ helpers */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const D = (iso) => new Date(iso + "T00:00:00");
const fmt = (iso, o = { day: "numeric", month: "short", year: "numeric" }) => iso ? D(iso).toLocaleDateString("en-GB", o) : "—";
const fmtDay = (iso) => fmt(iso, { weekday: "short", day: "numeric", month: "short", year: "numeric" });
const pct = (p) => `${Math.round(p * 100)}%`;
const SEV = { High: "critical", Moderate: "warn", Low: "good" };
const sevClass = (s) => ({ critical: "critical", serious: "serious", warning: "warn", warn: "warn", good: "good" }[String(s).toLowerCase()] || "neutral");
function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2600);
}
function table(cols, rows, { rowClass } = {}) {
  if (!rows.length) return `<p class="muted">Nothing recorded.</p>`;
  return `<div class="table-wrap"><table><thead><tr>${cols.map((c) => `<th class="${c.num ? "num" : ""}">${esc(c.h)}</th>`).join("")}</tr></thead><tbody>${rows
    .map((r) => `<tr class="${rowClass ? rowClass(r) : ""}">${cols.map((c) => `<td class="${c.num ? "num" : ""}">${c.html ? c.html(r) : esc(c.f ? c.f(r) : r[c.k])}</td>`).join("")}</tr>`)
    .join("")}</tbody></table></div>`;
}
const pill = (text, cls) => `<span class="pill ${cls}">${esc(text)}</span>`;
const statusPill = (abn) => abn ? pill("Needs review", "serious") : pill("Normal", "good");

const ICON = {
  check: `<svg viewBox="0 0 14 14" fill="none"><path d="M2.5 7.5l3 3 6-7" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  arrow: `<svg viewBox="0 0 28 12" fill="none"><path d="M0 6h26M21 1l5 5-5 5" stroke="currentColor" stroke-width="1.6"/></svg>`,
  alert: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.5"/></svg>`,
  ok: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></svg>`,
  info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></svg>`,
  mother: `<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="15" cy="7" r="4"/><path d="M10 31v-9c0-4 2-9 6-9 3 0 5 2 5 5 3 1 5 3 5 6s-3 5-7 5h-4v2"/></svg>`,
  steth: `<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8 4v8a6 6 0 0012 0V4"/><path d="M14 18v4a7 7 0 0014 0v-3"/><circle cx="28" cy="16" r="3"/></svg>`,
  bowl: `<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 16h26a13 13 0 01-26 0z"/><path d="M12 12c0-3 2-3 2-6M18 12c0-3 2-3 2-6"/></svg>`,
};
const checkItem = (t) => `<li><span class="check">${ICON.check}</span>${esc(t)}</li>`;
function notice(cls, title, body, icon) {
  const ic = icon || (cls === "good" ? ICON.ok : cls === "plum" ? ICON.info : ICON.alert);
  return `<div class="notice ${cls}">${ic}<div><span class="t">${esc(title)}</span>${body ? `<p>${body}</p>` : ""}</div></div>`;
}

/* ------------------------------------------------------------------ the 40-week arc */
function arc(ga, { dark = false, label = true } = {}) {
  const W = 400, H = 232, cx = 200, cy = 212, R = 172, SW = 20;
  const ang = (w) => Math.PI - (Math.min(Math.max(w, 0), 40) / 40) * Math.PI;
  const pt = (w, r = R) => [cx + r * Math.cos(ang(w)), cy - r * Math.sin(ang(w))];
  const path = (a, b, r = R) => { const [x1, y1] = pt(a, r), [x2, y2] = pt(b, r); return `M${x1.toFixed(1)} ${y1.toFixed(1)} A${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`; };
  const c = dark
    ? { track: "rgba(255,255,255,.16)", done: "#F6DCE7", text: "#fff", sub: "#F0CADB", tick: "rgba(255,255,255,.55)" }
    : { track: "#E6D4C4", done: "#7A1E4E", text: "#2B1D22", sub: "#5A4A50", tick: "#8A797F" };
  const tri = [[0, 13], [13, 28], [28, 40]];
  const seg = tri.map(([a, b]) => `<path d="${path(a + 0.25, b - 0.25)}" stroke="${c.track}" stroke-width="${SW}" fill="none" stroke-linecap="butt"/>`).join("");
  const done = ga > 0 ? `<path d="${path(0.25, Math.min(ga, 40))}" stroke="${c.done}" stroke-width="${SW}" fill="none" stroke-linecap="round"/>` : "";
  const [mx, my] = pt(ga);
  const ticks = [0, 13, 28, 40].map((w) => { const [x, y] = pt(w, R + 30); return `<text x="${x.toFixed(0)}" y="${(y + 4).toFixed(0)}" text-anchor="middle" font-size="13" fill="${c.tick}" font-family="Figtree, sans-serif">${w}</text>`; }).join("");
  const wk = Math.floor(ga), dd = Math.round((ga - wk) * 7);
  const center = label
    ? `<text x="${cx}" y="${cy - 52}" text-anchor="middle" font-family="Fraunces, Georgia, serif" font-size="58" fill="${c.text}">${wk}<tspan font-size="26">w</tspan> ${dd}<tspan font-size="26">d</tspan></text>
       <text x="${cx}" y="${cy - 18}" text-anchor="middle" font-size="15" fill="${c.sub}" font-family="Figtree, sans-serif">${ga >= 40 ? "Due now" : (() => { const n = Math.max(1, Math.ceil(40 - ga)); return `${n} week${n === 1 ? "" : "s"} to go`; })()}</text>`
    : "";
  return `<svg viewBox="-24 -24 ${W + 48} ${H + 30}" role="img" aria-label="${wk} weeks ${dd} days of 40">${seg}${done}${ticks}
    <circle cx="${mx.toFixed(1)}" cy="${my.toFixed(1)}" r="15" fill="#EE5A4F" stroke="${dark ? "#7A1E4E" : "#EFE2D6"}" stroke-width="5"/>${center}</svg>`;
}

/* ------------------------------------------------------------------ charts (SVG, no library) */
const charts = new Map();
let chartSeq = 0;
const CH = { plum: "#7A1E4E", coral: "#E0483D", teal: "#2A8577" };
function lineChart({ title, series, refs = [], band = null, unit = "", xLabel = "week", height = 230, yMin, yMax, fmtY = (v) => v }) {
  const id = `c${++chartSeq}`;
  const W = 640, H = height, L = 44, Rr = 14, T = 14, B = 30;
  const pts = series.flatMap((s) => s.points);
  if (!pts.length) return "";
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]).concat(refs.map((r) => r.y));
  if (band) ys.push(...band.lo.map((p) => p[1]), ...band.hi.map((p) => p[1]));
  let x0 = Math.min(...xs), x1 = Math.max(...xs); if (x0 === x1) { x0 -= 1; x1 += 1; }
  let y0 = yMin ?? Math.min(...ys), y1 = yMax ?? Math.max(...ys); const pad = (y1 - y0) * 0.12 || 1; y0 = yMin ?? y0 - pad; y1 = yMax ?? y1 + pad;
  const sx = (x) => L + ((x - x0) / (x1 - x0)) * (W - L - Rr), sy = (y) => T + (1 - (y - y0) / (y1 - y0)) * (H - T - B);
  const nice = (a, b, n) => { const st = Math.pow(10, Math.floor(Math.log10((b - a) / n))); const m = [1, 2, 5, 10].find((k) => (b - a) / (st * k) <= n) * st; const out = []; for (let v = Math.ceil(a / m) * m; v <= b + 1e-9; v += m) out.push(+v.toFixed(6)); return out; };
  const grid = nice(y0, y1, 4).map((v) => `<line x1="${L}" x2="${W - Rr}" y1="${sy(v)}" y2="${sy(v)}" stroke="#EFE5DC"/><text x="${L - 8}" y="${sy(v) + 4}" text-anchor="end" font-size="12" fill="#8A797F">${fmtY(v)}</text>`).join("");
  const xt = nice(x0, x1, 6).map((v) => `<text x="${sx(v)}" y="${H - 8}" text-anchor="middle" font-size="12" fill="#8A797F">${v}</text>`).join("");
  const bandPath = band ? `<path d="M${band.hi.map((p) => `${sx(p[0])},${sy(p[1])}`).join("L")}L${band.lo.slice().reverse().map((p) => `${sx(p[0])},${sy(p[1])}`).join("L")}Z" fill="rgba(42,133,119,.14)"/>` : "";
  const refL = refs.map((r) => `<line x1="${L}" x2="${W - Rr}" y1="${sy(r.y)}" y2="${sy(r.y)}" stroke="#8A797F" stroke-dasharray="5 5"/><text x="${W - Rr}" y="${sy(r.y) - 6}" text-anchor="end" font-size="12" fill="#5A4A50">${esc(r.label)}</text>`).join("");
  const lines = series.map((s) => `<path d="M${s.points.map((p) => `${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("L")}" fill="none" stroke="${s.color}" stroke-width="2.2" stroke-linejoin="round"/>` +
    s.points.map((p) => `<circle cx="${sx(p[0]).toFixed(1)}" cy="${sy(p[1]).toFixed(1)}" r="4.5" fill="${s.color}" stroke="#FFFDF9" stroke-width="2"/>`).join("")).join("");
  charts.set(id, { series, sx, sy, W, unit, xLabel });
  const legend = series.length > 1 || band ? `<div class="legend-c">${series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join("")}${band ? `<span><i style="background:rgba(42,133,119,.35);height:8px"></i>${esc(band.label)}</span>` : ""}</div>` : "";
  return `<div class="chart" data-chart="${id}"><h4>${esc(title)}</h4>${legend}
    <svg viewBox="0 0 ${W} ${H}" aria-label="${esc(title)} chart">${grid}${xt}${bandPath}${refL}${lines}<line class="xh" y1="${T}" y2="${H - B}" stroke="#2B1D22" stroke-opacity=".25" visibility="hidden"/></svg>
    <div class="tip"></div></div>`;
}
function initCharts(root) {
  root.querySelectorAll("[data-chart]").forEach((el) => {
    const spec = charts.get(el.dataset.chart); if (!spec) return;
    const svg = el.querySelector("svg"), tip = el.querySelector(".tip"), xh = svg.querySelector(".xh");
    const xsAll = [...new Set(spec.series.flatMap((s) => s.points.map((p) => p[0])))].sort((a, b) => a - b);
    svg.addEventListener("mousemove", (e) => {
      const r = svg.getBoundingClientRect(); const mx = ((e.clientX - r.left) / r.width) * spec.W;
      let best = xsAll[0]; for (const x of xsAll) if (Math.abs(spec.sx(x) - mx) < Math.abs(spec.sx(best) - mx)) best = x;
      const rows = spec.series.map((s) => { const p = s.points.find((q) => q[0] === best); return p ? `${esc(s.name)}: <b>${p[2] ?? p[1]}${spec.unit}</b>` : ""; }).filter(Boolean);
      xh.setAttribute("x1", spec.sx(best)); xh.setAttribute("x2", spec.sx(best)); xh.setAttribute("visibility", "visible");
      tip.innerHTML = `${spec.xLabel === "date" ? "" : "Week " + (+best).toFixed(1) + "<br>"}${rows.join("<br>")}`;
      tip.style.left = `${(spec.sx(best) / spec.W) * r.width + 16}px`; tip.style.top = `${e.clientY - r.top + 40}px`; tip.classList.add("show");
    });
    svg.addEventListener("mouseleave", () => { tip.classList.remove("show"); xh.setAttribute("visibility", "hidden"); });
  });
}
function bars(items, { max, fmtV = (v) => v.toFixed(3), color = CH.plum } = {}) {
  const m = max ?? Math.max(...items.map((i) => Math.abs(i.value)), 1e-9);
  return `<div class="stack" style="--g:8px">${items.map((i) => `<div><div class="row small" style="justify-content:space-between"><span>${esc(i.label)}</span><span class="muted">${fmtV(i.value)}</span></div>
    <div style="height:8px;background:var(--cream);border-radius:9px"><div style="height:8px;width:${Math.max(2, (Math.abs(i.value) / m) * 100)}%;background:${i.color || color};border-radius:9px"></div></div></div>`).join("")}</div>`;
}
function weightBand(lo, hi) {
  const L = [], H = [];
  for (let w = 4; w <= 40; w += 1) {
    L.push([w, w <= 13 ? 0.5 * w / 13 : 0.5 + (lo - 0.5) * (w - 13) / 27]);
    H.push([w, w <= 13 ? 2 * w / 13 : 2 + (hi - 2) * (w - 13) / 27]);
  }
  return { lo: L, hi: H, label: "Recommended gain" };
}
function weightChart(r) {
  const v = r.visits, w0 = v[0].weight;
  return lineChart({ title: "Weight gained since booking", unit: " kg", series: [{ name: "Weight gain", color: CH.plum, points: v.map((x) => [+x.ga.toFixed(1), +(x.weight - w0).toFixed(1)]) }], band: weightBand(r.weight.lo, r.weight.hi) });
}

/* ------------------------------------------------------------------ router */
function route() {
  const h = location.hash.slice(1) || "/";
  const [path, q] = h.split("?");
  return { view: path.split("/").filter(Boolean)[0] || "home", params: Object.fromEntries(new URLSearchParams(q || "")) };
}
function href(view, params = {}) {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")).toString();
  return `#/${view}${q ? "?" + q : ""}`;
}
function setParams(upd, replace = false) {
  const r = route(); const h = href(r.view, { ...r.params, ...upd });
  if (replace) { history.replaceState(null, "", h); render(); } else location.hash = h;
}
let renderToken = 0;
let meta = null;
async function render() {
  const token = ++renderToken;
  const { view, params } = route();
  document.querySelectorAll("[data-nav]").forEach((a) => a.toggleAttribute("aria-current", a.dataset.nav === view) || a.setAttribute("aria-current", a.dataset.nav === view ? "page" : ""));
  document.querySelectorAll("[data-nav]").forEach((a) => { if (a.dataset.nav !== view) a.removeAttribute("aria-current"); });
  try {
    meta = meta || (await api("/api/meta"));
    const views = { home: viewHome, patient: viewPatient, doctor: viewDoctor, dietician: viewDietician };
    const html = await (views[view] || viewHome)(params);
    if (token !== renderToken) return;           // a newer click won the race
    const y = window.scrollY, same = $app.dataset.view === view;
    $app.innerHTML = html; $app.dataset.view = view;
    charts.forEach((_, k) => { if (!$app.querySelector(`[data-chart="${k}"]`)) charts.delete(k); });
    initCharts($app);
    (afterRender[view] || (() => {}))(params);
    if (!same) window.scrollTo(0, 0); else window.scrollTo(0, y);
  } catch (e) {
    if (token !== renderToken) return;
    $app.innerHTML = `<div class="page">${notice("critical", "This page could not load", esc(e.message) + ". Check that the server window is still running, then reload.")}</div>`;
  }
}
const afterRender = {};
window.addEventListener("hashchange", render);

/* ------------------------------------------------------------------ home */
async function viewHome() {
  return `
  <section class="hero">
    <div class="hero-copy">
      <h1>Care that follows every week of pregnancy.</h1>
      <ul class="checklist">
        ${["Reports, medicines and diet in one place", "Risks flagged early and confirmed by a doctor", "Visits booked to match the stage of pregnancy", "Built on Indian antenatal guidance (MoHFW, ICMR-NIN)"].map(checkItem).join("")}
      </ul>
      <div class="row">
        <a class="btn btn-primary" href="#/patient">Open my pregnancy</a>
        <a class="btn btn-light" href="#/doctor">Go to today's clinic</a>
      </div>
    </div>
    <div class="hero-art"><div><div class="arc-wrap">${arc(28.4, { dark: true })}</div>
      <div class="arc-caption">First, second and third trimester — tracked visit by visit.</div></div></div>
  </section>
  <section class="roles">
    <div><h2>One record, three ways to see it.</h2><p class="muted" style="margin-top:14px;max-width:44ch">Each person sees what they need for the visit in front of them. Everything is built from the same six linked datasets.</p></div>
    <div class="rowlist">
      <a class="rowlink" href="#/patient"><span class="icon">${ICON.mother}</span><span class="label">I'm expecting<span class="sub">My reports, medicines, diet and appointments</span></span><span class="arrow">${ICON.arrow}</span></a>
      <a class="rowlink" href="#/doctor"><span class="icon">${ICON.steth}</span><span class="label">I'm the doctor<span class="sub">Today's clinic, alerts, risk review and prescribing checks</span></span><span class="arrow">${ICON.arrow}</span></a>
      <a class="rowlink" href="#/dietician"><span class="icon">${ICON.bowl}</span><span class="label">I'm the dietician<span class="sub">Nutrition worklist and diet plans to approve</span></span><span class="arrow">${ICON.arrow}</span></a>
    </div>
  </section>`;
}

/* ================================================================== PATIENT */
async function viewPatient(p) {
  const preg = p.preg || "PRG0029";
  const visits = await api(`/api/visits/${preg}`);
  const vid = p.v || visits[visits.length - 1].visit_id;
  const r = await api(`/api/record/${preg}/${vid}`);
  const tab = p.tab || "reports";
  const v = r.visit, ap = r.appointments;
  const upcoming = ap.list.filter((a) => a.status === "Booked" && a.date >= ap.today).sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time))[0];
  const tabs = [["reports", "Reports"], ["medicines", "Medicines"], ["diet", "Diet"], ["journey", "Pregnancy journey"], ["appointments", "Appointments"]];
  const body = { reports: patientReports, medicines: patientMeds, diet: patientDiet, journey: patientJourney, appointments: patientAppointments }[tab](r, p);
  // warm the neighbouring visits so the "as of" switcher is instant
  prefetch(visits.slice(-4).map((x) => `/api/record/${preg}/${x.visit_id}`));
  return `
  <section class="pt-hero"><div class="pt-hero-inner">
    <div class="arc-wrap">${arc(v.ga)}</div>
    <div>
      <div class="demo-bar">
        <label>Viewing as <select data-act="pt-preg">${meta.patients.map((x) => `<option value="${x.pregnancy_id}" ${x.pregnancy_id === preg ? "selected" : ""}>${x.patient_id}</option>`).join("")}</select></label>
        <label>on <select data-act="pt-visit">${visits.slice().reverse().map((x) => `<option value="${x.visit_id}" ${x.visit_id === vid ? "selected" : ""}>${fmt(x.date)} (week ${x.ga_w})</option>`).join("")}</select></label>
      </div>
      <h1 style="margin-top:14px">Week ${v.ga_w} of your pregnancy</h1>
      <div class="facts">
        <div class="fact"><div class="k">Due date</div><div class="v">${fmt(r.patient.edd)}</div></div>
        <div class="fact"><div class="k">Trimester</div><div class="v">${esc(v.trimester)}</div></div>
        <div class="fact"><div class="k">Next appointment</div><div class="v">${upcoming ? `${fmt(upcoming.date, { day: "numeric", month: "short" })}, ${upcoming.time}` : "Not booked"}</div></div>
      </div>
      ${r.review.patient_text ? notice(r.review.confirmed.overall.band === "High" ? "warn" : "plum", "From your doctor", `${esc(r.review.patient_text)} <span class="muted">Reviewed ${fmt(r.review.confirmed.overall.date)}.</span>`) :
        (!upcoming ? `<a class="btn btn-primary btn-sm" href="${href("patient", { ...p, preg, v: vid, tab: "appointments" })}">Book your next visit</a>` : "")}
    </div>
  </div></section>
  <div class="page">
    <nav class="tabs" role="tablist">${tabs.map(([k, l]) => `<a role="tab" href="${href("patient", { preg, v: vid, tab: k })}" aria-selected="${k === tab}">${l}</a>`).join("")}</nav>
    ${body}
  </div>`;
}
afterRender.patient = (p) => {
  $app.querySelector('[data-act="pt-preg"]')?.addEventListener("change", (e) => setParams({ preg: e.target.value, v: "", d: "", test: "" }));
  $app.querySelector('[data-act="pt-visit"]')?.addEventListener("change", (e) => setParams({ v: e.target.value, d: "" }));
  if ((p.tab || "reports") === "appointments") bindBooking(p);
  $app.querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", () => setParams({ mode: b.dataset.mode }, true)));
  $app.querySelectorAll("[data-date]").forEach((b) => b.addEventListener("click", () => setParams({ d: b.dataset.date }, true)));
  $app.querySelector('[data-act="test"]')?.addEventListener("change", (e) => setParams({ test: e.target.value }, true));
  $app.querySelectorAll("[data-assess]").forEach((b) => b.addEventListener("click", () => setParams({ a: b.dataset.assess }, true)));
};

function patientReports(r, p) {
  const mode = p.mode || "date";
  const labs = r.labs;
  const seg = `<div class="seg" role="group"><button data-mode="date" aria-pressed="${mode === "date"}">By date</button><button data-mode="test" aria-pressed="${mode === "test"}">By test</button></div>`;
  if (!labs.length) return seg + `<p class="muted" style="margin-top:20px">No reports yet. They appear here after your first blood or urine test.</p>`;
  if (mode === "date") {
    const dates = [...new Set(labs.map((l) => l.date))].sort().reverse();
    const d = p.d && dates.includes(p.d) ? p.d : dates[0];
    const rows = labs.filter((l) => l.date === d);
    const nAbn = rows.filter((l) => l.abnormal).length;
    return `<div class="stack">${seg}
      <div class="chips">${dates.map((x) => `<button class="chip" data-date="${x}" aria-pressed="${x === d}">${labs.some((l) => l.date === x && l.abnormal) ? '<span class="dot" aria-label="has results to review"></span>' : ""}${fmt(x)}</button>`).join("")}</div>
      <div class="section-title"><h3>Results from ${fmt(d)}</h3><span class="muted small">${rows.length} tests${nAbn ? `, ${nAbn} for your doctor to review` : ", all normal"}</span></div>
      ${table([{ h: "Test", k: "test_label" }, { h: "Result", f: (x) => `${x.result} ${x.unit || ""}` }, { h: "Normal range", k: "ref" }, { h: "Status", html: (x) => statusPill(x.abnormal) }, { h: "Why it was done", k: "reason" }], rows, { rowClass: (x) => (x.abnormal ? "abn" : "") })}
    </div>`;
  }
  const tests = [...new Set(labs.map((l) => l.test))].sort();
  const t = p.test && tests.includes(p.test) ? p.test : tests.includes("Haemoglobin") ? "Haemoglobin" : tests[0];
  const rows = labs.filter((l) => l.test === t);
  const num = rows.filter((l) => l.num !== null);
  const refs = t === "Haemoglobin" ? [{ y: 11, label: "11 g/dL — below this is anaemia" }] : [];
  return `<div class="stack">${seg}
    <label class="field" style="max-width:360px">Test<select class="input" data-act="test">${tests.map((x) => `<option value="${x}" ${x === t ? "selected" : ""}>${esc(x.replaceAll("_", " "))}</option>`).join("")}</select></label>
    ${num.length >= 2 ? lineChart({ title: `${t.replaceAll("_", " ")} over your pregnancy`, unit: ` ${num[0].unit}`, series: [{ name: t.replaceAll("_", " "), color: CH.plum, points: num.map((x) => [x.ga_w, x.num]) }], refs }) : ""}
    ${table([{ h: "Date", f: (x) => fmt(x.date) }, { h: "Week", k: "ga_w", num: true }, { h: "Result", f: (x) => `${x.result} ${x.unit || ""}` }, { h: "Normal range", k: "ref" }, { h: "Status", html: (x) => statusPill(x.abnormal) }], rows.slice().reverse(), { rowClass: (x) => (x.abnormal ? "abn" : "") })}
  </div>`;
}

function patientMeds(r) {
  const meds = r.meds_active;
  return `<div class="grid-2">
    <div><div class="section-title"><h3>Medicines you take now</h3></div>
      ${meds.length ? `<div class="medlist">${meds.map((m) => `<article class="med"><h3>${esc(m.name)}</h3><dl>
        <dt>Why</dt><dd>${esc(m.indication)}</dd><dt>How</dt><dd>${esc(m.regimen)} (${esc(m.route)})</dd><dt>Since</dt><dd>${fmt(m.started)}, week ${m.ga_w}</dd></dl>
        <p class="small muted" style="margin:10px 0 0">Possible side effects: ${esc(m.common_ae)}. Tell your doctor straight away about: ${esc(m.serious_ae)}.</p></article>`).join("")}</div>` : `<p class="muted">No medicines on record.</p>`}
    </div>
    <div><div class="section-title"><h3>Medicine history</h3></div>
      ${table([{ h: "Date", f: (x) => fmt(x.date) }, { h: "Week", k: "ga_w", num: true }, { h: "Medicine", k: "name" }, { h: "What happened", k: "action" }], r.meds_history.slice().reverse())}
    </div></div>`;
}

function dietNoteFor(r, visitId) {
  const plans = r.notes.filter((n) => n.kind === "diet_plan");
  return plans.find((n) => n.visit_id === visitId) || plans[0];
}
function patientDiet(r, p) {
  const A = r.nutrition.assessments;
  if (!A.length) return `<p class="muted">Your first diet assessment happens at a check-up.</p>`;
  const a = A.find((x) => x.visit_id === p.a) || A[A.length - 1];
  const note = dietNoteFor(r, a.visit_id);
  const groups = {};
  r.nutrition.foods.forEach((f) => (groups[f.context] ||= []).push(f.food));
  return `<div class="stack">
    <div class="chips">${A.slice().reverse().map((x) => `<button class="chip" data-assess="${x.visit_id}" aria-pressed="${x.visit_id === a.visit_id}">${fmt(x.date)}</button>`).join("")}</div>
    ${note ? notice("good", "Your dietician's plan", esc(note.text)) : ""}
    <div class="grid-2">
      <div class="panel"><h3>Your plan this month</h3>
        <p class="muted" style="margin-top:6px">Diet type: ${esc(a.pattern)}${a.food_allergy ? `. Food allergy: ${esc(a.food_allergy)}` : ""}.</p>
        ${a.focus.length ? `<p style="margin-bottom:6px">Focus on</p><div>${a.focus.map((f) => `<span class="tag">${esc(f)}</span>`).join("")}</div>` : ""}
        ${a.tips.length ? `<h3 style="margin:18px 0 8px;font-size:1.1rem">Tips for your medicines and meals</h3><ul style="padding-left:20px;margin:0">${a.tips.map((t) => `<li style="margin-bottom:8px">${esc(t.text)}</li>`).join("")}</ul>` : ""}
      </div>
      <div class="panel"><h3>Foods recommended for you</h3>
        <p class="muted small" style="margin-top:4px">${r.nutrition.foods_date ? `List from your diet review on ${fmt(r.nutrition.foods_date)}, filtered for your diet type and allergies.` : ""}</p>
        ${Object.entries(groups).map(([k, fs]) => `<p style="margin:14px 0 6px;font-weight:600">${esc(k)}</p><div>${[...new Set(fs)].map((f) => `<span class="tag">${esc(f)}</span>`).join("")}</div>`).join("") || `<p class="muted">No food list yet.</p>`}
      </div>
    </div></div>`;
}

function patientJourney(r) {
  return `<div class="grid-2">
    <div class="panel"><h3 style="margin-bottom:18px">Milestones</h3>
      <ol class="timeline">${r.milestones.map((m) => `<li class="${m.status === "Done" ? "done" : m.status === "Now" ? "now" : ""}"><div class="w">${esc(m.window)}${m.status === "Now" ? " · now" : ""}</div>${esc(m.text)}</li>`).join("")}</ol>
    </div>
    <div class="stack">${weightChart(r)}
      <p class="small muted">Pre-pregnancy BMI ${r.patient.bmi} (${r.weight.category}): recommended total gain ${r.weight.lo}–${r.weight.hi} kg. You have gained ${r.weight.gain} kg so far.</p>
      ${table([{ h: "Date", f: (x) => fmt(x.date) }, { h: "Week", k: "ga_w", num: true }, { h: "BP", f: (x) => `${x.sbp}/${x.dbp}` }, { h: "Weight", f: (x) => `${x.weight} kg` }, { h: "Visit", k: "type" }], r.visits.slice().reverse())}
    </div></div>`;
}

/* ---- appointments */
const bookingState = { day: null, slot: null, danger: new Set() };
function patientAppointments(r) {
  const ap = r.appointments;
  const [lo, ideal, hi] = ap.window;
  const every = ap.interval_days / 7;
  const mine = ap.list;
  return `<div class="grid-2">
    <div class="stack">
      <div><h3>Are you having any of these right now?</h3><p class="muted small" style="margin-top:4px">Tick any that apply.</p></div>
      <div class="danger-grid">${ap.danger_signs.map((d, i) => `<label class="check-row"><input type="checkbox" data-danger="${i}" ${bookingState.danger.has(d) ? "checked" : ""}>${esc(d)}</label>`).join("")}</div>
      <div id="urgent"></div>
    </div>
    <div class="stack">
      ${notice("plum", `Your next visit: ${fmt(lo, { day: "numeric", month: "short" })} – ${fmt(hi)}`, `Ideally on <b>${fmtDay(ideal)}</b>. At week ${r.visit.ga_w} with ${ap.risk_used.toLowerCase()} risk you should be seen every ${every === 1 ? "week" : every + " weeks"}.`)}
      <div class="panel stack" id="book">
        <h3>Book an appointment</h3>
        <div class="grid-2" style="gap:14px">
          <label class="field">Type of visit<select class="input" data-act="vtype">${ap.types.map((t) => `<option>${esc(t)}</option>`).join("")}</select></label>
          <label class="field">Date<input class="input" type="date" data-act="day" min="${ap.today}" max="${addDays(ap.today, 60)}" value="${bookingState.day || (ideal < ap.today ? ap.today : ideal)}"></label>
        </div>
        <div id="slots" class="stack"></div>
        <label class="field">Anything the doctor should know? (optional)<input class="input" data-act="reason" maxlength="200"></label>
        <div class="row"><button class="btn btn-primary" data-act="book">Book appointment</button><span id="book-msg" class="small"></span></div>
      </div>
      <div><h3 style="margin-bottom:10px">My appointments</h3>
        ${mine.length ? `<div class="rowlist">${mine.map((a) => `<div class="rowlink compact" style="cursor:default"><span class="label">${fmtDay(a.date)}, ${a.time}<span class="sub">${esc(a.type)}${a.reason ? " — " + esc(a.reason) : ""}</span></span>
          <span class="spacer"></span>${a.status === "Booked" && a.date >= ap.today ? `<button class="btn btn-outline btn-sm" data-cancel="${a.id}">Cancel</button>` : pill(a.status, a.status === "Booked" ? "good" : "neutral")}</div>`).join("")}</div>` : `<p class="muted">No appointments booked yet.</p>`}
      </div>
    </div></div>`;
}
function addDays(iso, n) { const d = D(iso); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); }
function bindBooking(p) {
  const preg = p.preg || "PRG0029";
  const recPath = [...cache.keys()].find((k) => k.startsWith(`/api/record/${preg}/`) && (!p.v || k.endsWith(p.v)));
  cache.get(recPath)?.then((r) => {
    const ap = r.appointments;
    const dayEl = $app.querySelector('[data-act="day"]'), typeEl = $app.querySelector('[data-act="vtype"]');
    const urgent = () => typeEl.value.startsWith("Urgent");
    const drawUrgent = () => {
      const n = bookingState.danger.size;
      $app.querySelector("#urgent").innerHTML = n ? notice("critical", "Don't wait for an appointment", `Go to the nearest hospital now, or call <b>108</b> (ambulance) or <b>102</b> (free maternal transport). Tell them you are ${r.visit.ga_w} weeks pregnant.`) : "";
      if (n) { typeEl.value = ap.types[ap.types.length - 1]; dayEl.value = ap.today; loadSlots(); }
    };
    async function loadSlots() {
      if (urgent()) dayEl.value = ap.today;
      const day = dayEl.value; bookingState.day = day;
      const box = $app.querySelector("#slots");
      const s = await api(`/api/slots/${day}`);
      if (s.closed) { box.innerHTML = notice("warn", "The clinic is closed on Sundays", "Choose another day."); return; }
      const [lo, , hi] = ap.window;
      const outside = !urgent() && (day < lo || day > hi);
      if (!s.free.includes(bookingState.slot)) bookingState.slot = s.free[0] || null;
      box.innerHTML = `<div class="small muted">${fmtDay(day)}: ${s.free.length} of ${s.all.length} slots free${outside ? `. This is outside your recommended window (${fmt(lo, { day: "numeric", month: "short" })} – ${fmt(hi, { day: "numeric", month: "short" })}).` : ""}</div>
        <div class="slots" role="group" aria-label="Time slots">${s.all.map((t) => `<button class="slot" data-slot="${t}" ${s.free.includes(t) ? "" : "disabled"} aria-pressed="${t === bookingState.slot}">${t}</button>`).join("")}</div>`;
      box.querySelectorAll("[data-slot]").forEach((b) => b.addEventListener("click", () => { bookingState.slot = b.dataset.slot; box.querySelectorAll("[data-slot]").forEach((x) => x.setAttribute("aria-pressed", x === b)); }));
    }
    $app.querySelectorAll("[data-danger]").forEach((c) => c.addEventListener("change", () => {
      const d = ap.danger_signs[+c.dataset.danger]; c.checked ? bookingState.danger.add(d) : bookingState.danger.delete(d);
      $app.querySelector('[data-act="reason"]').value = [...bookingState.danger].join(", ");
      drawUrgent();
    }));
    dayEl.addEventListener("change", () => { bookingState.slot = null; loadSlots(); });
    typeEl.addEventListener("change", loadSlots);
    $app.querySelector('[data-act="book"]').addEventListener("click", async (e) => {
      const msg = $app.querySelector("#book-msg");
      if (!bookingState.slot) { msg.textContent = "Choose a time slot first."; return; }
      e.target.disabled = true;
      const res = await api("/api/appointments", { pregnancy_id: preg, day: dayEl.value, slot: bookingState.slot, type: typeEl.value, reason: $app.querySelector('[data-act="reason"]').value });
      e.target.disabled = false;
      if (!res.ok) { msg.innerHTML = `<span style="color:var(--critical)">${esc(res.message)}</span>`; invalidate("/api/slots/"); loadSlots(); return; }
      toast(`Booked for ${fmtDay(dayEl.value)} at ${bookingState.slot}`);
      bookingState.danger.clear(); bookingState.slot = null; bookingState.day = null;
      invalidate(`/api/record/${preg}/`); invalidate("/api/slots/"); invalidate("/api/clinic/"); meta = null; cache.delete("/api/meta");
      render();
    });
    $app.querySelectorAll("[data-cancel]").forEach((b) => b.addEventListener("click", async () => {
      await api(`/api/appointments/${b.dataset.cancel}/cancel`, {});
      toast("Appointment cancelled");
      invalidate(`/api/record/${preg}/`); invalidate("/api/slots/"); invalidate("/api/clinic/"); meta = null; cache.delete("/api/meta");
      render();
    }));
    if (bookingState.danger.size) drawUrgent();
    loadSlots();
  });
}

/* ================================================================== DOCTOR */
async function viewDoctor(p) {
  const day = p.day || meta.default_day;
  const clinic = await api(`/api/clinic/${day}`);
  const search = !!p.preg;
  let preg, vid, visits = null;
  if (search) {
    preg = p.preg; visits = await api(`/api/visits/${preg}`);
    vid = p.v && visits.some((x) => x.visit_id === p.v) ? p.v : visits[visits.length - 1].visit_id;
  } else {
    const cur = clinic.find((c) => c.visit_id === p.v) || clinic[0];
    preg = cur?.pregnancy_id; vid = cur?.visit_id;
  }
  if (!preg) return `<div class="page">${notice("plum", "No patients on this day", "Pick another clinic date.")}</div>`;
  const r = await api(`/api/record/${preg}/${vid}`);
  prefetch(clinic.filter((c) => c.visit_id !== vid).map((c) => `/api/record/${c.pregnancy_id}/${c.visit_id}`));
  const tab = p.tab || "overview";
  const needs = r.review.reasons.length && !r.review.done_this_visit;
  const tabs = [["overview", "Overview"], ["meds", "Medications"], ["tests", "Tests"], ["risk", "Risk & review"], ["nutrition", "Nutrition"], ["notes", "Notes"], ["model", "Model performance"]];
  const body = await { overview: docOverview, meds: docMeds, tests: docTests, risk: docRisk, nutrition: docNutrition, notes: docNotes, model: docModel }[tab](r, p);
  const conf = r.review.confirmed.overall;
  const booked = r.appointments.list.filter((a) => a.status === "Booked" && a.date >= r.visit.date)[0];
  const linkFor = (c) => href("doctor", { day, v: c.visit_id, tab });
  return `<div class="page split">
    <aside>
      <label class="field">Clinic day<select class="input" data-act="day">${meta.clinic_days.map((d) => `<option value="${d.date}" ${d.date === day ? "selected" : ""}>${fmtDay(d.date)} — ${d.n + d.booked} patients</option>`).join("")}</select></label>
      <div class="legend"><span><i class="flag review"></i>Review needed</span><span><i class="flag reviewed"></i>Reviewed</span></div>
      <div class="rowlist">${clinic.map((c) => `<a class="rowlink compact ${!search && c.visit_id === vid ? "active" : ""}" href="${linkFor(c)}">
        <i class="flag ${c.flag || "none"}" aria-label="${c.flag === "review" ? "review needed" : c.flag === "reviewed" ? "reviewed" : ""}"></i>
        <span class="label">${c.booked_time ? c.booked_time + " " : ""}${c.patient_id}<span class="sub">${c.booked_time ? `Booked in app: ${esc(c.type)}` : `Week ${c.ga_w}, ${c.risk.toLowerCase()} risk, ${esc(c.type.replace(" ANC", "").toLowerCase())} check-up`}</span></span>
        <span class="arrow">${ICON.arrow}</span></a>`).join("")}</div>
      <label class="field" style="margin-top:22px">Or find any patient<select class="input" data-act="find"><option value="">Choose a patient ID</option>${meta.patients.map((x) => `<option value="${x.pregnancy_id}" ${search && x.pregnancy_id === preg ? "selected" : ""}>${x.patient_id}</option>`).join("")}</select></label>
      ${search ? `<label class="field" style="margin-top:12px">Consultation<select class="input" data-act="visit">${visits.slice().reverse().map((x) => `<option value="${x.visit_id}" ${x.visit_id === vid ? "selected" : ""}>${fmt(x.date)} (week ${x.ga_w})</option>`).join("")}</select></label>` : ""}
    </aside>
    <section class="stack">
      <div class="chart-head">
        <div class="arc-wrap">${arc(r.visit.ga)}</div>
        <div>
          <h1>${r.patient.patient_id}</h1>
          <div class="meta-line"><span>Mother's age <b>${r.patient.age} years</b></span><span>G${r.patient.gravida} P${r.patient.para}</span><span><b>${esc(r.visit.trimester)}</b> trimester</span><span>Due <b>${fmt(r.patient.edd)}</b></span><span>Blood group <b>${esc(r.patient.blood_group)}</b></span><span>Visit ${r.visit.no} on <b>${fmt(r.visit.date)}</b></span></div>
          <div class="row">${pill(`Visit graded ${r.visit.risk}`, SEV[r.visit.risk])}
            ${conf ? pill(`Doctor-confirmed ${conf.band}`, SEV[conf.band]) : ""}
            ${needs ? pill("Risk review needed", "serious") : r.review.done_this_visit ? pill("Reviewed this visit", "good") : ""}
            ${r.patient.drug_allergy ? pill(`Allergy: ${r.patient.drug_allergy} (${r.patient.allergy_reaction})`, "critical") : ""}</div>
          ${booked ? `<p class="small muted" style="margin:10px 0 0">Next appointment booked by the patient: ${fmtDay(booked.date)} at ${booked.time} (${esc(booked.type)}).</p>` : ""}
        </div>
      </div>
      ${needs && tab !== "risk" ? `<div class="notice serious">${ICON.alert}<div><span class="t">Review the risk classification for this visit</span><p>${r.review.reasons.map(esc).join(". ")}.</p></div><a class="btn btn-plum btn-sm" style="margin-left:auto;flex:none" href="${href("doctor", { ...p, day, v: vid, tab: "risk" })}">Review now</a></div>` : ""}
      ${r.alerts.length ? `<div class="alerts">${r.alerts.map((a) => notice(sevClass(a.sev), a.title, esc(a.body))).join("")}</div>` : notice("good", "No alerts at this visit", "Vitals and results are within the expected range.")}
      <nav class="tabs" role="tablist">${tabs.map(([k, l]) => `<a role="tab" href="${href("doctor", { ...p, day, v: vid, tab: k })}" aria-selected="${k === tab}">${l}${k === "risk" && needs ? '<span class="count">1</span>' : ""}</a>`).join("")}</nav>
      <div>${body}</div>
    </section></div>`;
}
afterRender.doctor = (p) => {
  $app.querySelector('[data-act="day"]')?.addEventListener("change", (e) => setParams({ day: e.target.value, v: "", preg: "" }));
  $app.querySelector('[data-act="find"]')?.addEventListener("change", (e) => setParams({ preg: e.target.value, v: "" }));
  $app.querySelector('[data-act="visit"]')?.addEventListener("change", (e) => setParams({ v: e.target.value }));
  (docBind[p.tab || "overview"] || (() => {}))(p);
};
const docBind = {};
function curRecord() {
  const { params } = route();
  // the record on screen is the most recently rendered one
  return lastRecord;
}
let lastRecord = null;

function docOverview(r) {
  lastRecord = r;
  const v = r.visit, vs = r.visits, prev = vs.length > 1 ? vs[vs.length - 2] : null;
  const hb = r.labs.filter((l) => l.test === "Haemoglobin" && l.num !== null);
  const d = (a, b, u) => (prev ? `${a - b >= 0 ? "+" : ""}${(a - b).toFixed(u === "kg" ? 1 : 0)} ${u} since last visit` : "first visit");
  return `<div class="stack">
    <div class="stats">
      <div class="stat"><div class="k">Blood pressure</div><div class="v">${v.sbp}/${v.dbp}</div><div class="d">${prev ? d(v.sbp, prev.sbp, "systolic") : "first visit"}</div></div>
      <div class="stat"><div class="k">Weight</div><div class="v">${v.weight} kg</div><div class="d">${prev ? d(v.weight, prev.weight, "kg") : "first visit"}</div></div>
      <div class="stat"><div class="k">SpO₂</div><div class="v">${v.spo2}%</div></div>
      <div class="stat"><div class="k">Fetal heart rate</div><div class="v">${v.fhr ?? "—"}</div><div class="d">${v.fhr ? "bpm" : "not measured yet"}</div></div>
      <div class="stat"><div class="k">Latest Hb</div><div class="v">${r.latest_hb ? r.latest_hb.value.toFixed(1) : "—"}</div><div class="d">${r.latest_hb ? "g/dL on " + fmt(r.latest_hb.date, { day: "numeric", month: "short" }) : "not tested yet"}</div></div>
    </div>
    <div class="grid-2">
      ${lineChart({ title: "Blood pressure", unit: " mmHg", series: [{ name: "Systolic", color: CH.plum, points: vs.map((x) => [+x.ga.toFixed(1), x.sbp]) }, { name: "Diastolic", color: CH.coral, points: vs.map((x) => [+x.ga.toFixed(1), x.dbp]) }], refs: [{ y: 140, label: "140 systolic limit" }, { y: 90, label: "90 diastolic limit" }] })}
      ${hb.length ? lineChart({ title: "Haemoglobin", unit: " g/dL", series: [{ name: "Hb", color: CH.plum, points: hb.map((x) => [x.ga_w, x.num]) }], refs: [{ y: 11, label: "11 g/dL anaemia cut-off" }] }) : `<div class="chart"><h4>Haemoglobin</h4><p class="muted">Not tested yet.</p></div>`}
    </div>
    <div class="grid-2">
      <div class="panel"><h3 style="margin-bottom:10px">Baseline risk factors</h3>${r.patient.risk_factors.length ? r.patient.risk_factors.map((f) => `<span class="tag">${esc(f)}</span>`).join("") : '<p class="muted">None recorded.</p>'}</div>
      <div class="panel"><h3 style="margin-bottom:10px">Today</h3><p>${esc(v.assessment)}. Symptoms: ${esc(v.symptoms)}${v.severity && v.severity !== "None" ? ` (${esc(v.severity).toLowerCase()})` : ""}. Oedema ${esc(v.oedema).toLowerCase()}. Presentation ${esc(v.presentation).toLowerCase()}, fetal movement ${esc(v.fetal_movement).toLowerCase()}.</p></div>
    </div>
    ${table([{ h: "Date", f: (x) => fmt(x.date) }, { h: "Week", k: "ga_w", num: true }, { h: "BP", f: (x) => `${x.sbp}/${x.dbp}` }, { h: "Weight", f: (x) => `${x.weight}`, num: true }, { h: "SpO₂", k: "spo2", num: true }, { h: "Risk", html: (x) => pill(x.risk, SEV[x.risk]) }, { h: "Assessment", k: "assessment" }, { h: "Referral", k: "referral" }], vs.slice().reverse())}
  </div>`;
}

function findingsHTML(list, okText) {
  if (!list.length) return notice("good", okText, "");
  return `<div class="stack" style="--g:10px">${list.map((f) => notice(sevClass(f.severity), `${f.check}: ${f.medicine}`, esc(f.finding))).join("")}</div>`;
}
function docMeds(r) {
  lastRecord = r;
  return `<div class="stack">
    <div class="section-title"><h3>Current medications</h3></div>
    ${table([{ h: "Medicine", k: "name" }, { h: "For", k: "indication" }, { h: "Regimen", k: "regimen" }, { h: "Since", f: (x) => `${fmt(x.started)} (wk ${x.ga_w})` }, { h: "Monitoring", k: "monitoring" }], r.meds_active)}
    <div class="section-title"><h3>Changed at this visit</h3></div>
    ${r.meds_today.length ? table([{ h: "Medicine", k: "name" }, { h: "Action", k: "action" }, { h: "Trigger", f: (x) => [x.trigger, x.trigger_test, x.trigger_value].filter((y) => y && y !== "None").join(", ") }, { h: "For", k: "indication" }], r.meds_today) : `<p class="muted">No changes recorded at this visit.</p>`}
    <div class="section-title"><h3>Suggested changes</h3><span class="small muted">From clinical rules, for you to decide</span></div>
    ${r.suggestions.length ? r.suggestions.map((s) => `<div class="panel stack"><div><b>Consider ${esc(s.drug)}</b><p class="muted" style="margin:4px 0 0">${esc(s.why)}</p></div>${findingsHTML(s.issues, "No allergy or interaction conflict with her current medicines")}</div>`).join("") : `<p class="muted">The rules suggest no changes at this visit.</p>`}
    <div class="section-title"><h3>Safety check of the current regimen</h3></div>
    ${findingsHTML(r.regimen_safety, "No allergy, interaction or pregnancy conflicts")}
    <div class="panel stack">
      <h3>Check a medicine before prescribing</h3>
      <div class="row"><select class="input" style="max-width:420px" data-act="drug"><option value="">Choose a medicine</option>${meta.drugs.map((d) => `<option>${esc(d)}</option>`).join("")}</select>
      <button class="btn btn-plum" data-act="check-drug">Check for this patient</button></div>
      <div id="drug-result"></div>
    </div></div>`;
}
docBind.meds = (p) => {
  const r = lastRecord;
  $app.querySelector('[data-act="check-drug"]')?.addEventListener("click", async () => {
    const drug = $app.querySelector('[data-act="drug"]').value; if (!drug) return;
    const out = $app.querySelector("#drug-result"); out.innerHTML = `<p class="muted">Checking…</p>`;
    const res = await api("/api/drug-check", { pregnancy_id: r.patient.pregnancy_id, visit_id: r.visit.visit_id, drug });
    const pr = res.profile;
    out.innerHTML = findingsHTML(res.findings, `No allergy, interaction or pregnancy flag for ${drug} — still review dose and indication`) +
      `<div class="grid-2" style="margin-top:16px"><div><p><b>Pregnancy-specific risks.</b> ${esc(pr.Pregnancy_Specific_Risks)}</p><p><b>By trimester.</b> ${esc(pr.Trimester_Notes)}</p><p><b>Contraindications.</b> ${esc(pr.Contraindications)}</p></div>
       <div><p><b>Common side effects.</b> ${esc(pr.Common_Adverse_Effects)}</p><p><b>Serious side effects.</b> ${esc(pr.Serious_Adverse_Effects)}</p><p><b>Monitor.</b> ${esc(pr.Monitoring)}</p></div></div>
       <p class="small muted">Reference regimen: ${esc(pr.Reference_Regimen_or_Dose_Band)}. Evidence ${esc(pr.Evidence_Grade)}: ${esc(pr.Evidence_Sources)}.</p>`;
  });
};

function docTests(r) {
  lastRecord = r;
  const today = r.labs.filter((l) => l.visit_id === r.visit.visit_id);
  const stCls = { Overdue: "critical", "Due now": "serious", "Due soon": "warn", "Every visit": "neutral" };
  return `<div class="stack">
    <div class="section-title"><h3>Results from this visit</h3></div>
    ${today.length ? table([{ h: "Test", k: "test_label" }, { h: "Result", f: (x) => `${x.result} ${x.unit || ""}` }, { h: "Reference", k: "ref" }, { h: "Flag", html: (x) => (x.abnormal ? pill(x.flag, "serious") : pill("Normal", "good")) }, { h: "Reason", k: "reason" }], today, { rowClass: (x) => (x.abnormal ? "abn" : "") }) : `<p class="muted">No tests done at this visit.</p>`}
    <div class="section-title"><h3>Due next or overdue</h3><span class="small muted">${r.visit.next_visit ? `Next visit set for ${fmt(r.visit.next_visit)}` : ""}</span></div>
    ${table([{ h: "Test", k: "test" }, { h: "Window", k: "window" }, { h: "Why", k: "reason" }, { h: "Status", html: (x) => pill(x.status, stCls[x.status] || "neutral") }], r.test_plan)}
    <div class="section-title"><h3>Abnormal results so far</h3></div>
    ${table([{ h: "Date", f: (x) => fmt(x.date) }, { h: "Week", k: "ga_w", num: true }, { h: "Test", k: "test_label" }, { h: "Result", f: (x) => `${x.result} ${x.unit || ""}` }, { h: "Flag", k: "flag" }], r.labs.filter((l) => l.abnormal).reverse())}
  </div>`;
}

const LABELS = { overall: "Overall pregnancy risk", preterm: "Preterm birth", nicu: "NICU admission", gdm: "Gestational diabetes" };
function docRisk(r) {
  lastRecord = r;
  if (!r.risk.available) return notice("warn", "Risk models are not loaded", "Stop the server, run <b>python train_models.py</b> (about a minute), then start it again.");
  const rv = r.review, res = r.risk.results || {};
  const RANK = { Low: 0, Moderate: 1, High: 2 };
  const items = [["overall", null, r.visit.risk]].concat(Object.entries(res).filter(([, x]) => x.prob !== null).map(([t, x]) => [t, x.prob, x.band]));
  const maxBand = [r.visit.risk, ...Object.values(res).map((x) => x.band).filter(Boolean)].sort((a, b) => RANK[b] - RANK[a])[0];
  const form = `<div class="panel stack">
    <div class="section-title" style="margin:0"><h3>Your review of the risk classification</h3>${rv.done_this_visit ? pill(`Reviewed ${rv.done_at}`, "good") : rv.reasons.length ? pill("Needed for this visit", "serious") : pill("Optional", "neutral")}</div>
    ${rv.reasons.length ? `<ul style="margin:0;padding-left:20px">${rv.reasons.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p class="muted" style="margin:0">Nothing unusual at this visit.</p>`}
    <div class="grid-${Math.min(items.length, 4) === 4 ? "2" : "3"}" style="grid-template-columns:repeat(${items.length},1fr);gap:14px">
      ${items.map(([t, prob, band]) => {
        const def = rv.confirmed[t]?.band || (t === "overall" ? maxBand : band);
        return `<label class="field">${LABELS[t]}<select class="input" data-review="${t}" data-model="${t === "overall" ? "" : band}" data-prob="${prob ?? ""}">${["Low", "Moderate", "High"].map((b) => `<option ${b === def ? "selected" : ""}>${b}</option>`).join("")}</select>
          <span class="small muted">${t === "overall" ? `Visit graded ${band}` : `Model says ${band} (${pct(prob)})`}</span></label>`;
      }).join("")}
    </div>
    <label class="field">Clinical reasoning (needed if you change what the model says)<textarea class="input" data-act="review-reason" placeholder="e.g. Hb falling and reduced fetal movement; raising preterm risk"></textarea></label>
    <div class="row"><button class="btn btn-plum" data-act="save-review">Confirm risk classification</button><span id="review-msg" class="small"></span></div>
    ${rv.history.length ? `<details><summary class="small" style="cursor:pointer">Review history (${rv.history.length} decisions)</summary><div style="margin-top:10px">${table([{ h: "When", k: "timestamp" }, { h: "Visit", f: (x) => fmt(x.visit_date) }, { h: "Outcome", f: (x) => LABELS[x.outcome] }, { h: "Model", k: "model_band" }, { h: "Doctor", k: "final_band" }, { h: "Changed", k: "changed" }, { h: "Reason", k: "reason" }], rv.history)}</div></details>` : ""}
  </div>`;
  const cards = Object.entries(res).map(([t, x]) => {
    const fin = rv.confirmed[t]?.band;
    if (x.prob === null) return `<div class="risk-card"><h3>${esc(LABELS[t])}</h3>${x.band ? `<div style="margin:10px 0">${pill(`Measured: ${x.band}`, SEV[x.band])}</div>` : ""}<p class="muted" style="margin-top:10px">${esc(x.note)}</p></div>`;
    return `<div class="risk-card">
      <h3>${esc(LABELS[t])}</h3>
      <div class="prob">${pct(x.prob)} <small>chance</small></div>
      <div class="row">${pill(`Model: ${x.band}`, SEV[x.band])}${fin ? pill(`Doctor: ${fin}`, SEV[fin]) : ""}</div>
      <div class="scale" style="--m:${x.thresholds.moderate * 100}%;--h:${x.thresholds.high * 100}%"><i style="left:${Math.min(99, x.prob * 100)}%"></i></div>
      <div class="small muted">Low below ${pct(x.thresholds.moderate)}, high from ${pct(x.thresholds.high)}. ${x.note ? esc(x.note) : ""}</div>
      <p style="margin:12px 0 4px"><b>What to do.</b> ${esc(x.action)}</p>
      <details data-explain="${x.visit_used}" data-target="${t}"><summary class="small" style="cursor:pointer;color:var(--plum)">Why this score</summary><div class="explain" style="margin-top:12px"><p class="muted small">Loading…</p></div></details>
    </div>`;
  }).join("");
  const T = r.risk.trajectory || [];
  const ser = [["preterm", "Preterm birth", CH.plum], ["nicu", "NICU admission", CH.coral], ["gdm", "GDM (before 24 wk)", CH.teal]]
    .map(([k, n, c]) => ({ name: n, color: c, points: T.filter((x) => x[k] !== null && x[k] !== undefined).map((x) => [+x.ga.toFixed(1), Math.round(x[k] * 100)]) })).filter((s) => s.points.length);
  return `<div class="stack">${form}
    <div class="grid-3">${cards}</div>
    ${lineChart({ title: "Predicted risk at each visit", unit: "%", series: ser, yMin: 0, fmtY: (v) => v + "%" })}
    <p class="small muted">Each score uses only what was known at that visit, from a model that never saw this patient in training. The model suggests; you decide.</p>
  </div>`;
}
docBind.risk = () => {
  const r = lastRecord;
  $app.querySelectorAll("details[data-explain]").forEach((d) => d.addEventListener("toggle", async () => {
    if (!d.open || d.dataset.loaded) return; d.dataset.loaded = 1;
    const e = await api(`/api/explain/${d.dataset.explain}/${d.dataset.target}`);
    const items = [...e.up.map((x) => ({ label: x.label, value: x.effect * 100, color: "#B4232F" })), ...e.down.map((x) => ({ label: x.label, value: x.effect * 100, color: "#2E7D4F" }))];
    d.querySelector(".explain").innerHTML = items.length ? `<p class="small muted" style="margin-bottom:10px">How much each factor moves her risk compared with a typical patient. Red raises it, green lowers it.</p>` + bars(items, { fmtV: (v) => `${v > 0 ? "+" : ""}${v.toFixed(1)} points` }) : `<p class="small muted">No single factor stands out.</p>`;
  }));
  $app.querySelector('[data-act="save-review"]')?.addEventListener("click", async (e) => {
    const decisions = [...$app.querySelectorAll("[data-review]")].map((s) => ({ Outcome: s.dataset.review, Model_Band: s.dataset.model, Model_Prob: s.dataset.prob ? +(+s.dataset.prob).toFixed(3) : "", Final_Band: s.value }));
    e.target.disabled = true;
    const res = await api("/api/review", { pregnancy_id: r.patient.pregnancy_id, visit_id: r.visit.visit_id, decisions, reason: $app.querySelector('[data-act="review-reason"]').value });
    e.target.disabled = false;
    if (!res.ok) { $app.querySelector("#review-msg").innerHTML = `<span style="color:var(--critical)">${esc(res.message)}</span>`; return; }
    toast("Risk classification confirmed");
    invalidate(`/api/record/${r.patient.pregnancy_id}/`); invalidate("/api/clinic/");
    render();
  });
};

function docNutrition(r) {
  lastRecord = r;
  const a = r.nutrition.assessments.at(-1);
  if (!a) return `<p class="muted">No nutrition assessment yet.</p>`;
  const plan = r.notes.find((n) => n.kind === "diet_plan"), referred = r.notes.some((n) => n.kind === "referral");
  return `<div class="grid-2"><div class="panel stack">
      <h3>Latest nutrition assessment</h3>
      <p style="margin:0">${esc(a.pattern)}, nutrition risk ${pill(a.risk, SEV[a.risk])}, dietician referral: ${esc(a.referral)}.</p>
      <div>${a.focus.map((f) => `<span class="tag">${esc(f)}</span>`).join("") || '<span class="muted">Routine</span>'}</div>
      ${plan ? notice("good", "Dietician's plan", esc(plan.text)) : ""}
      <div class="row"><button class="btn btn-plum" data-act="refer" ${referred ? "disabled" : ""}>${referred ? "Referred to dietician" : "Refer to dietician"}</button></div>
    </div>
    <div>${weightChart(r)}</div></div>`;
}
docBind.nutrition = () => {
  const r = lastRecord;
  $app.querySelector('[data-act="refer"]')?.addEventListener("click", async () => {
    await api("/api/notes", { role: "Doctor", pregnancy_id: r.patient.pregnancy_id, visit_id: r.visit.visit_id, kind: "referral", text: "Referred to dietician" });
    toast("Referred to dietician"); invalidate(`/api/record/${r.patient.pregnancy_id}/`); invalidate("/api/worklist"); render();
  });
};
function docNotes(r) {
  lastRecord = r;
  return `<div class="grid-2"><div class="panel stack"><h3>Note for this visit</h3><textarea class="input" data-act="note" placeholder="Findings, plan, advice given"></textarea><div><button class="btn btn-plum" data-act="save-note">Save note</button></div></div>
    <div>${table([{ h: "When", k: "timestamp" }, { h: "By", k: "role" }, { h: "Type", k: "kind" }, { h: "Note", k: "text" }], r.notes)}</div></div>`;
}
docBind.notes = () => {
  const r = lastRecord;
  $app.querySelector('[data-act="save-note"]')?.addEventListener("click", async () => {
    const text = $app.querySelector('[data-act="note"]').value.trim(); if (!text) return;
    await api("/api/notes", { role: "Doctor", pregnancy_id: r.patient.pregnancy_id, visit_id: r.visit.visit_id, kind: "clinical", text });
    toast("Note saved"); invalidate(`/api/record/${r.patient.pregnancy_id}/`); render();
  });
};

async function docModel(r) {
  lastRecord = r;
  const m = await api("/api/model");
  const f2 = (x) => (x === null || x === undefined ? "—" : (+x).toFixed(2)), f3 = (x) => (x === null || x === undefined ? "—" : (+x).toFixed(3));
  return `<div class="stack">
    ${notice("plum", "How to read these numbers", "These outcomes are uncommon (preterm 17%, NICU 7%, GDM 28%), so accuracy alone misleads: a model that always says “no” already scores the always-no accuracy. Judge the models by ROC-AUC (0.5 = guessing, 1 = perfect), balanced accuracy, sensitivity and specificity. Every number is out-of-fold, from 5-fold cross-validation grouped by pregnancy.")}
    ${table([{ h: "Outcome", f: (x) => LABELS[x.target] }, { h: "Model", k: "model" }, { h: "ROC-AUC", f: (x) => f3(x.roc_auc), num: true }, { h: "Best possible", f: (x) => f3(x.ceiling), num: true }, { h: "Accuracy", f: (x) => f2(x.landmark.accuracy), num: true }, { h: "Always-no accuracy", f: (x) => f2(x.landmark.baseline_accuracy), num: true }, { h: "Balanced accuracy", f: (x) => f2(x.landmark.balanced_accuracy), num: true }, { h: "Sensitivity", f: (x) => f2(x.landmark.sensitivity), num: true }, { h: "Specificity", f: (x) => f2(x.landmark.specificity), num: true }, { h: "F1", f: (x) => f2(x.landmark.f1), num: true }], m.models)}
    <p class="small muted">Accuracy, sensitivity, specificity and F1 use one prediction per pregnancy (last visit up to 28 weeks; up to 24 weeks for GDM) at the balanced threshold. Best possible = the score from the data generator's own true probabilities.</p>
    ${m.models.map((x) => `<div class="panel"><h3>${esc(LABELS[x.target])}: ${esc(x.model)}</h3>
      <div class="grid-3" style="margin-top:16px">
        <div>${table([{ h: "Model", k: "model" }, { h: "ROC-AUC", f: (y) => f3(y.roc_auc), num: true }, { h: "PR-AUC", f: (y) => f3(y.pr_auc), num: true }], x.comparison)}</div>
        <div>${table([{ h: "", k: "a" }, { h: "Predicted no", k: "n", num: true }, { h: "Predicted yes", k: "y", num: true }], [{ a: "Actually no", n: x.landmark.tn, y: x.landmark.fp }, { a: "Actually yes", n: x.landmark.fn, y: x.landmark.tp }])}
          <p class="small muted" style="margin-top:8px">${x.landmark.n_pregnancies} pregnancies.${x.ceiling ? ` Best possible ROC-AUC ${f3(x.ceiling)}; this model ${f3(x.roc_auc)}.` : ""}</p></div>
        <div><p class="small" style="margin-bottom:10px"><b>Most important factors</b> (drop in ROC-AUC when shuffled)</p>${bars(x.importance)}</div>
      </div></div>`).join("")}
  </div>`;
}

/* ================================================================== DIETICIAN */
async function viewDietician(p) {
  const wl = await api("/api/worklist");
  const filt = (p.f || "High,Moderate").split(",").filter(Boolean);
  const list = wl.filter((w) => filt.includes(w.risk) || w.referred);
  const preg = p.preg || list[0]?.pregnancy_id || wl[0].pregnancy_id;
  const visits = await api(`/api/visits/${preg}`);
  const vid = p.v && visits.some((x) => x.visit_id === p.v) ? p.v : visits[visits.length - 1].visit_id;
  const r = await api(`/api/record/${preg}/${vid}`);
  lastRecord = r;
  prefetch(list.slice(0, 8).map((w) => `/api/visits/${w.pregnancy_id}`));
  const tab = p.tab || "drivers";
  const a = r.nutrition.assessments.at(-1);
  const body = !a ? `<p class="muted">No nutrition assessment for this visit yet.</p>` : { drivers: dietDrivers, plan: dietPlan, history: dietHistory }[tab](r, a);
  const conf = r.review.confirmed;
  return `<div class="page split">
    <aside>
      <div class="chips" style="margin-bottom:12px">${["High", "Moderate", "Low"].map((k) => `<button class="chip" data-f="${k}" aria-pressed="${filt.includes(k)}">${k} risk</button>`).join("")}</div>
      <p class="small muted">${list.length} patients, referred first</p>
      <div class="rowlist">${list.map((w) => `<a class="rowlink compact ${w.pregnancy_id === preg ? "active" : ""}" href="${href("dietician", { ...p, preg: w.pregnancy_id, v: "" })}">
        <i class="flag ${w.risk === "High" ? "review" : "none"}"></i><span class="label">${w.patient_id}<span class="sub">${w.risk} risk, ${esc(w.focus.toLowerCase())}${w.referred ? ". Referred by doctor" : ""}</span></span><span class="arrow">${ICON.arrow}</span></a>`).join("")}</div>
    </aside>
    <section class="stack">
      <div>
        <div class="demo-bar"><label>Assessment on <select data-act="visit">${visits.slice().reverse().map((x) => `<option value="${x.visit_id}" ${x.visit_id === vid ? "selected" : ""}>${fmt(x.date)} (week ${x.ga_w})</option>`).join("")}</select></label></div>
        <h1 style="margin:10px 0 8px">${r.patient.patient_id}'s nutrition</h1>
        <div class="meta-line"><span>Week <b>${r.visit.ga_w}</b></span><span>${esc(a?.pattern || r.patient.diet_pattern)}</span>${a?.restrictions ? `<span>${esc(a.restrictions)}</span>` : ""}<span>Food allergy: <b>${esc(a?.food_allergy || r.patient.food_allergy || "none")}</b></span></div>
        <div class="row">${a ? pill(`Nutrition risk ${a.risk}`, SEV[a.risk]) : ""}${conf.overall ? pill(`Doctor: overall ${conf.overall.band}`, SEV[conf.overall.band]) : ""}${conf.gdm ? pill(`Doctor: GDM ${conf.gdm.band}`, SEV[conf.gdm.band]) : ""}</div>
      </div>
      <nav class="tabs" role="tablist">${[["drivers", "What's driving her diet"], ["plan", "Diet plan"], ["history", "History"]].map(([k, l]) => `<a role="tab" href="${href("dietician", { ...p, preg, v: vid, tab: k })}" aria-selected="${k === tab}">${l}</a>`).join("")}</nav>
      <div>${body}</div>
    </section></div>`;
}
afterRender.dietician = (p) => {
  $app.querySelector('[data-act="visit"]')?.addEventListener("change", (e) => setParams({ v: e.target.value }));
  $app.querySelectorAll("[data-f]").forEach((b) => b.addEventListener("click", () => {
    const cur = new Set((p.f || "High,Moderate").split(",").filter(Boolean));
    cur.has(b.dataset.f) ? cur.delete(b.dataset.f) : cur.add(b.dataset.f);
    setParams({ f: [...cur].join(",") || "High" }, true);
  }));
  if (p.tab === "plan") bindPlan();
};
function dietDrivers(r, a) {
  const hb = r.latest_hb, v = r.visit;
  const alerts = [];
  if (hb && hb.value < 11) alerts.push(notice("serious", `Anaemia (Hb ${hb.value.toFixed(1)} g/dL)`, "Pair iron foods with vitamin C; keep tea, milk and calcium away from iron."));
  if (r.nutrition.glucose === "Abnormal") alerts.push(notice("serious", "Abnormal glucose test", "Carbohydrate quality and spacing; low-GI grains; protein at every meal."));
  if (v.sbp >= 140 || v.dbp >= 90) alerts.push(notice("warn", "Raised blood pressure", "Cut back on salt; add potassium-rich vegetables and fruit."));
  return `<div class="stack">
    <div class="stats">
      <div class="stat"><div class="k">Latest Hb</div><div class="v">${hb ? hb.value.toFixed(1) : "—"}</div><div class="d">${hb ? "g/dL" : "not tested"}</div></div>
      <div class="stat"><div class="k">Glucose tests</div><div class="v">${esc(r.nutrition.glucose)}</div></div>
      <div class="stat"><div class="k">Blood pressure</div><div class="v">${v.sbp}/${v.dbp}</div></div>
      <div class="stat"><div class="k">BMI now</div><div class="v">${a.bmi}</div><div class="d">${r.patient.bmi} before pregnancy</div></div>
    </div>
    ${alerts.length ? `<div class="alerts">${alerts.join("")}</div>` : ""}
    <div class="grid-2"><div>${weightChart(r)}<p class="small muted" style="margin-top:8px">${r.weight.category} BMI: recommended total gain ${r.weight.lo}–${r.weight.hi} kg. Gained ${r.weight.gain} kg so far.</p></div>
      <div class="stack"><h3>Medicines that affect meals</h3>
        ${table([{ h: "Medicine", k: "name" }, { h: "Food and drug interactions", k: "interactions" }], r.meds_active)}
        ${a.tips.length ? `<ul style="padding-left:20px;margin:0">${a.tips.map((t) => `<li style="margin-bottom:6px"><b>${esc(t.flag)}.</b> ${esc(t.text)}</li>`).join("")}</ul>` : ""}
      </div></div></div>`;
}
function dietPlan(r) {
  const F = r.nutrition.foods;
  if (!F.length) return `<p class="muted">No food recommendations have been generated for her yet.</p>`;
  const plan = dietNoteFor(r, r.visit.visit_id);
  return `<div class="stack">
    <p class="muted" style="margin:0">Recommended foods from ${fmt(r.nutrition.foods_date)}, already filtered for her diet type and food allergies. Untick any you want to leave out, then share the plan.</p>
    ${table([{ h: "Keep", html: (x) => `<input type="checkbox" checked data-food="${esc(x.food)}" aria-label="Keep ${esc(x.food)}">` }, { h: "Food", html: (x) => `<b>${esc(x.food)}</b>` }, { h: "Helps with", html: (x) => x.contexts.map((c) => `<span class="tag">${esc(c)}</span>`).join("") }, { h: "Serving", f: (x) => `${x.serving ?? "—"} g`, num: true }, { h: "kcal", k: "kcal", num: true }, { h: "Protein g", k: "protein", num: true }, { h: "Iron mg", k: "iron", num: true }, { h: "Calcium mg", k: "calcium", num: true }, { h: "GI", k: "gi" }], foodRows(F))}
    <div class="panel stack"><h3>Guidance applied</h3>
      ${table([{ h: "For", k: "context" }, { h: "Principle", k: "principle" }, { h: "Emphasise", k: "emphasize" }, { h: "Limit", k: "limit" }], r.nutrition.rules)}</div>
    <div class="panel stack"><h3>Share the plan with her</h3>
      ${plan ? notice("good", `Last shared ${plan.timestamp}`, esc(plan.text)) : ""}
      <label class="field">Message to the patient<textarea class="input" data-act="plan-note">Follow the foods below. Take iron and calcium at different times of day.</textarea></label>
      <div><button class="btn btn-primary" data-act="approve">Share plan with patient</button></div></div>
  </div>`;
}
function foodRows(F) {
  // one row per food, listing every condition it helps with
  const m = new Map();
  F.forEach((f) => { const r = m.get(f.food) || { ...f, contexts: [] }; if (!r.contexts.includes(f.context)) r.contexts.push(f.context); m.set(f.food, r); });
  return [...m.values()].sort((a, b) => b.contexts.length - a.contexts.length);
}
function bindPlan() {
  const r = lastRecord;
  $app.querySelector('[data-act="approve"]')?.addEventListener("click", async () => {
    const kept = [...$app.querySelectorAll("[data-food]")].filter((c) => c.checked).map((c) => c.dataset.food);
    const text = `${$app.querySelector('[data-act="plan-note"]').value.trim()} Foods: ${[...new Set(kept)].slice(0, 15).join(", ")}.`;
    await api("/api/notes", { role: "Dietician", pregnancy_id: r.patient.pregnancy_id, visit_id: r.nutrition.assessments.at(-1).visit_id, kind: "diet_plan", text });
    toast("Plan shared with patient"); invalidate(`/api/record/${r.patient.pregnancy_id}/`); render();
  });
}
function dietHistory(r) {
  return `<div class="stack">${table([{ h: "Date", f: (x) => fmt(x.date) }, { h: "Week", k: "ga_w", num: true }, { h: "Weight", f: (x) => `${x.weight} kg` }, { h: "BMI", k: "bmi", num: true }, { h: "Risk", html: (x) => pill(x.risk, SEV[x.risk]) }, { h: "Appetite", k: "appetite" }, { h: "Nausea", k: "nausea" }, { h: "Focus", f: (x) => x.focus.join(", ") || "Routine" }], r.nutrition.assessments.slice().reverse())}
    <h3>Notes</h3>${table([{ h: "When", k: "timestamp" }, { h: "By", k: "role" }, { h: "Type", k: "kind" }, { h: "Note", k: "text" }], r.notes)}</div>`;
}

/* ------------------------------------------------------------------ start */
render();
