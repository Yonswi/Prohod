"use strict";
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
let state = null;
let screen = null;
let lastLogLen = -1;

// Связь с программой: в собранном Prohod — мост окна (window.pywebview.api),
// в режиме разработки — локальный сервер с cookie сессии.
const bridge = () => (window.pywebview && window.pywebview.api) || null;

async function api(action, body = {}) {
  const b = bridge();
  try {
    if (b) {
      if (action === "pick") await b.pick(body.name);
      else if (action === "toggle") await b.toggle(body.key, body.value);
      else if (action === "answer") await b.answer(body.id, body.yes);
      else await b[action]();
      return { ok: true };
    }
    return await fetch("/api/" + action, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Prohod": "1" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    return null;
  }
}

async function securityInfo() {
  const b = bridge();
  return b ? b.security() : (await fetch("/api/security")).json();
}

function show(name) {
  if (name === screen) return;
  const order = ["setup", "main", "log", "security"];
  for (const el of $$(".screen")) {
    const n = el.id.slice(2);
    el.classList.toggle("active", n === name);
    el.classList.toggle("back", order.indexOf(n) < order.indexOf(name));
  }
  screen = name;
  if (name === "security") loadSecurity();
  if (name === "log") { const l = $("#log"); l.scrollTop = l.scrollHeight; }
}

function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("show"), 1600);
}

const CHIP = { off: "Выключен", starting: "Запуск…", on: "Работает", error: "Ошибка" };

function render(s) {
  if (state && typeof s.version === "number" && s.version < state.version) return;  // устаревший снимок
  state = s;
  if (screen === null || screen === "setup" || s.screen === "setup") show(s.screen);

  $("#power").dataset.state = s.power;
  $("#chip").dataset.tone = s.power;
  $("#chip-text").textContent = CHIP[s.power];
  $("#title").textContent = s.title;
  $("#sub").textContent = s.sub;
  $("#strategy").textContent = s.strategy || "—";
  $("#engine").textContent = s.engine;
  $("#auto-note").textContent = s.auto_note;
  $("#auto-label").textContent = s.auto ? "Остановить подбор" : "Подобрать автоматически";
  $("#b-auto").classList.toggle("stop", s.auto);

  for (const [svc, p] of Object.entries(s.pills)) {
    const el = $("#p-" + svc);
    if (!el) continue;
    el.dataset.tone = p.tone;
    el.querySelector(".note").textContent = p.note;
  }
  for (const sw of $$(".switch")) sw.setAttribute("aria-checked", String(!!s.toggles[sw.dataset.key]));

  const busy = s.busy;
  for (const id of ["#select", "#b-check", "#b-download", "#b-folder", "#b-folder2", "#b-update"]) $(id).disabled = busy;
  $("#b-auto").disabled = busy && !s.auto;

  const st = $("#setup-status");
  st.textContent = s.setup.text || "";
  st.dataset.tone = s.setup.tone || "muted";
  const pr = $("#dl-progress");
  pr.style.display = typeof s.setup.progress === "number" ? "block" : "none";
  if (typeof s.setup.progress === "number") pr.firstElementChild.style.width = (s.setup.progress * 100).toFixed(1) + "%";

  const steps = $("#steps");
  if (s.setup.step) steps.dataset.step = s.setup.step; else delete steps.dataset.step;
  $("#setup-actions").hidden = !s.setup.retry;
  $("#setup-auto").hidden = !!s.setup.retry;
  $("#about").textContent = "Prohod " + (s.app_version || "") + (s.engine ? " · " + s.engine : "");
  $("#b-uninstall").disabled = busy;
  $("#upd-apply").disabled = busy;  // пока идёт другая задача, обновлять нельзя — карточка подождёт

  renderLog(s.log);
  renderUpdate(s.update);
  renderDialog(s.dialog);
}

let updKey = null;
function renderUpdate(u) {
  const box = $("#upd");
  if (!u) { box.classList.remove("open"); updKey = null; return; }
  const key = u.current + ">" + u.latest;
  if (key === updKey) return;
  updKey = key;
  $("#upd-from").textContent = u.current;
  $("#upd-to").textContent = u.latest;
  const notes = u.notes || [];
  $("#upd-list").replaceChildren(...notes.map((n) => {
    const li = document.createElement("li");
    li.textContent = n;
    return li;
  }));
  $("#upd-empty").hidden = notes.length > 0;
  $("#upd-more-label").textContent = notes.length ? "Что нового — " + notes.length : "Что нового";
  box.classList.remove("expanded");
  $("#upd-more").setAttribute("aria-expanded", "false");
  box.classList.add("open");
}

