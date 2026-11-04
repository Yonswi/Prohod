"use strict";
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
let state = null;
let screen = null;
let lastLogKey = null;

// ---- тексты окна на двух языках (сообщения программы переводит она сама)
const I18N = {
  ru: {
    "setup.tagline": "YouTube, Discord и другие сервисы — стабильное соединение",
    "setup.s1": "Скачаю движок", "setup.s1d": "Официальный zapret с GitHub",
    "setup.s2": "Проверю файлы", "setup.s2d": "Сверю контрольную сумму архива",
    "setup.s3": "Подберу настройку", "setup.s3d": "Под вашего провайдера, автоматически",
    "setup.auto": "Ничего нажимать не нужно — всё произойдёт само",
    "setup.retry": "Повторить", "setup.folder": "У меня уже есть папка zapret",
    "setup.av": "Антивирус может пожаловаться на WinDivert. Это часть движка, через которую идёт трафик: без неё обход не работает.",
    "nav.settings": "Настройки", "nav.back": "Назад", "nav.boost": "Ускорение",
    "boost.mbps": "Мбит/с", "boost.ping": "Отклик {} мс", "boost.measure": "Замерить скорость",
    "boost.again": "Замерить ещё раз", "boost.measuring": "Замеряю… {}%",
    "boost.speedd": "Скачаю до 25 МБ с каждого из трёх серверов",
    "boost.yandex": "Яндекс", "boost.avg": "Ответили {} из 3, отклик {} мс", "boost.src_run": "Замеряю {}, {} из 3",
    "boost.fail": "нет связи", "boost.ping_s": "{} мс",
    "boost.reset": "Вернуть всё как было", "boost.resetd": "DNS, Wi-Fi и настройки сети — как до NIXYZ",
    "boost.reset_btn": "Вернуть", "boost.reset_none": "NIXYZ ещё ничего не менял — возвращать нечего",
    "boost.delta_up": "▲ {}% к прошлому замеру", "boost.delta_down": "▼ {}% к прошлому замеру",
    "boost.go": "Ускорить интернет", "boost.undo": "Вернуть как было", "boost.working": "Настраиваю…",
    "boost.scanning": "Замеряю…",
    "boost.off_note": "Подберу самый быстрый DNS, уберу энергосбережение Wi-Fi и проверю настройки сети. Вернуть всё можно одной кнопкой.",
    "boost.on_note": "Ускорение включено. Прежние настройки сохранены — их можно вернуть в любой момент.",
    "boost.dns": "Сервер DNS", "boost.rescan": "Обновить", "boost.rescanning": "Замеряю…", "boost.own": "Ваш обычный DNS", "boost.own_d": "От провайдера, как до NIXYZ",
    "boost.own_ip": "{}, как до NIXYZ",
    "boost.fastest": "быстрее всех", "boost.ms": "{} мс", "boost.noanswer": "нет ответа",
    "boost.dnsd": "DNS превращает адрес сайта в IP. Быстрый DNS — сайты начинают открываться раньше.",
    "boost.tune": "Тонкая настройка",
    "boost.wifi": "Wi-Fi без энергосбережения", "boost.wifid": "Меньше задержек и обрывов, особенно на ноутбуке",
    "boost.nowifi": "Wi-Fi-адаптер не подключён",
    "boost.tcp": "Подстройка под скорость линии", "boost.tcpd": "Windows сама решает, сколько данных принимать за раз",
    "boost.flush": "Очистить кэш DNS", "boost.flush_btn": "Очистить", "boost.flushd": "Если сайт сменил адрес и перестал открываться",
    "boost.flushed": "Кэш DNS очищен",
    "boost.honest": "Скорость выше тарифа не станет — такого не умеет ни одна программа. Ускорение убирает то, что её тормозит: медленный DNS, засыпающий Wi-Fi и сбитые настройки сети.",
    "main.power": "Включить или выключить обход", "main.strategy": "Стратегия",
    "main.auto": "Подобрать автоматически", "main.stop": "Остановить подбор", "main.stopping": "Останавливаю…", "main.check": "Проверить доступ",
    "main.autod": "Переберу стратегии и оставлю лучшую", "main.checkd": "Проверить, открываются ли сервисы",
    "main.partial": "Работает частично",
    "up.min": "Работает {} мин", "up.hour": "Работает {} ч {} мин", "up.now": "Только что включён",
    "up.partial": "Открывается не всё. Попробуйте подбор", "main.picking": "подбираю…",
    "set.game": "Игровой режим", "set.gamed": "Обход работает и в онлайн-играх",
    "set.open": "Включать при открытии", "set.opend": "Сразу запускать последнюю стратегию",
    "set.auto": "Запуск вместе с Windows", "set.autod": "Тихо стартовать в трее при входе",
    "set.look": "Оформление", "set.lang": "Язык", "set.theme": "Тема", "set.auto_opt": "Авто",
    "set.light": "Светлая", "set.dark": "Тёмная",
    "set.langd": "«Авто» — по региону Windows: русский для СНГ, английский для остальных стран.",
    "set.engine": "Движок", "set.version": "Версия", "set.update": "Проверить обновление",
    "set.log": "Журнал", "set.hashes": "Проверка файлов движка", "set.open_dir": "Открыть папку движка",
    "set.change_dir": "Указать другую папку", "set.repo": "Исходный код движка",
    "legal.terms": "Пользовательское соглашение", "legal.privacy": "Политика конфиденциальности", "legal.close": "Закрыть", "legal.err": "Не удалось открыть документ",
    "set.privacy": "Конфиденциальность", "set.uninstall": "Удалить NIXYZ с компьютера",
    "f1": "Обход работает на компьютере", "f1d": "Это не VPN: пакеты меняются прямо здесь. Только «Умный обход», если его включить, ведёт ИИ-сервисы через сторонний прокси",
    "f2": "Слежки и телеметрии нет", "f2d": "В сеть — к GitHub за движком, к проверяемым сервисам и к серверам замера скорости",
    "f3": "Файлы проверяются", "f3d": "Архив сверяется по контрольной сумме при установке, файлы движка — перед каждым запуском",
    "hash.none": "нет файла", "hash.missing": "Движок не установлен", "hash.folder": "Папка",
    "hash.copy": "нажмите, чтобы скопировать", "hash.copied": "Хэш скопирован",
    "log.copy": "Копировать", "copy.fail": "Не удалось скопировать — щёлкните по окну и попробуйте ещё раз", "log.copied": "Журнал скопирован",
    "repo.copied": "Адрес скопирован — откройте его в браузере",
    "chip.off": "Выключен", "chip.on": "Работает",
    "upd.title": "Доступно обновление", "upd.sub": "Новая версия движка zapret. Перед установкой сверю контрольную сумму.",
    "upd.more": "Что нового", "upd.empty": "Список изменений не опубликован.",
    "upd.apply": "Обновить", "upd.later": "Позже", "upd.skip": "Пропустить эту версию",
    "dlg.ok": "Понятно", "dlg.yes": "Да", "dlg.no": "Нет",
    "offline": "Окно потеряло связь с программой. Закройте его и запустите NIXYZ снова.",
    // десктопная раскладка: меню, сервисы, «Списки», доступ к ИИ
    "nav.main": "Главная", "nav.lists": "Списки", "main.services": "Сервисы", "set.general": "Общие",
    // короткие статусы плиток: помещаются без многоточия
    "tone.idle": "Не проверено", "tone.wait": "Проверяю…", "tone.ok": "Открыт", "tone.warn": "Частично",
    "tone.bad": "Не открывается", "tone.geo": "Закрыт для страны",
    "svc.geo_hint": "«Закрыт для страны» — сайт открывается, но сам сервис не работает в вашей стране. Это ограничение со стороны сервиса, а не ошибка: обычный обход тут не поможет — включите «Умный обход».",
    "svc.ai": "ИИ", "ai.more": "Ещё через умный обход: DeepL, ElevenLabs, OpenRouter, Cursor",
    "ai.sum_idle": "Не проверено", "ai.sum_wait": "Проверяю…", "ai.sum_ok": "Все открываются", "ai.sum_part": "{} из {} открыты",
    "ai.sum_none": "Не открываются", "ai.sum_geo": "Закрыты в стране",
    // «Умный обход»: ИИ через умный DNS
    "smart.first": "Запросы к этим ИИ пойдут через сторонний DNS и его прокси: содержимое зашифровано, но владелец сервера видит, когда и откуда вы обращаетесь. Некоторые сервисы ограничивают работу из неподдерживаемых стран и могут заблокировать аккаунт.",
    "smart.title": "Умный обход", "smart.d": "ChatGPT, Claude, Grok и другие ИИ — через умный DNS",
    "set.smart_list": "Через умный DNS открываются: ChatGPT, Claude, Grok, DeepL, ElevenLabs, OpenRouter, Cursor.",
    "set.buddy": "Показывать NIXY", "set.buddyd": "Звёздный помощник подсказывает, когда что-то не так",
    // NIXY: реакции на игру с ним
    "buddy.ouch": ["Ай!", "Больно же!", "Эй, я на работе!", "Щекотно!"],
    "buddy.dizzy": "Ох… всё кружится",
    "buddy.check_svc": "Сейчас проверю {}…",
    "buddy.pick_stop": "Остановить подбор стратегии?", "buddy.strategy_ask": "Сейчас стратегия «{}». Подобрать лучшую?", "buddy.game_on": "Включить игровой режим?", "buddy.game_off": "Выключить игровой режим?",
    "buddy.check_ask": "Облететь и проверить все сервисы?", "buddy.diag_ask": "Проверить, почему не работает?", "buddy.go_there": "Летим: {}!", "buddy.this_is": "Это «{}». Нажать можно и без меня.",
    "svc.more": "И множество других сайтов и сервисов", 
    "buddy.menu_checks": "Что могу проверить", "buddy.menu_tasks": "Что могу сделать",
    "buddy.menu_tour": "Проверить все сервисы", "buddy.menu_site": "Проверить один сайт", "buddy.menu_speed": "Замерить скорость интернета",
    "buddy.menu_on": "Включить обход", "buddy.menu_off": "Выключить обход",
    "buddy.menu_smart_on": "Включить «Умный обход»", "buddy.menu_smart_off": "Выключить «Умный обход»", "buddy.menu_boost": "Открыть «Ускорение»",
    "buddy.menu_hide": "Спрятать NIXY", "buddy.menu_hidden": "NIXY можно вернуть в Настройках",
    "buddy.svc_ok": "{} открывается — всё в порядке ✨", "buddy.ask_power": "Обход сейчас выключен — включить?",
    "buddy.smart_on_already": "«Умный обход» уже включён — попробуйте обновить страницу сервиса через минуту.",
    "diag.engine_none": "Движка ещё нет — скачайте его", "diag.engine_bad": "Файлы движка изменены — скачайте заново",
    "diag.admin_bad": "Нет прав администратора — перезапустите NIXYZ от имени администратора",
    "diag.dpi_d": "Посторонних обходчиков не найдено", 
    "diag.dns_bad": "DNS подменяет адреса — смените его в «Ускорении»", "diag.time_d": "Время совпадает с интернетом",
    "diag.time_bad": "Часы расходятся с интернетом на {} мин — защищённые сайты не откроются",
    "diag.strategy_off": "Обход выключен — включите его", "diag.strategy_ok": "YouTube и Discord открываются",
    "diag.strategy_bad": "Открывается {} из {} — подберите стратегию заново",
    "set.export_done": "Настройки сохранены в «Загрузки»", "set.report_done": "Отчёт сохранён в «Загрузки»",
    "set.save_err": "Не получилось сохранить — подробности в журнале",
    "set.import_done": "Настройки загружены", "set.import_bad": "Это не файл настроек NIXYZ",
    "buddy.power_on": "Включить обход?", "buddy.power_off": "Выключить обход?", "buddy.pick": "Подобрать стратегию",
    "buddy.yawn": "Ой, я задремал… Чем помочь?",
    "smart.note": "Умный DNS видит, к каким ИИ вы обращаетесь.",
    "smart.how_btn": "Как это работает", "smart.setup": "Настроить",
    "smart.how": "Запросы только к адресам этих ИИ уходят к умному DNS (Comss) по HTTPS; он отвечает адресами своих прокси — те пропускают трафик к сервису без расшифровки. Остальные сайты идут как обычно.",
    // диагностика и конфликты
    "diag.open": "Почему не работает?", "diag.sub": "Проверю всё по порядку и подскажу, что исправить",
    "diag.fix": "Исправить", "diag.rerun": "Проверить ещё раз", "diag.close": "Закрыть",
    "diag.note": "Если всё зелёное, а сайт не открывается — попробуйте подбор стратегии.",
    "diag.engine": "Движок на месте", "diag.engine_d": "Файлы zapret не менялись после установки",
    "diag.admin": "Права администратора", "diag.admin_d": "Есть — драйвер WinDivert запустится",
    "diag.dpi": "Других обходчиков нет", "diag.dpi_bad": "Работает {} — два обходчика мешают друг другу",
    "diag.dns": "DNS отвечает", "diag.dns_none": "Не удалось узнать адрес сайта — похоже, нет интернета", "diag.unknown": "Проверка не завершилась — запустите диагностику ещё раз", "diag.dns_d": "Адреса сайтов определяются правильно",
    "diag.time": "Часы Windows точные",
    "diag.strategy": "Стратегия подходит", "diag.strategy_d": "Проверяю, открываются ли сервисы…",
    // настройки: защита, уведомления, модули, данные
    "set.guard": "Защита и надёжность", "set.watch": "Сторож", "set.watchd": "Следит, работает ли обход, и сам чинит, если сломался",
    "set.nightly": "Перепроверять ночью", "set.rollback": "Автооткат к рабочей стратегии",
    "set.rollbackd": "Если новая стратегия хуже — вернусь к прошлой",
    "set.notify_g": "Уведомления", "set.notify": "Уведомления Windows", "set.notifyd": "Сообщу, если обход выключился или что-то перестало открываться",
    "set.aidns": "Умный DNS для ИИ", "set.aidnsd": "Свой сервер — адрес DoH или IP:",
    "set.dns_builtin": "Встроенный", "set.dns_custom": "Свой",
    "set.aidns_ph": "dns.example.com или 1.2.3.4",
    "set.data": "Данные", "set.export": "Экспорт настроек", "set.import": "Импорт настроек",
    "set.report": "Отчёт для поддержки", "set.reportd": "Журнал и настройки одним файлом — имя пользователя и адреса в сети скрыты",
    // помощник
    "buddy.name": "NIXY — помощник", "buddy.yes": "Да", "buddy.no": "Нет", "buddy.ok": "Понятно",
    "buddy.hello": "Привет, я NIXY! Слежу, чтобы всё открывалось. Проверить, всё ли работает?",
    "buddy.thanks": "Хорошо, я рядом, если что.",
    // облёт-проверка
    "buddy.tour_ok": "Всё в порядке! {} открываются ✨", "buddy.tour_unknown": "Не дождался ответа — проверка не завершилась. Попробуйте ещё раз.",
    "buddy.prob_bad": "Вот тут проблема: {} не открывается.", "buddy.prob_warn": "{} открывается не полностью.",
    "buddy.prob_geo": "{} закрыт для вашей страны.", "buddy.ask_smart": "Включить «Умный обход»?", "buddy.ask_pick": "Подобрать стратегию?",
    "buddy.more": "И ещё {} — покажу дальше.", "buddy.next": "Дальше",
    "lists.probe_ph": "Адрес сайта, например example.com", "lists.probe": "Проверить", "lists.add": "Добавить в обход",
    "lists.ok": "Открывается", "lists.cut": "Обрывается после {} КБ", "lists.noreply": "Не отвечает",
    "lists.nodns": "Адрес не находится — такого сайта нет или его скрывает DNS", "lists.reset": "Соединение сбрасывают — похоже на блокировку",
    "lists.checking": "Проверяю…", "lists.ok_answer": "Сервер отвечает — соединение не режут", "lists.badname": "Это не похоже на адрес сайта",
    "lists.saved": "Список сохранён", "lists.save_err": "Не получилось сохранить список",
    "lists.bad_line": "Не похоже на адрес в строке {} — поправьте и сохраните ещё раз",
    "lists.general": "Обходить", "lists.exclude": "Не трогать", "lists.ipexclude": "Исключить IP",
    "lists.general_d": "Свои сайты, к которым применять обход — в дополнение к встроенным",
    "lists.exclude_d": "Сайты, которые работают и так: обход их не касается",
    "lists.ipexclude_d": "Адреса и подсети, которые обход пропускает — например, локальная сеть или игровые серверы",
    "lists.hint_general": "По одному домену на строку, например", "lists.hint_ip": "По одному адресу или подсети на строку, например",
    "lists.n_dom": ["{} домен", "{} домена", "{} доменов"], "lists.n_ip": ["{} адрес", "{} адреса", "{} адресов"],
    "lists.save": "Сохранить", "lists.about": "Что за списки",
    "lists.note": "Поддомены подхватываются сами: youtube.com включает и www.youtube.com. Строки с # — комментарии.",
  },
  en: {
    "setup.tagline": "YouTube, Discord and more — stable connections",
    "setup.s1": "Download the engine", "setup.s1d": "Official zapret from GitHub",
    "setup.s2": "Verify the files", "setup.s2d": "The archive checksum is verified",
    "setup.s3": "Find the right setting", "setup.s3d": "Tuned to your provider, automatically",
    "setup.auto": "Nothing to press — it all happens by itself",
    "setup.retry": "Retry", "setup.folder": "I already have a zapret folder",
    "setup.av": "Your antivirus may complain about WinDivert. It's the part of the engine that traffic passes through, and the bypass can't work without it.",
    "nav.settings": "Settings", "nav.back": "Back", "nav.boost": "Boost",
    "boost.mbps": "Mbit/s", "boost.ping": "Response {} ms", "boost.measure": "Test speed",
    "boost.again": "Test again", "boost.measuring": "Testing… {}%",
    "boost.speedd": "Downloads up to 25 MB from each of three servers",
    "boost.yandex": "Yandex", "boost.avg": "{} of 3 replied, response {} ms", "boost.src_run": "Testing {}, {} of 3",
    "boost.fail": "no link", "boost.ping_s": "{} ms",
    "boost.reset": "Put everything back", "boost.resetd": "DNS, Wi-Fi and network settings, as before NIXYZ",
    "boost.reset_btn": "Restore", "boost.reset_none": "NIXYZ hasn't changed anything yet — nothing to restore",
    "boost.delta_up": "▲ {}% vs last test", "boost.delta_down": "▼ {}% vs last test",
    "boost.go": "Boost my internet", "boost.undo": "Restore original settings", "boost.working": "Tuning…",
    "boost.scanning": "Measuring…",
    "boost.off_note": "I'll pick the fastest DNS, turn off Wi-Fi power saving and check network settings. One button undoes it all.",
    "boost.on_note": "Boost is on. Your original settings are saved — restore them any time.",
    "boost.dns": "DNS server", "boost.rescan": "Refresh", "boost.rescanning": "Measuring…", "boost.own": "Your usual DNS", "boost.own_d": "From your provider, as before NIXYZ",
    "boost.own_ip": "{}, as before NIXYZ",
    "boost.fastest": "fastest", "boost.ms": "{} ms", "boost.noanswer": "no reply",
    "boost.dnsd": "DNS turns a site's name into an IP address. A fast DNS makes sites start loading sooner.",
    "boost.tune": "Fine-tuning",
    "boost.wifi": "Wi-Fi without power saving", "boost.wifid": "Less lag and fewer drops, especially on laptops",
    "boost.nowifi": "No Wi-Fi adapter connected",
    "boost.tcp": "Match to line speed", "boost.tcpd": "Windows decides how much data to take in at once",
    "boost.flush": "Clear DNS cache", "boost.flush_btn": "Clear", "boost.flushd": "If a site moved and stopped opening",
    "boost.flushed": "DNS cache cleared",
    "boost.honest": "No app can make you faster than your plan. Boost removes what slows you down: a slow DNS, a sleepy Wi-Fi adapter and broken network settings.",
    "main.power": "Turn the bypass on or off", "main.strategy": "Strategy",
    "main.auto": "Find automatically", "main.stop": "Stop searching", "main.stopping": "Stopping…", "main.check": "Check access",
    "main.autod": "I'll try each strategy and keep the best", "main.checkd": "Check whether the services open",
    "main.partial": "Partly working",
    "up.min": "On for {} min", "up.hour": "On for {} h {} min", "up.now": "Just turned on",
    "up.partial": "Not everything opens. Try a search", "main.picking": "searching…",
    "set.game": "Game mode", "set.gamed": "The bypass works in online games too",
    "set.open": "Turn on at launch", "set.opend": "Start the last strategy right away",
    "set.auto": "Start with Windows", "set.autod": "Start quietly in the tray at sign-in",
    "set.look": "Appearance", "set.lang": "Language", "set.theme": "Theme", "set.auto_opt": "Auto",
    "set.light": "Light", "set.dark": "Dark",
    "set.langd": "“Auto” follows your Windows region: Russian in CIS countries, English elsewhere.",
    "set.engine": "Engine", "set.version": "Version", "set.update": "Check for updates",
    "set.log": "Log", "set.hashes": "Engine file check", "set.open_dir": "Open engine folder",
    "set.change_dir": "Choose another folder", "set.repo": "Engine source code",
    "legal.terms": "Terms of Use", "legal.privacy": "Privacy Policy", "legal.close": "Close", "legal.err": "Couldn't open the document",
    "set.privacy": "Privacy", "set.uninstall": "Remove NIXYZ from this computer",
    "f1": "The bypass works on your PC", "f1d": "Not a VPN: packets are changed right here. Only Smart bypass, if you turn it on, routes AI services through a third-party proxy",
    "f2": "No tracking or telemetry", "f2d": "Connects to GitHub for the engine, to the services being checked and to speed test servers",
    "f3": "Files are verified", "f3d": "The archive checksum is verified at install, engine files before every start",
    "hash.none": "no file", "hash.missing": "Engine not installed", "hash.folder": "Folder",
    "hash.copy": "click to copy", "hash.copied": "Hash copied",
    "log.copy": "Copy", "copy.fail": "Couldn't copy — click the window and try again", "log.copied": "Log copied",
    "repo.copied": "Link copied — open it in your browser",
    "chip.off": "Off", "chip.on": "On",
    "upd.title": "Update available", "upd.sub": "A new version of the zapret engine. I'll verify its checksum before installing.",
    "upd.more": "What's new (in Russian)", "upd.empty": "No changelog was published.",
    "upd.apply": "Update", "upd.later": "Later", "upd.skip": "Skip this version",
    "dlg.ok": "OK", "dlg.yes": "Yes", "dlg.no": "No",
    "offline": "The window lost connection to the app. Close it and start NIXYZ again.",
    "nav.main": "Home", "nav.lists": "Lists", "main.services": "Services", "set.general": "General",
    "tone.idle": "Not checked", "tone.wait": "Checking…", "tone.ok": "Open", "tone.warn": "Partly",
    "tone.bad": "Not opening", "tone.geo": "Not in your country",
    "svc.geo_hint": "“Not in your country” — the site opens, but the service itself isn't offered in your country. That's the service's restriction, not an error: the regular bypass can't help here, turn on Smart route.",
    "svc.ai": "AI", "ai.more": "Also via Smart route: DeepL, ElevenLabs, OpenRouter, Cursor",
    "ai.sum_idle": "Not checked", "ai.sum_wait": "Checking…", "ai.sum_ok": "All open", "ai.sum_part": "{} of {} open",
    "ai.sum_none": "Not opening", "ai.sum_geo": "Region-locked",
    "smart.first": "Requests to these AI services will go through a third-party DNS and its proxies: the content is encrypted, but the server's owner can see when and from where you connect. Some services restrict use from unsupported countries and may block your account.",
    "smart.title": "Smart route", "smart.d": "ChatGPT, Claude, Grok and other AI — via smart DNS",
    "set.smart_list": "Smart DNS opens: ChatGPT, Claude, Grok, DeepL, ElevenLabs, OpenRouter, Cursor.",
    "set.buddy": "Show NIXY", "set.buddyd": "The star assistant points out when something's wrong",
    "buddy.ouch": ["Ouch!", "Hey, that hurts!", "I'm working here!", "That tickles!"],
    "buddy.dizzy": "Whoa… everything's spinning",
    "buddy.check_svc": "Let me check {}…",
    "buddy.pick_stop": "Stop the strategy search?", "buddy.strategy_ask": "The strategy is \"{}\" right now. Find a better one?", "buddy.game_on": "Turn game mode on?", "buddy.game_off": "Turn game mode off?",
    "buddy.check_ask": "Fly around and check all services?", "buddy.diag_ask": "Check why it isn't working?", "buddy.go_there": "Off we go: {}!", "buddy.this_is": "This is \"{}\". You can press it without me.",
    "svc.more": "And many other sites and services", 
    "buddy.menu_checks": "What I can check", "buddy.menu_tasks": "What I can do",
    "buddy.menu_tour": "Check all services", "buddy.menu_site": "Check one site", "buddy.menu_speed": "Measure internet speed",
    "buddy.menu_on": "Turn the bypass on", "buddy.menu_off": "Turn the bypass off",
    "buddy.menu_smart_on": "Turn Smart route on", "buddy.menu_smart_off": "Turn Smart route off", "buddy.menu_boost": "Open Speed-up",
    "buddy.menu_hide": "Hide NIXY", "buddy.menu_hidden": "You can bring NIXY back in Settings",
    "buddy.svc_ok": "{} opens — all good ✨", "buddy.ask_power": "The bypass is off right now — turn it on?",
    "buddy.smart_on_already": "Smart route is already on — try reloading the service page in a minute.",
    "diag.engine_none": "No engine yet — download it", "diag.engine_bad": "Engine files were changed — download them again",
    "diag.admin_bad": "No administrator rights — restart NIXYZ as administrator",
    "diag.dpi_d": "No other bypass tools found", 
    "diag.dns_bad": "DNS returns fake addresses — change it in Speed-up", "diag.time_d": "Time matches the internet",
    "diag.time_bad": "The clock is {} min off — secure sites won't open",
    "diag.strategy_off": "The bypass is off — turn it on", "diag.strategy_ok": "YouTube and Discord open",
    "diag.strategy_bad": "{} of {} open — pick a strategy again",
    "set.export_done": "Settings saved to Downloads", "set.report_done": "Report saved to Downloads",
    "set.save_err": "Couldn't save — see the log for details",
    "set.import_done": "Settings loaded", "set.import_bad": "This isn't a NIXYZ settings file",
    "buddy.power_on": "Turn the bypass on?", "buddy.power_off": "Turn the bypass off?", "buddy.pick": "Find a strategy",
    "buddy.yawn": "Oh, I dozed off… How can I help?",
    "smart.note": "The smart DNS can see which AI tools you use.",
    "smart.how_btn": "How it works", "smart.setup": "Set up",
    "smart.how": "Only requests to these AI addresses go to a smart DNS (Comss) over HTTPS; it answers with the addresses of its proxies, which pass traffic to the service without decrypting it. All other sites work as usual.",
    "diag.open": "Why isn't it working?", "diag.sub": "I'll check everything in order and tell you what to fix",
    "diag.fix": "Fix", "diag.rerun": "Check again", "diag.close": "Close",
    "diag.note": "If everything is fine but a site still won't open, try a strategy search.",
    "diag.engine": "Engine in place", "diag.engine_d": "zapret files haven't changed since install",
    "diag.admin": "Administrator rights", "diag.admin_d": "Granted — the WinDivert driver can start",
    "diag.dpi": "No other bypass tools", "diag.dpi_bad": "{} is running — two bypass tools get in each other's way",
    "diag.dns": "DNS responds", "diag.dns_none": "Couldn't look up a site address — there may be no internet", "diag.unknown": "The check didn't finish — run the diagnostics again", "diag.dns_d": "Site addresses resolve correctly",
    "diag.time": "Windows clock is accurate",
    "diag.strategy": "Strategy fits", "diag.strategy_d": "Checking whether services open…",
    "set.guard": "Protection & reliability", "set.watch": "Watchdog", "set.watchd": "Keeps an eye on the bypass and fixes it if it breaks",
    "set.nightly": "Re-check at night", "set.rollback": "Roll back to a working strategy",
    "set.rollbackd": "If a new strategy is worse, I'll return to the previous one",
    "set.notify_g": "Notifications", "set.notify": "Windows notifications", "set.notifyd": "I'll tell you if the bypass turns off or something stops opening",
    "set.aidns": "Smart DNS for AI", "set.aidnsd": "Your own server — DoH address or IP:",
    "set.dns_builtin": "Built-in", "set.dns_custom": "Custom",
    "set.aidns_ph": "dns.example.com or 1.2.3.4",
    "set.data": "Data", "set.export": "Export settings", "set.import": "Import settings",
    "set.report": "Support report", "set.reportd": "Log and settings in one file — user name and network addresses hidden",
    "buddy.name": "NIXY — assistant", "buddy.yes": "Yes", "buddy.no": "No", "buddy.ok": "Got it",
    "buddy.hello": "Hi, I'm NIXY! I make sure everything opens. Shall I check that it all works?",
    "buddy.thanks": "Okay, I'm here if you need me.",
    "buddy.tour_ok": "All good! {} open ✨", "buddy.tour_unknown": "No answer yet — the check didn't finish. Please try again.",
    "buddy.prob_bad": "Here's the problem: {} won't open.", "buddy.prob_warn": "{} only opens partly.",
    "buddy.prob_geo": "{} is closed to your country.", "buddy.ask_smart": "Turn on Smart route?", "buddy.ask_pick": "Find a new strategy?",
    "buddy.more": "And {} more — I'll show you next.", "buddy.next": "Next",
    "lists.probe_ph": "Site address, e.g. example.com", "lists.probe": "Check", "lists.add": "Add to bypass",
    "lists.ok": "Opens", "lists.cut": "Cuts off after {} KB", "lists.noreply": "No reply",
    "lists.nodns": "Address not found — the site doesn't exist or DNS hides it", "lists.reset": "Connection gets reset — looks like a block",
    "lists.checking": "Checking…", "lists.ok_answer": "The server answers — the connection isn't cut", "lists.badname": "That doesn't look like a site address",
    "lists.saved": "List saved", "lists.save_err": "Couldn't save the list",
    "lists.bad_line": "Line {} doesn't look like an address — fix it and save again",
    "lists.general": "Bypass", "lists.exclude": "Leave alone", "lists.ipexclude": "Exclude IPs",
    "lists.general_d": "Your own sites to apply the bypass to — on top of the built-in ones",
    "lists.exclude_d": "Sites that work fine anyway: the bypass won't touch them",
    "lists.ipexclude_d": "Addresses and subnets the bypass skips — like your home network or game servers",
    "lists.hint_general": "One domain per line, e.g.", "lists.hint_ip": "One address or subnet per line, e.g.",
    "lists.n_dom": ["{} domain", "{} domains", "{} domains"], "lists.n_ip": ["{} address", "{} addresses", "{} addresses"],
    "lists.save": "Save", "lists.about": "About the lists",
    "lists.note": "Subdomains are included: youtube.com also covers www.youtube.com. Lines starting with # are comments.",
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
  for (const el of $$("[data-t-ph]")) el.placeholder = t(el.dataset.tPh);
  if (typeof renderListMeta === "function") renderListMeta();  // подсказка и счётчик редактора списков
  updKey = null;  // перерисовать подписи в карточке обновления
  if (!$("#sec-kv").hidden) loadHashes();  // раскрытая панель переводится, даже если язык сменили с другого экрана
}

function applyTheme(theme) {
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;
}

// ---- связь с программой: в собранном NIXYZ — мост окна, в режиме разработки — локальный сервер
const bridge = () => (window.pywebview && window.pywebview.api) || null;

async function api(action, body = {}) {
  const b = bridge();
  try {
    if (b) {
      if (action === "pick") await b.pick(body.name);
      else if (action === "toggle") await b.toggle(body.key, body.value);
      else if (action === "pref") await b.pref(body.key, body.value);
      else if (action === "answer") await b.answer(body.id, body.yes);
      else if (action === "net_dns") await b.net_dns(body.name);
      else if (action === "net_item") await b.net_item(body.key, body.value);
      else if (action === "probe") await b.probe(body.domain);
      else if (action === "list_save") return await b.list_save(body.name, body.text);
      else if (action === "diag_fix") await b.diag_fix(body.id);
      else if (action === "settings_import") return await b.settings_import(body.text);
      else if (action === "export" || action === "report") return await b[action]();
      else await b[action]();
      return { ok: true };
    }
    return await fetch("/api/" + action, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-NIXYZ": "1" },
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

// капсула выбранного пункта внизу плавно переезжает с одного пункта на другой
function navGlow() {
  const nav = $(".nav"), cur = nav.querySelector('[aria-current="page"]');
  let glow = nav.querySelector(".nav-glow");
  if (!glow) { glow = document.createElement("i"); glow.className = "nav-glow"; nav.prepend(glow); }
  if (!cur || !cur.offsetWidth) return;   // панель скрыта (экран установки)
  glow.style.width = cur.offsetWidth + "px";
  glow.style.height = cur.offsetHeight + "px";
  glow.style.transform = `translate(${cur.offsetLeft}px, ${cur.offsetTop}px)`;
  if (!glow.classList.contains("ready")) requestAnimationFrame(() => glow.classList.add("ready"));   // первое появление — без езды
}
new ResizeObserver(navGlow).observe($(".nav"));
// ---- плавные выезды. Экран едет с той стороны, куда идёшь:
// дальше по нижней панели — справа, назад — слева. Первое открытие программы — снизу
const NAV_ORDER = ["main", "boost", "lists", "settings", "log"];
function slideIn(els, dx, dy, opts = {}) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const { duration = 680, step = 70, first = 40 } = opts;
  [...els].forEach((el, i) => {
    for (const a of slideAnims) if (a.effect.target === el) a.finish();
    const delay = first + i * step;
    const a = el.animate([{ opacity: 0, transform: `translate(${dx}px, ${dy}px)` }, { opacity: 1, transform: "none" }],
      { duration, delay, easing: "cubic-bezier(.22, .8, .2, 1)", fill: "backwards" });
    slideAnims.add(a);
    a.onfinish = a.oncancel = () => slideAnims.delete(a);
    // анимация может застрять в ожидании старта и держать элемент невидимым: содержимое важнее красоты
    setTimeout(() => { if (a.pending) a.finish(); }, 200);
  });
}
const slideAnims = new Set();
function slideStop() {   // завершить, а не оборвать: обрыв посреди выезда заставлял WebView2 терять слой и не рисовать содержимое
  slideAnims.forEach((a) => a.finish());
}
let lastShow = -1000;
function show(name) {
  if (name === screen) return;
  slideStop();
  const now = performance.now(), rapid = now - lastShow < 300;   // быстрые щелчки: содержимое сразу, без выезда
  lastShow = now;
  const from = NAV_ORDER.indexOf(screen), to = NAV_ORDER.indexOf(name), firstOpen = from < 0;
  for (const el of $$(".screen")) el.classList.toggle("active", el.id.slice(2) === name);
  // боковое меню: подсветка текущего раздела; на экране установки меню скрыто (CSS по data-screen)
  for (const b of $$(".nav [data-go]")) b.setAttribute("aria-current", b.dataset.go === name ? "page" : "false");
  navGlow();
  document.body.dataset.screen = name;
  screen = name;
  $("#s-" + name).scrollTop = 0;
  // едет экран целиком: анимация отдельных блоков заставляла WebView2 терять их слои, и блоки оставались пустыми
  if (!rapid) slideIn([$("#s-" + name)], firstOpen || to < 0 ? 0 : to > from ? 44 : -44, firstOpen ? 26 : 0, { duration: 460, first: 0 });
  if (!buddyBusy) buddyHome();  // меню могло появиться или исчезнуть — помощник возвращается на своё место
  if (firstOpen && name !== "setup") slideIn([$(".bottom")], 0, 26, { first: 180 });   // после посадки NIXY: он считает место по доку
  closePopover();
  if (name === "log") { const l = $("#log"); l.scrollTop = l.scrollHeight; }
  if (name === "boost" && state && state.net && !state.net.scanned && !state.net.busy) api("net_scan");
}

function copy(text, done) {
  navigator.clipboard.writeText(text).then(() => toast(t(done)), () => toast(t("copy.fail")));
}

function toast(text) {
  const el = $("#toast");
  el.textContent = text;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 1800);
}

// «работает частично»: обход включён, но проверка показала, что открывается не всё
const isPartial = (s) => s.power === "on" && !s.auto && Object.values(s.pills || {}).some((p) => p.tone === "warn" || p.tone === "bad");

function uptime() {
  const on = !!(state && state.power === "on" && state.on_since);
  $("#uptime").classList.toggle("show", on);
  if (!on) return;
  if (isPartial(state)) { $("#uptime-text").textContent = t("up.partial"); return; }
  const min = Math.floor((Date.now() / 1000 - state.on_since) / 60);
  $("#uptime-text").textContent = min < 1 ? t("up.now") : min < 60 ? t("up.min", min) : t("up.hour", Math.floor(min / 60), min % 60);
}

// засечки вокруг кнопки: по одной на стратегию; пройденные горят, текущая мигает
function renderTicks(p) {
  const g = $("#ticks"), n = p ? p[1] : 0;
  if (g.childElementCount !== n) {
    const NS = "http://www.w3.org/2000/svg";
    g.replaceChildren(...Array.from({ length: n }, (_, k) => {
      const a = 2 * Math.PI * k / n - Math.PI / 2, c = Math.cos(a), s = Math.sin(a);
      const l = document.createElementNS(NS, "line");
      l.setAttribute("x1", (132 + 113 * c).toFixed(1)); l.setAttribute("y1", (132 + 113 * s).toFixed(1));  // центр кольца (132, 132)
      l.setAttribute("x2", (132 + 122 * c).toFixed(1)); l.setAttribute("y2", (132 + 122 * s).toFixed(1));
      return l;
    }));
  }
  if (p) [...g.children].forEach((l, k) => l.setAttribute("class", k < p[0] ? "done" : k === p[0] ? "cur" : ""));
}

function renderOrb(s, partial) {
  const orb = $("#orb");
  if (orb.dataset.state !== "on" && s.power === "on") {  // только что включился — вспышка сияния
    orb.classList.add("pop");
    clearTimeout(renderOrb.timer);
    renderOrb.timer = setTimeout(() => orb.classList.remove("pop"), 1000);
    buddyMood("joy", 1500);  // помощник радуется включению
  }
  orb.dataset.state = s.power;
  orb.classList.toggle("partial", partial);
  const look = partial ? "partial" : s.power;  // фон и огонёк в меню знают и про «частично»
  $("#backdrop").dataset.state = look;
  document.body.dataset.power = look;
  orb.classList.toggle("auto", !!s.auto_progress);
  renderTicks(s.auto_progress);
}
let stopping = false;  // нажали «Остановить подбор»: программа доведёт текущую стратегию и остановится
setInterval(uptime, 15000);

function render(s) {
  if (state && typeof s.version === "number" && s.version < state.version) return;  // устаревший снимок
  const langChanged = !state || state.lang !== s.lang;
  state = s;
  if (langChanged) applyLang(s.lang);
  applyTheme(s.prefs && s.prefs.theme);
  if (screen === null || screen === "setup" || s.screen === "setup") show(s.screen);

  const partial = isPartial(s);
  $("#power").dataset.state = s.power;
  $("#power").setAttribute("aria-pressed", String(s.power === "on"));
  renderOrb(s, partial);
  $("#title").textContent = partial ? t("main.partial") : s.title;
  $("#side-state").textContent = partial ? t("main.partial") : s.title;  // то же состояние — внизу бокового меню
  $("#sub").textContent = s.sub;  // при «частично» пояснение даёт янтарная строка под ним
  uptime();
  $("#strategy").textContent = s.auto ? t("main.picking") : s.strategy || "—";  // во время подбора выбор ещё не сделан
  $("#engine").textContent = s.engine || "—";
  if (!s.auto) stopping = false;
  $("#auto-note").textContent = s.auto_note;
  $("#auto-note").hidden = !!s.auto;  // ход подбора уже виден в статусе и на засечках — второй раз не дублирую
  $("#auto-label").textContent = s.auto ? t(stopping ? "main.stopping" : "main.stop") : t("main.auto");
  $("#b-auto").classList.toggle("stop", s.auto);
  document.title = "NIXYZ — " + (s.power === "on" ? t("chip.on") : t("chip.off"));

  for (const [svc, p] of Object.entries(s.pills || {})) {
    const el = $("#p-" + svc);
    if (!el) continue;
    el.dataset.tone = p.tone;
    el.querySelector(".note").textContent = p.note;
    el.querySelector(".st").textContent = t("tone." + p.tone);
  }
  renderAiSummary();  // плитка «ИИ» — итог по ChatGPT, Claude, Grok
  renderLists(s);
  renderDiag(s.diag);
  // плитки, о которых программа пока не сообщает (новые сервисы), остаются «не проверено»
  $("#geo-hint").hidden = !Object.values(s.pills || {}).some((p) => p.tone === "geo");
  // переключатель с data-def="1" включён, пока программа не сообщила иное (например, buddy)
  for (const sw of $$(".switch[data-key]")) {
    const v = s.toggles[sw.dataset.key];
    sw.setAttribute("aria-checked", String(v === undefined ? sw.dataset.def === "1" : !!v));
  }
  wrap.hidden = s.toggles.buddy === false;  // «Показывать NIXY» выключен — помощника нет
  for (const seg of $$(".seg[data-pref]")) {
    const cur = (s.prefs || {})[seg.dataset.pref] || seg.children[0].dataset.v;
    for (const b of seg.children) b.setAttribute("aria-pressed", String(b.dataset.v === cur));
  }
  if (document.activeElement !== $("#ai-dns")) $("#ai-dns").value = (s.prefs || {}).smart_doh || "";

  const busy = s.busy;
  for (const id of ["#select", "#b-check", "#b-download", "#b-folder", "#b-folder2", "#b-update"]) $(id).disabled = busy;
  $("#b-auto").disabled = busy && !s.auto;
  $("#power").disabled = busy && !s.auto;
  $("#b-uninstall").disabled = busy;
  $('.switch[data-key="game"]').disabled = busy;
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
  $("#about").textContent = "NIXYZ " + (s.app_version || "") + (s.engine ? "\n" + s.engine : "");

  renderNet(s.net);
  renderLog(s.log);
  renderUpdate(s.update);
  renderDialog(s.dialog);
}

// ---- ускорение интернета
const DNS_IDS = ["own", "cloudflare", "google", "quad9"];
const DNS_IP = { cloudflare: "1.1.1.1", google: "8.8.8.8", quad9: "9.9.9.9" };
const DNS_NAME = { cloudflare: "Cloudflare", google: "Google", quad9: "Quad9" };  // до первого замера имён от программы ещё нет
const num = (x) => x.toLocaleString(lang === "ru" ? "ru-RU" : "en-US", { maximumFractionDigits: x < 10 ? 1 : 0 });

// шкала логарифмическая: 1, 10, 100 и 1000 Мбит/с — равные шаги
const gaugePos = (mbps) => Math.min(1, Math.log10(1 + mbps) / 3);

// деления и подписи спидометра: та же формула, что у дуги; центр (120, 122), дуга радиусом 100
(function buildScale() {
  const NS = "http://www.w3.org/2000/svg";
  const at = (v, r) => { const a = Math.PI * (1 - gaugePos(v)); return [120 + r * Math.cos(a), 122 - r * Math.sin(a)]; };
  const g = $("#g-scale");
  for (const v of [0, 2, 5, 20, 50, 200, 500, 1, 10, 100, 1000]) {
    const major = [1, 10, 100, 1000].includes(v);
    const [x1, y1] = at(v, 88), [x2, y2] = at(v, major ? 80 : 84);
    const l = document.createElementNS(NS, "line");
    l.setAttribute("x1", x1.toFixed(1)); l.setAttribute("y1", y1.toFixed(1));
    l.setAttribute("x2", x2.toFixed(1)); l.setAttribute("y2", y2.toFixed(1));
    if (major) l.setAttribute("class", "major");
    g.append(l);
    if (!major) continue;
    const [x, y] = at(v, 64);
    const tx = document.createElementNS(NS, "text");
    tx.setAttribute("x", (v === 1000 ? x - 8 : v === 1 ? x + 3 : x).toFixed(1));  // крайние подписи — чуть внутрь, подальше от засечек
    tx.setAttribute("y", y.toFixed(1));
    tx.textContent = v;
    g.append(tx);
  }
})();

function renderGauge(n) {
  const run = n.busy === "speed";
  const sp = n.speed && n.speed.last;
  const prev = n.speed && n.speed.prev;
  const box = $("#gauge");
  box.dataset.state = run ? "run" : sp ? "done" : "idle";
  const pct = Math.min(1, Math.max(0, run ? (n.progress || 0) : sp ? gaugePos(sp.down) : 0));
  box.style.setProperty("--p", pct.toFixed(4));  // бегунок, свечение и заливка капсулы замера
  $("#g-arc").style.strokeDashoffset = $("#g-glow").style.strokeDashoffset = String(100 - pct * 100);
  $("#g-down").textContent = run ? (n.live ? num(n.live) : "…") : sp ? num(sp.down) : "—";  // во время замера — текущая скорость
  const okN = sp && sp.sources ? Object.values(sp.sources).filter(Boolean).length : 0;
  $("#g-ping").textContent = run || !sp ? "" : okN ? t("boost.avg", okN, sp.ping) : t("boost.ping", sp.ping);
  const d = $("#g-delta");
  if (!run && sp && prev && prev.down > 0) {
    const pc = Math.round((sp.down / prev.down - 1) * 100);
    d.textContent = pc === 0 ? "" : t(pc > 0 ? "boost.delta_up" : "boost.delta_down", Math.abs(pc));
    d.dataset.tone = pc > 0 ? "up" : "down";
  } else d.textContent = "";
  const SRC = ["cloudflare", "yandex", "selectel"];
  const label = (s) => s === "yandex" ? t("boost.yandex") : s[0].toUpperCase() + s.slice(1);
  $("#speed-label").textContent = run && n.src ? t("boost.src_run", label(n.src), SRC.indexOf(n.src) + 1)
    : run ? t("boost.measuring", Math.round((n.progress || 0) * 100)) : t(sp ? "boost.again" : "boost.measure");
  // плитки источников: во время замера — готовые, текущий и ожидающие; после — итог каждого
  const done = run ? n.sources || {} : (sp && sp.sources) || {};
  for (const el of $$("#g-src .src")) {
    const s = el.dataset.src, r = done[s];
    let st = "none", v = "—", p = "";
    if (run && s === n.src) { st = "run"; v = n.live ? num(n.live) : "…"; }
    else if (r) { st = "ok"; v = num(r.down); p = t("boost.ping_s", r.ping); }
    else if (s in done) { st = "fail"; v = t("boost.fail"); }
    else if (run) { st = "wait"; v = "…"; }
    el.dataset.st = st;
    el.querySelector(".v").textContent = v;
    el.querySelector(".p").textContent = p;
  }
}

let dnsKey = null;
function renderDns(n) {
  const key = JSON.stringify([lang, n.dns, n.dns_cur, n.best, n.busy, n.scanned]);
  if (key === dnsKey) return;
  dnsKey = key;
  const rows = n.dns.length ? n.dns : DNS_IDS.map((id) => ({ id, name: "", ms: undefined }));
  const box = $("#dns-list");
  const focused = box.contains(document.activeElement) ? document.activeElement.dataset.id : null;
  box.textContent = "";
  for (const r of rows) {
    const b = document.createElement("button");
    b.className = "row dns";
    b.setAttribute("aria-pressed", String(r.id === n.dns_cur));
    b.disabled = !!n.busy;
    const radio = document.createElement("span");  // выбирается один сервер — радиокнопка слева
    radio.className = "radio";
    const label = document.createElement("span");
    label.className = "label";
    const title = document.createElement("div");
    title.textContent = r.id === "own" ? t("boost.own") : r.name || DNS_NAME[r.id] || r.id;
    const sub = document.createElement("div");
    sub.className = "d";
    sub.textContent = r.id === "own" ? (r.name ? t("boost.own_ip", r.name) : t("boost.own_d")) : DNS_IP[r.id] || "";
    if (r.id === n.best && r.ms != null) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = t("boost.fastest");
      title.append(tag);  // капсула сразу за названием — самый быстрый виден с первого взгляда
    }
    label.append(title, sub);
    const ms = document.createElement("span");
    ms.className = "ms";
    const scanning = n.busy === "scan" || r.ms === undefined;
    ms.dataset.tone = scanning ? "wait" : r.ms == null ? "slow" : r.id === n.best ? "fast" : "";
    ms.textContent = scanning ? "…" : r.ms == null ? t("boost.noanswer") : t("boost.ms", r.ms);
    b.append(radio, label, ms);
    b.onclick = () => { if (r.id !== n.dns_cur) api("net_dns", { name: r.id }); };
    b.dataset.id = r.id;
    box.append(b);
    if (r.id === focused && !b.disabled) b.focus();
  }
}

function renderNet(n) {
  if (!n) return;
  const busy = !!n.busy;
  $("#b-boost").classList.toggle("on", n.on);
  renderGauge(n);
  renderDns(n);
  const cta = $("#b-boost-all");
  cta.classList.toggle("undo", n.on && n.busy !== "apply");
  cta.classList.toggle("busy", n.busy === "apply");
  cta.disabled = busy;
  $("#boost-label").textContent = n.busy === "apply" ? t("boost.working") : n.busy === "scan" && !n.scanned ? t("boost.scanning") : t(n.on ? "boost.undo" : "boost.go");
  $("#boost-note").textContent = t(n.on ? "boost.on_note" : "boost.off_note");
  $("#b-speed").disabled = busy;
  $("#b-flush").disabled = busy;
  const rs = $("#b-rescan");
  rs.disabled = busy;
  rs.classList.toggle("spin", n.busy === "scan");
  rs.lastElementChild.textContent = t(n.busy === "scan" ? "boost.rescanning" : "boost.rescan");
  $("#b-reset").disabled = busy;
  $("#b-reset").classList.toggle("off", !n.on);
  for (const sw of $$(".switch[data-net]")) {
    const v = n[sw.dataset.net];
    if (!busy) sw.setAttribute("aria-checked", String(v === true));
    sw.disabled = busy || v == null;
  }
  $("#wifi-d").textContent = t(n.scanned && n.wifi == null ? "boost.nowifi" : "boost.wifid");
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
  $("#upd-more-label").textContent = t("upd.more");
  $("#upd-count").textContent = notes.length || "";
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
        b.onclick = () => copy(full, "hash.copied");
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
$("#b-auto").onclick = () => {
  if (state && state.auto) { stopping = true; $("#auto-label").textContent = t("main.stopping"); }  // мгновенный отклик
  api("auto");
};
$("#b-check").onclick = () => api("check");
$("#b-download").onclick = () => api("download");
$("#b-folder").onclick = $("#b-folder2").onclick = () => api("folder");
$("#b-update").onclick = () => api("update");
$("#b-open").onclick = () => api("open_dir");
// окно не уводит в интернет: адрес копируется, открыть его можно в своём браузере
// соглашение и политика: простая разметка переводится в элементы, текст только через textContent
function legalBody(text) {
  const out = [];
  let list = null;
  for (const line of text.split(/\r?\n/)) {
    if (line.startsWith("- ")) {
      if (!list) out.push(list = document.createElement("ul"));
      list.append(Object.assign(document.createElement("li"), { textContent: line.slice(2) }));
      continue;
    }
    list = null;
    if (line.startsWith("## ")) out.push(Object.assign(document.createElement("h3"), { textContent: line.slice(3) }));
    else if (line.trim() && !line.startsWith("# ")) out.push(Object.assign(document.createElement("p"), { textContent: line }));
  }
  return out;
}
async function openLegal(name, titleKey) {
  const b = bridge(), text = b ? await b.legal(name).catch(() => "") : "";
  if (!text) return toast(t("legal.err"));
  $("#legal-title").textContent = t(titleKey);
  $("#legal-text").replaceChildren(...legalBody(text));
  $("#legal-text").scrollTop = 0;
  $("#legal").classList.add("open");
  $("#legal-close").focus();
}
const closeLegal = () => $("#legal").classList.remove("open");
$("#b-terms").onclick = () => openLegal("terms", "legal.terms");
$("#b-policy").onclick = () => openLegal("privacy", "legal.privacy");
$("#legal-close").onclick = closeLegal;
$("#legal").addEventListener("click", (e) => { if (e.target === e.currentTarget) closeLegal(); });
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && $("#legal").classList.contains("open")) { e.stopPropagation(); closeLegal(); }
}, true);
$("#b-repo").onclick = () => copy("https://github.com/Flowseal/zapret-discord-youtube", "repo.copied");
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
  copy(text, "log.copied");
};
$("#select").onclick = (e) => { e.stopPropagation(); $("#popover").classList.contains("open") ? closePopover() : openPopover(); };
document.addEventListener("click", (e) => { if (!$("#popover").contains(e.target)) closePopover(); });
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (bubbleAnswer) return bubbleAnswer("no");                        // сначала закрывается пузырь помощника,
  if (tour) { tour.stop = true; return; }                             // облёт-проверка прерывается,
  if (!$("#nixy-menu").hidden) return nixyMenuClose();                // меню NIXY,
  if ($("#diag").classList.contains("open")) return diagOpen(false);  // потом диагностика
  if ($("#popover").classList.contains("open")) return closePopover();
  if (screen && screen !== "setup" && screen !== "main") show("main");
});
for (const b of $$("[data-go]")) b.onclick = () => show(b.dataset.go);
// док: стрелки влево/вправо, Home и End переводят фокус между разделами
$(".nav").addEventListener("keydown", (e) => {
  const items = [...$$(".nav button")], i = items.indexOf(document.activeElement);
  const j = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : null;
  if (j === null || i < 0) return;
  e.preventDefault();
  items[(j + items.length) % items.length].focus();
});
for (const sw of $$(".switch[data-net]")) sw.onclick = () => {
  const v = sw.getAttribute("aria-checked") !== "true";
  sw.setAttribute("aria-checked", String(v));
  api("net_item", { key: sw.dataset.net, value: v });
};
$("#b-boost-all").onclick = () => api(state && state.net && state.net.on ? "net_restore" : "net_boost");
$("#b-speed").onclick = () => api("net_speed");
$("#b-rescan").onclick = () => api("net_scan");
$("#b-flush").onclick = () => { api("net_flush"); toast(t("boost.flushed")); };
$("#b-reset").onclick = () => { if (state && state.net && state.net.on) api("net_restore"); else toast(t("boost.reset_none")); };
let smartHintShown = false;
function smartFirstHint() {
  const hidden = wrap.hidden;   // помощник выключен в настройках: реплика всё равно должна дойти до человека
  wrap.hidden = false;
  buddySay({ target: '.switch[data-key="smart"]', text: t("smart.first") }).finally(() => { if (hidden) wrap.hidden = state.toggles.buddy === false; });
}
for (const sw of $$(".switch[data-key]")) sw.onclick = () => {
  const v = sw.getAttribute("aria-checked") !== "true";
  if (sw.dataset.key !== "autostart") sw.setAttribute("aria-checked", String(v));  // мгновенный отклик
  if (sw.dataset.key === "smart" && v && !smartHintShown && state && !state.toggles.smart_told) {  // один раз за всё время
    smartHintShown = true;
    smartFirstHint();
  }
  api("toggle", { key: sw.dataset.key, value: v });
};
for (const seg of $$(".seg[data-pref]")) for (const b of seg.children) b.onclick = () => {
  for (const x of seg.children) x.setAttribute("aria-pressed", String(x === b));  // мгновенный отклик
  if (seg.dataset.pref === "theme") applyTheme(b.dataset.v);
  api("pref", { key: seg.dataset.pref, value: b.dataset.v });
};
// ---- «Умный обход»: «как это работает» раскрывается в блоке; свой DNS-сервер — настройка программы.
$("#b-smart-how").onclick = () => {
  const box = $("#smart-how"), open = !box.classList.contains("open");
  box.classList.toggle("open", open);
  $("#b-smart-how").setAttribute("aria-expanded", String(open));
};
$("#smart-dns").addEventListener("click", (e) => { if (e.target.closest("[data-v='custom']")) $("#ai-dns").focus(); });
$("#ai-dns").addEventListener("change", () => api("pref", { key: "smart_doh", value: $("#ai-dns").value.trim() }));
// «Настроить» ведёт в Настройки и показывает группу «Умный обход»
async function apiResult(action, body) {   // действие, которое отвечает { error }: "" — получилось
  const r = await api(action, body);
  const res = r && (typeof r.json === "function" ? await r.json().catch(() => null) : r);
  return res ? res.error || "" : "?";
}
$("#b-export").onclick = async () => { const e = await apiResult("export"); toast(e ? t("set.save_err") : t("set.export_done")); };
$("#b-report").onclick = async () => { const e = await apiResult("report"); toast(e ? t("set.save_err") : t("set.report_done")); };
const importInput = Object.assign(document.createElement("input"), { type: "file", accept: ".json,application/json", hidden: true });
document.body.append(importInput);
$("#b-import").onclick = () => importInput.click();
importInput.onchange = async () => {
  const f = importInput.files[0];
  importInput.value = "";
  if (!f) return;
  if (f.size > 2 * 1024 * 1024) return toast(t("set.import_bad"));
  const r = await api("settings_import", { text: await f.text() });
  const res = r && (typeof r.json === "function" ? await r.json().catch(() => null) : r);
  toast(res && !res.error ? t("set.import_done") : (res && res.error) || t("set.import_bad"));
};
$("#b-smart-setup").addEventListener("click", () => setTimeout(() => $("#set-smart").scrollIntoView({ block: "start", behavior: "smooth" }), 80));

