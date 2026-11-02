r"""
Prohod — оболочка для официального движка zapret (winws.exe).

Что делает:
  * скачивает официальный релиз Flowseal/zapret-discord-youtube с GitHub
    и сверяет SHA-256 с контрольной суммой, которую публикует GitHub;
  * читает стратегии из general*.bat и запускает winws.exe напрямую,
    без cmd и без выполнения .bat-файлов;
  * умеет сам перебрать стратегии и выбрать ту, при которой открываются
    YouTube и Discord.

Чего НЕ делает: не шлёт телеметрию, не пускает трафик через чужие серверы
(никаких VPN/прокси). В сеть ходит только к GitHub (проверка обновлений при запуске,
скачивание движка) и к YouTube/Discord при проверке доступа. winws меняет пакеты прямо
на этом компьютере.

Собранная программа (Prohod.exe) живёт в C:\Program Files\Prohod, данные — там же в папке
data: менять их может только администратор. Окно — ui/index.html
+ ui/app.js в собственном окне программы (pywebview / WebView2). Команды идут только через мост
pywebview; его встроенный сервер на 127.0.0.1 отдаёт лишь файлы окна и ничем не управляет.
Режим разработки (запуск .pyw) может показывать окно в Edge.
"""

import ctypes
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "Prohod"
APP_TITLE = "Prohod"
APP_VERSION = "1.3.0"
TASK_NAME = "Prohod"

# ---------------------------------------------------------------- язык

# Страны, где по умолчанию русский (регион из «Параметры → Время и язык → Регион», без интернета)
RU_REGIONS = {"RU", "BY", "KZ", "KG", "TJ", "UZ", "AM", "AZ", "MD", "TM"}
LANGS = ("auto", "ru", "en")
LANG = "ru"  # текущий язык окна и сообщений: "ru" или "en"


def system_lang():
    """Язык по умолчанию: русский для СНГ или русской Windows, иначе английский."""
    k32 = ctypes.windll.kernel32
    buf = ctypes.create_unicode_buffer(16)
    try:
        if k32.GetUserDefaultGeoName(buf, 16) and buf.value.upper() in RU_REGIONS:
            return "ru"
    except AttributeError:  # Windows старше 10 1709
        pass
    return "ru" if k32.GetUserDefaultUILanguage() & 0x3FF == 0x19 else "en"  # LANG_RUSSIAN


def apply_lang(choice):
    global LANG
    LANG = choice if choice in ("ru", "en") else system_lang()


def T(text, *args):
    """Перевод фразы: в коде — русский текст, английский берётся из EN."""
    if LANG == "en":
        text = EN.get(text, text)
    return text.format(*args) if args else text


EN = {
    " (обход включён)": " (bypass on)",
    " (обход выключен)": " (bypass off)",
    " Часть сайтов всё ещё недоступна.": " Some sites are still unreachable.",
    ". Запуск заблокирован. Скачайте движок заново или укажите папку повторно.":
        ". Start blocked. Download the engine again or choose the folder again.",
    "GitHub вернул странный номер версии": "GitHub returned an odd version number",
    "GitHub не дал контрольную сумму файла — скачивание отменено":
        "GitHub gave no checksum for the file — download cancelled",
    "Prohod будет запускаться при входе в Windows с правами администратора, без запроса.\n\n":
        "Prohod will start when you sign in to Windows, with administrator rights and no prompt.\n\n",
    "Prohod работает в трее. Выйти — правой кнопкой по значку → «Выйти».":
        "Prohod keeps running in the tray. To quit, right-click the icon → Quit.",
    "Prohod удалён": "Prohod removed",
    "Prohod удалён с компьютера.": "Prohod has been removed from this computer.",
    "Prohod уже запущен — значок в трее рядом с часами.":
        "Prohod is already running — look for its icon in the tray next to the clock.",
    "SHA-256 не совпал с официальным. Файл подменён или повреждён — он отброшен.":
        "SHA-256 doesn't match the official one. The file was tampered with or damaged — discarded.",
    "SHA-256 совпал с официальным, движок установлен": "SHA-256 matches the official one, engine installed",
    "winws.exe закрылся сразу (код {}). Подробности — в журнале.":
        "winws.exe exited right away (code {}). See the log for details.",
    "winws.exe неожиданно завершился (код {})": "winws.exe exited unexpectedly (code {})",
    "{} {} запущен, права администратора: {}": "{} {} started, administrator rights: {}",
    "{} из {}: «{}»": "{} of {}: “{}”",
    "{} — ссылка, а не папка. Переустановите Prohod.": "{} is a link, not a folder. Reinstall Prohod.",
    "{}: запуск обхода при входе в Windows": "{}: start the bypass when signing in to Windows",
    "«{}»: движок упал во время проверки": "“{}”: the engine crashed during the test",
    "«{}»: не запустилась — {}": "“{}”: failed to start — {}",
    "Автоподбор: {} стратегий": "Auto-select: {} strategies",
    "Архив больше заявленного — скачивание отменено": "The archive is larger than declared — download "
                                                      "cancelled",
    "Архив скачался не полностью": "The archive was not fully downloaded",
    "Архив слишком большой после распаковки": "The archive is too large when unpacked",
    "Без обхода всё открывается — проверка не отличит рабочую стратегию от нерабочей. "
    "Подбор пропущен, выбор не изменён.":
        "Everything opens without the bypass — the test can't tell a working strategy from a broken one. "
        "Auto-select skipped, selection unchanged.",
    "Без обхода доступно {} из {}": "Without the bypass: {} of {} reachable",
    "Без прав администратора обход работать не может: winws.exe ставит драйвер WinDivert.":
        "The bypass can't work without administrator rights: winws.exe installs the WinDivert driver.",
    "В {} есть --{} (пишет файлы) — такой запуск запрещён": "{} contains --{} (writes files) — not allowed",
    "В {} не найдена команда запуска winws.exe": "No winws.exe command found in {}",
    "В {} недопустимое значение: {}": "Invalid value in {}: {}",
    "В {} недопустимый путь: {}": "Invalid path in {}: {}",
    "В {} путь за пределами папки движка: {}": "Path outside the engine folder in {}: {}",
    "В архиве нет bin\\winws.exe. Скорее всего его удалил антивирус — добавьте папку {} "
    "в исключения и повторите.":
        "The archive has no bin\\winws.exe. Most likely your antivirus removed it — add the folder {} "
        "to its exclusions and try again.",
    "В релизе нет .zip архива": "The release has no .zip archive",
    "Важно: Prohod или сам Python лежат там, куда может писать любая программа вашей учётной записи. "
    "Вирус, попавший на компьютер, сможет подменить файлы и получить права администратора при следующем "
    "входе. Надёжнее держать Prohod в C:\\Program Files и поставить Python «для всех пользователей».\n\n":
        "Important: Prohod or Python itself is in a place any program of your account can write to. "
        "Malware could replace the files and get administrator rights at your next sign-in. It's safer to "
        "keep Prohod in C:\\Program Files and install Python “for all users”.\n\n",
    "Версия {} пропущена по вашему выбору": "Version {} skipped as you chose",
    "Версия {} пропущена — напомню о следующей": "Version {} skipped — I'll remind you about the next one",
    "Включены TCP timestamps (netsh), как делает service.bat": "TCP timestamps enabled (netsh), as service.bat does",
    "Включить автозапуск?": "Turn on autostart?",
    "Включить обход": "Turn bypass on",
    "Выбрана «{}» ({}/{})": "Selected “{}” ({}/{})",
    "Выйти": "Quit",
    "Выключаю обход и убираю следы в системе": "Turning the bypass off and cleaning up the system",
    "Выключаю…": "Turning off…",
    "Выключить обход": "Turn bypass off",
    "Готово — подлинность подтверждена": "Done — authenticity confirmed",
    "Движок обновлён: {} → {}, SHA-256 совпал": "Engine updated: {} → {}, SHA-256 matches",
    "Движок остановился": "The engine stopped",
    "Движок: {} (версия {}, стратегий: {})": "Engine: {} (version {}, strategies: {})",
    "Доступно {} из {}": "{} of {} reachable",
    "Доступно обновление движка: {} → {}": "Engine update available: {} → {}",
    "Закрыт посторонний winws.exe: {}": "Closed a foreign winws.exe: {}",
    "Запуск с Windows: {}": "Start with Windows: {}",
    "Запуск стратегии «{}»": "Starting strategy “{}”",
    "Запускаю…": "Starting…",
    "Здесь нет bin\\winws.exe и general*.bat. Укажите распакованную папку zapret-discord-youtube.":
        "There's no bin\\winws.exe and general*.bat here. Choose the unpacked zapret-discord-youtube folder.",
    "Значок в трее не создан: {}": "Tray icon not created: {}",
    "Игровой режим: {}": "Game mode: {}",
    "Контрольные суммы движка записаны заново": "Engine checksums saved again",
    "Контрольные суммы движка не найдены — нужно подтверждение": "Engine checksums not found — confirmation needed",
    "Лучшая: «{}» — открывается {} из {}.": "Best: “{}” — {} of {} reachable.",
    "Нажмите «Повторить».": "Press “Retry”.",
    "Не найден Microsoft Edge — он нужен, чтобы показать окно.": "Microsoft Edge not found — it's needed to "
                                                                 "show the window.",
    "Не найдены сохранённые контрольные суммы движка (настройки сброшены или папка перенесена)."
    "\n\n{}\n\nДоверять файлам в этой папке? Отвечайте «Да», только если вы сами ставили этот движок. "
    "Иначе нажмите «Нет» и скачайте движок заново.":
        "No saved engine checksums found (settings were reset or the folder was moved).\n\n{}\n\n"
        "Trust the files in this folder? Answer “Yes” only if you installed this engine yourself. "
        "Otherwise press “No” and download the engine again.",
    "Не получилось изменить автозапуск. Подробности в журнале.": "Couldn't change autostart. See the log for details.",
    "Не получилось изменить автозапуск: {}": "Couldn't change autostart: {}",
    "Не получилось проверить обновления. Подробности в журнале.": "Couldn't check for updates. See the log for details.",
    "Не удалось вернуть «{}»: {}": "Couldn't restore “{}”: {}",
    "Не удалось запустить": "Couldn't start",
    "Не удалось запустить: {}": "Couldn't start: {}",
    "Не удалось открыть окно: {}\n\nУстановите «Microsoft Edge WebView2 Runtime» с сайта Microsoft "
    "и запустите Prohod снова.":
        "Couldn't open the window: {}\n\nInstall “Microsoft Edge WebView2 Runtime” from the Microsoft "
        "website and start Prohod again.",
    "Не удалось получить список изменений: {}": "Couldn't get the list of changes: {}",
    "Недопустимое имя версии": "Invalid version name",
    "Неизвестная переменная %{}% в {}": "Unknown variable %{}% in {}",
    "Неожиданный размер архива": "Unexpected archive size",
    "Нет файла ui/{}": "No file ui/{}",
    "Ни одна стратегия не помогла. Выбор не изменён — попробуйте игровой режим или обновите движок.":
        "No strategy helped. Selection unchanged — try game mode or update the engine.",
    "Ни одна стратегия не улучшила доступ (без обхода {} из {})":
        "No strategy improved access (without the bypass {} of {})",
    "Нужны права администратора. Перезапустите Prohod.": "Administrator rights needed. Restart Prohod.",
    "Обновлений нет: движок {} — последняя версия": "No updates: engine {} is the latest",
    "Обновляю движок…": "Updating the engine…",
    "Обход выключен": "Bypass is off",
    "Обход работает": "Bypass is on",
    "Обход работает: «{}»": "Bypass is on: “{}”",
    "Окно WebView2 не открылось: {}": "WebView2 window didn't open: {}",
    "Окно закроется само": "The window will close by itself",
    "Окно открыло чужую страницу ({}) — вызов отклонён": "The window opened a foreign page ({}) — call "
                                                         "rejected",
    "Окно открыто напрямую, не через планировщик ({})": "Window opened directly, not via the scheduler ({})",
    "Окно попыталось открыть чужую страницу — возвращаю": "The window tried to open a foreign page — going "
                                                          "back",
    "Окно устарело. Закройте его и запустите Prohod заново.": "This window is outdated. Close it and start "
                                                              "Prohod again.",
    "Опасный путь в архиве: {}": "Unsafe path in the archive: {}",
    "Останавливаю после текущей стратегии…": "Stopping after the current strategy…",
    "Откройте журнал. Частая причина — антивирус или другой обход.":
        "Open the log. A common cause is antivirus or another bypass tool.",
    "Открыть {}": "Open {}",
    "Ошибка: {}": "Error: {}",
    "Папка zapret-discord-youtube (где bin и general.bat)": "zapret-discord-youtube folder (with bin and "
                                                            "general.bat)",
    "Первый запуск: подбираю стратегию автоматически": "First run: selecting a strategy automatically",
    "Подбираю стратегию…": "Finding a strategy…",
    "Подбор отменён": "Auto-select cancelled",
    "Подбор отменён, выбор не изменён.": "Auto-select cancelled, selection unchanged.",
    "Подозрительные аргументы в {}: {}": "Suspicious arguments in {}: {}",
    "Приложение закрывается": "The app is closing",
    "Проверка доступа": "Access check",
    "Проверка обновлений не удалась: {}": "Update check failed: {}",
    "Проверьте интернет и нажмите «Повторить».": "Check your internet connection and press “Retry”.",
    "Проверяю «{}» — {} из {}": "Testing “{}” — {} of {}",
    "Проверяю доступ без обхода": "Checking access without the bypass",
    "Работает служба «zapret» (установлена через service.bat). Она уже делает обход и будет мешать."
    "\n\nОстановить её сейчас? Удалить насовсем можно в service.bat.":
        "The “zapret” service is running (installed via service.bat). It already does a bypass and will "
        "interfere.\n\nStop it now? You can remove it for good in service.bat.",
    "Релиз {}: {}, SHA-256 {}": "Release {}: {}, SHA-256 {}",
    "Сайты открываются и без обхода — подбирать не из чего.": "Sites open without the bypass — nothing to "
                                                              "choose from.",
    "Сверяю SHA-256 и запоминаю файлы…": "Checking SHA-256 and remembering the files…",
    "Скачиваю {} — {}%": "Downloading {} — {}%",
    "Служба zapret остановлена": "zapret service stopped",
    "Сначала выключите обход.": "Turn the bypass off first.",
    "Спрашиваю у GitHub последний релиз…": "Asking GitHub for the latest release…",
    "Ссылка ведёт не на официальный репозиторий: {}": "The link doesn't point to the official repository: {}",
    "Стратегия {} изменена после установки или добавлена позже": "Strategy {} was changed after install or added later",
    "Стратегия «{}»": "Strategy “{}”",
    "Стратегия «{}» · движок {}": "Strategy “{}” · engine {}",
    "Стратегия «{}» не найдена": "Strategy “{}” not found",
    "У вас последняя версия движка — {}.": "You have the latest engine version — {}.",
    "Удалено: ": "Removed: ",
    "Удаляю Prohod…": "Removing Prohod…",
    "Уже запущен другой winws.exe (наверное, zapret открыт вручную через .bat). Два одновременно "
    "не работают.\n\nЗакрыть его?":
        "Another winws.exe is already running (probably zapret started by hand via .bat). Two can't work "
        "at once.\n\nClose it?",
    "Файлы движка изменились после установки: ": "Engine files changed after install: ",
    "Эту папку Prohod не скачивал и не может проверить её подлинность. Используйте только zapret со "
    "страницы github.com/Flowseal.\n\nЗапомнить текущие файлы? Если потом их кто-то изменит, Prohod "
    "откажется запускать движок.":
        "Prohod didn't download this folder and can't verify it. Use only zapret from "
        "github.com/Flowseal.\n\nRemember the current files? If someone changes them later, Prohod "
        "will refuse to start the engine.",
    "автозапуск": "autostart",
    "драйвер {}": "driver {}",
    "запись в «Приложениях»": "the Apps entry",
    "системных следов не было": "there were no system traces",
    "ярлык {}": "shortcut {}",
    # ниже — фразы, которые собираются не одним вызовом
    "да": "yes", "нет": "no", "вкл": "on", "выкл": "off",
    "Нажмите, чтобы включить": "Click to turn on",
    "обход работает": "bypass on", "запуск…": "starting…", "ошибка": "error", "обход выключен": "bypass off",
    "Удалить Prohod с компьютера полностью?\n\nБудут выключены обход и автозапуск, удалены драйвер WinDivert, "
    "движок zapret, настройки, ярлыки, запись в «Приложениях» и сама программа.\n\nОтменить это нельзя.":
        "Remove Prohod from this computer completely?\n\nThe bypass and autostart will be turned off, and the "
        "WinDivert driver, the zapret engine, settings, shortcuts, the Apps entry and the program itself "
        "will be deleted.\n\nThis can't be undone.",
    "стратегия": "strategy", "стратегии": "strategies", "стратегий": "strategies",
}