function renderLog(lines) {
  const key = lines.length + ":" + (lines.length ? lines[lines.length - 1].join("|") : "");
  if (key === lastLogLen) return;
  lastLogLen = key;
  const box = $("#log");
  const stick = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
  box.replaceChildren(...lines.map(([tm, msg, tag]) => {
    const row = document.createElement("div");
    row.className = "ln";
    const a = document.createElement("span"); a.className = "tm"; a.textContent = tm;
    const b = document.createElement("span"); b.className = "msg " + tag; b.textContent = msg;
    row.append(a, b);
    return row;
  }));
  if (stick) box.scrollTop = box.scrollHeight;
}

let dialogId = null;
const answered = new Set();  // ответы в пути: не показывать этот диалог снова, пока сервер не подтвердит
function renderDialog(d) {
  const scrim = $("#scrim");
  if (!d || answered.has(d.id)) { scrim.classList.remove("open"); dialogId = null; return; }
  if (d.id === dialogId) return;
  dialogId = d.id;
  $("#dlg-text").textContent = d.text;
  const acts = $("#dlg-acts");
  acts.className = "acts" + (d.kind === "alert" ? " one" : "");
  const mk = (label, cls, yes) => {
    const b = document.createElement("button");
    b.className = "btn " + cls; b.textContent = label;
    b.onclick = async () => {
      answered.add(d.id);
      scrim.classList.remove("open");
      dialogId = null;
      const r = await api("answer", { id: d.id, yes });
      if (!r || !r.ok) { answered.delete(d.id); if (state) renderDialog(state.dialog); }  // не дошло — показать снова
    };
    return b;
  };
  const buttons = d.kind === "alert"
    ? [mk("Понятно", "btn-primary", true)]
    : [mk("Нет", "btn-plain", false), mk("Да", "btn-primary", true)];
  acts.replaceChildren(...buttons);
  scrim.classList.add("open");
  // Диалог появляется внезапно: короткая пауза и фокус на «Нет», чтобы случайный Enter
  // или пробел не подтвердил то, чего человек не читал.
  for (const b of buttons) b.disabled = true;
  setTimeout(() => { for (const b of buttons) b.disabled = false; buttons[0].focus(); }, 700);
}

async function loadSecurity() {
  const kv = $("#sec-kv");
  kv.innerHTML = "";
  try {
    const info = await securityInfo();
    const add = (k, v, cls = "", full = "") => {
      const a = document.createElement("div"); a.className = "k"; a.textContent = k;
      const b = document.createElement("div"); b.className = "v " + cls; b.textContent = v;
      if (full) { b.title = full + "\n(нажмите, чтобы скопировать)"; b.onclick = () => navigator.clipboard.writeText(full).then(() => toast("Хэш скопирован")); }
      kv.append(a, b);
    };
    if (!info.installed) { add("Статус", "движок не установлен"); return; }
    add("Версия", info.version);
    add("Папка", info.short, "", info.path);
    for (const f of info.files) add(f.name, f.sha256 ? f.sha256.slice(0, 24) + "…" : "нет файла", f.sha256 ? "hash" : "", f.sha256);
  } catch (e) { /* окно закрывается */ }
}

// ---- выпадающий список стратегий
function openPopover() {
  const pop = $("#popover"), sel = $("#select");
  const r = sel.getBoundingClientRect();
  pop.style.left = r.left + "px";
  pop.style.width = r.width + "px";
  const below = innerHeight - r.bottom - 12;
  pop.style.maxHeight = Math.max(180, Math.min(340, below)) + "px";
  pop.style.top = (r.bottom + 6) + "px";
  pop.replaceChildren(...state.strategies.map((n) => {
    const b = document.createElement("button");
    b.setAttribute("role", "option");
    b.textContent = n;
    if (n === state.strategy) {
      b.setAttribute("aria-selected", "true");
      b.insertAdjacentHTML("beforeend", '<svg><use href="#i-check"/></svg>');
    }
    b.onclick = () => { closePopover(); api("pick", { name: n }); };
    return b;
  }));
  pop.classList.add("open");
  sel.setAttribute("aria-expanded", "true");
  // прокрутить только сам список, не весь экран (scrollIntoView сдвигал страницу)
  const cur = pop.querySelector('[aria-selected="true"]');
  if (cur) pop.scrollTop = cur.offsetTop - pop.clientHeight / 2 + cur.offsetHeight / 2;
}
function closePopover() {
  $("#popover").classList.remove("open");
  $("#select").setAttribute("aria-expanded", "false");
}