// ---- плитка «ИИ»: итог по строкам списка. Esc прячет список, пока фокус или курсор не уйдут
function renderAiSummary() {
  const items = [...$$(".ai-item")], tones = items.map((i) => i.dataset.tone), n = items.length;
  const ok = tones.filter((x) => x === "ok").length;
  let tone = "warn", key = "ai.sum_part";
  if (tones.every((x) => x === "idle")) { tone = "idle"; key = "ai.sum_idle"; }
  else if (tones.includes("wait")) { tone = "wait"; key = "ai.sum_wait"; }
  else if (ok === n) { tone = "ok"; key = "ai.sum_ok"; }
  else if (tones.every((x) => x === "geo")) { tone = "geo"; key = "ai.sum_geo"; }
  else if (ok === 0) { tone = "bad"; key = "ai.sum_none"; }
  $("#p-AI").dataset.tone = tone;
  $("#ai-sum").dataset.t = key;
  $("#ai-sum").textContent = t(key, ok, n);
}
const aiChip = $("#p-AI");
aiChip.addEventListener("keydown", (e) => { if (e.key === "Escape") { aiChip.classList.add("shut"); e.stopPropagation(); } });
aiChip.addEventListener("mouseleave", () => aiChip.classList.remove("shut"));
aiChip.addEventListener("focusout", () => aiChip.classList.remove("shut"));

