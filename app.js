"use strict";

// ---------- フォーマッタ ----------
const nf = (d = 2) => new Intl.NumberFormat("ja-JP", { minimumFractionDigits: d, maximumFractionDigits: d });
const fmt = (v, d = 2) => (v == null || Number.isNaN(v) ? "—" : nf(d).format(v));
const fmtUsd = (v, d = 2) => (v == null ? "—" : "$" + nf(d).format(v));
const fmtPct = (v, d = 2) => (v == null ? "—" : nf(d).format(v) + "%");

function fmtCompactUsd(v) {
  if (v == null) return "—";
  const a = Math.abs(v);
  if (a >= 1e12) return "$" + (v / 1e12).toFixed(2) + "T";
  if (a >= 1e9) return "$" + (v / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return "$" + (v / 1e6).toFixed(2) + "M";
  return fmtUsd(v);
}
function fmtCompactShares(v) {
  if (v == null) return "—";
  const a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2) + "B株";
  if (a >= 1e6) return (v / 1e6).toFixed(1) + "M株";
  if (a >= 1e3) return (v / 1e3).toFixed(1) + "K株";
  return String(v);
}
function fmtDateTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("ja-JP", {
      timeZone: "Asia/Tokyo", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}
function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("ja-JP", { timeZone: "Asia/Tokyo", year: "numeric", month: "numeric", day: "numeric" });
  } catch { return iso; }
}

async function loadJson(name) {
  const res = await fetch(`./data/${name}?t=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${name}: ${res.status}`);
  return res.json();
}

// ---------- 現在値 ----------
function renderHero(price) {
  const q = price.quote || {};
  document.getElementById("price").textContent = fmtUsd(q.price);
  const ch = document.getElementById("change");
  if (q.change != null && q.change_pct != null) {
    const up = q.change >= 0;
    ch.textContent = `${up ? "+" : ""}${fmt(q.change)} (${up ? "+" : ""}${fmt(q.change_pct)}%)`;
    ch.className = "change " + (up ? "up" : "down");
  } else {
    ch.textContent = "—";
  }
  document.getElementById("hero-meta").innerHTML = `
    <div><b>${fmtUsd(q.day_high)}</b>当日高値</div>
    <div><b>${fmtUsd(q.day_low)}</b>当日安値</div>
    <div><b>${fmtUsd(q.previous_close)}</b>前日終値</div>`;
}

// ---------- 株価チャート ----------
let chart, candleSeries, priceData = {}, activeRange = "1M";

function buildChart() {
  const el = document.getElementById("chart");
  chart = LightweightCharts.createChart(el, {
    width: el.clientWidth,
    height: el.clientHeight,
    layout: { background: { color: "transparent" }, textColor: "#8b97a6", fontSize: 11 },
    grid: { vertLines: { color: "#1c232c" }, horzLines: { color: "#1c232c" } },
    rightPriceScale: { borderColor: "#232b35" },
    timeScale: { borderColor: "#232b35", timeVisible: true, secondsVisible: false },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    handleScale: true, handleScroll: true,
  });
  candleSeries = chart.addCandlestickSeries({
    upColor: "#2ebd85", downColor: "#f6465d", borderVisible: false,
    wickUpColor: "#2ebd85", wickDownColor: "#f6465d",
  });
  new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight })).observe(el);
}

function setRange(key) {
  activeRange = key;
  const data = priceData[key] || [];
  candleSeries.setData(data);
  chart.timeScale().fitContent();
  document.querySelectorAll(".range-btn").forEach((b) => b.classList.toggle("active", b.dataset.range === key));
}

function renderRanges(price) {
  priceData = price.series || {};
  const wrap = document.getElementById("ranges");
  const keys = Object.keys(priceData).filter((k) => (priceData[k] || []).length > 0);
  wrap.innerHTML = "";
  keys.forEach((k) => {
    const btn = document.createElement("button");
    btn.className = "range-btn";
    btn.dataset.range = k;
    btn.textContent = k;
    btn.onclick = () => setRange(k);
    wrap.appendChild(btn);
  });
  const initial = keys.includes("1M") ? "1M" : keys[0];
  if (initial) setRange(initial);
}

// ---------- 指標 ----------
function metricCard(label, value, sub) {
  return `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div>${sub ? `<div class="sub">${sub}</div>` : ""}</div>`;
}
function renderMetrics(f) {
  const m = f.metrics || {};
  const cards = [
    metricCard("実績 PER", fmt(m.trailingPE), "trailing P/E"),
    metricCard("フォワード PER", fmt(m.forwardPE), "forward P/E"),
    metricCard("時価総額", fmtCompactUsd(m.marketCap)),
    metricCard("実績 EPS", fmtUsd(m.trailingEps)),
    metricCard("予想 EPS", fmtUsd(m.forwardEps)),
  ];
  if (m.revenueGrowth != null) cards.push(metricCard("増収率", fmtPct(m.revenueGrowth * 100)));
  document.getElementById("metrics").innerHTML = cards.join("");
}

