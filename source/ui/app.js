"use strict";
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
let state = null;
let screen = null;
let lastLogKey = null;

// ---- тексты окна на двух языках (сообщения программы переводит она сама)
const I18N = {
  ru: {
    "setup.tagline": "Свободный доступ к YouTube и Discord",
    "setup.s1": "Скачаю движок", "setup.s1d": "Официальный zapret с GitHub",
    "setup.s2": "Проверю подлинность", "setup.s2d": "Сверю SHA-256 до последнего байта",
    "setup.s3": "Подберу настройку", "setup.s3d": "Под вашего провайдера, автоматически",
    "setup.auto": "Ничего нажимать не нужно — всё произойдёт само",
    "setup.retry": "Повторить", "setup.folder": "У меня уже есть папка zapret",
    "setup.av": "Антивирус может ругаться на WinDivert — это драйвер перехвата пакетов, без него обход невозможен.",
    "nav.settings": "Настройки", "nav.back": "Назад",
    "main.power": "Включить или выключить обход", "main.strategy": "Стратегия",
    "main.auto": "Подобрать автоматически", "main.stop": "Остановить подбор", "main.check": "Проверить доступ",
    "main.checkd": "Открываются ли YouTube и Discord",
    "up.min": "Работает {} мин", "up.hour": "Работает {} ч {} мин", "up.now": "Только что включён",
    "set.game": "Игровой режим", "set.gamed": "Обход и для игр, порты 1024–65535",
    "set.open": "Включать при открытии", "set.opend": "Сразу запускать последнюю стратегию",
    "set.auto": "Запуск вместе с Windows", "set.autod": "Тихо стартовать в трее при входе",
    "set.look": "Оформление", "set.lang": "Язык", "set.theme": "Тема", "set.auto_opt": "Авто",
    "set.light": "Светлая", "set.dark": "Тёмная",
    "set.langd": "«Авто» — по региону Windows: русский для СНГ, английский для остальных стран.",
    "set.engine": "Движок", "set.version": "Версия", "set.update": "Проверить обновление",
    "set.log": "Журнал", "set.hashes": "Контрольные суммы", "set.open_dir": "Открыть папку движка",
    "set.change_dir": "Указать другую папку", "set.repo": "Исходники движка",
    "set.privacy": "Конфиденциальность", "set.uninstall": "Удалить Prohod с компьютера",
    "f1": "Трафик не уходит на чужие серверы", "f1d": "Это не VPN и не прокси — пакеты меняются прямо на компьютере",
    "f2": "В сеть — только к GitHub", "f2d": "Обновления и движок. Телеметрии нет",
    "f3": "Подлинность проверяется", "f3d": "SHA-256 при установке и перед каждым запуском",
    "hash.none": "нет файла", "hash.missing": "Движок не установлен", "hash.folder": "Папка",
    "hash.copy": "нажмите, чтобы скопировать", "hash.copied": "Хэш скопирован",
    "log.copy": "Копировать", "log.copied": "Журнал скопирован",
    "repo.copied": "Адрес скопирован — откройте его в браузере",
    "chip.off": "Выключен", "chip.on": "Работает",
    "upd.title": "Доступно обновление", "upd.sub": "Движок zapret · проверяется по SHA-256",
    "upd.more": "Что нового", "upd.empty": "Список изменений не опубликован.",
    "upd.apply": "Обновить", "upd.later": "Позже", "upd.skip": "Пропустить эту версию",
    "dlg.ok": "Понятно", "dlg.yes": "Да", "dlg.no": "Нет",
    "offline": "Окно потеряло связь с программой. Закройте его и запустите Prohod снова.",
  },
  en: {
    "setup.tagline": "Open access to YouTube and Discord",
    "setup.s1": "Download the engine", "setup.s1d": "Official zapret from GitHub",
    "setup.s2": "Verify authenticity", "setup.s2d": "SHA-256 checked down to the last byte",
    "setup.s3": "Find the right setting", "setup.s3d": "Tuned to your provider, automatically",
    "setup.auto": "Nothing to press — it all happens by itself",
    "setup.retry": "Retry", "setup.folder": "I already have a zapret folder",
    "setup.av": "Antivirus may flag WinDivert — it's a packet driver, and the bypass can't work without it.",
    "nav.settings": "Settings", "nav.back": "Back",
    "main.power": "Turn the bypass on or off", "main.strategy": "Strategy",
    "main.auto": "Find automatically", "main.stop": "Stop searching", "main.check": "Check access",
    "main.checkd": "Whether YouTube and Discord open",
    "up.min": "On for {} min", "up.hour": "On for {} h {} min", "up.now": "Just turned on",
    "set.game": "Game mode", "set.gamed": "Bypass for games too, ports 1024–65535",
    "set.open": "Turn on at launch", "set.opend": "Start the last strategy right away",
    "set.auto": "Start with Windows", "set.autod": "Start quietly in the tray at sign-in",
    "set.look": "Appearance", "set.lang": "Language", "set.theme": "Theme", "set.auto_opt": "Auto",
    "set.light": "Light", "set.dark": "Dark",
    "set.langd": "“Auto” follows your Windows region: Russian in CIS countries, English elsewhere.",
    "set.engine": "Engine", "set.version": "Version", "set.update": "Check for updates",
    "set.log": "Log", "set.hashes": "Checksums", "set.open_dir": "Open engine folder",
    "set.change_dir": "Choose another folder", "set.repo": "Engine source",
    "set.privacy": "Privacy", "set.uninstall": "Remove Prohod from this computer",
    "f1": "Traffic never goes to third-party servers", "f1d": "Not a VPN or proxy — packets are changed right on your PC",
    "f2": "Only talks to GitHub", "f2d": "Updates and the engine. No telemetry",
    "f3": "Authenticity is verified", "f3d": "SHA-256 at install and before every start",
    "hash.none": "no file", "hash.missing": "Engine not installed", "hash.folder": "Folder",
    "hash.copy": "click to copy", "hash.copied": "Hash copied",
    "log.copy": "Copy", "log.copied": "Log copied",
    "repo.copied": "Link copied — open it in your browser",
    "chip.off": "Off", "chip.on": "On",
    "upd.title": "Update available", "upd.sub": "zapret engine · verified with SHA-256",
    "upd.more": "What's new (in Russian)", "upd.empty": "No changelog was published.",
    "upd.apply": "Update", "upd.later": "Later", "upd.skip": "Skip this version",
    "dlg.ok": "OK", "dlg.yes": "Yes", "dlg.no": "No",
    "offline": "The window lost connection to the app. Close it and start Prohod again.",
  },
};
let lang = (navigator.language || "").toLowerCase().startsWith("ru") ? "ru" : "en";  // до первого ответа программы
const t = (key, ...args) => {
  let s = (I18N[lang] && I18N[lang][key]) || I18N.ru[key] || key;
  for (const a of args) s = s.replace("{}", a);
  return s;
};