// ---- диагностика «Почему не работает?»: программа проверяет по порядку (state.diag), у проблем — «Исправить»
function diagOpen(open) {
  $("#diag").classList.toggle("open", open);
  if (open) $("#diag-close").focus();
}
function renderDiag(d) {
  for (const li of $$("#diag-list .check")) {
    const c = d && d[li.dataset.check];
    li.dataset.state = c ? c.state : "wait";
    const desc = li.querySelector(".d");
    if (c && c.d) { desc.dataset.t = c.d; desc.textContent = t(c.d, ...(c.args || [])); desc.dataset.args = JSON.stringify(c.args || []); }
    li.querySelector(".fix").hidden = !(c && c.fix);
    li.querySelector(".fix").dataset.fix = (c && c.fix) || "";
  }
}
for (const b of $$("#diag-list .fix")) b.onclick = () => {
  const fix = b.dataset.fix;
  if (fix === "boost") { diagOpen(false); show("boost"); return; }
  if (fix === "auto" || fix === "power") diagOpen(false);
  api("diag_fix", { id: fix });
};
$("#diag-rerun").onclick = () => api("diagnose");
$("#b-diag").onclick = () => { diagOpen(true); api("diagnose"); };
$("#diag-close").onclick = () => diagOpen(false);
$("#diag").addEventListener("click", (e) => { if (e.target === $("#diag")) diagOpen(false); });