// ---------- 空売り残高 ----------
let shortChart = null;
function renderShort(s) {
  const changeCls = s.shares_short_change_pct == null ? "" : (s.shares_short_change_pct >= 0 ? "metric-up" : "metric-down");
  const changeTxt = s.shares_short_change_pct == null ? "" :
    `<span class="${changeCls}">${s.shares_short_change_pct >= 0 ? "+" : ""}${fmt(s.shares_short_change_pct)}% 前月比</span>`;
  document.getElementById("si-date").textContent = s.date_short_interest ? `基準日 ${fmtDate(s.date_short_interest)}` : "";
  document.getElementById("short-metrics").innerHTML = [
    metricCard("空売り残高", fmtCompactShares(s.shares_short), changeTxt),
    metricCard("空売り比率", fmt(s.short_ratio), "days to cover"),
    metricCard("対浮動株比率", s.short_percent_of_float == null ? "—" : fmtPct(s.short_percent_of_float * 100)),
  ].join("");

  if (s.shares_short != null && s.shares_short_prior_month != null && window.Chart) {
    const ctx = document.getElementById("short-chart");
    if (shortChart) shortChart.destroy();
    shortChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["前月", "今回"],
        datasets: [{
          data: [s.shares_short_prior_month / 1e6, s.shares_short / 1e6],
          backgroundColor: ["#3a4654", "#76b900"],
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.parsed.y.toFixed(1)}M株` } } },
        scales: {
          x: { grid: { display: false }, ticks: { color: "#8b97a6" } },
          y: { grid: { color: "#1c232c" }, ticks: { color: "#8b97a6", callback: (v) => v + "M" } },
        },
      },
    });
  }
}

// ---------- ニュース ----------
function renderNews(n) {
  const ul = document.getElementById("news");
  const items = n.items || [];
  ul.innerHTML = items.map((it) => `
    <li><a href="${it.link}" target="_blank" rel="noopener">
      <div class="n-title">${escapeHtml(it.title)}</div>
      <div class="n-meta">${escapeHtml(it.source)}・${it.published ? fmtDateTime(it.published) : ""}</div>
    </a></li>`).join("") || `<li><a>ニュースを取得できませんでした</a></li>`;
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- X(Twitter) ----------
function renderX(x) {
  const ul = document.getElementById("x-feed");
  const items = (x && x.items) || [];
  ul.innerHTML = items.map((it) => `
    <li><a href="${it.link}" target="_blank" rel="noopener">
      <div class="n-title">${escapeHtml(it.text)}</div>
      <div class="n-meta">${it.author ? escapeHtml(it.author) + "・" : ""}${it.published ? fmtDateTime(it.published) : ""}</div>
    </a></li>`).join("") || `<li><a>X投稿を取得できませんでした</a></li>`;
}

// ---------- 決算まとめ ----------
function renderEarnings(e) {
  const el = document.getElementById("earnings");
  if (!e || !e.quarter) {
    el.innerHTML = `<p class="note">決算情報がまだありません。</p>`;
    return;
  }
  const head = `<div class="card-head"><h2>${escapeHtml(e.quarter)} 決算</h2><span class="hint">${e.report_date ? fmtDate(e.report_date) + " 発表" : ""}</span></div>`;
  const summary = e.summary ? `<p class="earnings-summary">${escapeHtml(e.summary)}</p>` : "";
  const cards = (e.highlights || []).map((h) => metricCard(escapeHtml(h.label), escapeHtml(h.value), h.note ? escapeHtml(h.note) : "")).join("");
  const grid = cards ? `<div class="metrics">${cards}</div>` : "";
  const sources = (e.sources || []).map((s) =>
    `<a href="${s.url}" target="_blank" rel="noopener">${escapeHtml(s.label)} ↗</a>`).join("");
  const src = sources ? `<div class="earnings-sources">情報元: ${sources}</div>` : "";
  el.innerHTML = head + summary + grid + src;
}

// ---------- タブ切替 ----------
function setupTabs() {
  const btns = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".tab-panel");
  btns.forEach((btn) => {
    btn.onclick = () => {
      const tab = btn.dataset.tab;
      btns.forEach((b) => b.classList.toggle("active", b === btn));
      panels.forEach((p) => p.classList.toggle("active", p.id === `tab-${tab}`));
      // 隠れていたパネルでChart.jsを描画するとサイズ0になるため、表示時にリサイズ
      if (tab === "short" && shortChart) shortChart.resize();
    };
  });
}

// ---------- 起動 ----------
async function init() {
  buildChart();
  setupTabs();

  const tasks = [
    ["price.json", (d) => { renderHero(d); renderRanges(d); document.getElementById("updated").textContent = "更新 " + fmtDateTime(d.updated_at); }],
    ["fundamentals.json", renderMetrics],
    ["short_interest.json", renderShort],
    ["news.json", renderNews],
    ["x.json", renderX],
    ["earnings.json", renderEarnings],
  ];
  await Promise.all(tasks.map(async ([name, fn]) => {
    try { fn(await loadJson(name)); }
    catch (e) { console.error(e); }
  }));
}

document.addEventListener("DOMContentLoaded", init);

// Service Worker 登録
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(console.error));
}