function applyLang(next) {
  lang = next === "en" ? "en" : "ru";
  document.documentElement.lang = lang;
  for (const el of $$("[data-t]")) el.textContent = t(el.dataset.t);
  for (const el of $$("[data-t-aria]")) el.setAttribute("aria-label", t(el.dataset.tAria));
  updKey = null;  // перерисовать подписи в карточке обновления
  if (screen === "settings" && !$("#sec-kv").hidden) loadHashes();
}

function applyTheme(theme) {
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;
}

// ---- связь с программой: в собранном Prohod — мост окна, в режиме разработки — локальный сервер
const bridge = () => (window.pywebview && window.pywebview.api) || null;

async function api(action, body = {}) {
  const b = bridge();
  try {
    if (b) {
      if (action === "pick") await b.pick(body.name);
      else if (action === "toggle") await b.toggle(body.key, body.value);
      else if (action === "pref") await b.pref(body.key, body.value);
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
  const order = ["setup", "main", "settings", "log"];
  for (const el of $$(".screen")) {
    const n = el.id.slice(2);
    el.classList.toggle("active", n === name);
    el.classList.toggle("back", order.indexOf(n) < order.indexOf(name));
  }
  screen = name;
  document.body.classList.toggle("on-main", name === "main" || name === "setup");
  closePopover();
  if (name === "log") { const l = $("#log"); l.scrollTop = l.scrollHeight; }
}

function toast(text) {
  const el = $("#toast");
  el.textContent = text;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 1800);
}

function uptime() {
  const on = !!(state && state.power === "on" && state.on_since);
  $("#uptime").classList.toggle("show", on);
  if (!on) return;
  const min = Math.floor((Date.now() / 1000 - state.on_since) / 60);
  $("#uptime-text").textContent = min < 1 ? t("up.now") : min < 60 ? t("up.min", min) : t("up.hour", Math.floor(min / 60), min % 60);
}

const RING = 2 * Math.PI * 95;  // длина окружности кольца прогресса
function renderOrb(s) {
  const orb = $("#orb");
  if (orb.dataset.state !== "on" && s.power === "on") {  // только что включился — вспышка сияния
    orb.classList.add("pop");
    clearTimeout(renderOrb.timer);
    renderOrb.timer = setTimeout(() => orb.classList.remove("pop"), 900);
  }
  orb.dataset.state = s.power;
  $("#backdrop").dataset.state = s.power;
  const p = s.auto_progress;
  orb.classList.toggle("auto", !!p);
  $("#arc").style.strokeDashoffset = p ? String(RING * (1 - Math.max(0.03, p[0] / p[1]))) : "";
}
setInterval(uptime, 15000);

function render(s) {
  if (state && typeof s.version === "number" && s.version < state.version) return;  // устаревший снимок
  const langChanged = !state || state.lang !== s.lang;
  state = s;
  if (langChanged) applyLang(s.lang);
  applyTheme(s.prefs && s.prefs.theme);
  if (screen === null || screen === "setup" || s.screen === "setup") show(s.screen);

  $("#power").dataset.state = s.power;
  renderOrb(s);
  $("#title").textContent = s.title;
  $("#sub").textContent = s.sub;
  uptime();
  $("#strategy").textContent = s.strategy || "—";
  $("#engine").textContent = s.engine || "—";
  $("#auto-note").textContent = s.auto_note;
  $("#auto-label").textContent = s.auto ? t("main.stop") : t("main.auto");
  $("#b-auto").classList.toggle("stop", s.auto);
  document.title = "Prohod — " + (s.power === "on" ? t("chip.on") : t("chip.off"));

  for (const [svc, p] of Object.entries(s.pills)) {
    const el = $("#p-" + svc);
    if (!el) continue;
    el.dataset.tone = p.tone;
    el.querySelector(".note").textContent = p.note;
  }
  for (const sw of $$(".switch")) sw.setAttribute("aria-checked", String(!!s.toggles[sw.dataset.key]));
  for (const seg of $$(".seg")) {
    const cur = (s.prefs || {})[seg.dataset.pref] || "auto";
    for (const b of seg.children) b.setAttribute("aria-pressed", String(b.dataset.v === cur));
  }

  const busy = s.busy;
  for (const id of ["#select", "#b-check", "#b-download", "#b-folder", "#b-folder2", "#b-update"]) $(id).disabled = busy;
  $("#b-auto").disabled = busy && !s.auto;
  $("#power").disabled = busy && !s.auto;
  $("#b-uninstall").disabled = busy;
  $("#upd-apply").disabled = busy;  // пока идёт другая задача, обновлять нельзя — карточка подождёт

  const st = $("#setup-status");
  st.textContent = s.setup.text || "";
  st.dataset.tone = s.setup.tone || "muted";
  const pr = $("#dl-progress");
  pr.style.display = typeof s.setup.progress === "number" ? "block" : "none";
  if (typeof s.setup.progress === "number") pr.firstElementChild.style.width = (s.setup.progress * 100).toFixed(1) + "%";
  const steps = $("#steps");
  if (s.setup.step) steps.dataset.step = s.setup.step; else delete steps.dataset.step;
  if (s.setup.tone === "ok") steps.dataset.done = ""; else delete steps.dataset.done;
  $("#setup-actions").hidden = !s.setup.retry;
  $("#setup-auto").hidden = !!s.setup.retry;
  $("#about").textContent = "Prohod " + (s.app_version || "") + (s.engine ? " · " + s.engine : "");

  renderLog(s.log);
  renderUpdate(s.update);
  renderDialog(s.dialog);
}

let updKey = null;
function renderUpdate(u) {
  const box = $("#upd");
  if (!u) { box.classList.remove("open"); updKey = null; return; }
  const key = lang + ":" + u.current + ">" + u.latest;
  if (key === updKey) return;
  const first = !updKey || !updKey.endsWith(u.current + ">" + u.latest);
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
  $("#upd-more-label").textContent = t("upd.more") + (notes.length ? " · " + notes.length : "");
  if (first) {
    box.classList.remove("expanded");
    $("#upd-more").setAttribute("aria-expanded", "false");
  }
  box.classList.add("open");
}

function renderLog(lines) {
  const key = lines.length + ":" + (lines.length ? lines[lines.length - 1].join("|") : "");
  if (key === lastLogKey) return;
  lastLogKey = key;
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
const answered = new Set();  // ответы в пути: не показывать этот диалог снова, пока программа не подтвердит
function renderDialog(d) {
  const scrim = $("#scrim");
  if (!d || answered.has(d.id)) { scrim.classList.remove("open"); dialogId = null; return; }
  if (d.id === dialogId) return;
  dialogId = d.id;
  $("#dlg-text").textContent = d.text;
  const acts = $("#dlg-acts");
  acts.className = "acts" + (d.kind === "alert" ? " one" : "");
  const mk = (label, strong, yes) => {
    const b = document.createElement("button");
    b.textContent = label;
    if (strong) b.className = "strong";
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
    ? [mk(t("dlg.ok"), true, true)]
    : [mk(t("dlg.no"), false, false), mk(t("dlg.yes"), true, true)];
  acts.replaceChildren(...buttons);
  scrim.classList.add("open");
  // Диалог появляется внезапно: короткая пауза и фокус на «Нет», чтобы случайный Enter
  // или пробел не подтвердил то, чего человек не читал.
  for (const b of buttons) b.disabled = true;
  setTimeout(() => { for (const b of buttons) b.disabled = false; buttons[0].focus(); }, 700);
}

async function loadHashes() {
  const kv = $("#sec-kv");
  try {
    const info = await securityInfo();
    const rows = [];
    const add = (k, v, full = "") => {
      const a = document.createElement("div"); a.className = "k"; a.textContent = k;
      const b = document.createElement("div"); b.className = "v" + (full ? " hash" : ""); b.textContent = v;
      if (full) {
        b.title = full + "\n(" + t("hash.copy") + ")";
        b.onclick = () => navigator.clipboard.writeText(full).then(() => toast(t("hash.copied")));
      }
      rows.push(a, b);
    };
    if (!info.installed) add("—", t("hash.missing"));
    else {
      add(t("hash.folder"), info.short, info.path);
      for (const f of info.files) add(f.name, f.sha256 ? f.sha256.slice(0, 20) + "…" : t("hash.none"), f.sha256);
    }
    kv.replaceChildren(...rows);
  } catch (e) { /* окно закрывается */ }
}

// ---- выпадающий список стратегий
function openPopover() {
  const pop = $("#popover"), sel = $("#select");
  const r = sel.getBoundingClientRect();
  pop.style.left = (r.left + 8) + "px";
  pop.style.width = (r.width - 16) + "px";
  const above = r.top - 12, below = innerHeight - r.bottom - 12;
  const h = Math.min(360, Math.max(above, below));
  pop.style.maxHeight = h + "px";
  // список длинный, а строка внизу экрана: открываем вверх, если снизу места меньше
  if (below >= Math.min(260, above)) { pop.style.top = (r.bottom + 6) + "px"; pop.style.bottom = ""; pop.style.transformOrigin = "top center"; }
  else { pop.style.top = ""; pop.style.bottom = (innerHeight - r.top + 6) + "px"; pop.style.transformOrigin = "bottom center"; }
  pop.replaceChildren(...state.strategies.map((n) => {
    const b = document.createElement("button");
    b.setAttribute("role", "option");
    const label = document.createElement("span");
    label.textContent = n;
    b.append(label);
    if (n === state.strategy) {
      b.setAttribute("aria-selected", "true");
      b.insertAdjacentHTML("beforeend", '<svg><use href="#i-check"/></svg>');
    }
    b.onclick = () => { closePopover(); api("pick", { name: n }); };
    return b;
  }));
  pop.classList.add("open");
  sel.setAttribute("aria-expanded", "true");
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
  .then(() => toast(t("repo.copied")));
$("#b-uninstall").onclick = () => api("uninstall");  // подтверждение — системным окном Windows
$("#b-hashes").onclick = () => {
  const kv = $("#sec-kv"), open = kv.hidden;
  kv.hidden = !open;
  $("#b-hashes").setAttribute("aria-expanded", String(open));
  $("#hash-chev").style.transform = open ? "rotate(180deg)" : "";
  if (open) loadHashes();
};
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
  navigator.clipboard.writeText(text).then(() => toast(t("log.copied")));
};
$("#select").onclick = (e) => { e.stopPropagation(); $("#popover").classList.contains("open") ? closePopover() : openPopover(); };
document.addEventListener("click", (e) => { if (!$("#popover").contains(e.target)) closePopover(); });
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if ($("#popover").classList.contains("open")) return closePopover();
  if (screen === "log") show("settings");
  else if (screen === "settings") show("main");
});
for (const b of $$("[data-go]")) b.onclick = () => show(b.dataset.go);
for (const sw of $$(".switch")) sw.onclick = () => {
  const v = sw.getAttribute("aria-checked") !== "true";
  if (sw.dataset.key !== "autostart") sw.setAttribute("aria-checked", String(v));  // мгновенный отклик
  api("toggle", { key: sw.dataset.key, value: v });
};
for (const seg of $$(".seg")) for (const b of seg.children) b.onclick = () => {
  for (const x of seg.children) x.setAttribute("aria-pressed", String(x === b));  // мгновенный отклик
  if (seg.dataset.pref === "theme") applyTheme(b.dataset.v);
  api("pref", { key: seg.dataset.pref, value: b.dataset.v });
};
window.addEventListener("resize", closePopover);
// перетащенный в окно файл или ссылка не должны открываться вместо интерфейса
document.addEventListener("dragover", (e) => e.preventDefault());
document.addEventListener("drop", (e) => e.preventDefault());
applyLang(lang);

// ---- поток состояния
window.__prohod = (s) => { $("#offline").classList.remove("show"); render(s); };  // сюда программа шлёт состояние

// Способ связи определяется по факту: мост сообщает о готовности сам,
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