def _known_folder(csidl):
    buf = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) == 0:
        return Path(buf.value)
    return None


# Пути берутся у Windows, а не из переменных окружения, которые можно подменить
PROGRAM_FILES = _known_folder(0x26)      # C:\Program Files
PROGRAM_DIRS = [p for p in (_known_folder(0x2A), PROGRAM_FILES) if p]  # x86, x64
INSTALL_DIR = PROGRAM_FILES / APP_NAME if PROGRAM_FILES else None
UNINSTALL_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"

FROZEN = bool(getattr(sys, "frozen", False))  # собранная программа Prohod.exe
APP_DIR = Path(sys.executable if FROZEN else __file__).resolve().parent
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
# Данные собранной программы — в C:\Program Files\Prohod\data: туда без прав администратора
# нельзя ни записать, ни заранее подложить папку или ссылку (в отличие от ProgramData).
DATA_DIR = APP_DIR / "data"
ENGINE_DIR = DATA_DIR / "engine" if FROZEN else APP_DIR / "engine"
SETTINGS_FILE = DATA_DIR / "settings.json"

REPO = "Flowseal/zapret-discord-youtube"
RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/"
MAX_DOWNLOAD = 64 * 1024 * 1024
MAX_UNPACKED = 256 * 1024 * 1024
USER_AGENT = f"{APP_NAME}/{APP_VERSION}"

TARGETS = {
    "YouTube": [
        "https://www.youtube.com",
        "https://i.ytimg.com",
        "https://redirector.googlevideo.com",
    ],
    "Discord": [
        "https://discord.com",
        "https://gateway.discord.gg",
        "https://cdn.discordapp.com",
    ],
}

# Значения как в service.bat: порт 12 — «пустой» фильтр, когда игровой режим выключен
GAME_OFF = "12"
GAME_RANGE = "1024-65535"

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class EngineError(Exception):
    pass


class TamperError(EngineError):
    """Файлы движка не совпадают с запомненными контрольными суммами."""


# ---------------------------------------------------------------- система

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _system_dir():
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.kernel32.GetSystemDirectoryW(buf, 260)
    return buf.value or os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")


SYSTEM_DIR = _system_dir()


def system_tool(name):
    """Полный путь к утилите Windows — чтобы не подхватить одноимённый файл из чужой папки."""
    sub = ("WindowsPowerShell", "v1.0") if name == "powershell" else ()
    return os.path.join(SYSTEM_DIR, *sub, name + ".exe")


DANGEROUS_ENV = ("COR_", "COMPLUS_", "DOTNET_", "CORECLR_", "WEBVIEW2_")


def sanitize_environment():
    """Убирает из окружения переменные, которые меняют поведение .NET (профилировщики),
    WebView2 (свой браузер, порт отладки) и PowerShell (свои модули). Их может записать
    в раздел реестра HKCU Environment любая программа пользователя, а Prohod работает как администратор."""
    for key in list(os.environ):
        if key.upper().startswith(DANGEROUS_ENV):
            del os.environ[key]
    os.environ["PSModulePath"] = os.path.join(SYSTEM_DIR, "WindowsPowerShell", "v1.0", "Modules")
    os.environ["ComSpec"] = os.path.join(SYSTEM_DIR, "cmd.exe")


def gui_python():
    exe = Path(sys.executable)
    if FROZEN:
        return str(exe)
    w = exe.with_name("pythonw.exe")
    return str(w if w.is_file() else exe)


def self_args(*extra):
    """Аргументы для запуска этой же программы: у Prohod.exe — только флаги,
    у .pyw — ещё -I (Python не подхватит модули из папки скрипта и PYTHON*-переменные)."""
    return list(extra) if FROZEN else ["-I", str(Path(__file__).resolve()), *extra]


def relaunch_as_admin():
    params = subprocess.list2cmdline(self_args(*sys.argv[1:]))
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", gui_python(), params, SYSTEM_DIR, 1)
    return rc > 32


def run_quiet(args, timeout=20, env=None):
    """Запуск системной утилиты (по имени из System32) без окна консоли. Возвращает (код, вывод)."""
    args = [system_tool(args[0]), *args[1:]]
    try:
        p = subprocess.run(args, capture_output=True, timeout=timeout, creationflags=NO_WINDOW,
                           cwd=SYSTEM_DIR, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)
    out = (p.stdout + p.stderr).decode("oem", errors="replace")
    return p.returncode, out


def winws_pids():
    _, out = run_quiet(["tasklist", "/FI", "IMAGENAME eq winws.exe", "/FO", "CSV", "/NH"])
    pids = []
    for line in out.splitlines():
        parts = [x.strip('"') for x in line.split('","')]
        if len(parts) > 1 and parts[0].lower() == "winws.exe" and parts[1].isdigit():
            pids.append(int(parts[1]))
    return pids


def service_running(name):
    code, out = run_quiet(["sc", "query", name])
    return code == 0 and "RUNNING" in out


def enable_tcp_timestamps():
    # То же самое делает service.bat перед запуском стратегий. Вывод netsh локализован,
    # поэтому не разбираем его, а просто ставим значение — команда идемпотентна.
    return run_quiet(["netsh", "interface", "tcp", "set", "global", "timestamps=enabled"])


def stop_stale_drivers():
    # Драйвер WinDivert от прежней версии движка мешает запуску новой (так же чистит service.bat)
    for name in ("WinDivert", "WinDivert14"):
        run_quiet(["sc", "stop", name])


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plural(n, one, few, many):
    if LANG == "en":
        return one if n == 1 else many
    if n % 10 == 1 and n % 100 != 11:
        return one
    return few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def natural_key(s):
    return [(0, int(t), "") if t.isdigit() else (1, 0, t.lower()) for t in re.findall(r"\d+|\D+", s)]


# ---------------------------------------------------------------- настройки

DEFAULTS = {"engine_dir": "", "strategy": "", "game_filter": False, "start_on_open": False,
            "skip_version": "", "lang": "auto", "theme": "auto",
            "engine_hashes": {}}
THEMES = ("auto", "light", "dark")


def load_settings():
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(DEFAULTS)
    if not isinstance(data, dict):
        return dict(DEFAULTS)
    return {k: data[k] if isinstance(data.get(k), type(v)) else v for k, v in DEFAULTS.items()}


_settings_lock = threading.Lock()


