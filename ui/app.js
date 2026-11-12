// Cloud Cost Tracker dashboard. Talks to the FastAPI backend under /api.
const $ = (id) => document.getElementById(id);
const API = window.COST_API_BASE || "";
const SLOTS = 7; // top N series get categorical colors; the rest fold into "Other"

const state = {
  meta: null,
  dimension: "SERVICE",
  tagKey: "",
  breakdown: null,
  chart: null,
};

// ---------- helpers ----------
const iso = (d) => d.toISOString().slice(0, 10);
const addDays = (d, n) => new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() + n));
const monthStart = (d, offset = 0) => new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + offset, 1));
const todayUTC = () => { const n = new Date(); return new Date(Date.UTC(n.getFullYear(), n.getMonth(), n.getDate())); };

let unit = "USD";
const money = (v, digits = 2) =>
  v == null ? "n/a" : new Intl.NumberFormat(undefined, { style: "currency", currency: unit, maximumFractionDigits: digits, minimumFractionDigits: digits }).format(v);
const compact = (v) =>
  new Intl.NumberFormat(undefined, { style: "currency", currency: unit, notation: "compact", maximumFractionDigits: 1 }).format(v);
const fmtDate = (s, opts = { month: "short", day: "numeric" }) =>
  new Date(s + "T00:00:00Z").toLocaleDateString(undefined, { ...opts, timeZone: "UTC" });
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, params = {}, opts = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== ""));
  const res = await fetch(`${API}/api/${path}${qs.size ? "?" + qs : ""}`, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(`${path}: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`);
  }
  return res.json();
}

function showError(err) {
  const el = $("error");
  el.hidden = !err;
  el.textContent = err ? `Couldn't load cost data — ${err.message}` : "";
}

// ---------- range ----------
function currentRange() {
  const today = todayUTC();
  const v = $("range").value;
  if (v === "custom") {
    const s = $("start").value, e = $("end").value;
    if (s && e && s <= e) return { start: s, end: iso(addDays(new Date(e + "T00:00:00Z"), 1)) };
  }
  if (v === "last") return { start: iso(monthStart(today, -1)), end: iso(monthStart(today)) };
  if (/^\d+$/.test(v)) return { start: iso(monthStart(today, -(+v - 1))), end: iso(addDays(today, 1)) };
  return { start: iso(monthStart(today)), end: iso(addDays(today, 1)) };
}
const rangeDays = ({ start, end }) => (new Date(end) - new Date(start)) / 864e5;
const rangeLabel = (r) => `${fmtDate(r.start, { month: "short", day: "numeric", year: "numeric" })} – ${fmtDate(iso(addDays(new Date(r.end + "T00:00:00Z"), -1)), { month: "short", day: "numeric", year: "numeric" })}`;

// ---------- KPIs ----------
function delta(pct, vs) {
  if (pct == null) return vs;
  const cls = pct > 0 ? "up" : "down";
  const arrow = pct > 0 ? "▲" : "▼";
  return `<span class="${cls}">${arrow} ${Math.abs(pct).toFixed(1)}%</span> ${vs}`;
}

async function loadSummary(metric) {
  const s = await api("summary", { metric });
  unit = s.unit || "USD";
  $("kpi-mtd").textContent = money(s.month_to_date);
  $("kpi-mtd-sub").innerHTML = s.month_to_date_days
    ? delta(s.mtd_change_pct, `vs first ${s.month_to_date_days} days of last month`)
    : "No complete days yet this month";
  $("kpi-proj").textContent = money(s.projected_month);
  $("kpi-proj-sub").innerHTML = s.projected_month == null ? "AWS has too little history to forecast" : delta(s.projected_change_pct, "vs last month");
  $("kpi-last").textContent = money(s.last_month);
  $("kpi-last-sub").textContent = fmtDate(s.periods.last_month[0], { month: "long", year: "numeric" });
}