// ---- звёздный помощник
// buddySay({ text, target, actions }) → Promise<value>. target — CSS-селектор любого элемента на любом экране:
// помощник переключит экран, прокрутит к элементу, подлетит, подсветит его и спросит в пузыре.
// actions — [{ label, value }]; без них — одна кнопка «Понятно» (value "ok"). Esc и крестик дают "no".
// hold: мс — пузырь без кнопок сам закрывается через это время (value "done").
// Несколько вызовов подряд встают в очередь и звучат по одному.
const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const sleepMs = (ms) => new Promise((r) => setTimeout(r, calm() ? 0 : ms));
const wrap = $("#buddy-wrap"), bubble = $("#bubble");
const BW = 84, BH = 63;            // размер NIXY в «доме»
let buddyBusy = false, bubbleAnswer = null, buddyQueue = Promise.resolve(), moodTimer = 0;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

function buddyPlace(x, y) {
  const cur = wrap.getBoundingClientRect();
  x = Math.round(x); y = Math.round(y);
  if (Math.abs(x - cur.left) < 2 && Math.abs(y - cur.top) < 2) return;   // уже на месте
  wrap.style.setProperty("--tilt", clamp((x - cur.left) / 30, -14, 14).toFixed(1) + "deg");  // наклон по ходу полёта
  wrap.classList.remove("land");
  wrap.classList.add("flying");
  wrap.style.setProperty("--bx", x + "px");
  wrap.style.setProperty("--by", y + "px");
  clearTimeout(buddyPlace.timer);
  buddyPlace.timer = setTimeout(() => {  // приземлился — пружинка
    wrap.classList.remove("flying");
    wrap.classList.add("land");
    buddyPlace.timer = setTimeout(() => wrap.classList.remove("land"), 650);
  }, calm() ? 0 : 900);
}
// NIXY у элемента: если панель изменила размер (появилась подсказка, например), он и пузырь пересаживаются
let buddyAnchor = null;
function buddyReanchor() {
  if (!buddyAnchor || drag.on || !buddyAnchor.el.isConnected) return;
  const { el, w, h } = buddyAnchor;
  const spot = spotNear(el, w, h);
  buddyPlace(spot.bx, spot.by);
  if (!bubble.classList.contains("open")) return;
  Object.assign(spot, bubbleAt(spot.bx, spot.by, spot.side, bubble.offsetWidth, bubble.offsetHeight));
  bubble.dataset.side = spot.side;
  bubble.style.left = spot.px + "px";
  bubble.style.top = spot.py + "px";
  lastSide = spot.side;
}
new ResizeObserver(() => requestAnimationFrame(buddyReanchor)).observe($(".main-grid > .panel"));
function buddyHome() {
  buddyAnchor = null;  // «дом» — справа от дока в нижней строке; без неё (установка) — левый нижний угол
  const h = $("#buddy-home").getBoundingClientRect();
  // по центру дока, без учёта выезда нижней панели: она может ещё ехать, а NIXY должен встать туда, где она окажется
  const dock = $(".dock").getBoundingClientRect(), shift = new DOMMatrixReadOnly(getComputedStyle($(".bottom")).transform).m42;
  if (h.width) buddyPlace(h.left + (h.width - BW) / 2, dock.top - shift + (dock.height - BH) / 2);
  else buddyPlace(28, innerHeight - BH - 32);
}
function buddyMood(mood, ms) {
  wrap.dataset.mood = mood;
  clearTimeout(moodTimer);
  if (ms) moodTimer = setTimeout(() => { wrap.dataset.mood = "idle"; }, ms);
}