def save_settings(s):
    with _settings_lock:
        _save_settings(s)


def _save_settings(s):
    DATA_DIR.mkdir(exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_FILE)


# ---------------------------------------------------------------- движок

def forbidden_option(opt):
    """Параметры winws, которые пишут файлы. getopt_long понимает сокращения (--deb == --debug),
    поэтому запрещаем и их."""
    if opt.startswith(("debug", "hostlist-auto", "wf-save")) or opt.startswith("hostlist-a"):
        return True
    return len(opt) >= 2 and any(bad.startswith(opt) for bad in ("debug", "wf-save"))


def split_args(s):
    """Разбивает строку аргументов как cmd: пробелы вне кавычек, кавычки убираются."""
    out, cur, quoted, touched = [], [], False, False
    for ch in s:
        if ch == '"':
            quoted, touched = not quoted, True
        elif ch.isspace() and not quoted:
            if cur or touched:
                out.append("".join(cur))
                cur, touched = [], False
        else:
            cur.append(ch)
    if cur or touched:
        out.append("".join(cur))
    return out


class Engine:
    """Папка релиза zapret-discord-youtube: bin/winws.exe, lists/, general*.bat."""

    def __init__(self, root):
        self.root = Path(root)
        self.bin = self.root / "bin"
        self.lists = self.root / "lists"
        self.exe = self.bin / "winws.exe"

    @staticmethod
    def find(path):
        path = Path(path)
        if not path.is_dir():
            return None
        candidates = [path] + [p for p in path.iterdir() if p.is_dir()]
        for p in candidates:
            e = Engine(p)
            if e.exe.is_file() and e.strategies():
                return e
        return None

    def version(self):
        try:
            text = (self.root / "service.bat").read_text(encoding="utf-8", errors="replace")
            m = re.search(r'set\s+"LOCAL_VERSION=([^"]+)"', text)
            return m.group(1) if m else "?"
        except OSError:
            return "?"

    def strategies(self):
        """[(название, путь к .bat)] — стандартная первой, дальше по порядку."""
        result = []
        for f in self.root.glob("general*.bat"):
            m = re.search(r"\((.+)\)", f.stem)
            result.append((m.group(1) if m else "general", f))
        result.sort(key=lambda x: (x[1].stem.lower() != "general", natural_key(x[0])))
        return result

    def ensure_user_lists(self):
        # Как load_user_lists в service.bat: winws не любит отсутствующие файлы
        defaults = {
            "ipset-exclude-user.txt": "203.0.113.113/32\n",
            "list-general-user.txt": "# Never leave this file empty\ndomain.example.abc\n",
            "list-exclude-user.txt": "domain.example.abc\n",
        }
        for name, content in defaults.items():
            f = self.lists / name
            if not f.exists():
                f.write_text(content, encoding="utf-8")

    def command(self, bat, game_filter, text=None):
        """Собирает команду winws.exe из .bat-файла. Сам .bat не выполняется.
        text — уже прочитанное и сверенное содержимое, чтобы файл не перечитывался после проверки."""
        if text is None:
            text = Path(bat).read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"\^[ \t]*\r?\n", " ", text)
        m = re.search(r'^\s*start\s+"[^"]*"\s+(?:/min\s+)?"%BIN%winws\.exe"\s+(.+)$',
                      text, re.IGNORECASE | re.MULTILINE)
        if not m:
            raise EngineError(T("В {} не найдена команда запуска winws.exe", Path(bat).name))

        port = GAME_RANGE if game_filter else GAME_OFF
        values = {
            "bin": str(self.bin) + "\\",
            "lists": str(self.lists) + "\\",
            "gamefilter": port,
            "gamefiltertcp": port,
            "gamefilterudp": port,
        }

        def sub(mm):
            key = mm.group(1).lower()
            if key not in values:
                raise EngineError(T("Неизвестная переменная %{}% в {}", mm.group(1), Path(bat).name))
            return values[key]

        line = m.group(1).replace("%~dp0", str(self.root) + "\\")
        line = re.sub(r"%(\w+)%", sub, line)
        args = split_args(line)
        name = Path(bat).name
        bad = [a for a in args if not a.startswith("--")]
        if not args or bad:
            raise EngineError(T("Подозрительные аргументы в {}: {}", name, ' '.join(bad[:3])))
        root = self.root.resolve()
        for a in args:
            opt, _, value = a[2:].partition("=")
            if forbidden_option(opt.lower()):
                raise EngineError(T("В {} есть --{} (пишет файлы) — такой запуск запрещён", name, opt))
            if value.startswith("@") or ".." in value or "cygdrive" in value.lower():
                raise EngineError(T("В {} недопустимое значение: {}", name, a))
            if re.match(r"[A-Za-z]:", value):
                # только полный путь вида C:\... и только внутри папки движка
                p = Path(value).resolve()
                if not re.match(r"[A-Za-z]:\\", value) or (p != root and root not in p.parents):
                    raise EngineError(T("В {} путь за пределами папки движка: {}", name, value))
            elif "\\" in value or "/" in value:
                raise EngineError(T("В {} недопустимый путь: {}", name, value))
        return [str(self.exe), *args]

    def _binaries(self):
        return [p for p in self.bin.iterdir() if p.suffix.lower() in (".exe", ".dll", ".sys")]

    def manifest(self):
        """{относительный путь: sha256} для исполняемых файлов и всех стратегий."""
        files = self._binaries() + [b for _, b in self.strategies()]
        return {str(p.relative_to(self.root)): sha256_file(p) for p in files}

    def verify_binaries(self, manifest):
        """Сверяет .exe/.dll/.sys с хэшами, записанными при установке. Возвращает изменённые."""
        changed = [str(p.relative_to(self.root)) for p in self._binaries()
                   if manifest.get(str(p.relative_to(self.root))) != sha256_file(p)]
        return sorted(changed)

    def read_verified_bat(self, manifest, bat):
        """Читает .bat один раз и сверяет именно прочитанные байты — подменить файл между
        проверкой и разбором нельзя."""
        data = Path(bat).read_bytes()
        if manifest.get(str(Path(bat).relative_to(self.root))) != hashlib.sha256(data).hexdigest():
            raise TamperError(T("Стратегия {} изменена после установки или добавлена позже", Path(bat).name))
        return data.decode("utf-8", errors="replace")


# Job Object: winws.exe завершится вместе с Prohod, даже если окно убьют или оно упадёт
class _IoCounters(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]