// ---- события
$("#power").onclick = () => api("power");
$("#b-auto").onclick = () => api("auto");
$("#b-check").onclick = () => api("check");
$("#b-download").onclick = () => api("download");
$("#b-folder").onclick = $("#b-folder2").onclick = () => api("folder");
$("#b-update").onclick = () => api("update");
$("#b-open").onclick = () => api("open_dir");
// окно не уводит в интернет: адрес копируется, открыть его можно в своём браузере
$("#b-repo").onclick = () => navigator.clipboard.writeText("https://github.com/Flowseal/zapret-discord-youtube")
  .then(() => toast("Адрес скопирован — откройте его в своём браузере"));
$("#b-uninstall").onclick = () => api("uninstall");  // подтверждение — системным окном Windows
$("#upd-more").onclick = () => {
  const box = $("#upd");
  box.classList.toggle("expanded");
  $("#upd-more").setAttribute("aria-expanded", String(box.classList.contains("expanded")));
};
$("#upd-apply").onclick = () => { $("#upd").classList.remove("open"); api("update_apply"); };
$("#upd-later").onclick = () => { $("#upd").classList.remove("open"); api("update_later"); };
$("#upd-skip").onclick = () => { $("#upd").classList.remove("open"); api("update_skip"); };
$("#b-copy").onclick = () => {
  const text = state.log.map((l) => l[0] + "  " + l[1]).join("\n");
  navigator.clipboard.writeText(text).then(() => toast("Журнал скопирован"));
};
$("#select").onclick = (e) => { e.stopPropagation(); $("#popover").classList.contains("open") ? closePopover() : openPopover(); };
document.addEventListener("click", (e) => { if (!$("#popover").contains(e.target)) closePopover(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closePopover(); if (screen !== "main" && screen !== "setup") show("main"); } });
for (const b of $$("[data-go]")) b.onclick = () => show(b.dataset.go);
for (const sw of $$(".switch")) sw.onclick = () => {
  const v = sw.getAttribute("aria-checked") !== "true";
  if (sw.dataset.key !== "autostart") sw.setAttribute("aria-checked", String(v)); // мгновенный отклик
  api("toggle", { key: sw.dataset.key, value: v });
};
window.addEventListener("resize", closePopover);
// Перетащенный в окно файл или ссылка не должны открываться вместо интерфейса
document.addEventListener("dragover", (e) => e.preventDefault());
document.addEventListener("drop", (e) => e.preventDefault());

// ---- поток состояния
window.__prohod = (s) => { $("#offline").classList.remove("show"); render(s); };  // сюда программа шлёт состояние

// Способ связи определяется не по таймеру, а по факту: мост сообщает о готовности сам,
// а локальный сервер режима разработки отвечает на /api/ping (сервер pywebview — нет).
let mode = null;   // "bridge" | "http"
let es = null;

function connect() {
  if (mode !== "http") return;
  es = new EventSource("/api/events");
  es.onmessage = (e) => { $("#offline").classList.remove("show"); render(JSON.parse(e.data)); };
  es.onerror = () => {
    es.close();
    if (mode !== "http") return;
    $("#offline").classList.add("show");
    setTimeout(connect, 1500);
  };
}

window.addEventListener("pywebviewready", () => {
  mode = "bridge";
  if (es) { es.close(); es = null; }
  $("#offline").classList.remove("show");
  bridge().hello().then(window.__prohod);
});

(async function detect() {
  for (let i = 0; i < 40 && !mode; i++) {
    if (!window.pywebview) {
      const r = await fetch("/api/ping").catch(() => null);
      if (r && r.ok && !mode) { mode = "http"; connect(); return; }
    }
    await new Promise((res) => setTimeout(res, 250));
  }
})();