// ---------- time series ----------
function seriesColors() {
  return [1, 2, 3, 4, 5, 6, 7].map((i) => cssVar(`--s${i}`));
}

async function loadTimeseries(metric, range) {
  const granularity = rangeDays(range) > 62 ? "MONTHLY" : "DAILY";
  const group_by = $("ts-group").value;
  const ts = await api("timeseries", { ...range, metric, granularity, group_by });

  // Rank entities by total spend in the range; top SLOTS get stable colors, rest -> Other.
  const totals = {};
  ts.periods.forEach((p) => Object.entries(p.groups).forEach(([k, v]) => (totals[k] = (totals[k] || 0) + v)));
  const ranked = Object.keys(totals).sort((a, b) => totals[b] - totals[a]);
  const top = ranked.slice(0, SLOTS);
  const hasOther = ranked.length > SLOTS;
  const colors = seriesColors();

  const labels = ts.periods.map((p) => granularity === "DAILY" ? fmtDate(p.start) : fmtDate(p.start, { month: "short", year: "2-digit" }));
  const datasets = top.map((k, i) => ({ label: k, data: ts.periods.map((p) => p.groups[k] || 0), backgroundColor: colors[i] }));
  if (hasOther) {
    datasets.push({
      label: `Other (${ranked.length - SLOTS})`,
      data: ts.periods.map((p) => Object.entries(p.groups).reduce((s, [k, v]) => (top.includes(k) ? s : s + v), 0)),
      backgroundColor: cssVar("--other"),
    });
  }
  datasets.forEach((d) => Object.assign(d, { borderColor: cssVar("--surface"), borderWidth: { top: 2 }, borderSkipped: "bottom", maxBarThickness: 48 }));

  renderChart(labels, datasets, ts.periods.map((p) => p.total));
  return ts.periods.reduce((sum, p) => sum + p.total, 0);
}

function renderChart(labels, datasets, totals) {
  const text2 = cssVar("--text-2"), grid = cssVar("--grid"), muted = cssVar("--muted");
  if (state.chart) state.chart.destroy();
  state.chart = new Chart($("ts-chart"), {
    type: "bar",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { color: muted, maxRotation: 0, autoSkipPadding: 12 } },
        y: { stacked: true, grid: { color: grid }, border: { display: false }, ticks: { color: muted, callback: (v) => compact(v) } },
      },
      plugins: {
        legend: { position: "bottom", labels: { color: text2, boxWidth: 10, boxHeight: 10, useBorderRadius: true, borderRadius: 2 } },
        tooltip: {
          itemSort: (a, b) => b.raw - a.raw,
          filter: (item) => item.raw > 0.005,
          callbacks: {
            label: (c) => ` ${c.dataset.label}: ${money(c.raw)}`,
            footer: (items) => items.length ? `Total: ${money(totals[items[0].dataIndex])}` : "",
          },
        },
      },
    },
  });
}

// ---------- breakdown ----------
function renderTabs() {
  const tabs = $("tabs");
  tabs.innerHTML = "";
  Object.entries(state.meta.dimensions).forEach(([key, label]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.role = "tab";
    b.textContent = label;
    b.setAttribute("aria-selected", String(state.dimension === key));
    b.onclick = () => { state.dimension = key; renderTabs(); loadBreakdown(); };
    tabs.append(b);
  });
  if (state.tags?.length) {
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", "Group by tag");
    sel.innerHTML = `<option value="">By tag…</option>` + state.tags.map((t) => `<option ${state.dimension === "TAG:" + t ? "selected" : ""}>${esc(t)}</option>`).join("");
    sel.onchange = () => { if (sel.value) { state.dimension = "TAG:" + sel.value; renderTabs(); loadBreakdown(); } };
    tabs.append(sel);
  }
}

async function loadBreakdown() {
  const range = currentRange();
  try {
    state.breakdown = await api("breakdown", { ...range, metric: $("metric").value, group_by: state.dimension });
    renderRows();
  } catch (err) { showError(err); }
}