class _BasicLimit(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", ctypes.c_uint32), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32)]


class _ExtLimit(ctypes.Structure):
    _fields_ = [("Basic", _BasicLimit), ("Io", _IoCounters), ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]


def make_kill_job():
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = ctypes.c_void_p
    k32.SetInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    k32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    job = k32.CreateJobObjectW(None, None)
    if not job:
        return None, None
    info = _ExtLimit()
    info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        return None, None
    return k32, job


class Bypass:
    """Один процесс winws.exe, запущенный этим приложением. Потокобезопасен."""

    def __init__(self, on_output):
        self.proc = None
        self.on_output = on_output
        self.closed = False
        self.lock = threading.RLock()
        self.k32, self.job = make_kill_job()

    @property
    def running(self):
        p = self.proc
        return p is not None and p.poll() is None

    def take_exit_code(self):
        """Если наш winws умер сам — забирает код выхода (один раз), иначе None."""
        with self.lock:
            p = self.proc
            if p is not None and p.poll() is not None:
                self.proc = None
                return p.returncode
        return None

    def start(self, cmd, cwd):
        self.stop()
        with self.lock:
            if self.closed:
                raise EngineError(T("Приложение закрывается"))
            p = subprocess.Popen(
                cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
            if self.job:
                self.k32.AssignProcessToJobObject(self.job, int(p._handle))
            old, self.proc = self.proc, p
        _terminate(old)  # на случай, если другой поток успел запустить свой между stop() и замком
        threading.Thread(target=self._pump, args=(p,), daemon=True).start()

    def _pump(self, proc):
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            if line:
                self.on_output(line)

    def stop(self):
        with self.lock:
            p, self.proc = self.proc, None
        _terminate(p)

    def close(self):
        with self.lock:
            self.closed = True
            p, self.proc = self.proc, None
        _terminate(p)


def _terminate(p):
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(5)


# ---------------------------------------------------------------- сеть

def _direct_opener():
    # Проверка идёт напрямую, мимо системного прокси — иначе тест врёт
    ctx = ssl.create_default_context()
    return urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                       urllib.request.HTTPSHandler(context=ctx))


def probe(url, timeout=6):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with _direct_opener().open(req, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True  # сервер ответил — соединение прошло
    except Exception:
        return False


def check_targets():
    """{сервис: [(url, ok)]}"""
    urls = [(svc, u) for svc, lst in TARGETS.items() for u in lst]
    with ThreadPoolExecutor(len(urls)) as pool:
        oks = list(pool.map(lambda x: probe(x[1]), urls))
    result = {svc: [] for svc in TARGETS}
    for (svc, u), ok in zip(urls, oks):
        result[svc].append((u, ok))
    return result


def score(res):
    return sum(ok for items in res.values() for _, ok in items)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read(2 * 1024 * 1024))


def latest_release():
    rel = fetch_json(RELEASE_API)
    tag = str(rel.get("tag_name", ""))
    if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]{0,39}", tag) or ".." in tag:
        raise EngineError(T("GitHub вернул странный номер версии"))
    asset = next((a for a in rel.get("assets", []) if str(a.get("name", "")).lower().endswith(".zip")), None)
    if not asset:
        raise EngineError(T("В релизе нет .zip архива"))
    url = str(asset.get("browser_download_url", ""))
    if not url.startswith(DOWNLOAD_PREFIX):
        raise EngineError(T("Ссылка ведёт не на официальный репозиторий: {}", url))
    digest = str(asset.get("digest") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise EngineError(T("GitHub не дал контрольную сумму файла — скачивание отменено"))
    size = int(asset.get("size", 0))
    if not 0 < size <= MAX_DOWNLOAD:
        raise EngineError(T("Неожиданный размер архива"))
    return {"tag": tag, "url": url, "sha256": digest[7:], "size": size, "name": asset["name"]}


def newer_version(tag, current):
    tag, current = tag.lstrip("vV"), (current or "").lstrip("vV")
    if not re.match(r"\d", current):
        return True  # текущую версию прочитать не удалось — лучше предложить обновление
    return natural_key(tag) > natural_key(current)


def clean_note(line):
    """Строка из описания релиза Flowseal → короткий пункт на русском без ссылок и ников."""
    line = re.sub(r"\s+by @[\w-]+(\s+in\s+\S+)?", "", line)
    line = re.sub(r"\s*(от\s+)?@[\w-]+", "", line)
    line = re.sub(r"https?://\S+", "", line)
    line = line.replace("**", "").replace("`", "").strip(" -*\t")
    return line[:180]


def release_notes(current, limit=10):
    """Пункты «что нового» из всех релизов новее текущей версии, свежие первыми."""
    rels = fetch_json(f"https://api.github.com/repos/{REPO}/releases?per_page=15")
    notes = []
    for rel in rels if isinstance(rels, list) else []:
        tag = str(rel.get("tag_name", ""))
        if not newer_version(tag, current) or rel.get("draft") or rel.get("prerelease"):
            continue
        for raw in str(rel.get("body") or "").splitlines():
            m = re.match(r"^[*-]\s+(.+)", raw)  # только пункты верхнего уровня
            if not m or "Full Changelog" in raw or "first contribution" in raw:
                continue
            text = clean_note(m.group(1))
            if len(text) > 3 and text not in notes:
                notes.append(text)
            if len(notes) >= limit:
                return notes
    return notes


def download_verified(rel, progress):
    """Скачивает архив в память и возвращает байты, только если SHA-256 совпал.
    Архив не лежит на диске между проверкой и распаковкой — подменить его негде."""
    h = hashlib.sha256()
    buf = bytearray()
    req = urllib.request.Request(rel["url"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        while True:
            chunk = r.read(64 * 1024)
            if not chunk:
                break
            if len(buf) + len(chunk) > rel["size"]:
                raise EngineError(T("Архив больше заявленного — скачивание отменено"))
            h.update(chunk)
            buf += chunk
            progress(len(buf) / rel["size"])
    if len(buf) != rel["size"]:
        raise EngineError(T("Архив скачался не полностью"))
    if h.hexdigest() != rel["sha256"]:
        raise EngineError(T("SHA-256 не совпал с официальным. Файл подменён или повреждён — он отброшен."))
    return bytes(buf)


def safe_extract(data, dest):
    dest = Path(dest).resolve()
    written = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if target != dest and dest not in target.parents:
                raise EngineError(T("Опасный путь в архиве: {}", info.filename))
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                while chunk := src.read(1 << 20):
                    written += len(chunk)  # считаем реальные байты, а не заявленные в заголовке
                    if written > MAX_UNPACKED:
                        raise EngineError(T("Архив слишком большой после распаковки"))
                    out.write(chunk)


def _inside_engine_dir(p):
    return Path(p).resolve().parent == ENGINE_DIR.resolve()


def install_release(rel, progress):
    ENGINE_DIR.mkdir(exist_ok=True)
    final = ENGINE_DIR / rel["tag"]
    partial = ENGINE_DIR / (rel["tag"] + ".partial")
    if not (_inside_engine_dir(final) and _inside_engine_dir(partial)):
        raise EngineError(T("Недопустимое имя версии"))
    data = download_verified(rel, progress)
    try:
        if partial.exists():
            shutil.rmtree(partial)
        safe_extract(data, partial)
        e = Engine.find(partial)
        if not e:
            raise EngineError(T("В архиве нет bin\\winws.exe. Скорее всего его удалил антивирус — добавьте "
                                "папку {} в исключения и повторите.", ENGINE_DIR))
        sub = e.root.relative_to(partial)
        old = ENGINE_DIR / (rel["tag"] + ".old")
        if old.exists():
            shutil.rmtree(old)
        if final.exists():
            final.rename(old)
        try:
            partial.rename(final)
        except OSError:
            if old.exists() and not final.exists():
                old.rename(final)  # вернуть рабочий движок на место
            raise
        shutil.rmtree(old, ignore_errors=True)
    finally:
        if partial.exists():
            shutil.rmtree(partial, ignore_errors=True)
    return Engine(final / sub)


# ---------------------------------------------------------------- автозапуск

def autostart_enabled():
    code, _ = run_quiet(["schtasks", "/Query", "/TN", TASK_NAME])
    return code == 0


def in_program_files(path):
    path = Path(path).resolve()
    return any(r.resolve() in path.parents for r in PROGRAM_DIRS)


def set_autostart(on):
    if not on:
        code, out = run_quiet(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        return code == 0, out
    # Задача создаётся через PowerShell напрямую из параметров — без временного XML-файла,
    # который можно было бы подменить между записью и регистрацией.
    # Пути передаются через переменные окружения, а не вставкой в текст скрипта:
    # никакие кавычки в имени папки не смогут превратиться в команду PowerShell.
    env = dict(os.environ,
               PROHOD_EXE=gui_python(),
               PROHOD_ARGS=subprocess.list2cmdline(self_args("--autostart")),
               PROHOD_DIR=str(APP_DIR),
               PROHOD_TASK=TASK_NAME,
               PROHOD_DESC=T("{}: запуск обхода при входе в Windows", APP_NAME))
    script = """
$ErrorActionPreference = 'Stop'
$u = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$a = New-ScheduledTaskAction -Execute $env:PROHOD_EXE -Argument $env:PROHOD_ARGS -WorkingDirectory $env:PROHOD_DIR
$t = New-ScheduledTaskTrigger -AtLogOn -User $u
$t.Delay = 'PT5S'
$p = New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Highest
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $env:PROHOD_TASK -Description $env:PROHOD_DESC -Action $a -Trigger $t -Principal $p -Settings $s -Force | Out-Null
"""
    code, out = run_quiet(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                           "-Command", script], timeout=60, env=env)
    return code == 0, out


# ---------------------------------------------------------------- окно

UI_DIR = BUNDLE_DIR / "ui"
UI_FILES = {"/": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8")}


def find_edge():
    for root in PROGRAM_DIRS:
        p = root / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        if p.is_file():
            return p
    return None


def edge_command(url, profile_dir):
    """Edge в режиме приложения: без вкладок и адресной строки, с отдельным пустым профилем
    и выключенными фоновыми сервисами браузера."""
    edge = find_edge()
    if not edge:
        raise EngineError(T("Не найден Microsoft Edge — он нужен, чтобы показать окно."))
    return [
        str(edge), f"--app={url}", f"--user-data-dir={profile_dir}",
        "--window-size=420,800", "--no-first-run", "--no-default-browser-check",
        "--disable-sync", "--disable-background-networking", "--disable-component-update",
        "--disable-extensions", "--disable-default-apps", "--disable-domain-reliability",
        "--disable-breakpad", "--disable-crash-reporter", "--metrics-recording-only", "--no-pings",
        "--disable-client-side-phishing-detection", "--no-service-autorun",
        "--disable-features=Translate,msEdgeSidebarV2,msImplicitSignin,msShowSigninPrompt,"
        "AutofillServerCommunication,OptimizationHints,MediaRouter",
    ]


def open_window(url, profile_dir):
    """Открывает окно С ОБЫЧНЫМИ правами пользователя, а не администратора: через разовую
    задачу планировщика с RunLevel=Limited. Так из окна нельзя попасть в интернет с правами
    администратора. Если не вышло — запасной путь напрямую (в окне нет внешних ссылок)."""
    cmd = edge_command(url, profile_dir)
    task = f"{TASK_NAME}-window-{secrets.token_hex(4)}"
    env = dict(os.environ, PROHOD_EXE=cmd[0], PROHOD_ARGS=subprocess.list2cmdline(cmd[1:]),
               PROHOD_DIR=SYSTEM_DIR, PROHOD_TASK=task)
    script = """
$ErrorActionPreference = 'Stop'
$u = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$a = New-ScheduledTaskAction -Execute $env:PROHOD_EXE -Argument $env:PROHOD_ARGS -WorkingDirectory $env:PROHOD_DIR
$p = New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Limited
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $env:PROHOD_TASK -Action $a -Principal $p -Settings $s -Force | Out-Null
try { Start-ScheduledTask -TaskName $env:PROHOD_TASK; Start-Sleep -Milliseconds 1500 }
finally { Unregister-ScheduledTask -TaskName $env:PROHOD_TASK -Confirm:$false }
"""
    code, out = run_quiet(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                           "-Command", script], timeout=60, env=env)
    if code == 0:
        return "limited"
    subprocess.Popen(cmd, cwd=SYSTEM_DIR, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    return "direct: " + out.strip()[:300]


def shortcut_paths():
    """Ярлыки, которые создаёт установщик: «Пуск» и рабочий стол для всех пользователей."""
    dirs = [_known_folder(0x17), _known_folder(0x19)]  # COMMON_PROGRAMS, COMMON_DESKTOPDIRECTORY
    names = (f"{APP_TITLE}.lnk", "Проход.lnk")  # «Проход.lnk» — так назывались ярлыки версии 1.1.0
    return [d / n for d in dirs if d for n in names]


def is_link(path):
    try:
        return bool(os.lstat(path).st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except OSError:
        return False


def secure_data_dir():
    """Папка данных. У собранной программы она внутри Program Files и наследует его права
    (менять могут только администраторы); ссылку вместо папки не принимаем."""
    if is_link(DATA_DIR):
        raise EngineError(T("{} — ссылка, а не папка. Переустановите Prohod.", DATA_DIR))
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def own_processes(exe):
    """PID процессов, запущенных ровно из этого файла (не просто с таким же именем)."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_wchar_p,
                                               ctypes.POINTER(ctypes.c_uint32)]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    _, out = run_quiet(["tasklist", "/FI", f"IMAGENAME eq {Path(exe).name}", "/FO", "CSV", "/NH"])
    found = []
    for line in out.splitlines():
        parts = [x.strip('"') for x in line.split('","')]
        if len(parts) < 2 or not parts[1].isdigit():
            continue
        pid = int(parts[1])
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            continue
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_uint32(1024)
        try:
            if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)) and \
                    os.path.normcase(buf.value) == os.path.normcase(str(exe)):
                found.append(pid)
        finally:
            k32.CloseHandle(h)
    return found


def driver_is_ours(name):
    """Драйвер WinDivert ставит каждый, кто им пользуется (другой zapret, GoodbyeDPI…).
    Удаляем только тот, что загружен из нашей папки движка."""
    code, out = run_quiet(["sc", "qc", name])
    if code != 0:
        return False
    m = re.search(r"BINARY_PATH_NAME\s*:\s*(.+)", out)
    path = (m.group(1).strip().strip('"') if m else "").lower().replace("\\??\\", "")
    return str(ENGINE_DIR.resolve()).lower() in path


def remove_system_traces():
    """Всё, что Prohod оставляет в Windows, кроме своей папки: автозапуск, свой драйвер,
    ярлыки, запись в «Приложениях»."""
    import winreg
    done = []
    if autostart_enabled():
        set_autostart(False)
        done.append(T("автозапуск"))
    for name in ("WinDivert", "WinDivert14"):
        if not driver_is_ours(name):
            continue
        run_quiet(["sc", "stop", name])
        for _ in range(17):  # до ~5 с: драйвер отпускает файл не сразу
            code, out = run_quiet(["sc", "query", name])
            if code != 0 or "STOPPED" in out:
                break
            time.sleep(0.3)
        if run_quiet(["sc", "delete", name])[0] == 0:
            done.append(T("драйвер {}", name))
    for lnk in shortcut_paths():
        try:
            lnk.unlink()
            done.append(T("ярлык {}", lnk.parent.name))
        except OSError:
            pass
    try:
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, UNINSTALL_KEY)
        done.append(T("запись в «Приложениях»"))
    except OSError:
        pass
    return done


def schedule_removal():
    """Папку программы нельзя удалить, пока программа запущена, — это делает отдельный процесс
    после её выхода. Удаляется только ровно папка программы в Program Files, и через «rd», который,
    в отличие от Remove-Item, не уходит по ссылкам внутри папки."""
    if not (FROZEN and INSTALL_DIR and APP_DIR == INSTALL_DIR and not is_link(APP_DIR)):
        return  # режим разработки: свои папки рядом со скриптом не трогаем
    env = dict(os.environ, PROHOD_DIR=str(APP_DIR), PROHOD_PID=str(os.getpid()),
               PROHOD_CMD=system_tool("cmd"))
    script = ("Wait-Process -Id ([int]$env:PROHOD_PID) -Timeout 120 -ErrorAction SilentlyContinue; "
              "for ($i = 0; $i -lt 40; $i++) { & $env:PROHOD_CMD /d /c rd /s /q $env:PROHOD_DIR; "
              "if (-not (Test-Path -LiteralPath $env:PROHOD_DIR)) { break }; Start-Sleep -Milliseconds 750 }")
    subprocess.Popen([system_tool("powershell"), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                      "-Command", script], cwd=SYSTEM_DIR, env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)


UNINSTALL_QUESTION = ("Удалить Prohod с компьютера полностью?\n\n"
                      "Будут выключены обход и автозапуск, удалены драйвер WinDivert, движок zapret, "
                      "настройки, ярлыки, запись в «Приложениях» и сама программа.\n\nОтменить это нельзя.")


def uninstall_from_windows():
    """Удаление из «Параметры → Приложения» (Prohod.exe --uninstall): без окна программы."""
    if not native_confirm(T(UNINSTALL_QUESTION)):
        return
    if FROZEN:  # закрыть открытый Prohod (ровно этот exe) — его winws.exe закроется вместе с ним
        for pid in own_processes(sys.executable):
            if pid != os.getpid():
                run_quiet(["taskkill", "/F", "/PID", str(pid)])
        time.sleep(1)
    remove_system_traces()
    schedule_removal()
    message(T("Prohod удалён с компьютера."))


def native_confirm(text):
    """Системное окно Windows «Да/Нет» (по умолчанию — «Нет»). Для самых опасных решений:
    его нельзя нажать через окно-браузер или подделанный запрос."""
    flags = 0x4 | 0x30 | 0x100 | 0x40000 | 0x10000  # YESNO, WARNING, DEFBUTTON2, TOPMOST, SETFOREGROUND
    return ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, flags) == 6


def message(text, error=False):
    """Системное окно Windows с одной кнопкой «ОК»."""
    icon = 0x10 if error else 0x40  # ICONERROR / ICONINFORMATION
    ctypes.windll.user32.MessageBoxW(None, text, APP_TITLE, icon | 0x40000 | 0x10000)  # TOPMOST, FOREGROUND


def pick_folder(title):
    """Системный диалог выбора папки Windows (WinForms в отдельном STA-потоке)."""
    result = {}

    def run():
        import clr
        clr.AddReference("System.Windows.Forms")
        from System.Windows.Forms import DialogResult, FolderBrowserDialog, Form
        owner = Form()  # невидимый владелец поверх всех окон — диалог не спрячется за Prohod
        owner.TopMost, owner.ShowInTaskbar, owner.Opacity = True, False, 0
        owner.Show()
        dlg = FolderBrowserDialog()
        dlg.Description = title
        if dlg.ShowDialog(owner) == DialogResult.OK:
            result["d"] = dlg.SelectedPath
        owner.Close()

    import clr  # noqa: F401 — загружает .NET, после этого импортируется System.*
    from System.Threading import ApartmentState, Thread, ThreadStart
    t = Thread(ThreadStart(run))
    t.SetApartmentState(ApartmentState.STA)
    t.Start()
    t.Join()
    return result.get("d") or ""


# ---------------------------------------------------------------- логика приложения

IDLE_TITLE, IDLE_SUB = "Обход выключен", "Нажмите, чтобы включить"


class Controller:
    """Всё состояние приложения. Окно только показывает self.state и присылает команды."""

    def __init__(self, autostart=False):
        self.settings = load_settings()
        self.engine = None
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.version = 0
        self.is_busy = False
        self.closing = False
        self._auto_running = False
        self._tcp_done = False
        self.running_name = None  # стратегия, с которой сейчас работает наш winws
        self.stop_flag = threading.Event()
        self.dialogs = []
        self.on_theme = None         # окно перекрашивает свой заголовок под тему
        self.on_quit = None          # окно задаёт, как себя закрыть (нужно для удаления программы)
        self.uninstalling = False
        self._pending_release = None
        self._checking = threading.Lock()   # одна проверка обновлений за раз
        self._uninstall_done = threading.Event()
        self._trust_pending = False
        self.log_lines = deque(maxlen=400)
        self.bypass = Bypass(lambda line: self.log(line, "engine"))
        apply_lang(self.settings["lang"])
        self.state = {
            "screen": "setup", "power": "off", "title": T(IDLE_TITLE), "sub": T(IDLE_SUB),
            "strategy": "", "strategies": [], "engine": "", "busy": False, "auto": False,
            "auto_note": "",
            "pills": {svc: {"tone": "idle", "note": ""} for svc in TARGETS},
            "toggles": {"game": self.settings["game_filter"], "open": self.settings["start_on_open"],
                        "autostart": False},
            "setup": {"text": "", "tone": "muted"}, "dialog": None, "admin": is_admin(),
            "update": None, "app_version": APP_VERSION, "on_since": None, "auto_progress": None,
            "lang": LANG, "prefs": {"lang": self.settings["lang"], "theme": self.settings["theme"]},
        }
        self.log(T("{} {} запущен, права администратора: {}", APP_NAME, APP_VERSION, T('да') if is_admin() else T('нет')))
        self._load_engine()
        threading.Thread(target=lambda: self.set(toggles=dict(self.state["toggles"],
                                                              autostart=autostart_enabled())),
                         daemon=True).start()
        if self.engine and (autostart or self.settings["start_on_open"]):  # без подтверждённых хэшей engine=None
            self.start_bypass()
        if self.engine:
            self.check_updates()
        elif not self._trust_pending:
            self.download(auto=True)  # первый запуск: всё сам — скачать, проверить, подобрать, включить

    # ---- состояние

    def set(self, **kw):
        with self.lock:
            self.state.update(kw)
            self.version += 1
            self.changed.notify_all()

    def snapshot(self):
        with self.lock:
            return dict(self.state, log=list(self.log_lines), version=self.version)

    def log(self, text, tag="info"):
        with self.lock:
            self.log_lines.append([time.strftime("%H:%M:%S"), text, tag])
            self.version += 1
            self.changed.notify_all()

    def _status(self, power, title, sub):
        # с какого момента обход работает без перерыва — окно показывает «работает 12 мин»
        since = None
        if power == "on":
            since = self.state["on_since"] if self.state["power"] == "on" else time.time()
        self.set(power=power, title=title, sub=sub, on_since=since)

    def _refresh_status(self):
        if self.bypass.running and self.running_name:
            self._status("on", T("Обход работает"), T("Стратегия «{}»", self.running_name))
        else:
            self._status("off", T(IDLE_TITLE), T(IDLE_SUB))

    def _reset_pills(self):
        self.set(pills={svc: {"tone": "idle", "note": ""} for svc in TARGETS})

    def _set_busy(self, v):
        self.is_busy = v
        self.set(busy=v, auto=self._auto_running)

    def watchdog(self):
        """Замечает, если наш winws.exe умер сам."""
        while not self.closing:
            time.sleep(0.3)
            if not self.is_busy:
                code = self.bypass.take_exit_code()
                if code is not None:
                    self.running_name = None
                    self.log(T("winws.exe неожиданно завершился (код {})", code), "err")
                    self._reset_pills()
                    self._status("error", T("Движок остановился"),
                                 T("Откройте журнал. Частая причина — антивирус или другой обход."))

    def run_bg(self, fn, *args, notify=False):
        """Тяжёлая работа в фоне, по одной задаче за раз. Если fn вернёт функцию,
        она выполнится после снятия блокировки — так можно начать следующее действие."""
        with self.lock:
            if self.is_busy:
                return False
            self._set_busy(True)

        def wrap():
            then = None
            try:
                then = fn(*args)
            except Exception as e:
                self.log(T("Ошибка: {}", e), "err")
                self._refresh_status()
                if notify:
                    self.alert(str(e))
            finally:
                self._set_busy(False)
                if callable(then):
                    then()

        threading.Thread(target=wrap, daemon=True).start()
        return True

    # ---- диалоги в окне (очередь: показывается первый, остальные ждут)

    def _dialog(self, text, kind):
        d = {"id": secrets.token_hex(8), "text": text, "kind": kind, "event": threading.Event(), "yes": False}
        with self.lock:
            self.dialogs.append(d)
            self._show_dialog()
        return d

    def _show_dialog(self):
        head = self.dialogs[0] if self.dialogs else None
        self.set(dialog={k: head[k] for k in ("id", "text", "kind")} if head else None)

    def ask(self, text):
        """Вопрос «да/нет». Ждёт ответа из окна (вызывать из фонового потока)."""
        d = self._dialog(text, "confirm")
        while not d["event"].wait(0.2):
            if self.closing:
                return False
        return d["yes"]

    def alert(self, text):
        self._dialog(text, "alert")

    def answer(self, did, yes):
        with self.lock:
            d = next((d for d in self.dialogs if d["id"] == did), None)
            if not d:
                return
            self.dialogs.remove(d)
            d["yes"] = yes is True
            d["event"].set()
            self._show_dialog()

    # ---- движок

    def _load_engine(self):
        e = Engine.find(self.settings["engine_dir"]) if self.settings["engine_dir"] else None
        if e and self.settings["engine_hashes"]:
            self._set_engine(e)
            return
        if not e and ENGINE_DIR.is_dir():
            for d in sorted(ENGINE_DIR.iterdir(), key=lambda p: natural_key(p.name), reverse=True):
                if not d.name.endswith((".partial", ".old")):
                    e = Engine.find(d)
                    if e:
                        break
        self._set_engine(None)
        if e:
            # Контрольных сумм нет (настройки сброшены или папка сменилась). Молча доверять
            # файлам нельзя — иначе подмену можно «узаконить», просто удалив settings.json.
            self.log(T("Контрольные суммы движка не найдены — нужно подтверждение"), "err")
            self._trust_pending = True
            threading.Thread(target=self._ask_trust, args=(e,), daemon=True).start()

    def _ask_trust(self, e):
        if native_confirm(T("Не найдены сохранённые контрольные суммы движка (настройки сброшены или папка "
                            "перенесена).\n\n{}\n\nДоверять файлам в этой папке? Отвечайте «Да», только "
                            "если вы сами ставили этот движок. Иначе нажмите «Нет» и скачайте движок "
                            "заново.", e.root)):
            self._set_engine(e, e.manifest())
            self.log(T("Контрольные суммы движка записаны заново"), "ok")

    def _set_engine(self, e, manifest=None):
        with self.lock:
            self.engine = e
            if not e:
                self.set(screen="setup")
                return
            if manifest is not None:
                self.settings["engine_hashes"] = manifest
            self.settings["engine_dir"] = str(e.root)
            names = [n for n, _ in e.strategies()]
            if self.settings["strategy"] not in names:
                self.settings["strategy"] = names[0]
            save_settings(self.settings)
        self.set(screen="main", strategies=names, strategy=self.settings["strategy"], engine=self._engine_label())
        self.log(T("Движок: {} (версия {}, стратегий: {})", e.root, e.version(), len(names)))

    def _engine_label(self):
        n = len(self.engine.strategies())
        return f"zapret {self.engine.version()} · {n} {T(plural(n, 'стратегия', 'стратегии', 'стратегий'))}"

    def security_info(self):
        if not self.engine:
            return {"installed": False}
        root = self.engine.root
        files = []
        for name in ("winws.exe", "WinDivert.dll", "WinDivert64.sys"):
            try:
                files.append({"name": name, "sha256": sha256_file(self.engine.bin / name)})
            except OSError:
                files.append({"name": name, "sha256": ""})
        return {"installed": True, "version": self.engine.version(), "path": str(root),
                "short": str(root if len(str(root)) <= 40 else Path("…", *root.parts[-2:])), "files": files}

    def _strategy_path(self, name):
        return dict(self.engine.strategies()).get(name)

    def _need_admin(self):
        if is_admin():
            return False
        self.alert(T("Нужны права администратора. Перезапустите Prohod."))
        return True

    def _resolve_conflicts(self):
        """True — можно запускать."""
        if service_running("zapret"):
            if not self.ask(T("Работает служба «zapret» (установлена через service.bat). Она уже делает "
                              "обход и будет мешать.\n\nОстановить её сейчас? Удалить насовсем можно в "
                              "service.bat.")):
                return False
            run_quiet(["sc", "stop", "zapret"])
            time.sleep(1.5)
            self.log(T("Служба zapret остановлена"))
        p = self.bypass.proc
        ours = p.pid if p else None
        others = [pid for pid in winws_pids() if pid != ours]
        if others:
            if not self.ask(T("Уже запущен другой winws.exe (наверное, zapret открыт вручную через .bat). "
                              "Два одновременно не работают.\n\nЗакрыть его?")):
                return False
            for pid in others:
                run_quiet(["taskkill", "/PID", str(pid), "/F"])
            time.sleep(1)
            self.log(T("Закрыт посторонний winws.exe: {}", others))
        if not self.bypass.running:
            stop_stale_drivers()
        return True

    def _check_binaries(self):
        changed = self.engine.verify_binaries(self.settings["engine_hashes"])
        if changed:
            raise TamperError(T("Файлы движка изменились после установки: ") + ", ".join(changed[:4])
                              + T(". Запуск заблокирован. Скачайте движок заново или укажите папку повторно."))

    def _launch(self, name):
        """Запускает стратегию и ждёт, не упадёт ли движок сразу."""
        bat = self._strategy_path(name)
        if not bat:
            raise EngineError(T("Стратегия «{}» не найдена", name))
        self._check_binaries()
        text = self.engine.read_verified_bat(self.settings["engine_hashes"], bat)
        self.engine.ensure_user_lists()
        cmd = self.engine.command(bat, self.settings["game_filter"], text)
        if not self._tcp_done:
            if enable_tcp_timestamps()[0] == 0:
                self.log(T("Включены TCP timestamps (netsh), как делает service.bat"))
            self._tcp_done = True
        self.bypass.start(cmd, str(self.engine.bin))
        for _ in range(15):
            time.sleep(0.1)
            code = self.bypass.take_exit_code()
            if code is not None:
                raise EngineError(T("winws.exe закрылся сразу (код {}). Подробности — в журнале.", code))
        self.running_name = name

    # ---- команды из окна

    def power(self):
        if self.is_busy:
            return
        if self.bypass.running:
            self.stop_bypass()
        else:
            self.start_bypass()

    def start_bypass(self):
        if not self.engine or self.is_busy or self._need_admin():
            return
        name = self.settings["strategy"]

        def job():
            self._status("starting", T("Запускаю…"), T("Стратегия «{}»", name))
            self._reset_pills()
            self.log(T("Запуск стратегии «{}»", name))
            try:
                if not self._resolve_conflicts():
                    self._refresh_status()
                    return
                self._launch(name)
            except Exception as e:
                self.bypass.stop()  # иначе прежний winws работал бы, а экран показывал «ошибку»
                self.running_name = None
                self.log(T("Не удалось запустить: {}", e), "err")
                self._status("error", T("Не удалось запустить"), str(e))
                return
            self.log(T("Обход работает: «{}»", name), "ok")
            self._status("on", T("Обход работает"), T("Стратегия «{}»", name))
            return self.check  # сразу показать, открываются ли YouTube и Discord

        self.run_bg(job)

    def stop_bypass(self):
        def job():
            self._status("starting", T("Выключаю…"), "")
            self.bypass.stop()
            self.running_name = None
            self.log(T("Обход выключен"))
            self._reset_pills()
            self._refresh_status()

        self.run_bg(job)

    def pick(self, name):
        if self.is_busy or not self.engine or name not in self.state["strategies"]:
            return
        self.settings["strategy"] = name
        save_settings(self.settings)
        self.set(strategy=name)
        if self.bypass.running:
            self.start_bypass()

    def toggle(self, key, value):
        value = bool(value)
        if key == "open":
            self.settings["start_on_open"] = value
            save_settings(self.settings)
            self.set(toggles=dict(self.state["toggles"], open=value))
        elif key == "game" and not self.is_busy:
            self.settings["game_filter"] = value
            save_settings(self.settings)
            self.set(toggles=dict(self.state["toggles"], game=value))
            self.log(T("Игровой режим: {}", T('вкл') if value else T('выкл')))
            if self.bypass.running:
                self.start_bypass()
        elif key == "autostart":
            self.toggle_autostart(value)

    def pref(self, key, value):
        """Язык и тема окна."""
        allowed = {"lang": LANGS, "theme": THEMES}.get(key, ())
        if value not in allowed:
            return
        self.settings[key] = value
        save_settings(self.settings)
        prefs = dict(self.state["prefs"], **{key: value})
        if key == "theme":
            if self.on_theme:
                self.on_theme()
            return self.set(prefs=prefs)
        apply_lang(value)
        self.set(prefs=prefs, lang=LANG)
        if not self.is_busy:  # перевести то, что уже на экране
            self._refresh_status()
            self.set(auto_note="")
        if self.engine:
            self.set(engine=self._engine_label())

    def toggle_autostart(self, v):
        protected = in_program_files(APP_DIR) and in_program_files(gui_python())

        def job():
            if v and not native_confirm(
                    T("Prohod будет запускаться при входе в Windows с правами администратора, без запроса.\n\n")
                    + ("" if protected else
                       T("Важно: Prohod или сам Python лежат там, куда может писать любая программа вашей "
                         "учётной записи. Вирус, попавший на компьютер, сможет подменить файлы и получить "
                         "права администратора при следующем входе. Надёжнее держать Prohod в C:\\Program "
                         "Files и поставить Python «для всех пользователей».\n\n"))
                    + T("Включить автозапуск?")):
                return
            ok, out = set_autostart(v)
            if not ok:
                self.log(T("Не получилось изменить автозапуск: {}", out.strip()), "err")
                self.alert(T("Не получилось изменить автозапуск. Подробности в журнале."))
                return
            self.set(toggles=dict(self.state["toggles"], autostart=v))
            self.log(T("Запуск с Windows: {}", T('вкл') if v else T('выкл')), "ok")

        self.run_bg(job)

    def _show_results(self, res):
        pills = {}
        for svc, items in res.items():
            good = sum(ok for _, ok in items)
            pills[svc] = {"tone": "ok" if good == len(items) else "warn" if good else "bad",
                          "note": f"{good}/{len(items)}"}
            for url, ok in items:
                self.log(f"  {'✓' if ok else '✗'} {url}", "ok" if ok else "err")
        self.set(pills=pills)

    def check(self):
        def job():
            self.log(T("Проверка доступа") + (T(" (обход включён)") if self.bypass.running else T(" (обход выключен)")))
            self.set(pills={svc: {"tone": "wait", "note": "…"} for svc in TARGETS})
            res = check_targets()
            total = sum(len(items) for items in res.values())
            self._show_results(res)
            self.log(T("Доступно {} из {}", score(res), total), "ok" if score(res) == total else "err")

        self.run_bg(job)

    def auto(self):
        if self._auto_running:
            self.stop_flag.set()
            self.set(auto_note=T("Останавливаю после текущей стратегии…"))
            return
        if not self.engine or self.is_busy or self._need_admin():
            return
        names = [n for n, _ in self.engine.strategies()]
        prev = self.running_name if self.bypass.running else None
        self.stop_flag.clear()
        self._auto_running = True
        self.log(T("Автоподбор: {} стратегий", len(names)))

        def job():
            try:
                self._auto_job(names, prev)
            finally:
                self._auto_running = False
                self.set(auto_progress=None)

        if not self.run_bg(job):
            self._auto_running = False

    def _auto_job(self, names, prev):
        if not self._resolve_conflicts():
            self._refresh_status()
            return
        try:
            self._check_binaries()
        except TamperError as e:
            self.log(str(e), "err")
            self._status("error", T("Подбор отменён"), str(e))
            return
        self.bypass.stop()
        self.running_name = None
        self._reset_pills()
        self._status("starting", T("Подбираю стратегию…"), T("Проверяю доступ без обхода"))
        base = check_targets()
        base_ok, total = score(base), sum(len(items) for items in base.values())
        self.log(T("Без обхода доступно {} из {}", base_ok, total))
        if base_ok == total:
            self.log(T("Без обхода всё открывается — проверка не отличит рабочую стратегию от нерабочей. "
                       "Подбор пропущен, выбор не изменён."), "err")
            self.set(auto_note=T("Сайты открываются и без обхода — подбирать не из чего."))
            self._restore(prev)
            return

        best, best_score, best_res = None, base_ok, None
        for i, name in enumerate(names, 1):
            if self.stop_flag.is_set():
                break
            self._status("starting", T("Подбираю стратегию…"), T("{} из {}: «{}»", i, len(names), name))
            self.set(auto_progress=[i - 1, len(names)])  # кольцо вокруг кнопки
            self.set(auto_note=T("Проверяю «{}» — {} из {}", name, i, len(names)))
            try:
                self._launch(name)
            except Exception as e:
                self.log(T("«{}»: не запустилась — {}", name, e), "err")
                continue
            time.sleep(1.5)
            res = check_targets()
            alive = self.bypass.running
            self.bypass.stop()
            self.running_name = None
            if not alive:
                self.log(T("«{}»: движок упал во время проверки", name), "err")
                continue
            s = score(res)
            self.log(f"«{name}»: {s}/{total}", "ok" if s == total else "info")
            if s > best_score:
                best, best_score, best_res = name, s, res
            if s == total:
                break

        if self.stop_flag.is_set():
            self.log(T("Подбор отменён"))
            self.set(auto_note=T("Подбор отменён, выбор не изменён."))
            self._restore(prev)
            return
        if best is None:
            self.log(T("Ни одна стратегия не улучшила доступ (без обхода {} из {})", base_ok, total), "err")
            self.set(auto_note=T("Ни одна стратегия не помогла. Выбор не изменён — попробуйте игровой режим "
                                 "или обновите движок."))
            self._restore(prev)
            return
        self.settings["strategy"] = best
        save_settings(self.settings)
        self.set(strategy=best, auto_note=T("Лучшая: «{}» — открывается {} из {}.", best, best_score, total)
                 + ("" if best_score == total else T(" Часть сайтов всё ещё недоступна.")))
        self._show_results(best_res)
        self.log(T("Выбрана «{}» ({}/{})", best, best_score, total), "ok")
        self._launch(best)
        self.log(T("Обход работает: «{}»", best), "ok")
        self._status("on", T("Обход работает"), T("Стратегия «{}»", best))

    def _restore(self, prev):
        """После отмены или неудачи подбора возвращает то, что было до него."""
        if prev and not self.closing:
            try:
                self._launch(prev)
            except Exception as e:
                self.log(T("Не удалось вернуть «{}»: {}", prev, e), "err")
        self._refresh_status()

    def download(self, auto=None):
        """Скачать и проверить движок. На первом запуске (движка ещё нет) — сразу подобрать
        стратегию и включить обход, ничего не спрашивая; так же и после «Повторить»."""
        if auto is None:
            auto = self.engine is None
        if self.bypass.running:
            self.alert(T("Сначала выключите обход."))
            return

        def job():
            self.set(setup={"text": T("Спрашиваю у GitHub последний релиз…"), "tone": "muted", "step": 1})
            try:
                rel = latest_release()
                self.log(T("Релиз {}: {}, SHA-256 {}", rel['tag'], rel['name'], rel['sha256']))
                e = install_release(rel, lambda p: self.set(
                    setup={"text": T("Скачиваю {} — {}%", rel['name'], int(p * 100)), "tone": "muted",
                           "progress": p, "step": 1}))
                self.set(setup={"text": T("Сверяю SHA-256 и запоминаю файлы…"), "tone": "muted", "step": 2})
                manifest = e.manifest()
            except Exception as ex:
                net = isinstance(ex, OSError) and not isinstance(ex, EngineError)
                self.set(setup={"text": f"{ex}\n" + (T("Проверьте интернет и нажмите «Повторить».")
                                                     if net else T("Нажмите «Повторить».")),
                                "tone": "bad", "retry": True})
                raise
            self.log(T("SHA-256 совпал с официальным, движок установлен"), "ok")
            self.set(setup={"text": T("Готово — подлинность подтверждена"), "tone": "ok", "step": 3})
            self._set_engine(e, manifest)
            if auto and not self.closing:
                self.log(T("Первый запуск: подбираю стратегию автоматически"))
                return self.auto
            return None

        self.run_bg(job)

    def update(self):
        self.check_updates(manual=True)

    def check_updates(self, manual=False):
        """Сверяет версию движка с последним релизом. При запуске — тихо, по кнопке — с ответом.
        Если есть новее — окно покажет карточку: версии и список изменений."""
        def job():
            if not self._checking.acquire(blocking=False):
                return  # проверка уже идёт
            try:
                check()
            finally:
                self._checking.release()

        def check():
            cur = self.engine.version() if self.engine else ""
            try:
                rel = latest_release()
            except Exception as e:
                self.log(T("Проверка обновлений не удалась: {}", e), "err")
                if manual:
                    self.alert(T("Не получилось проверить обновления. Подробности в журнале."))
                return
            if not newer_version(rel["tag"], cur):
                self.log(T("Обновлений нет: движок {} — последняя версия", cur))
                if manual:
                    self.alert(T("У вас последняя версия движка — {}.", cur))
                return
            if not manual and self.settings["skip_version"] == rel["tag"]:
                self.log(T("Версия {} пропущена по вашему выбору", rel['tag']))
                return
            try:
                notes = release_notes(cur)
            except Exception as e:
                notes = []
                self.log(T("Не удалось получить список изменений: {}", e), "err")
            cur = self.engine.version() if self.engine else ""  # пока качали описание, могли обновиться
            if not newer_version(rel["tag"], cur):
                return
            self._pending_release = rel
            self.set(update={"current": cur or "—", "latest": rel["tag"], "notes": notes})
            self.log(T("Доступно обновление движка: {} → {}", cur, rel['tag']), "ok")

        threading.Thread(target=job, daemon=True).start()

    def update_later(self):
        self.set(update=None)

    def update_skip(self):
        rel = self._pending_release
        if rel:
            self.settings["skip_version"] = rel["tag"]
            save_settings(self.settings)
            self.log(T("Версия {} пропущена — напомню о следующей", rel['tag']))
        self.set(update=None)

    def update_apply(self):
        rel = self._pending_release
        if not rel:
            return
        cur = self.engine.version() if self.engine else "—"

        def job():
            self._status("starting", T("Обновляю движок…"), f"{cur} → {rel['tag']}")
            # Новая версия скачивается и проверяется в свою папку, пока старая работает
            e = install_release(rel, lambda p: self.set(sub=T("Скачиваю {} — {}%", rel['tag'], int(p * 100))))
            manifest = e.manifest()
            was_on = self.bypass.running
            self.bypass.stop()
            self.running_name = None
            old_root = self.engine.root if self.engine else None
            self._set_engine(e, manifest)
            self._pending_release = None
            self.log(T("Движок обновлён: {} → {}, SHA-256 совпал", cur, rel['tag']), "ok")
            # убрать прежнюю версию — только если это папка версии, которую ставил сам Prohod
            if old_root:
                top = ENGINE_DIR / old_root.relative_to(ENGINE_DIR).parts[0] if ENGINE_DIR in old_root.parents else None
                if top and top.name != rel["tag"] and re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]{0,39}", top.name):
                    shutil.rmtree(top, ignore_errors=True)
            if was_on:
                self._launch(self.settings["strategy"])
                self._status("on", T("Обход работает"), T("Стратегия «{}» · движок {}", self.settings['strategy'], rel['tag']))
            else:
                self._refresh_status()

        if self.run_bg(job, notify=True):
            self.set(update=None)

    def uninstall(self):
        """Удалить Prohod полностью: обход, автозапуск, драйвер, движок, настройки, ярлыки, программу."""
        def job():
            if not native_confirm(T(UNINSTALL_QUESTION)):
                return
            self.uninstalling = True  # с этого момента закрытие окна не оборвёт удаление
            try:
                self._status("starting", T("Удаляю Prohod…"), T("Выключаю обход и убираю следы в системе"))
                self.stop_flag.set()
                self.bypass.close()
                self.running_name = None
                done = remove_system_traces()
                self.log(T("Удалено: ") + (", ".join(done) or T("системных следов не было")), "ok")
                self._status("off", T("Prohod удалён"), T("Окно закроется само"))
            finally:
                self._uninstall_done.set()
            time.sleep(1.2)
            if self.on_quit:
                self.on_quit()

        self.run_bg(job)

    def folder(self):
        if self.bypass.running:
            self.alert(T("Сначала выключите обход."))
            return

        def job():
            d = pick_folder(T("Папка zapret-discord-youtube (где bin и general.bat)"))
            if not d:
                return
            e = Engine.find(d)
            if not e:
                self.alert(T("Здесь нет bin\\winws.exe и general*.bat. Укажите распакованную папку "
                             "zapret-discord-youtube."))
                return
            if not native_confirm(T("Эту папку Prohod не скачивал и не может проверить её подлинность. "
                                    "Используйте только zapret со страницы "
                                    "github.com/Flowseal.\n\nЗапомнить текущие файлы? Если потом их кто-то "
                                    "изменит, Prohod откажется запускать движок.")):
                return
            self._set_engine(e, e.manifest())

        self.run_bg(job)

    def open_dir(self):
        if self.engine:
            os.startfile(self.engine.root)

    def shutdown(self):
        self.closing = True
        self.stop_flag.set()
        self.bypass.close()  # после этого новый winws уже не запустится, даже из фонового потока
        with self.lock:
            self.changed.notify_all()


# ---------------------------------------------------------------- локальный сервер для окна

def _same(a, b):
    return secrets.compare_digest(a.encode("utf-8", "surrogateescape"), b.encode())


class UiServer(ThreadingHTTPServer):
    """Слушает только 127.0.0.1. Окно входит по одноразовому пропуску из адреса: сервер сразу
    его «сжигает» и выдаёт cookie сессии, которая живёт только в памяти окна. Пропуск, видный
    в командной строке Edge или в его истории, после этого бесполезен."""

    daemon_threads = True
    MAX_CONNECTIONS = 24
    MAX_STREAMS = 2

    def __init__(self, ctl):
        super().__init__(("127.0.0.1", 0), UiHandler)
        self.ctl = ctl
        self.ticket = secrets.token_urlsafe(32)
        self.session = secrets.token_urlsafe(32)
        self.ticket_used = False
        self.host = f"127.0.0.1:{self.server_address[1]}"
        self.lock = threading.Lock()
        self.slots = threading.BoundedSemaphore(self.MAX_CONNECTIONS)
        self.clients = 0
        self.last_seen = time.time()

    @property
    def entry_url(self):
        return f"http://{self.host}/?k={self.ticket}"

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):  # защита от тысяч пустых соединений
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class UiHandler(BaseHTTPRequestHandler):
    server: UiServer
    timeout = 15
    ACTIONS = {"power", "auto", "check", "download", "update", "folder", "open_dir",
               "update_apply", "update_later", "update_skip", "uninstall"}
    CSP = ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
           "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'")

    def log_message(self, *a):
        pass

    def _host_ok(self):
        return self.headers.get("Host") == self.server.host

    def _session_ok(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except CookieError:
            return False
        s = cookie.get("s")
        return bool(s) and _same(s.value, self.server.session)

    def _headers(self, code, ctype, length, extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", self.CSP)
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()

    def _send(self, code, body=b"", ctype="application/json; charset=utf-8", extra=()):
        self._headers(code, ctype, len(body), extra)
        self.wfile.write(body)

    def _deny(self, code=403):
        self._send(code, T("Окно устарело. Закройте его и запустите Prohod заново.").encode(),
                   "text/plain; charset=utf-8")

    def do_GET(self):
        if not self._host_ok():
            return self._deny()
        path, _, query = self.path.partition("?")
        if path == "/" and query.startswith("k="):
            return self._enter(query[2:])
        if not self._session_ok():
            return self._deny()
        if path in UI_FILES:
            name, ctype = UI_FILES[path]
            try:
                return self._send(200, (UI_DIR / name).read_bytes(), ctype)
            except OSError:
                return self._send(500, T("Нет файла ui/{}", name).encode(), "text/plain; charset=utf-8")
        if path == "/api/events":
            return self._events()
        if path == "/api/ping":
            return self._send(200, b"{}")
        if path == "/api/security":
            return self._send(200, json.dumps(self.server.ctl.security_info()).encode())
        self._send(404)

    def _enter(self, ticket):
        srv = self.server
        with srv.lock:
            ok = not srv.ticket_used and _same(ticket, srv.ticket)
            if ok:
                srv.ticket_used = True
        if not ok:
            return self._deny()
        self._send(303, extra=[("Location", "/"),
                               ("Set-Cookie", f"s={srv.session}; HttpOnly; SameSite=Strict; Path=/")])

    def do_POST(self):
        if not (self._host_ok() and self._session_ok() and self.headers.get("X-Prohod") == "1"):
            return self._deny()
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._send(400)
        if not 0 <= n <= 65536:
            return self._send(413)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400)
        if not isinstance(body, dict):
            return self._send(400)
        ctl, action = self.server.ctl, self.path.removeprefix("/api/")
        if action in self.ACTIONS:
            getattr(ctl, action)()
        elif action == "pick":
            ctl.pick(str(body.get("name", "")))
        elif action == "toggle":
            ctl.toggle(str(body.get("key", "")), body.get("value") is True)
        elif action == "pref":
            ctl.pref(str(body.get("key", "")), str(body.get("value", "")))
        elif action == "answer":
            ctl.answer(str(body.get("id", "")), body.get("yes") is True)
        else:
            return self._send(404)
        self._send(200, b"{}")

    def _events(self):
        """Поток состояния (Server-Sent Events). Пока он открыт — окно живо."""
        ctl, srv = self.server.ctl, self.server
        with srv.lock:
            if srv.clients >= srv.MAX_STREAMS:
                return self._send(429)
            srv.clients += 1
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            seen = -1
            while not ctl.closing:
                with ctl.lock:
                    if ctl.version == seen:
                        ctl.changed.wait(2)
                    changed = ctl.version != seen
                if changed:
                    snap = ctl.snapshot()
                    seen = snap["version"]
                    self.wfile.write(f"data: {json.dumps(snap, ensure_ascii=False)}\n\n".encode())
                else:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
                srv.last_seen = time.time()
                time.sleep(0.08)  # не чаще ~12 обновлений в секунду
        except OSError:
            pass
        finally:
            with srv.lock:
                srv.clients -= 1
            srv.last_seen = time.time()


class Bridge:
    """Методы, которые окно вызывает через window.pywebview.api.*. Отвечают только нашей
    странице: если окно каким-то образом перешло на чужую (перетащили файл, ссылку),
    вызовы отклоняются, а окно возвращается к себе."""

    def __init__(self, ctl):
        self._ctl = ctl          # подчёркивание — pywebview не показывает такие поля странице
        self._window = None
        self._home = None        # адрес нашей страницы, запоминается при первой загрузке

    def _ok(self):
        try:
            url = (self._window.get_current_url() or "").split("#")[0]
        except Exception:
            return False
        if self._home is None:
            return False
        if url != self._home:
            self._ctl.log(T("Окно открыло чужую страницу ({}) — вызов отклонён", url[:80]), "err")
            return False
        return True

    def hello(self):
        return self._ctl.snapshot() if self._ok() else None

    def security(self):
        return self._ctl.security_info() if self._ok() else None

    def pick(self, name):
        if self._ok():
            self._ctl.pick(str(name))

    def toggle(self, key, value):
        if self._ok():
            self._ctl.toggle(str(key), value is True)

    def pref(self, key, value):
        if self._ok():
            self._ctl.pref(str(key), str(value))

    def answer(self, did, yes):
        if self._ok():
            self._ctl.answer(str(did), yes is True)


def _bridge_action(name):
    def call(self):
        if self._ok():
            getattr(self._ctl, name)()
    return call


for _name in UiHandler.ACTIONS:
    setattr(Bridge, _name, _bridge_action(_name))


def push_state(ctl, window):
    """Отправляет состояние в окно при каждом изменении (не чаще ~12 раз в секунду)."""
    seen = -1
    while not ctl.closing:
        with ctl.lock:
            if ctl.version == seen:
                ctl.changed.wait(2)
            if ctl.version == seen:
                continue
        snap = ctl.snapshot()
        seen = snap["version"]
        try:
            window.evaluate_js(f"window.__prohod && window.__prohod({json.dumps(snap, ensure_ascii=False)})")
        except Exception:
            pass
        time.sleep(0.08)


def theme_is_dark(theme):
    """Тёмная ли тема окна: выбранная вручную или как у приложений Windows («Авто»)."""
    if theme in ("light", "dark"):
        return theme == "dark"
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


def paint_title_bar(window, theme):
    """Заголовок окна Windows в цвет темы (DWMWA_USE_IMMERSIVE_DARK_MODE)."""
    try:
        hwnd = window.native.Handle.ToInt64()
        val = ctypes.c_int(1 if theme_is_dark(theme) else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 20, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


def free_port():
    import socket
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


SHOW_EVENT = "Local\\ProhodShowWindow"  # второй запуск ярлыком просит первый показать окно

TRAY_STATUS = {"on": "обход работает", "starting": "запуск…", "error": "ошибка", "off": "обход выключен"}


class Tray:
    """Значок в трее (WinForms NotifyIcon в отдельном STA-потоке). Левый клик — открыть окно,
    правый — меню: открыть, включить/выключить обход, выйти. Выход — только отсюда."""

    def __init__(self, ctl, show, quit):
        self.ctl, self.show, self.quit = ctl, show, quit
        self._icon = None
        self._hint_shown = False
        self._want_hint = False
        self.session_ending = False

    def start(self):
        import clr
        clr.AddReference("System.Windows.Forms")
        clr.AddReference("System.Drawing")
        from System.Threading import ApartmentState, Thread, ThreadStart
        t = Thread(ThreadStart(self._run))
        t.SetApartmentState(ApartmentState.STA)
        t.IsBackground = True
        t.Start()

    def hinted_hide(self):
        """Окно спрятали крестиком — один раз подсказать, где теперь Prohod."""
        if not self._hint_shown:
            self._want_hint = True

    def remove(self):
        if self._icon is not None:
            try:
                self._icon.Visible = False
                self._icon.Dispose()
            except Exception:
                pass

    def _run(self):
        from Microsoft.Win32 import SystemEvents
        from System.Drawing import Font, FontStyle, Icon
        from System.Windows.Forms import (Application, ContextMenuStrip, MouseButtons, NotifyIcon, Timer,
                                          ToolStripMenuItem, ToolStripSeparator, ToolTipIcon)
        icon_file = Path(sys.executable) if FROZEN else APP_DIR / "packaging" / "prohod.ico"
        icon = NotifyIcon()
        try:
            icon.Icon = Icon.ExtractAssociatedIcon(str(icon_file)) if FROZEN else Icon(str(icon_file))
        except Exception:
            from System.Drawing import SystemIcons
            icon.Icon = SystemIcons.Application
        icon.Text = APP_TITLE

        menu = ContextMenuStrip()
        open_item = ToolStripMenuItem(T("Открыть {}", APP_TITLE))
        open_item.Font = Font(open_item.Font, FontStyle.Bold)
        power_item = ToolStripMenuItem(T("Включить обход"))
        exit_item = ToolStripMenuItem(T("Выйти"))
        open_item.Click += lambda sender, args: self.show()
        power_item.Click += lambda sender, args: self.ctl.power()
        exit_item.Click += lambda sender, args: self.quit()

        def on_opening(sender, args):
            open_item.Text, exit_item.Text = T("Открыть {}", APP_TITLE), T("Выйти")  # язык мог смениться
            power_item.Text = T("Выключить обход") if self.ctl.bypass.running else T("Включить обход")
            power_item.Enabled = self.ctl.engine is not None and not self.ctl.is_busy

        menu.Opening += on_opening
        for item in (open_item, power_item, ToolStripSeparator(), exit_item):
            menu.Items.Add(item)
        icon.ContextMenuStrip = menu

        def on_click(sender, args):
            if args.Button == MouseButtons.Left:
                self.show()

        icon.MouseClick += on_click

        def on_session_ending(sender, args):
            self.session_ending = True  # выключение/выход из Windows: не мешать, а закрыться

        SystemEvents.SessionEnding += on_session_ending

        def on_tick(sender, args):
            if self.ctl.closing:
                icon.Visible = False
                Application.ExitThread()
                return
            icon.Text = f"{APP_TITLE} — {T(TRAY_STATUS.get(self.ctl.state['power'], ''))}"[:63]
            if self._want_hint:
                self._want_hint, self._hint_shown = False, True
                icon.ShowBalloonTip(4000, APP_TITLE, T("Prohod работает в трее. Выйти — правой кнопкой по "
                                                       "значку → «Выйти»."), ToolTipIcon.Info)

        timer = Timer()
        timer.Interval = 700
        timer.Tick += on_tick
        timer.Start()
        icon.Visible = True
        self._icon = icon
        Application.Run()


def listen_for_show(show):
    """Ждёт сигнала от второго запуска («открыть ярлык ещё раз») и показывает окно."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateEventW.restype = ctypes.c_void_p
    k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    handle = k32.CreateEventW(None, False, False, SHOW_EVENT)
    if not handle:
        return
    while True:
        if k32.WaitForSingleObject(handle, 0xFFFFFFFF) == 0:
            show()


def ask_running_copy_to_show():
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenEventW.restype = ctypes.c_void_p
    k32.OpenEventW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
    k32.SetEvent.argtypes = [ctypes.c_void_p]
    handle = k32.OpenEventW(0x2, False, SHOW_EVENT)  # EVENT_MODIFY_STATE
    if not handle:
        return False
    k32.SetEvent(handle)
    k32.CloseHandle(ctypes.c_void_p(handle))
    return True


def run_native(ctl, webview, hidden=False):
    """Собственное окно программы (WebView2 внутри обычного окна Windows). Крестик прячет окно
    в трей — обход продолжает работать; закрыть программу можно только из меню значка."""
    port = free_port()
    bridge = Bridge(ctl)
    window = webview.create_window(
        APP_TITLE, url=str(UI_DIR / "index.html"), js_api=bridge, width=420, height=800,
        min_size=(380, 640), background_color="#000000" if theme_is_dark(ctl.settings["theme"]) else "#F2F2F7", text_select=False, http_port=port,
        hidden=hidden)
    bridge._window = window
    quitting = threading.Event()

    def show():
        window.show()
        window.restore()
        paint_title_bar(window, ctl.settings["theme"])

    def quit_app():
        quitting.set()
        window.destroy()

    tray = Tray(ctl, show, quit_app)
    ctl.on_theme = lambda: paint_title_bar(window, ctl.settings["theme"])
    ctl.on_quit = quit_app

    def on_closing():
        if quitting.is_set() or ctl.uninstalling or tray.session_ending:
            return True
        threading.Thread(target=window.hide, daemon=True).start()  # спрятать после отмены закрытия
        tray.hinted_hide()
        return False

    window.events.closing += on_closing
    window.events.shown += lambda: paint_title_bar(window, ctl.settings["theme"])

    def on_loaded():
        url = (window.get_current_url() or "").split("#")[0]
        if bridge._home is None and url.endswith("/index.html"):
            bridge._home = url  # первая загрузка — наша страница
        elif bridge._home and url != bridge._home:
            ctl.log(T("Окно попыталось открыть чужую страницу — возвращаю"), "err")
            window.load_url(bridge._home)

    window.events.loaded += on_loaded
    threading.Thread(target=push_state, args=(ctl, window), daemon=True).start()
    threading.Thread(target=listen_for_show, args=(show,), daemon=True).start()
    try:
        tray.start()
    except Exception as e:
        ctl.log(T("Значок в трее не создан: {}", e), "err")
    try:
        # WebView2 запускает свой браузерный процесс БЕЗ прав администратора, поэтому писать в
        # Program Files он не может. Приватный режим: служебные файлы окна — во временной папке
        # пользователя, и pywebview удаляет их при закрытии; окну хранить нечего.
        webview.start(gui="edgechromium", private_mode=True, debug=False, http_port=port)
    finally:
        tray.remove()


def run_browser(ctl):
    """Запасной режим (разработка или нет pywebview): окно — Edge в режиме приложения."""
    srv = UiServer(ctl)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ctl.on_quit = lambda: setattr(ctl, "closing", True)
    how = open_window(srv.entry_url, DATA_DIR / "window")
    if how != "limited":
        ctl.log(T("Окно открыто напрямую, не через планировщик ({})", how), "err")
    # Окно закрыли — соединение пропало дольше чем на 6 секунд (на F5 хватает с запасом).
    started = time.time()
    while not ctl.closing:
        time.sleep(0.5)
        if srv.clients == 0 and time.time() - srv.last_seen > (60 if srv.last_seen <= started else 6):
            break
    srv.shutdown()


def main():
    sanitize_environment()
    apply_lang(load_settings()["lang"])  # системные окна до запуска — уже на нужном языке
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    def fatal(text):
        message(text, error=True)

    if not is_admin():
        if relaunch_as_admin():
            return
        return fatal(T("Без прав администратора обход работать не может: winws.exe ставит драйвер WinDivert."))

    if "--uninstall" in sys.argv:
        return uninstall_from_windows()

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    k32.CreateMutexW(None, False, "Local\\ProhodApp")  # хэндл живёт до конца процесса
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS: Prohod уже работает (может, в трее)
        if not ask_running_copy_to_show():
            message(T("Prohod уже запущен — значок в трее рядом с часами."))
        return

    try:
        secure_data_dir()
    except EngineError as e:
        return fatal(str(e))
    autostart = "--autostart" in sys.argv
    ctl = Controller(autostart=autostart)
    threading.Thread(target=ctl.watchdog, daemon=True).start()
    try:
        import webview
    except ImportError:
        webview = None
    try:
        if webview is None or "--browser" in sys.argv:
            run_browser(ctl)
        else:
            try:
                run_native(ctl, webview, hidden=autostart)  # автозапуск — сразу в трей
            except Exception as e:  # нет WebView2 Runtime — пробуем окно Edge
                ctl.log(T("Окно WebView2 не открылось: {}", e), "err")
                run_browser(ctl)
    except Exception as e:
        fatal(T("Не удалось открыть окно: {}\n\nУстановите «Microsoft Edge WebView2 Runtime» с сайта "
                "Microsoft и запустите Prohod снова.", e))
    finally:
        if ctl.uninstalling:
            ctl._uninstall_done.wait(30)  # окно закрыли посреди удаления — доделать
        ctl.shutdown()
        if ctl.uninstalling:
            schedule_removal()


if __name__ == "__main__":
    main()