// глаза-звёзды следят за курсором; после 20 с покоя помощник скучает, после 45 с — засыпает
let idleAt = Date.now();
document.addEventListener("pointermove", (e) => {
  idleAt = Date.now();
  if (wrap.dataset.mood === "bored") buddyMood("idle");   // уснувшего будит только щелчок по нему (с зевком)
  if (buddyBusy) return;
  const r = wrap.getBoundingClientRect(), dx = e.clientX - (r.left + BW / 2), dy = e.clientY - (r.top + BH / 2);
  const d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 200);
  wrap.style.setProperty("--ex", (dx / d * 5 * k).toFixed(2));
  wrap.style.setProperty("--ey", (dy / d * 3 * k).toFixed(2));
});
document.addEventListener("keydown", () => { idleAt = Date.now(); if (wrap.dataset.mood === "bored") buddyMood("idle"); });
setInterval(() => {
  if (buddyBusy || !/^(idle|bored)$/.test(wrap.dataset.mood)) return;
  const quiet = Date.now() - idleAt;
  if (quiet > 45000) buddyMood("sleep");
  else if (quiet > 20000) buddyMood("bored");
}, 2000);

// куда встать NIXY рядом с элементом: не на нём и не на соседних кнопках.
// Кандидаты — четыре стороны вокруг контейнера элемента (панель, группа, редактор…) и вокруг самого элемента;
// у каждого считаются «помехи» (элементы управления под NIXY и под пузырём), берётся самый чистый.
const M = 12, GAP = 12;
const ZONE = ".panel, .group, .editor, .probe, .gauge-card, .lists-aside, .diag-card, .upd-card, .setup-head, .steps, .dock";
const INTERACTIVE = "button, input, textarea, .svc, .row, .switch, .seg, .check, .ai-item";
const overlap = (a, b) => a.x < b.right && a.x + a.w > b.left && a.y < b.bottom && a.y + a.h > b.top;
function clutter(box) {  // сколько из пяти точек прямоугольника падает на элементы управления
  let n = 0;
  for (const [fx, fy] of [[.5, .5], [.12, .15], [.88, .15], [.12, .85], [.88, .85]]) {
    const px = box.x + box.w * fx, py = box.y + box.h * fy;
    const e = document.elementFromPoint(px, py);
    if (e && !wrap.contains(e) && e.closest(INTERACTIVE)) n++;
  }
  return n;
}
function spotNear(el, w, h) {
  const r = el.getBoundingClientRect(), zone = el.parentElement && el.parentElement.closest(ZONE);
  const bases = zone ? [zone.getBoundingClientRect(), r] : [r];
  const cy = r.top + r.height / 2, cx = r.left + r.width / 2;
  let best = null;
  bases.forEach((R, bi) => {
    for (const side of ["right", "left", "above", "below"]) {
      const bx = clamp(side === "right" ? R.right + GAP : side === "left" ? R.left - GAP - BW : cx - BW / 2, M, innerWidth - BW - M);
      const by = clamp(side === "below" ? R.bottom + GAP : side === "above" ? R.top - GAP - BH : cy - BH / 2, M, innerHeight - BH - M);
      const b = bubbleAt(bx, by, side, w, h);
      const me = { x: bx, y: by, w: BW, h: BH }, pb = { x: b.px, y: b.py, w, h };
      const box = { left: bx, right: bx + BW, top: by, bottom: by + BH };
      const score = (overlap(me, r) ? 100 : 0) + (overlap(pb, r) ? 60 : 0) + clutter(me) * 4 + clutter(pb) + bi * 2
        + (overlap(pb, box) ? 80 : 0)   // у края окна пузырь мог лечь на самого NIXY
        + (zone && overlap(me, bases[0]) ? 30 : 0) + (zone && overlap(pb, bases[0]) ? 30 : 0);   // и закрыть панель с нужным элементом
      if (!best || score < best.score) best = { side, bx, by, score };
    }
  });
  return best;
}
// где открыть пузырь рядом с NIXY, стоящим в (bx, by): не уходит за край окна
function bubbleAt(bx, by, side, w, h) {
  const px = side === "right" ? bx + BW + GAP : side === "left" ? bx - GAP - w : bx + BW * .55;
  const py = side === "below" ? by + BH + GAP : side === "above" ? by - GAP - h : by - 6;
  return { px: clamp(px, M, innerWidth - w - M), py: clamp(py, M, innerHeight - h - M) };
}
const visible = (el) => el && el.getClientRects().length > 0 && !el.closest("[hidden]");