function renderRows() {
  const b = state.breakdown;
  if (!b) return;
  const q = $("filter").value.trim().toLowerCase();
  const rows = b.items.filter((i) => !q || i.label.toLowerCase().includes(q));
  const max = Math.max(...b.items.map((i) => Math.abs(i.amount)), 0) || 1;
  $("rows").innerHTML = rows.length
    ? rows.map((i) => `
      <tr>
        <td class="name">${esc(i.label)}</td>
        <td class="bar-col"><div class="bar ${i.amount < 0 ? "neg" : ""}" style="width:${(Math.abs(i.amount) / max) * 100}%"></div></td>
        <td class="num">${money(i.amount)}</td>
        <td class="num">${(i.share * 100).toFixed(1)}%</td>
      </tr>`).join("")
    : `<tr><td colspan="4" class="empty">${b.items.length ? "No rows match the filter" : "No spend in this range"}</td></tr>`;
  $("foot-total").textContent = money(b.total);
  $("row-count").textContent = `(${b.items.length} ${b.items.length === 1 ? "item" : "items"})`;
}

function exportCsv() {
  const b = state.breakdown;
  if (!b) return;
  const cell = (s) => `"${String(s).replace(/"/g, '""')}"`;
  const lines = [["name", "key", "cost", "share"].join(","), ...b.items.map((i) => [cell(i.label), cell(i.key), i.amount.toFixed(4), i.share.toFixed(6)].join(","))];
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
  a.download = `costs_${b.group_by.replace(":", "-").toLowerCase()}_${b.start}_${b.end}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---------- orchestration ----------
async function loadRangeViews() {
  const range = currentRange();
  const metric = $("metric").value;
  $("kpi-range-sub").textContent = rangeLabel(range);
  try {
    showError(null);
    const [total] = await Promise.all([loadTimeseries(metric, range), loadBreakdown()]);
    $("kpi-range").textContent = money(total);
  } catch (err) { showError(err); }
}

async function loadAll() {
  try {
    showError(null);
    await loadSummary($("metric").value);
  } catch (err) { showError(err); }
  await loadRangeViews();
}

async function init() {
  try {
    state.meta = await api("meta");
  } catch (err) { showError(err); return; }

  const badge = $("provider-badge");
  badge.hidden = false;
  badge.textContent = state.meta.provider.toUpperCase();

  $("metric").innerHTML = state.meta.metrics.map((m) => `<option value="${m}">${m.replace(/([a-z])([A-Z])/g, "$1 $2")}</option>`).join("");
  $("ts-group").innerHTML = Object.entries(state.meta.dimensions)
    .filter(([k]) => ["SERVICE", "LINKED_ACCOUNT", "REGION", "RECORD_TYPE", "PURCHASE_TYPE"].includes(k))
    .map(([k, v]) => `<option value="${k}">${v}</option>`).join("");

  try { state.tags = (await api("tags")).tags; } catch { state.tags = []; }
  renderTabs();

  const today = todayUTC();
  $("start").value = iso(monthStart(today, -2));
  $("end").value = iso(today);

  $("range").onchange = () => { $("custom-range").hidden = $("range").value !== "custom"; loadRangeViews(); };
  $("start").onchange = $("end").onchange = loadRangeViews;
  $("metric").onchange = loadAll;
  $("ts-group").onchange = () => loadTimeseries($("metric").value, currentRange()).catch(showError);
  $("filter").oninput = renderRows;
  $("export").onclick = exportCsv;
  $("refresh").onclick = async () => {
    $("refresh").disabled = true;
    try { await api("refresh", {}, { method: "POST" }); await loadAll(); }
    catch (err) { showError(err); }
    finally { $("refresh").disabled = false; }
  };
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => loadRangeViews());

  await loadAll();
}

init();