// stay — после ответа остаться у элемента; here — он уже у этого элемента: не перелетать, говорить с места
let lastSide = "right";
async function buddyRun({ text, target, actions, hold, mood, stay, here }) {
  buddyBusy = true;
  buddyMood(mood || "talk");   // mood — выражение лица на время реплики (по умолчанию — «говорит»)
  let el = target ? document.querySelector(target) : null;
  // элемент на другом экране — сначала туда (экраны-оверлеи вроде диагностики и обновления открыты и так)
  const scr = el && el.closest(".screen");
  if (scr && scr.id.slice(2) !== screen && scr.id !== "s-setup") { show(scr.id.slice(2)); await sleepMs(450); }
  if (!visible(el)) el = null;
  if (el) { el.scrollIntoView({ block: "nearest", behavior: calm() ? "auto" : "smooth" }); await sleepMs(380); }

  // пузырь: сначала текст и кнопки (невидимо), чтобы узнать размер, потом место
  const tx = $("#bubble-text"), acts = $("#bubble-acts");
  tx.textContent = text;
  const list = actions && actions.length ? actions : hold ? [] : [{ label: t("buddy.ok"), value: "ok" }];
  acts.replaceChildren(...list.map((a) => Object.assign(document.createElement("button"), { textContent: a.label, value: a.value })));
  const w = bubble.offsetWidth, h = bubble.offsetHeight;
  let spot;
  if (el) buddyAnchor = { el, w, h };
  if (el && here) {  // уже рядом — только подсветка, пузырь с той же стороны
    const me = wrap.getBoundingClientRect();
    spot = { side: lastSide, bx: me.left, by: me.top };
    el.classList.add("buddy-target");
  } else if (el) {  // подлетает к элементу и подсвечивает его
    spot = spotNear(el, w, h);
    buddyPlace(spot.bx, spot.by);
    el.classList.add("buddy-target");
    await sleepMs(950);
  } else {   // говорит со своего места: пузырь туда, где есть простор
    const me = wrap.getBoundingClientRect();
    const side = innerWidth - me.right >= w + GAP + M ? "right" : me.left >= w + GAP + M ? "left" : "above";
    spot = { side, bx: me.left, by: me.top };
  }
  Object.assign(spot, bubbleAt(spot.bx, spot.by, spot.side, w, h));
  if (el) lastSide = spot.side;
  // во время разговора глаза смотрят на пузырь
  wrap.style.setProperty("--ex", spot.side === "left" ? "-4.5" : spot.side === "right" ? "4.5" : "2");
  wrap.style.setProperty("--ey", spot.side === "above" ? "-3" : spot.side === "below" ? "3" : "0");
  bubble.dataset.side = spot.side;
  bubble.style.left = spot.px + "px";
  bubble.style.top = spot.py + "px";
  acts.hidden = true;
  tx.textContent = "";
  bubble.classList.add("open");

  // печатает по буквам, быстро
  tx.classList.add("typing");
  if (calm()) tx.textContent = text;
  else for (let i = 1; i <= text.length; i += 2) { tx.textContent = text.slice(0, i); await new Promise((res) => setTimeout(res, 16)); }
  tx.textContent = text;
  tx.classList.remove("typing");
  acts.hidden = false;
  if (acts.firstElementChild) acts.firstElementChild.focus();

  const value = await new Promise((resolve) => {
    bubbleAnswer = (v) => { bubbleAnswer = null; resolve(v); };
    for (const b of acts.children) b.onclick = () => bubbleAnswer(b.value);
    if (hold) setTimeout(() => bubbleAnswer && bubbleAnswer("done"), hold);
  });

  // ответ получен: кивает, пузырь закрывается, помощник летит домой
  bubble.classList.remove("open");
  if (el) el.classList.remove("buddy-target");
  if (!stay) {
    buddyMood(value === "no" ? "idle" : "happy", 700);
    await sleepMs(500);
    buddyHome();
    await sleepMs(el ? 950 : 0);
  }
  buddyBusy = false;
  return value;
}
function buddySay(opts) {
  const p = buddyQueue.then(() => buddyRun(opts));
  buddyQueue = p.catch(() => {});
  return p;
}
$("#bubble-close").onclick = () => bubbleAnswer && bubbleAnswer("no");
// щелчок по помощнику: здоровается и предлагает проверку — облёт buddyTour()
// ---- игра с NIXY. Всё срабатывает только на нём самом; клавиатура (Enter/Пробел) — как одиночный щелчок.
const pick = (list) => list[Math.floor(Math.random() * list.length)];
async function buddyGreet(woke) {
  const v = await buddySay({ text: t(woke ? "buddy.yawn" : "buddy.hello"), actions: [{ label: t("buddy.yes"), value: "yes" }, { label: t("buddy.no"), value: "no" }] });
  if (v === "yes") buddyTour();
  else buddySay({ text: t("buddy.thanks"), hold: 1800 });
}

// ---- облёт-проверка: buddyTour() → Promise: "ok" | { problems: [{ service, tone }] } | { cancelled: true }.
// Запускает обычную проверку (#b-check) и облетает плитки по порядку; у каждой «осматривает» её и, если ответа
// ещё нет, ждёт результата (не дольше 15 с). Порядок и скорость результатов могут быть любыми.
// Прервать: Esc, щелчок по NIXY или начало перетаскивания. При reduced-motion — без полётов, сразу итог у проблемы.
let tour = null;
const TOUR = ["#p-YouTube", "#p-Discord", "#p-Cloudflare", "#p-AI", "#smart", "#power"];
const tileName = (el) => el.id === "p-AI" ? t("svc.ai") : el.querySelector("b").textContent;
const tick = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitTone(el, ctl) {
  const t0 = Date.now();
  while (!ctl.stop && el.dataset.tone === "wait" && Date.now() - t0 < 15000) await tick(150);
  return el.dataset.tone;
}
function buddyTour() {
  if (tour) return tour.done;
  const ctl = tour = { stop: false };
  ctl.done = tourRun(ctl).catch(() => ({ cancelled: true })).finally(() => {
    for (const el of $$(".buddy-scan")) el.classList.remove("buddy-scan");
    buddyBusy = false;
    tour = null;
  });
  return ctl.done;
}
async function tourRun(ctl) {
  {
    await buddyQueue;   // сначала договорить начатое
    buddyBusy = true;
    if (screen !== "main") { show("main"); await sleepMs(450); }
    // сразу показываем «Проверяю…» у сервисов, о которых сообщает программа: результат сменит этот тон, когда придёт.
    // Плитки, которых программа пока не проверяет, остаются «не проверено», и облёт их не ждёт
    const pills = () => (state && state.pills) || {};
    for (const name of Object.keys(pills())) {
      const el = $("#p-" + name);
      if (!el) continue;
      el.dataset.tone = "wait";
      el.querySelector(".st").textContent = t("tone.wait");
    }
    renderAiSummary();
    $("#b-check").click();
    for (let i = 0; i < 25 && !Object.values(pills()).some((p) => p.tone === "wait"); i++) await tick(100);
    const results = [];
    for (const sel of TOUR) {
      if (ctl.stop) break;
      const el = $(sel);
      if (!calm()) {
        const spot = spotNear(el, 40, 20);
        buddyPlace(spot.bx, spot.by);
        await sleepMs(800);
        if (ctl.stop) break;
        const r = el.getBoundingClientRect(), me = wrap.getBoundingClientRect();   // смотрит на плитку
        wrap.style.setProperty("--ex", clamp((r.left + r.width / 2 - me.left - BW / 2) / 20, -5, 5).toFixed(1));
        wrap.style.setProperty("--ey", clamp((r.top + r.height / 2 - me.top - BH / 2) / 20, -3, 3).toFixed(1));
        buddyMood("scan");
        el.classList.add("buddy-scan");
        await sleepMs(650);
      }
      if (el.classList.contains("svc")) results.push({ el, tone: await waitTone(el, ctl) });
      el.classList.remove("buddy-scan");
    }
    for (const el of $$(".buddy-scan")) el.classList.remove("buddy-scan");
    buddyBusy = false;
    tour = null;
    if (ctl.stop) { buddyMood("idle"); buddyHome(); return { cancelled: true }; }
    const problems = results.filter((r) => /^(bad|warn|geo)$/.test(r.tone));
    if (!problems.length) {
      buddyHome();
      await sleepMs(900);
      const ok = results.filter((r) => r.tone === "ok").map((r) => tileName(r.el));
      buddySay({ text: ok.length ? t("buddy.tour_ok", ok.join(", ")) : t("buddy.tour_unknown"), hold: 3400, mood: ok.length ? "joy" : "talk" });
      return ok.length ? "ok" : { unknown: true };
    }
    buddyProblems(problems);
    return { problems: problems.map((p) => ({ service: p.el.id.slice(2), tone: p.tone })) };
  }
}
// чем помочь сервису: YouTube, Discord, Cloudflare — подбор стратегии; ChatGPT, Claude, Grok — «Умный обход»
function buddyRemedy(el, tone) {
  const id = el.id.slice(2);
  const smartOn = $('.switch[data-key="smart"]').getAttribute("aria-checked") === "true";
  if (tone === "geo" || id === "AI" || id === "ChatGPT" || id === "Claude" || id === "Grok")
    return smartOn ? { text: t("buddy.smart_on_already") } : { text: t("buddy.ask_smart"), act: "smart" };
  if (!state || state.power !== "on") return { text: t("buddy.ask_power"), act: "power" };   // обход выключен — его и включить
  return { text: t("buddy.ask_pick"), act: "pick" };
}
const svcName = (el) => el.classList.contains("ai-item") ? el.id.slice(2) : tileName(el);
// разбор проблем по одной: NIXY остаётся у плитки, объясняет и предлагает починку; «Дальше» — к следующей
async function buddyProblems(list, here = false) {
  for (let i = 0; i < list.length; i++) {
    const { el, tone } = list[i], rest = list.length - i - 1;
    const fix = buddyRemedy(el, tone);
    const at = el.classList.contains("ai-item") ? $("#p-AI") : el;   // строка ИИ — внутри всплывающего списка
    let text = t(tone === "geo" ? "buddy.prob_geo" : tone === "warn" ? "buddy.prob_warn" : "buddy.prob_bad", svcName(el)) + " " + fix.text;
    if (rest) text += " " + t("buddy.more", rest);
    const actions = fix.act ? [{ label: t("buddy.yes"), value: "yes" }] : [];
    if (rest) actions.push({ label: t("buddy.next"), value: "next" });
    actions.push({ label: t(fix.act ? "buddy.no" : "buddy.ok"), value: "no" });
    const v = await buddySay({ target: "#" + at.id, text, actions, mood: "alarm", stay: true, here: here && i === 0 });
    if (v === "yes" && fix.act === "pick") $("#b-auto").click();
    if (v === "yes" && fix.act === "power") $("#power").click();
    if (v === "yes" && fix.act === "smart") $('.switch[data-key="smart"]').click();
    if (v !== "next") break;
  }
  buddyHome();
}
// NIXY бросили на одну плитку: запускает проверку, ждёт ответ этого сервиса и говорит, что с ним
async function buddyCheckOne(tile) {
  const at = tile.classList.contains("ai-item") ? $("#p-AI") : tile;
  buddyBusy = true;
  tile.dataset.tone = "wait";
  at.classList.add("buddy-scan");
  buddyMood("think");
  const said = buddySay({ target: "#" + at.id, text: t("buddy.check_svc", svcName(tile)), hold: 1200, mood: "think", stay: true });
  $("#b-check").click();
  // сначала дождаться, что программа начала проверку (иначе прилетевшее старое состояние сойдёт за ответ)
  const id = tile.id.slice(2), t0 = Date.now();
  const pill = () => state && state.pills && state.pills[id];
  while (Date.now() - t0 < 2500 && !(pill() && pill().tone === "wait")) await tick(100);
  await said;
  buddyBusy = true;
  buddyMood("think");   // ждёт ответа на месте и «думает»
  const tone = await waitTone(tile, { stop: false });
  at.classList.remove("buddy-scan");
  buddyBusy = false;
  if (tone === "ok") return buddySay({ target: "#" + at.id, text: t("buddy.svc_ok", svcName(tile)), hold: 2600, mood: "joy", here: true });
  if (tone === "wait" || tone === "idle") return buddySay({ target: "#" + at.id, text: t("buddy.tour_unknown"), hold: 3000, here: true });
  return buddyProblems([{ el: tile, tone }], true);
}
// много щелчков подряд (4 за 2 с) — обижается: сальто, «> <», реплика, потом дуется и успокаивается
let clicks = [], clickTimer = 0, dragged = false;
async function buddyOuch() {
  clicks = [];
  await buddySay({ text: pick((I18N[lang] || I18N.ru)["buddy.ouch"]), hold: 1100, mood: "ouch" });
  buddyMood("sulk", 2200);
}
$("#buddy").onclick = () => {
  if (dragged) { dragged = false; return; }   // это было перетаскивание, а не щелчок
  if (tour) { tour.stop = true; return; }     // щелчок во время облёта — прервать
  if (buddyBusy) return;
  const now = Date.now();
  clicks = clicks.filter((c) => now - c < 2000).concat(now);
  clearTimeout(clickTimer);
  if (clicks.length >= 4) return buddyOuch();
  const woke = wrap.dataset.mood === "sleep";
  if (woke) buddyMood("yawn", 900);        // проснулся — сначала зевок
  clickTimer = setTimeout(() => { clicks = []; buddyGreet(woke); }, woke ? 900 : 380);
};

// правая кнопка (или клавиша меню) по NIXY: что он умеет — проверки и задачи. Пункты зависят от режима
function nixyMenuItems() {
  const on = !!state && state.power === "on", busy = !!(state && state.busy);
  const toMain = () => { if (screen !== "main") show("main"); };
  const click = (id) => () => { toMain(); $(id).click(); };
  const openOn = (name, then) => () => { show(name); then(); };
  const checks = [
    { icon: "t-spark", key: "buddy.menu_tour", run: () => buddyTour(), off: busy },
    { icon: "t-pulse", key: "diag.open", run: () => { diagOpen(true); api("diagnose"); } },
    { icon: "t-search", key: "buddy.menu_site", run: openOn("lists", () => $("#list-probe").focus()) },
    { icon: "t-wifi", key: "buddy.menu_speed", run: openOn("boost", () => $("#b-speed").click()) },
  ];
  const tasks = [
    { icon: "t-bolt", key: on ? "buddy.menu_off" : "buddy.menu_on", run: click("#power"), off: busy && !state.auto },
    { icon: "i-refresh", key: state && state.auto ? "main.stop" : "main.auto", run: click("#b-auto"), off: busy && !state.auto },
    { icon: "t-route", key: $('.switch[data-key="smart"]').getAttribute("aria-checked") === "true" ? "buddy.menu_smart_off" : "buddy.menu_smart_on",
      run: click('.switch[data-key="smart"]') },
    { icon: "t-gauge", key: "buddy.menu_boost", run: () => show("boost") },
  ];
  const more = [
    { icon: "t-report", key: "set.report", run: () => $("#b-report").click() },
    { icon: "t-eye", key: "buddy.menu_hide", run: () => { $('.switch[data-key="buddy"]').click(); toast(t("buddy.menu_hidden")); } },
  ];
  return [["buddy.menu_checks", checks], ["buddy.menu_tasks", [...tasks, ...more]]];
}
function nixyMenuOpen() {
  if (screen === "setup") return;
  const m = $("#nixy-menu");
  delete m.dataset.closing;
  m.getAnimations().forEach((a) => { a.onfinish = a.oncancel = null; a.cancel(); });
  m.replaceChildren();
  for (const [head, items] of nixyMenuItems()) {
    m.append(Object.assign(document.createElement("div"), { className: "mhead", textContent: t(head) }));
    for (const it of items) {
      const b = document.createElement("button");
      b.setAttribute("role", "menuitem");
      b.disabled = !!it.off;
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"), use = document.createElementNS("http://www.w3.org/2000/svg", "use");
      use.setAttribute("href", "#" + it.icon);
      svg.append(use);
      b.append(svg, Object.assign(document.createElement("span"), { textContent: t(it.key) }));
      b.onclick = () => { nixyMenuClose(); it.run(); };
      m.append(b);
    }
  }
  m.hidden = false;
  const me = wrap.getBoundingClientRect(), w = m.offsetWidth, h = m.offsetHeight;
  m.style.left = clamp(me.right - w, 12, innerWidth - w - 12) + "px";
  const top = clamp(me.top - h - 10, 12, innerHeight - h - 12);
  m.style.top = top + "px";
  m.getAnimations().forEach((a) => a.cancel());
  if (!calm()) {
    m.style.transformOrigin = `${me.left + me.width / 2 - parseFloat(m.style.left)}px ${me.top - top}px`;
    m.animate([{ opacity: 0, transform: "translateY(14px) scale(.94)" }, { opacity: 1, transform: "none" }],
      { duration: 300, easing: "cubic-bezier(.32, .72, 0, 1)" });
  }
  const first = m.querySelector("button:not(:disabled)");
  if (first) first.focus();
}
function nixyMenuClose() {
  const m = $("#nixy-menu");
  if (m.hidden || m.dataset.closing) return;
  if (m.contains(document.activeElement)) $("#buddy").focus({ preventScroll: true });   // фокус не теряется вместе с меню
  if (calm()) { m.hidden = true; return; }
  m.dataset.closing = "1";
  m.getAnimations().forEach((a) => a.cancel());
  const a = m.animate([{ opacity: 1, transform: "none" }, { opacity: 0, transform: "translateY(8px) scale(.97)" }], { duration: 150, easing: "ease-in" });
  a.onfinish = a.oncancel = () => { delete m.dataset.closing; m.hidden = true; };
}
$("#buddy").addEventListener("contextmenu", (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (tour || buddyBusy) return;
  nixyMenuOpen();
});
document.addEventListener("pointerdown", (e) => { if (!e.target.closest("#nixy-menu")) nixyMenuClose(); }, true);
$("#nixy-menu").addEventListener("keydown", (e) => {
  const items = [...$$("#nixy-menu button:not(:disabled)")], i = items.indexOf(document.activeElement);
  const j = e.key === "ArrowDown" ? i + 1 : e.key === "ArrowUp" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : null;
  if (j === null || !items.length) return;
  e.preventDefault();
  items[(j + items.length) % items.length].focus();
});

// NIXY бросили на элемент: говорит, что это, и предлагает действие. true — реакция была.
// Действия только через обычные кнопки; опасные (удаление, сброс) он сам не нажимает
async function buddyAsk(target, text, run, extra) {
  const v = await buddySay({ target, text, actions: [{ label: t("buddy.yes"), value: "yes" }, ...(extra ? [extra] : []), { label: t("buddy.no"), value: "no" }] });
  if (v === "yes") run();
  else if (extra && v === extra.value) extra.run();
  return true;
}
async function buddyDropOn(under) {
  const at = (sel) => under.closest(sel);
  const press = (sel) => () => $(sel).click();
  const onoff = (sw, on, off) => t($(sw).getAttribute("aria-checked") === "true" ? off : on);
  if (at("#power")) {
    const on = state && state.power === "on";
    return buddyAsk("#power", t(on ? "buddy.power_off" : "buddy.power_on"), press("#power"), { label: t("buddy.pick"), value: "pick", run: press("#b-auto") });
  }
  if (at("#b-auto")) {
    return buddyAsk("#b-auto", t(state && state.auto ? "buddy.pick_stop" : "buddy.ask_pick"), press("#b-auto"));
  }
  if (at("#smart")) return buddyAsk("#smart", onoff('.switch[data-key="smart"]', "buddy.menu_smart_on", "buddy.menu_smart_off") + "?", press('.switch[data-key="smart"]'));
  if (at("#select")) return buddyAsk("#select", t("buddy.strategy_ask", (state && state.strategy) || "—"), press("#b-auto"));
  if (at('.row:has(.switch[data-key="game"])')) return buddyAsk('.switch[data-key="game"]', onoff('.switch[data-key="game"]', "buddy.game_on", "buddy.game_off"), press('.switch[data-key="game"]'));
  if (at("#b-check")) return buddyAsk("#b-check", t("buddy.check_ask"), () => buddyTour());
  if (at("#b-diag")) return buddyAsk("#b-diag", t("buddy.diag_ask"), () => { diagOpen(true); api("diagnose"); });
  const go = at(".nav [data-go]");
  if (go) { await buddySay({ text: t("buddy.go_there", go.textContent.trim()), hold: 900, mood: "joy" }); show(go.dataset.go); return true; }
  // всё остальное: называет элемент, но ничего сам не нажимает
  const other = at("button, .row, .switch");
  const label = other && (other.getAttribute("aria-label") || (other.querySelector(".label") || other).textContent).trim().split("\n")[0].slice(0, 60);
  if (label) { await buddySay({ text: t("buddy.this_is", label), hold: 2200 }); return true; }
  return false;
}

// перетаскивание: NIXY летит за курсором с наклоном по ходу движения; отпустили — небольшой разгон
// по инерции и пружинистый полёт домой. Если трясти — закружится голова
const drag = { on: false, id: 0, dx: 0, dy: 0, x: 0, y: 0, vx: 0, vy: 0, t: 0, flips: 0, lastSign: 0, flipT: 0 };
$("#buddy").addEventListener("pointerdown", (e) => {
  if (tour) tour.stop = true;   // схватили во время облёта — облёт прерывается
  if (buddyBusy || e.button !== 0) return;
  const r = wrap.getBoundingClientRect();
  Object.assign(drag, { id: e.pointerId, dx: e.clientX - r.left, dy: e.clientY - r.top, sx: e.clientX, sy: e.clientY, x: r.left, y: r.top, vx: 0, vy: 0, t: performance.now(), flips: 0, lastSign: 0, on: false });
  $("#buddy").setPointerCapture(e.pointerId);
});
$("#buddy").addEventListener("pointermove", (e) => {
  if (e.pointerId !== drag.id || !$("#buddy").hasPointerCapture(e.pointerId)) return;
  if (!drag.on) {
    if (Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) < 6) return;   // мелкое дрожание руки — ещё щелчок
    drag.on = true;
    wrap.classList.add("drag");
    wrap.style.pointerEvents = "none";   // под ним видно, на что его бросают
    buddyMood("drag");
  }
  const now = performance.now(), dt = Math.max(8, now - drag.t);
  const x = clamp(e.clientX - drag.dx, 0, innerWidth - BW), y = clamp(e.clientY - drag.dy, 0, innerHeight - BH);
  drag.vx = (x - drag.x) / dt * 16; drag.vy = (y - drag.y) / dt * 16;   // px за кадр
  // тряска: резкие смены направления по горизонтали
  const sign = Math.sign(drag.vx);
  if (Math.abs(drag.vx) > 14 && sign && sign !== drag.lastSign) {
    if (now - drag.flipT > 1200) drag.flips = 0;
    drag.flips++; drag.flipT = now; drag.lastSign = sign;
  }
  Object.assign(drag, { x, y, t: now });
  wrap.style.setProperty("--tilt", clamp(drag.vx * 1.4, -24, 24).toFixed(1) + "deg");
  wrap.style.setProperty("--bx", x + "px");
  wrap.style.setProperty("--by", y + "px");
});
async function buddyDrop(e) {
  if (e.pointerId !== drag.id) return;
  if (!drag.on) return;
  drag.on = false;
  dragged = true;
  wrap.classList.remove("drag");
  const under = document.elementFromPoint(e.clientX, e.clientY);
  wrap.style.pointerEvents = "";
  const dizzy = drag.flips >= 5;
  // по инерции чуть дальше, потом — домой с пружинкой
  buddyPlace(clamp(drag.x + drag.vx * 8, M, innerWidth - BW - M), clamp(drag.y + drag.vy * 8, M, innerHeight - BH - M));
  if (dizzy) {
    buddyMood("dizzy");
    await sleepMs(600);
    await buddySay({ text: t("buddy.dizzy"), hold: 1600, mood: "dizzy" });
    return;
  }
  buddyMood("idle");
  const tile = under && under.closest(".svc, .ai-item");
  if (tile) {  // бросили на сервис — проверяет его по-настоящему, объясняет и предлагает починку
    await buddyCheckOne(tile);
    return;
  }
  if (under && await buddyDropOn(under)) return;
  await sleepMs(350);
  buddyHome();
}
$("#buddy").addEventListener("pointerup", buddyDrop);
$("#buddy").addEventListener("pointercancel", (e) => { if (drag.on) { drag.on = false; wrap.classList.remove("drag"); wrap.style.pointerEvents = ""; buddyMood("idle"); buddyHome(); } });

// поглаживание: медленно водят курсором по NIXY — жмурится, румянец и сердечко
let petTime = 0, petLast = 0;
$("#buddy").addEventListener("pointermove", (e) => {
  if (drag.on || buddyBusy || e.buttons) return;
  const now = performance.now(), speed = Math.hypot(e.movementX, e.movementY) / Math.max(1, now - petLast);
  if (now - petLast > 300) petTime = 0;
  petLast = now;
  if (speed > 0 && speed < .5) petTime += 16;
  if (petTime > 900 && wrap.dataset.mood !== "pet") { petTime = 0; buddyMood("pet", 1700); }
});
// «Показывать NIXY»: прячется сразу, не дожидаясь ответа программы
$('.switch[data-key="buddy"]').addEventListener("click", (e) => { wrap.hidden = e.currentTarget.getAttribute("aria-checked") !== "true"; });
window.addEventListener("resize", () => { if (!buddyBusy) buddyHome(); });
// док меняет ширину после загрузки шрифтов и смены текста состояния — «дом» сдвигается вместе с ним
new ResizeObserver(() => { if (!buddyBusy && !drag.on) buddyHome(); }).observe($(".dock"));
requestAnimationFrame(() => { wrap.style.transition = "none"; buddyHome(); requestAnimationFrame(() => { wrap.style.transition = ""; }); });

// ---- «Списки»: три своих списка движка. Текст приходит от программы (state.lists); правки,
// которые ещё не сохранены, не затираются новым состоянием.
const LISTS = { general: "", exclude: "", ipexclude: "" };
const listSaved = { general: null, exclude: null, ipexclude: null };  // что лежит в файле сейчас
let listTab = "general";
const plural = (forms, n) => {  // русские формы: 1 домен, 2 домена, 5 доменов
  const k = lang === "ru" ? (n % 10 === 1 && n % 100 !== 11 ? 0 : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? 1 : 2) : n === 1 ? 0 : 1;
  return forms[k].replace("{}", n);
};
function renderListMeta() {
  const ed = $("#list-editor"), lines = ed.value.split("\n");
  $("#list-gutter").textContent = lines.map((_, i) => i + 1).join("\n");
  const n = lines.filter((l) => l.trim() && !l.trim().startsWith("#")).length;
  const ip = listTab === "ipexclude";
  const forms = (I18N[lang] || I18N.ru)[ip ? "lists.n_ip" : "lists.n_dom"];
  $("#list-count").textContent = plural(forms, n);
  $("#list-hint").innerHTML = "";
  $("#list-hint").append(t(ip ? "lists.hint_ip" : "lists.hint_general") + " ", Object.assign(document.createElement("code"), { textContent: ip ? "203.0.113.0/24" : "example.com" }));
}
function showList(name) {
  LISTS[listTab] = $("#list-editor").value;  // правки не теряются при переходе между вкладками
  listTab = name;
  for (const b of $("#list-tabs").children) b.setAttribute("aria-pressed", String(b.dataset.list === name));
  $("#list-editor").value = LISTS[name];
  $("#list-editor").scrollTop = 0;
  renderListMeta();
}
for (const b of $("#list-tabs").children) b.onclick = () => showList(b.dataset.list);
function renderLists(s) {
  for (const name of Object.keys(LISTS)) {
    const fresh = (s.lists || {})[name];
    if (fresh === undefined || fresh === listSaved[name]) continue;
    const dirty = (name === listTab ? $("#list-editor").value : LISTS[name]) !== (listSaved[name] ?? "");
    listSaved[name] = fresh;
    if (dirty) continue;
    LISTS[name] = fresh;
    if (name === listTab) { $("#list-editor").value = fresh; renderListMeta(); }
  }
  const p = s.probe, box = $("#probe-result");
  box.hidden = !p;
  if (!p) return;
  box.dataset.tone = p.tone;
  box.querySelector(".dom").textContent = p.domain;
  box.querySelector(".verdict").textContent = t(p.key, p.kb);
  box.querySelector(".mark use").setAttribute("href", p.tone === "ok" ? "#i-check" : p.tone === "wait" ? "#t-search" : "#i-close");
  $("#b-probe-add").hidden = p.tone === "ok" || p.tone === "wait" || p.key === "lists.badname";
}
async function saveList() {
  LISTS[listTab] = $("#list-editor").value;
  const r = await api("list_save", { name: listTab, text: LISTS[listTab] });
  const res = r && (typeof r.json === "function" ? await r.json().catch(() => null) : r);
  const bad = (res && res.bad) || [0];
  if (!bad.length) return toast(t("lists.saved"));
  toast(bad[0] ? t("lists.bad_line", bad.slice(0, 5).join(", ")) : t("lists.save_err"));
}
$("#b-list-save").onclick = saveList;
$("#b-probe").onclick = () => { const v = $("#list-probe").value.trim(); if (v) api("probe", { domain: v }); };
$("#list-probe").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#b-probe").click(); });
$("#b-probe-add").onclick = () => {  // сайт уходит в «Обходить», и список сразу сохраняется
  const dom = $("#probe-result .dom").textContent;
  if (listTab !== "general") showList("general");
  const ed = $("#list-editor");
  if (!ed.value.split("\n").some((l) => l.trim().toLowerCase() === dom)) ed.value = (ed.value.trim() ? ed.value.trim() + "\n" : "") + dom;
  renderListMeta();
  saveList();
};
$("#list-editor").oninput = renderListMeta;
$("#list-editor").onscroll = () => { $("#list-gutter").scrollTop = $("#list-editor").scrollTop; };
document.addEventListener("keydown", (e) => {
  if (screen === "lists" && e.ctrlKey && e.code === "KeyS") { e.preventDefault(); $("#b-list-save").click(); }
});

// ---- звёзды фона: несколько десятков точек со случайным местом, размером, задержкой загорания (0–3 с)
// и периодом мерцания. Загораются по состоянию #backdrop (CSS); ~40 % помечены .p — светят и при «частично»
(function skyStars() {
  const box = $("#sky-stars"), r = (a, b) => a + Math.random() * (b - a);
  for (let i = 0; i < 46; i++) {
    const s = document.createElement("i");
    s.style.cssText = `--x:${r(1, 99).toFixed(1)}%;--y:${r(1, 97).toFixed(1)}%;--s:${r(1.2, 2.6).toFixed(1)}px;` +
      `--o:${r(.45, .9).toFixed(2)};--d:${r(0, 3).toFixed(2)}s;--t:${r(3, 6.5).toFixed(1)}s`;
    if (Math.random() < .4) s.className = "p";
    box.append(s);
  }
})();
// окно свёрнуто или скрыто — фоновые анимации (звёзды, облака) на паузе
document.addEventListener("visibilitychange", () => $("#backdrop").classList.toggle("paused", document.hidden));

window.addEventListener("resize", closePopover);
// перетащенный в окно файл или ссылка не должны открываться вместо интерфейса
document.addEventListener("dragover", (e) => e.preventDefault());
document.addEventListener("drop", (e) => e.preventDefault());
applyLang(lang);

// ---- поток состояния
window.__nixyz = (s) => { $("#offline").classList.remove("show"); render(s); };  // сюда программа шлёт состояние

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
  bridge().hello().then(window.__nixyz);
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
