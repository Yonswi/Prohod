r"""
NIXYZ — оболочка для официального движка zapret (winws.exe).

Что делает:
  * скачивает официальный релиз Flowseal/zapret-discord-youtube с GitHub
    и сверяет SHA-256 с контрольной суммой, которую публикует GitHub;
  * читает стратегии из general*.bat и запускает winws.exe напрямую,
    без cmd и без выполнения .bat-файлов;
  * умеет сам перебрать стратегии и выбрать ту, при которой открываются
    YouTube и Discord.

Чего НЕ делает: не шлёт телеметрию. Сам обход не пускает трафик через чужие серверы: winws
меняет пакеты прямо на этом компьютере. Исключение — «Умный обход» (выключен по умолчанию):
соединения с ИИ-сервисами идут через прокси умного DNS (Comss, GeoHide или свой сервер).
В сеть ходит: к GitHub (движок и его обновления); при проверке доступа — к YouTube, Discord,
Cloudflare, ChatGPT, Claude, Grok и сайту, который проверяет пользователь. В режиме «Ускорение» —
к DNS-серверам Cloudflare, Google и Quad9 (замер задержки) и, только по кнопке «Замерить скорость»,
к speed.cloudflare.com, Яндекс Интернетометру (yandex.ru/internet и его серверы *.yandex.net)
и speedtest.selectel.ru.

Собранная программа (NIXYZ.exe) живёт в C:\Program Files\NIXYZ, данные — там же в папке
data: менять их может только администратор. Окно — ui/index.html
+ ui/app.js в собственном окне программы (pywebview / WebView2). Команды идут только через мост
pywebview; его встроенный сервер на 127.0.0.1 отдаёт лишь файлы окна и ничем не управляет.
Режим разработки (запуск .pyw) может показывать окно в Edge.
"""

import ctypes
import hashlib
import io
import ipaddress
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "NIXYZ"
APP_TITLE = "NIXYZ"
APP_VERSION = "2.0.0"
TASK_NAME = "NIXYZ"

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
    "правила «Умного обхода»": "Smart route rules",
    "Умный обход: ИИ идут через умный DNS ({})": "Smart route: AI services go through smart DNS ({})",
    "Свой DNS-сервер не похож на адрес DoH или IP: {}": "Custom DNS server doesn't look like a DoH address or IP: {}",
    "Умный обход выключен": "Smart route off",
    "Умному обходу нужны права администратора": "The smart route needs administrator rights",
    "Свой DNS-сервер не задан — беру встроенный": "No custom DNS server set — using the built-in one",
    "Windows не приняла правило DNS: {}": "Windows rejected the DNS rule: {}",
    "сервис видит страну {} — закрыт для неё, поможет «Умный обход»":
        "the service sees country {} — it's closed there, the smart route will help",
    "открывается, страна для сервиса — {}": "opens, the service sees country {}",
    "не открывается": "doesn't open",
    "Не удалось сохранить список: {}": "Couldn't save the list: {}",
    "Отчёт сохранён в «Загрузки»: {} — имя пользователя, компьютера и адреса в сети скрыты":
        "Report saved to Downloads: {} — user name, computer name and network addresses are hidden",
    "Настройки сохранены в «Загрузки»: {}": "Settings saved to Downloads: {}",
    "Это не файл настроек NIXYZ": "This isn't a NIXYZ settings file",
    "Настройки загружены из файла": "Settings loaded from file",
    "Не удалось снять старые правила DNS: {}": "Couldn't remove old DNS rules: {}",
    "Не удалось вернуть настройки сети: {}": "Couldn't restore the network settings: {}",
    "Не удалось снять правила DNS «Умного обхода»: {}": "Couldn't remove the Smart route DNS rules: {}",
    "Диагностика прервалась: {}": "Diagnostics stopped: {}",
    "Сторож: ошибка {}": "Watchdog: error {}",
    "Сторож: похоже, пропал интернет — подбор не запускаю": "Watchdog: the internet seems to be down — not picking a strategy",
    "Не загружены списки с ошибками: {}": "Lists with errors were not loaded: {}",
    "Настройки загружены, но не все списки: {}": "Settings loaded, but not all lists: {}",
    "Диагностика: {}": "Diagnostics: {}",
    "Сторож: открывается {} из {} — подбираю стратегию заново": "Watchdog: {} of {} open — picking a strategy again",
    "YouTube или Discord перестали открываться — NIXYZ подбирает новую стратегию":
        "YouTube or Discord stopped opening — NIXYZ is picking a new strategy",
    "«{}» хуже прежней ({} против {}) — вернул «{}»": "\"{}\" is worse than the previous one ({} vs {}) — restored \"{}\"",
    "Новая стратегия оказалась хуже — NIXYZ вернул «{}»": "The new strategy was worse — NIXYZ restored \"{}\"",
    "Не удалось сохранить отчёт: {}": "Couldn't save the report: {}",
    "Не удалось сохранить настройки: {}": "Couldn't save the settings: {}",
    "всё в порядке": "all good",
    "Закрыт посторонний обходчик: {}": "Closed another bypass tool: {}",
    "Часы сверены с интернетом": "Clock synced with the internet",
    "Не удалось сверить часы": "Couldn't sync the clock",
    "Список «{}» сохранён": "List \"{}\" saved",
    "Проверка сайта {}: {}": "Site check {}: {}",
    "открывается": "opens",
    "обрывается после {} КБ": "cuts off after {} KB",
    "Не удалось занять адрес {}:53 ({})": "Couldn't take address {}:53 ({})",
    " (обход включён)": " (bypass on)",
    " (обход выключен)": " (bypass off)",
    " Часть сайтов всё ещё недоступна.": " Some sites are still unreachable.",
    ". Запуск заблокирован. Скачайте движок заново или укажите папку повторно.":
        ". Start blocked. Download the engine again or choose the folder again.",
    "GitHub вернул странный номер версии": "GitHub returned an odd version number",
    "GitHub не дал контрольную сумму файла — скачивание отменено":
        "GitHub gave no checksum for the file — download cancelled",
    "NIXYZ будет запускаться при входе в Windows с правами администратора, без запроса.\n\n":
        "NIXYZ will start when you sign in to Windows, with administrator rights and no prompt.\n\n",
    "NIXYZ работает в трее. Выйти — правой кнопкой по значку → «Выйти».":
        "NIXYZ keeps running in the tray. To quit, right-click the icon → Quit.",
    "NIXYZ удалён": "NIXYZ removed",
    "NIXYZ удалён с компьютера.": "NIXYZ has been removed from this computer.",
    "NIXYZ уже запущен — значок в трее рядом с часами.":
        "NIXYZ is already running — look for its icon in the tray next to the clock.",
    "SHA-256 не совпал. Файл подменён или повреждён — он отброшен.":
        "SHA-256 doesn't match. The file was tampered with or damaged — discarded.",
    "SHA-256 совпал, движок установлен": "SHA-256 matches, engine installed",
    "Контрольная сумма версии {} не совпала с записанной в NIXYZ — установка отменена":
        "The checksum of version {} doesn't match the one recorded in NIXYZ — installation cancelled",
    "Версия движка {} вышла после этой сборки NIXYZ, её автор не проверял.\n\n"
    "Контрольная сумма совпадает с данными GitHub. Это защита от порчи файла, но не от взлома "
    "репозитория.\n\nУстановить эту версию?":
        "Engine version {} came out after this NIXYZ build and its author hasn't checked it.\n\n"
        "The checksum matches GitHub's data. That protects against a damaged file, not against a hacked "
        "repository.\n\nInstall this version?",
    "Установка отменена": "Installation cancelled",
    "GitHub временно ограничил запросы. Подождите час и нажмите «Повторить».":
        "GitHub has temporarily limited requests. Wait an hour and press Retry.",
    "Нажмите «Повторить», чтобы скачать движок заново.": "Press Retry to download the engine again.",
    "Не удалось создать файл {}": "Couldn't create the file {}",
    "Сторож движка: ошибка {}": "Engine watcher: error {}",
    "Обход остановился — YouTube и Discord могут не открываться":
        "The bypass stopped — YouTube and Discord may not open",
    "Сторож: перезапускаю обход": "Watcher: restarting the bypass",
    "Умный обход для ИИ при этом продолжает работать": "Smart bypass for AI services keeps working",
    "Запросы к ИИ-сервисам пойдут через этот DNS-сервер:\n\n{}\n\nОн будет видеть, к каким из них вы "
    "обращаетесь, и сможет подставлять адреса. Указывайте только сервер, которому доверяете.\n\nИспользовать его?":
        "Requests to AI services will go through this DNS server:\n\n{}\n\nIt will see which of them you use "
        "and can substitute addresses. Only enter a server you trust.\n\nUse it?",
    "Не всё удалось вернуть: {}. Нажмите «Вернуть» ещё раз, когда сеть будет подключена.":
        "Couldn't restore everything: {}. Press Restore again once the network is connected.",
    "Не удалось вернуть: {}. Проверьте это вручную в параметрах сети Windows.":
        "Couldn't restore: {}. Check this manually in Windows network settings.",
    "TCP timestamps вернутся, когда обход будет выключен": "TCP timestamps will be restored once the bypass is off",
    "Скопировать эту папку в NIXYZ и запускать движок из копии? Копию обычные программы изменить не смогут.":
        "Copy this folder into NIXYZ and run the engine from the copy? Regular programs can't change the copy.",
    "winws.exe закрылся сразу (код {}). Подробности — в журнале.":
        "winws.exe exited right away (code {}). See the log for details.",
    "winws.exe неожиданно завершился (код {})": "winws.exe exited unexpectedly (code {})",
    "{} {} запущен, права администратора: {}": "{} {} started, administrator rights: {}",
    "{} из {}: «{}»": "{} of {}: “{}”",
    "{} — ссылка, а не папка. Переустановите NIXYZ.": "{} is a link, not a folder. Reinstall NIXYZ.",
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
    "Важно: NIXYZ или сам Python лежат там, куда может писать любая программа вашей учётной записи. "
    "Вирус, попавший на компьютер, сможет подменить файлы и получить права администратора при следующем "
    "входе. Надёжнее держать NIXYZ в C:\\Program Files и поставить Python «для всех пользователей».\n\n":
        "Important: NIXYZ or Python itself is in a place any program of your account can write to. "
        "Malware could replace the files and get administrator rights at your next sign-in. It's safer to "
        "keep NIXYZ in C:\\Program Files and install Python “for all users”.\n\n",
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
    "Готово — контрольная сумма совпала": "Done — the checksum matches",
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
    "и запустите NIXYZ снова.":
        "Couldn't open the window: {}\n\nInstall “Microsoft Edge WebView2 Runtime” from the Microsoft "
        "website and start NIXYZ again.",
    "Не удалось получить список изменений: {}": "Couldn't get the list of changes: {}",
    "Недопустимое имя версии": "Invalid version name",
    "Неизвестная переменная %{}% в {}": "Unknown variable %{}% in {}",
    "Неожиданный размер архива": "Unexpected archive size",
    "Нет файла ui/{}": "No file ui/{}",
    "Ни одна стратегия не помогла. Выбор не изменён — попробуйте игровой режим или обновите движок.":
        "No strategy helped. Selection unchanged — try game mode or update the engine.",
    "Ни одна стратегия не улучшила доступ (без обхода {} из {})":
        "No strategy improved access (without the bypass {} of {})",
    "Нужны права администратора. Перезапустите NIXYZ.": "Administrator rights needed. Restart NIXYZ.",
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
    "Окно устарело. Закройте его и запустите NIXYZ заново.": "This window is outdated. Close it and start "
                                                              "NIXYZ again.",
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
    "Удаляю NIXYZ…": "Removing NIXYZ…",
    "Уже запущен другой winws.exe (наверное, zapret открыт вручную через .bat). Два одновременно "
    "не работают.\n\nЗакрыть его?":
        "Another winws.exe is already running (probably zapret started by hand via .bat). Two can't work "
        "at once.\n\nClose it?",
    "Файлы движка изменились после установки: ": "Engine files changed after install: ",
    "Эту папку NIXYZ не скачивал и не может проверить её подлинность. Используйте только zapret со "
    "страницы github.com/Flowseal.\n\n":
        "NIXYZ didn't download this folder and can't verify it. Use only zapret from "
        "github.com/Flowseal.\n\n",
    "автозапуск": "autostart",
    "драйвер {}": "driver {}",
    "запись в «Приложениях»": "the Apps entry",
    "системных следов не было": "there were no system traces",
    "ярлык {}": "shortcut {}",
    # ниже — фразы, которые собираются не одним вызовом
    "да": "yes", "нет": "no", "вкл": "on", "выкл": "off",
    "Нажмите, чтобы включить": "Click to turn on",
    "обход работает": "bypass on", "запуск…": "starting…", "ошибка": "error", "обход выключен": "bypass off",
    "Удалить NIXYZ с компьютера полностью?\n\nБудут выключены обход и автозапуск, удалены драйвер WinDivert, "
    "движок zapret, настройки, ярлыки, запись в «Приложениях» и сама программа.\n\nОтменить это нельзя.":
        "Remove NIXYZ from this computer completely?\n\nThe bypass and autostart will be turned off, and the "
        "WinDivert driver, the zapret engine, settings, shortcuts, the Apps entry and the program itself "
        "will be deleted.\n\nThis can't be undone.",
    "стратегия": "strategy", "стратегии": "strategies", "стратегий": "strategies",
    "Чтобы менять настройки сети, запустите NIXYZ от имени администратора.":
        "Run NIXYZ as administrator to change network settings.",
    "DNS «{}»: как было": "DNS “{}”: restored",
    "DNS «{}»: {}": "DNS “{}”: {}",
    "Не удалось прочитать режим питания Wi-Fi": "Couldn't read the Wi-Fi power mode",
    "Wi-Fi без энергосбережения: {}": "Wi-Fi without power saving: {}",
    "Не удалось изменить режим питания Wi-Fi": "Couldn't change the Wi-Fi power mode",
    "Автонастройка TCP: {}": "TCP auto-tuning: {}",
    "Не удалось изменить автонастройку TCP": "Couldn't change TCP auto-tuning",
    "Wi-Fi: так было ещё до NIXYZ — возвращать нечего": "Wi-Fi: it was like this before NIXYZ — nothing to restore",
    "TCP: так было ещё до NIXYZ — возвращать нечего": "TCP: it was like this before NIXYZ — nothing to restore",
    "Ускорение: замеряю DNS-серверы…": "Boost: measuring DNS servers…",
    "DNS уже самый быстрый из доступных": "DNS is already the fastest available",
    "Ускорение включено": "Boost is on",
    "Сеть возвращена как было": "Network settings restored",
    "Замер скорости: {}…": "Speed test: {}…",
    "{}: {} Мбит/с, задержка {} мс": "{}: {} Mbit/s, latency {} ms",
    "{}: не удалось ({})": "{}: failed ({})",
    "Ни один сервер замера не ответил": "None of the speed test servers answered",
    "Общая скорость {} Мбит/с, задержка {} мс": "Overall speed {} Mbit/s, latency {} ms",
    "Яндекс не дал адрес для замера": "Yandex didn't return a test address",
    "Яндекс": "Yandex",
    "Кэш DNS очищен": "DNS cache cleared",
    "Не удалось очистить кэш DNS": "Couldn't clear the DNS cache",
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

FROZEN = bool(getattr(sys, "frozen", False))  # собранная программа NIXYZ.exe
APP_DIR = Path(sys.executable if FROZEN else __file__).resolve().parent
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
# Данные собранной программы — в C:\Program Files\NIXYZ\data: туда без прав администратора
# нельзя ни записать, ни заранее подложить папку или ссылку (в отличие от ProgramData).
DATA_DIR = APP_DIR / "data"
ENGINE_DIR = DATA_DIR / "engine" if FROZEN else APP_DIR / "engine"
SETTINGS_FILE = DATA_DIR / "settings.json"

REPO = "Flowseal/zapret-discord-youtube"
RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/"
# Версия движка, которую проверил автор этой сборки NIXYZ. Сумма зашита в программу, поэтому первая
# установка не зависит от того, что ответит сеть. Обновления новее неё ставятся только после вопроса.
TRUSTED_ENGINE = ("1.10.4", "291af673bd0238506f9548e0e94ca0abf244000f4c9a06960544fb01c5f97b34")
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
    # «bulk:» — скачать до 64 КБ: блокировка «по 16 КБ» обрывает соединение именно на этом
    "Cloudflare": [
        "https://www.cloudflare.com",
        "bulk:https://speed.cloudflare.com/__down?bytes=65536",
        "bulk:https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js",
    ],
}
AUTO_TARGETS = ("YouTube", "Discord")  # подбор стратегии смотрит только на то, что чинит zapret
# ИИ-сервисы работают не во всех странах: важно не «открывается ли», а какой страной нас видят.
# /cdn-cgi/trace — служебная страница Cloudflare перед сайтом, в ней loc=страна.
AI_TRACE = {"ChatGPT": "https://chatgpt.com/cdn-cgi/trace", "Claude": "https://claude.ai/cdn-cgi/trace",
            "Grok": "https://grok.com/cdn-cgi/trace"}
AI_GEO_BLOCKED = {"RU", "BY", "IR", "KP", "SY", "CU", "CN", "HK"}
PILLS = (*TARGETS, *AI_TRACE)

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


SAFE_ENV = {"TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "USERNAME", "USERDOMAIN", "COMPUTERNAME",
            "HOMEDRIVE", "HOMEPATH", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432",
            "COMMONPROGRAMFILES", "COMMONPROGRAMFILES(X86)", "COMMONPROGRAMW6432", "PUBLIC", "ALLUSERSPROFILE",
            "SYSTEMDRIVE", "OS", "PATHEXT", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
            "PROCESSOR_IDENTIFIER", "PROCESSOR_LEVEL", "PROCESSOR_REVISION", "SESSIONNAME", "LOGONSERVER"}


def sanitize_environment():
    """Оставляет только безобидные переменные окружения. Любая программа пользователя может записать
    свои в раздел реестра HKCU Environment, а NIXYZ работает как администратор: PYTHONNET_* и COR_*
    загрузили бы чужую DLL, SSL_CERT_FILE подменил бы корневые сертификаты, WEBVIEW2_* — браузер окна."""
    for key in list(os.environ):
        if key.upper() not in SAFE_ENV:
            del os.environ[key]
    win = os.path.dirname(SYSTEM_DIR)
    powershell = os.path.join(SYSTEM_DIR, "WindowsPowerShell", "v1.0")
    os.environ.update(SystemRoot=win, windir=win, ComSpec=os.path.join(SYSTEM_DIR, "cmd.exe"),
                      PATH=";".join((SYSTEM_DIR, win, os.path.join(SYSTEM_DIR, "Wbem"), powershell)),
                      PSModulePath=os.path.join(powershell, "Modules"))


def gui_python():
    exe = Path(sys.executable)
    if FROZEN:
        return str(exe)
    w = exe.with_name("pythonw.exe")
    return str(w if w.is_file() else exe)


def self_args(*extra):
    """Аргументы для запуска этой же программы: у NIXYZ.exe — только флаги,
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


def tcp_timestamps():
    """Значение TCP timestamps: "enabled", "disabled" или "", если прочитать не вышло."""
    code, out = run_quiet(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                           "(Get-NetTCPSetting -SettingName Internet).Timestamps"])
    value = out.strip().lower()
    return value if code == 0 and value in ("enabled", "disabled") else ""


def restore_tcp_timestamps(before):
    if before == "disabled":
        run_quiet(["netsh", "interface", "tcp", "set", "global", "timestamps=disabled"])


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
            "engine_hashes": {}, "net_backup": {}, "net_speed": {},
            "smart": False, "smart_told": False, "smart_dns": "builtin",
            "ts_backup": "",   # какими были TCP timestamps до NIXYZ, если он их менял: вернуть при удалении
            "smart_doh": "", "buddy": True, "watch": False, "nightly": False, "rollback": False, "notify": True}
THEMES = ("auto", "light", "dark")
SMART_DNS = ("builtin", "custom")
# переключатели, которые просто запоминаются (их действие — в других частях программы)
PLAIN_TOGGLES = ("buddy", "watch", "nightly", "rollback", "notify")


def load_settings():
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8-sig"))  # BOM оставляют некоторые редакторы
    except (OSError, ValueError, RecursionError):
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
    for attempt in range(5):
        try:
            text = json.dumps(s, ensure_ascii=False, indent=2)
            break
        except RuntimeError:  # другой поток как раз правит net_backup
            if attempt == 4:
                raise
            time.sleep(0.02)
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(SETTINGS_FILE)


# ---------------------------------------------------------------- движок

def forbidden_option(opt):
    """Параметры winws, которые пишут файлы. getopt_long понимает сокращения (--deb == --debug),
    поэтому запрещаем и их."""
    if opt.startswith(("debug", "hostlist-a", "wf-save")):
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
        for key, name in USER_LISTS.items():
            f = self.lists / name
            if not f.exists():
                f.write_text(LIST_STUBS[key], encoding="utf-8")

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
        if not self.bin.is_dir():
            return []  # пропавшая папка — это пропавшие файлы, их заметит verify_binaries
        return [p for p in self.bin.iterdir() if p.suffix.lower() in (".exe", ".dll", ".sys")]

    def manifest(self):
        """{относительный путь: sha256} для исполняемых файлов и всех стратегий."""
        files = self._binaries() + [b for _, b in self.strategies()]
        return {str(p.relative_to(self.root)): sha256_file(p) for p in files}

    def verify_binaries(self, manifest):
        """Сверяет .exe/.dll/.sys с хэшами, записанными при установке. Возвращает изменённые и пропавшие:
        вместо пропавшей DLL Windows стала бы искать одноимённую в других папках."""
        changed = [str(p.relative_to(self.root)) for p in self._binaries()
                   if manifest.get(str(p.relative_to(self.root))) != sha256_file(p)]
        missing = [k for k in manifest if k.lower().startswith("bin" + os.sep) and not (self.root / k).is_file()]
        return sorted({*changed, *missing})

    def read_verified_bat(self, manifest, bat):
        """Читает .bat один раз и сверяет именно прочитанные байты — подменить файл между
        проверкой и разбором нельзя."""
        data = Path(bat).read_bytes()
        if manifest.get(str(Path(bat).relative_to(self.root))) != hashlib.sha256(data).hexdigest():
            raise TamperError(T("Стратегия {} изменена после установки или добавлена позже", Path(bat).name))
        return data.decode("utf-8", errors="replace")


# Job Object: winws.exe завершится вместе с NIXYZ, даже если окно убьют или оно упадёт
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
            p = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
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

_opener = None


def _direct_opener():
    """Запросы идут напрямую, мимо системного прокси: иначе проверка врёт, а чужая программа могла бы
    прописать пользователю свой прокси. Один на всех: загрузка сертификатов Windows не бесплатна."""
    global _opener
    if _opener is None:
        ctx = ssl.create_default_context()
        _opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                              urllib.request.HTTPSHandler(context=ctx))
    return _opener


def probe(target, timeout=6):
    """Проверка одного адреса из TARGETS: https-адрес или «bulk:» адрес."""
    if target.startswith("bulk:"):
        return probe_bulk(target[5:], timeout + 2)
    req = urllib.request.Request(target, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with _direct_opener().open(req, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True  # сервер ответил — соединение прошло
    except Exception:
        return False


def probe_bulk(url, timeout=8):
    """True, если удалось скачать 64 КБ (или весь файл, если он меньше)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with _direct_opener().open(req, timeout=timeout) as r:
            got = 0
            while got < 65536:
                chunk = r.read(16384)
                if not chunk:
                    return True
                got += len(chunk)
            return True
    except Exception:
        return False


def check_targets(names=TARGETS):
    """{сервис: [(адрес, ok)]} для сервисов из names."""
    urls = [(svc, u) for svc in names for u in TARGETS[svc]]
    with ThreadPoolExecutor(len(urls)) as pool:
        oks = list(pool.map(lambda x: probe(x[1]), urls))
    result = {svc: [] for svc in names}
    for (svc, u), ok in zip(urls, oks):
        result[svc].append((u, ok))
    return result


def cf_trace(url, timeout=6):
    """Страна, которой нас видит сервис за Cloudflare (loc=…): "RU", "" — открылся без страны, None — не открылся."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with _direct_opener().open(req, timeout=timeout) as r:
            text = r.read(4096).decode("ascii", "replace")
    except urllib.error.HTTPError as e:  # ответил — значит открылся; страна, если есть, в теле
        text = e.read(4096).decode("ascii", "replace")
    except Exception:
        return None
    m = re.search(r"^loc=([A-Z]{2})$", text, re.M)
    return m.group(1) if m else ""


def check_ai():
    """{сервис: (тон, страна)}: ok — открывается, geo — сервис видит закрытую для него страну, bad — не открылся."""
    def one(item):
        svc, url = item
        loc = cf_trace(url)
        if loc is None:
            return svc, ("bad", "")
        return svc, ("geo" if loc in AI_GEO_BLOCKED else "ok", loc)

    with ThreadPoolExecutor(len(AI_TRACE)) as pool:
        return dict(pool.map(one, AI_TRACE.items()))


def score(res):
    return sum(ok for items in res.values() for _, ok in items)


# ---------------------------------------------------------------- ускорение интернета
# Только встроенные средства Windows, и всё обратимо: перед изменением NIXYZ запоминает
# в net_backup, как было, а «Вернуть как было» и удаление программы ставят это обратно.

DNS_PROVIDERS = {
    "cloudflare": ("Cloudflare", ("1.1.1.1", "1.0.0.1")),
    "google": ("Google", ("8.8.8.8", "8.8.4.4")),
    "quad9": ("Quad9", ("9.9.9.9", "149.112.112.112")),
}
# подгруппа «Параметры адаптера беспроводной сети» и её «Режим энергосбережения» (0 — макс. производительность)
WIFI_POWER = ("19cbb8fa-5279-450e-9fac-8a3d5fedd0c1", "12bbebe6-58d6-4636-95bb-3217ef867c1a")
TCP_LEVELS = ("disabled", "highlyrestricted", "restricted", "normal", "experimental")
TCPIP_IFACES = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
SPEED_BYTES = 25_000_000   # с каждого источника скачивается не больше 25 МБ и не дольше 15 с
SPEED_SOURCES = ("cloudflare", "yandex", "selectel")
YANDEX_PROBES = "https://yandex.ru/internet/api/v0/get-probes"
SPEED_NAMES = {"cloudflare": "Cloudflare", "yandex": "Яндекс", "selectel": "Selectel"}  # в журнал — через T()


def dns_rtt(server, timeout=1.5):
    """Медианное время ответа DNS-сервера в мс (три запроса типа A) или None, если не отвечает."""
    times = []
    for name in ("www.youtube.com", "discord.com", "www.google.com"):
        qid = secrets.randbits(16)
        pkt = (struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0)
               + b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0"
               + struct.pack(">HH", 1, 1))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            try:
                t0 = time.perf_counter()
                sock.sendto(pkt, (server, 53))
                while True:  # чужие и запоздавшие ответы пропускаем
                    data, addr = sock.recvfrom(512)
                    if addr[0] == server and data[:2] == struct.pack(">H", qid):
                        break
                times.append((time.perf_counter() - t0) * 1000)
            except OSError:
                pass
    return round(sorted(times)[len(times) // 2]) if times else None


def _reg_ips(key, name):
    import winreg
    try:
        v = winreg.QueryValueEx(key, name)[0]
    except OSError:
        return []
    out = []
    for x in re.split(r"[ ,]+", str(v).strip()):
        try:
            out.append(str(ipaddress.IPv4Address(x)))
        except ValueError:
            pass
    return out


def net_adapters():
    """Физические сетевые адаптеры: [{guid, index, name, up, wifi, static, dhcp}].
    static — DNS, вписанные вручную (пусто — берутся от роутера), dhcp — выданные роутером."""
    import winreg
    script = ("Get-NetAdapter -Physical | Select-Object InterfaceGuid, ifIndex, Name, Status, "
              "NdisPhysicalMedium | ConvertTo-Json -Compress")
    code, out = run_quiet(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])
    try:
        items = json.loads(out) if code == 0 and out.strip() else []
    except ValueError:
        items = []
    result = []
    for a in items if isinstance(items, list) else [items]:
        guid = str(a.get("InterfaceGuid") or "")
        if not re.fullmatch(r"\{[0-9A-Fa-f-]{36}\}", guid):
            continue
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, TCPIP_IFACES + "\\" + guid) as k:
                static, dhcp = _reg_ips(k, "NameServer"), _reg_ips(k, "DhcpNameServer")
        except OSError:
            static, dhcp = [], []
        result.append({"guid": guid.upper(), "index": int(a.get("ifIndex") or 0), "name": str(a.get("Name") or ""),
                       "up": str(a.get("Status")) == "Up", "wifi": a.get("NdisPhysicalMedium") in (1, 9),
                       "static": static, "dhcp": dhcp})
    return result


def set_dns(index, servers):
    """Вписывает адаптеру DNS-серверы; servers=None — снова брать их от роутера."""
    env = dict(os.environ, NIXYZ_IF=str(int(index)),
               NIXYZ_DNS=",".join(str(ipaddress.IPv4Address(x)) for x in servers or ()))
    script = ("$ErrorActionPreference = 'Stop'; $i = [int]$env:NIXYZ_IF; "
              "if ($env:NIXYZ_DNS) { Set-DnsClientServerAddress -InterfaceIndex $i "
              "-ServerAddresses ($env:NIXYZ_DNS -split ',') } "
              "else { Set-DnsClientServerAddress -InterfaceIndex $i -ResetServerAddresses }")
    return run_quiet(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env=env)


def wifi_power():
    """[от сети, от батареи] — режим энергосбережения Wi-Fi в текущей схеме питания, или None."""
    code, out = run_quiet(["powercfg", "/q", "SCHEME_CURRENT", *WIFI_POWER])
    vals = re.findall(r":\s*0x([0-9a-fA-F]{8})\s*$", out, re.M)
    return [int(v, 16) for v in vals[-2:]] if code == 0 and len(vals) >= 2 else None


def set_wifi_power(ac, dc):
    ok = all(run_quiet(["powercfg", flag, "SCHEME_CURRENT", *WIFI_POWER, str(int(v))])[0] == 0
             for flag, v in (("/setacvalueindex", ac), ("/setdcvalueindex", dc)))
    run_quiet(["powercfg", "/setactive", "SCHEME_CURRENT"])
    return ok


def tcp_autotuning():
    """Уровень автонастройки окна TCP: "normal" и т. п., или None, если прочитать не вышло."""
    code, out = run_quiet(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                           "(Get-NetTCPSetting -SettingName Internet).AutoTuningLevelLocal"])
    level = out.strip().lower()
    return level if code == 0 and level in TCP_LEVELS else None


def set_tcp_autotuning(level):
    if level not in TCP_LEVELS:
        return False
    return run_quiet(["netsh", "interface", "tcp", "set", "global", "autotuninglevel=" + level])[0] == 0


def flush_dns():
    return run_quiet(["ipconfig", "/flushdns"])[0] == 0


def speed_url(src):
    """Адрес файла для замера. Яндекс Интернетометр каждый раз выдаёт ближайший свой сервер —
    берём его, только если это https-адрес на *.yandex.net."""
    if src == "cloudflare":
        return "https://speed.cloudflare.com/__down?bytes=" + str(SPEED_BYTES)
    if src == "selectel":
        return "https://speedtest.selectel.ru/100MB"
    req = urllib.request.Request(YANDEX_PROBES, headers={"User-Agent": "Mozilla/5.0"})
    with _direct_opener().open(req, timeout=8) as r:
        data = json.loads(r.read(256 * 1024))
    for probe in data["download"]["probes"]:
        url = str(probe.get("url", ""))
        host = urllib.parse.urlsplit(url).hostname or ""
        if url.startswith("https://") and host.endswith(".yandex.net") and "/probes/50mb" in url:
            return url
    raise EngineError(T("Яндекс не дал адрес для замера"))


def speed_test(src, progress):
    """Задержка до сервера источника (лучшая из четырёх) и скорость скачивания до 25 МБ в Мбит/с."""
    url = speed_url(src)
    ip = socket.gethostbyname(urllib.parse.urlsplit(url).hostname)
    pings = []
    for _ in range(4):
        t0 = time.perf_counter()
        with socket.create_connection((ip, 443), timeout=4):
            pings.append((time.perf_counter() - t0) * 1000)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    got, t0 = 0, time.perf_counter()
    with _direct_opener().open(req, timeout=10) as r:
        while got < SPEED_BYTES and time.perf_counter() - t0 < 15:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            got += len(chunk)
            progress(got / SPEED_BYTES, got * 8 / max(time.perf_counter() - t0, 0.001) / 1e6)
    secs = max(time.perf_counter() - t0, 0.001)
    return {"ping": round(min(pings)), "down": round(got * 8 / secs / 1e6, 1)}


# ---------------------------------------------------------------- «Умный обход» для ИИ
# ИИ-сервисы сами ограничивают доступ по странам, zapret тут не поможет. «Умный DNS» (Comss, запасной —
# GeoHide) отвечает на имена ИИ адресами своих прокси; те пропускают трафик дальше без расшифровки,
# сертификаты остаются настоящими. Правило Windows NRPT шлёт запросы ТОЛЬКО для доменов ИИ на
# маленький DNS-сервер NIXYZ (127.78.73.90:53), а он пересылает их по HTTPS (DoH). Остальные имена
# этот сервер не видит и не обслуживает. Правила помечены комментарием NIXYZ: они снимаются при
# выключении, выходе и удалении, а на старте подчищаются, если программа однажды упала.

SMART_IP = "127.78.73.90"
SMART_DOH = ("https://dns.comss.one/dns-query", "https://geohide.ru/dns-query")
# только то, что умный DNS реально перенаправляет (проверено запросами к Comss)
AI_DOMAINS = ("chatgpt.com", "openai.com", "oaistatic.com", "oaiusercontent.com", "sora.com",
              "claude.ai", "anthropic.com", "claudeusercontent.com", "grok.com",
              "deepl.com", "elevenlabs.io", "openrouter.ai", "cursor.com")
HOST_RE = re.compile(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})")
NRPT_CLEAR = ("Get-DnsClientNrptRule | Where-Object { $_.Comment -eq 'NIXYZ' } | "
              "ForEach-Object { Remove-DnsClientNrptRule -Name $_.Name -Force }; ")


def doh_target(value):
    """Свой сервер: IP — обычный DNS ("ip", адрес), имя или https-адрес — DoH ("doh", url); иначе None."""
    v = value.strip().lower()
    try:
        return ("ip", str(ipaddress.ip_address(v)))
    except ValueError:
        pass
    if not v.startswith("https://"):
        return ("doh", f"https://{v}/dns-query") if HOST_RE.fullmatch(v) else None
    try:
        u = urllib.parse.urlsplit(v)
        if u.port not in (None, 443) or u.username or not HOST_RE.fullmatch(u.hostname or "") or \
                not re.fullmatch(r"(/[A-Za-z0-9._~-]+)*/?", u.path) or "/../" in u.path + "/":
            return None
    except ValueError:
        return None
    return ("doh", urllib.parse.urlunsplit(("https", u.hostname, u.path or "/dns-query", "", "")))


def dns_question(msg):
    """(имя, конец раздела вопроса) из DNS-запроса с одним вопросом, или (None, 0)."""
    if len(msg) < 17 or struct.unpack(">H", msg[4:6])[0] != 1:
        return None, 0
    labels, i = [], 12
    while i < len(msg):
        n = msg[i]
        if n == 0:
            end = i + 5
            return (".".join(labels).lower(), end) if end <= len(msg) else (None, 0)
        if n > 63 or i + 1 + n > len(msg):
            return None, 0
        labels.append(msg[i + 1:i + 1 + n].decode("ascii", "replace"))
        i += 1 + n
    return None, 0


def ai_name(name):
    return any(name == d or name.endswith("." + d) for d in AI_DOMAINS)


def dns_reply(query, end, rcode=0, tc=False):
    """Пустой ответ на запрос: тот же id и вопрос, флаги «ответ», код ошибки или «обрезано»."""
    flags = 0x8080 | (query[2] & 0x01) << 8 | (0x0200 if tc else 0) | rcode
    return query[:2] + struct.pack(">HHHHH", flags, 1, 0, 0, 0) + query[12:end]


def recv_exact(conn, n):
    """Ровно n байт из соединения или b"", если оно закрылось раньше."""
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return b""
        buf += chunk
    return buf


def nrpt_set(servers):
    """Правило NRPT: имена ИИ (и их поддомены) → servers. Прежние правила NIXYZ снимаются."""
    names = ",".join(n for d in AI_DOMAINS for n in (d, "." + d))
    env = dict(os.environ, NIXYZ_NAMES=names, NIXYZ_NS=",".join(str(ipaddress.ip_address(x)) for x in servers))
    script = ("$ErrorActionPreference = 'Stop'; " + NRPT_CLEAR +
              "Add-DnsClientNrptRule -Namespace ($env:NIXYZ_NAMES -split ',') -NameServers ($env:NIXYZ_NS -split ',') "
              "-Comment 'NIXYZ' -DisplayName 'NIXYZ' | Out-Null; Clear-DnsClientCache")
    return run_quiet(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env=env)


def nrpt_clear():
    return run_quiet(["powershell", "-NoProfile", "-NonInteractive", "-Command", NRPT_CLEAR + "Clear-DnsClientCache"])


class SmartDns:
    """DNS-сервер на 127.78.73.90:53 только для имён ИИ: каждый запрос уходит по HTTPS (DoH)
    к умному DNS, по очереди к адресам из urls. На чужие имена отвечает «отказано»."""

    def __init__(self, urls):
        self.urls = list(urls)
        self.socks = []
        self.pool = ThreadPoolExecutor(8)
        self.opener = _direct_opener()  # один контекст TLS на все запросы, а не новый на каждый

    def start(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socks = [udp, tcp]
        try:
            udp.bind((SMART_IP, 53))
            tcp.bind((SMART_IP, 53))
            tcp.listen(16)
        except OSError:
            self.close()
            raise
        threading.Thread(target=self._udp_loop, args=(udp,), daemon=True).start()
        threading.Thread(target=self._tcp_loop, args=(tcp,), daemon=True).start()

    def close(self):
        for s in self.socks:
            try:
                s.close()
            except OSError:
                pass
        self.socks = []
        self.pool.shutdown(wait=False, cancel_futures=True)

    def resolve(self, query):
        name, end = dns_question(query)
        if not name:
            return None
        if not ai_name(name):
            return dns_reply(query, end, rcode=5)  # REFUSED
        ask = b"\0\0" + query[2:]  # DoH советует id = 0
        for url in self.urls:
            req = urllib.request.Request(url, data=ask, method="POST", headers={
                "Content-Type": "application/dns-message", "Accept": "application/dns-message",
                "User-Agent": "Mozilla/5.0"})
            try:
                with self.opener.open(req, timeout=3) as r:
                    body = r.read(65535)
            except Exception:
                continue
            if len(body) >= 12 and body[2] & 0x80:
                return query[:2] + body[2:]
        return dns_reply(query, end, rcode=2)  # SERVFAIL

    def _udp_loop(self, udp):
        while True:
            try:
                query, addr = udp.recvfrom(4096)
                self.pool.submit(self._udp_answer, udp, query, addr)
            except ConnectionResetError:  # клиент ушёл, не дождавшись ответа (ICMP «порт закрыт»)
                continue
            except (OSError, RuntimeError):  # сокет закрыт или пул остановлен — сервер выключен
                return

    def _udp_answer(self, udp, query, addr):
        resp = self.resolve(query)
        if resp is None:
            return
        if len(resp) > 512 and struct.unpack(">H", query[10:12])[0] == 0:  # без EDNS — не больше 512 байт
            resp = dns_reply(query, dns_question(query)[1], tc=True)
        try:
            udp.sendto(resp, addr)
        except OSError:
            pass

    def _tcp_loop(self, tcp):
        while True:
            try:
                conn, _ = tcp.accept()
            except OSError:
                return
            try:
                self.pool.submit(self._tcp_answer, conn)
            except RuntimeError:
                conn.close()
                return

    def _tcp_answer(self, conn):
        with conn:
            conn.settimeout(10)
            try:
                while True:
                    head = recv_exact(conn, 2)
                    query = head and recv_exact(conn, struct.unpack(">H", head)[0])
                    if not query:
                        return
                    resp = self.resolve(query)
                    if resp is None:
                        return
                    conn.sendall(struct.pack(">H", len(resp)) + resp)
            except OSError:
                return


# ---------------------------------------------------------------- диагностика, отчёт
OTHER_DPI = ("goodbyedpi.exe", "ciadpi.exe", "byedpi.exe", "spoofdpi.exe", "dpi-tunnel.exe")
DIAG_CHECKS = ("engine", "admin", "dpi", "dns", "time", "strategy")
PUBLIC_DNS = {"1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9", "149.112.112.112", "77.88.8.8", "77.88.8.1",
              "127.78.73.90"}  # общеизвестные DNS и служебный адрес NIXYZ — в отчёте нужны


def other_dpi():
    """Запущенные посторонние обходчики (по имени процесса)."""
    code, out = run_quiet(["tasklist", "/FO", "CSV", "/NH"])
    found = {line.split('","')[0].strip('"').lower() for line in out.splitlines()} if code == 0 else set()
    return sorted(found & set(OTHER_DPI))


def clock_skew():
    """На сколько секунд часы Windows расходятся со временем сервера Cloudflare, или None."""
    from email.utils import parsedate_to_datetime
    req = urllib.request.Request("https://www.cloudflare.com", method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with _direct_opener().open(req, timeout=6) as r:
            date = r.headers.get("Date")
    except urllib.error.HTTPError as e:
        date = e.headers.get("Date")
    except Exception:
        return None
    try:
        return abs(time.time() - parsedate_to_datetime(date).timestamp())
    except (TypeError, ValueError):
        return None


def dns_spoofed():
    """True, если системный DNS отдаёт для YouTube заглушку (0.0.0.0, 127.x, частный адрес),
    None, если адрес узнать не удалось: без интернета это не подмена."""
    try:
        infos = socket.getaddrinfo("www.youtube.com", 443, type=socket.SOCK_STREAM)
    except OSError:
        return None
    ips = {ipaddress.ip_address(i[4][0]) for i in infos}
    return not ips or any(ip.is_private or ip.is_loopback or ip.is_unspecified for ip in ips)


def downloads_dir():
    """Папка «Загрузки» (может быть перенесена пользователем), иначе — домашняя."""
    guid = ctypes.c_char_p(uuid_bytes("374DE290-123F-4565-9164-39C4925E467B"))
    path = ctypes.c_wchar_p()
    try:
        ok = ctypes.windll.shell32.SHGetKnownFolderPath(guid, 0, None, ctypes.byref(path)) == 0
        p = Path(path.value) if ok and path.value else None
        ctypes.windll.ole32.CoTaskMemFree(path)
        if p and p.is_dir():
            return p
    except (OSError, AttributeError):
        pass
    p = Path.home() / "Downloads"
    return p if p.is_dir() else Path.home()


def write_new_file(path, text):
    """Создаёт новый файл и возвращает его путь. Существующий файл или подложенную ссылку не трогает:
    администратор пишет в папку, куда может заранее положить что угодно обычная программа."""
    path = Path(path)
    for i in range(100):
        target = path.with_name(f"{path.stem}-{i}{path.suffix}") if i else path
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        return target
    raise OSError(T("Не удалось создать файл {}", path.name))


def platform_name():
    import platform
    return platform.platform()


def uuid_bytes(text):
    import uuid
    return uuid.UUID(text).bytes_le


def reveal(path):
    """Показать файл в Проводнике."""
    try:
        subprocess.Popen([os.path.join(os.path.dirname(SYSTEM_DIR), "explorer.exe"),
                          "/select,", str(path)], creationflags=NO_WINDOW)
    except OSError:
        pass


def scrub(text):
    """Убирает из текста личное: имя пользователя и компьютера, папку профиля, адреса в сети
    (кроме общеизвестных DNS) — для отчёта в поддержку."""
    for var, mark in (("USERPROFILE", "%USERPROFILE%"), ("USERNAME", "<user>"), ("COMPUTERNAME", "<pc>")):
        val = os.environ.get(var)
        if val and len(val) > 1:
            text = re.sub(re.escape(val), mark, text, flags=re.I)
    text = re.sub(r"(?<![\w:])(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(?:%\w+)?(?![\w:])",
                  lambda m: m.group(0) if m.group(0).count(":") < 3 and "::" not in m.group(0) else "x:x::x", text)
    return re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", lambda m: m.group(0) if m.group(0) in PUBLIC_DNS else "x.x.x.x", text)


# «Умного обхода» и своего DNS здесь нет: присланный «на форуме» файл не должен
# без спроса направить запросы ИИ на чужой сервер
EXPORT_KEYS = ("strategy", "game_filter", "start_on_open", "lang", "theme",
               "buddy", "watch", "nightly", "rollback", "notify")


# ---------------------------------------------------------------- свои списки и проверка сайта
# Файлы *-user.txt в папке lists движка: service.bat и NIXYZ подмешивают их к встроенным спискам.
# Пустыми их оставлять нельзя (winws не любит пустые файлы) — тогда пишется безвредная заглушка,
# а в окне заглушка не показывается.

USER_LISTS = {"general": "list-general-user.txt", "exclude": "list-exclude-user.txt",
              "ipexclude": "ipset-exclude-user.txt"}
LIST_STUBS = {"general": "# Never leave this file empty\ndomain.example.abc\n",
              "exclude": "domain.example.abc\n", "ipexclude": "203.0.113.113/32\n"}
STUB_LINES = {"domain.example.abc", "203.0.113.113/32", "# Never leave this file empty"}
LIST_MAX = 256 * 1024


def read_user_list(engine, name):
    try:
        text = (engine.lists / USER_LISTS[name]).read_text(encoding="utf-8", errors="replace")[:LIST_MAX]
    except OSError:
        return ""
    return "\n".join(l for l in text.splitlines() if l.strip() not in STUB_LINES).strip()


def list_errors(name, text):
    """Номера строк, которые не похожи на домен (или IP/подсеть для ipexclude). Комментарии # — можно."""
    bad = []
    for i, line in enumerate(text.splitlines(), 1):
        v = line.strip().lower()
        if not v or v.startswith("#"):
            continue
        if name == "ipexclude":
            try:
                ipaddress.ip_network(v, strict=False)
                continue
            except ValueError:
                pass
        elif HOST_RE.fullmatch(list_host(v)):
            continue
        bad.append(i)
    return bad


def list_host(line):
    """Строка списка → домен как в запросе: без «*.», кириллица — в punycode (сайт.рф → xn--80aswg.xn--p1ai)."""
    v = line.strip()
    if v.startswith("#"):
        return v
    v = v.lower()
    v = re.sub(r"^[a-z]+://", "", v).split("/")[0].removeprefix("*.")  # вставили ссылку целиком — берём домен
    if v.isascii():
        return v
    try:
        return v.encode("idna").decode("ascii")
    except UnicodeError:
        return v


def write_user_list(engine, name, text):
    lines = [l.strip().lower() if name == "ipexclude" else list_host(l) for l in text.splitlines()]
    body = "\n".join(l for l in lines if l) + "\n"
    if not any(l and not l.startswith("#") for l in lines):
        body = LIST_STUBS[name]
    f = engine.lists / USER_LISTS[name]
    tmp = f.with_suffix(".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(f)


def probe_site(domain, timeout=8):
    """Диагноз одного сайта: (тон, ключ вердикта, КБ). ok — открылся; cut — оборвался посреди
    ответа (так выглядит блокировка «по 16 КБ»); bad — не находит адрес, сброс или молчание."""
    try:
        socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM)
    except OSError:
        return "bad", "lists.nodns", 0
    req = urllib.request.Request(f"https://{domain}/", headers={"User-Agent": "Mozilla/5.0"})
    got = 0
    try:
        try:
            r = _direct_opener().open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            r = e  # сервер ответил ошибкой — соединение прошло, тело тоже читаем
        with r:
            while got < 65536:
                chunk = r.read(8192)
                if not chunk:
                    break
                got += len(chunk)
    except ssl.SSLCertVerificationError:
        # сервер ответил, но сертификат проверить не вышло: Python не догружает промежуточные
        # сертификаты, как Windows, — а бывает и заглушка провайдера. Честно говорим как есть
        return "warn", "lists.ok_answer", 0
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            return "warn", "lists.ok_answer", 0
        if isinstance(e.reason, (ConnectionResetError, ConnectionAbortedError, ssl.SSLError)):
            return "bad", "lists.reset", 0
        return "bad", "lists.noreply", 0
    except (ConnectionResetError, ConnectionAbortedError, ssl.SSLError):
        if got:
            return "warn", "lists.cut", round(got / 1024)
        return "bad", "lists.reset", 0
    except Exception:
        if got:
            return "warn", "lists.cut", round(got / 1024)
        return "bad", "lists.noreply", 0
    return "ok", "lists.ok", round(got / 1024)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/vnd.github+json"})
    with _direct_opener().open(req, timeout=20) as r:
        return json.loads(r.read(2 * 1024 * 1024))


def latest_release(url=RELEASE_API):
    rel = fetch_json(url)
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


def trusted_release():
    """Релиз версии TRUSTED_ENGINE. Его сумму сравнивает download_verified, поэтому подделать архив
    не поможет ни ответ сети, ни взлом страницы релизов."""
    tag, sha = TRUSTED_ENGINE
    rel = latest_release(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}")
    if rel["sha256"] != sha:
        raise EngineError(T("Контрольная сумма версии {} не совпала с записанной в NIXYZ — установка отменена", tag))
    return rel


def confirm_unverified(rel):
    """Версию новее TRUSTED_ENGINE автор сборки не видел: её сумму подтверждает только сам GitHub."""
    return rel["sha256"] == TRUSTED_ENGINE[1] or native_confirm(T(
        "Версия движка {} вышла после этой сборки NIXYZ, её автор не проверял.\n\n"
        "Контрольная сумма совпадает с данными GitHub. Это защита от порчи файла, но не от взлома "
        "репозитория.\n\nУстановить эту версию?", rel["tag"]))


def release_to_install(current):
    """Что ставить при скачивании: проверенную версию, а если установлена более новая или проверенную
    убрали с GitHub — последнюю, после вопроса. Откатывать рабочий движок на старую версию нельзя."""
    if not (re.match(r"\d", current) and newer_version(current, TRUSTED_ENGINE[0])):
        try:
            return trusted_release()
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    rel = latest_release()
    if not confirm_unverified(rel):
        raise EngineError(T("Установка отменена"))
    return rel


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
    shown = -1
    req = urllib.request.Request(rel["url"], headers={"User-Agent": USER_AGENT})
    with _direct_opener().open(req, timeout=30) as r:
        while True:
            chunk = r.read(64 * 1024)
            if not chunk:
                break
            if len(buf) + len(chunk) > rel["size"]:
                raise EngineError(T("Архив больше заявленного — скачивание отменено"))
            h.update(chunk)
            buf += chunk
            percent = len(buf) * 100 // rel["size"]
            if percent != shown:
                shown = percent
                progress(percent / 100)
    if len(buf) != rel["size"]:
        raise EngineError(T("Архив скачался не полностью"))
    if h.hexdigest() != rel["sha256"]:
        raise EngineError(T("SHA-256 не совпал. Файл подменён или повреждён — он отброшен."))
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


def install_release(rel, progress, current=None):
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
        fresh = Engine.find(partial)
        if current and fresh:  # свои списки лежат в папке версии, новой они достаются от прежней
            fresh.lists.mkdir(exist_ok=True)
            for name in USER_LISTS.values():
                if (current.lists / name).is_file():
                    shutil.copyfile(current.lists / name, fresh.lists / name)
        return _commit_engine(partial, final)
    finally:
        if partial.exists():
            shutil.rmtree(partial, ignore_errors=True)


def _commit_engine(partial, final):
    """Ставит готовую папку на место версии, не теряя рабочий движок при сбое."""
    e = Engine.find(partial)
    if not e:
        raise EngineError(T("В архиве нет bin\\winws.exe. Скорее всего его удалил антивирус — добавьте "
                            "папку {} в исключения и повторите.", ENGINE_DIR))
    sub = e.root.relative_to(partial)
    old = final.with_name(final.name + ".old")
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
    return Engine(final / sub)


def copy_engine(src):
    """Копия папки, которую указал пользователь, в папку программы. Запускать файлы администратором
    прямо из его папки нельзя: любая его программа может заменить их сразу после проверки."""
    ENGINE_DIR.mkdir(exist_ok=True)
    final, partial = ENGINE_DIR / "custom", ENGINE_DIR / "custom.partial"
    if partial.exists():
        shutil.rmtree(partial)
    written = 0
    try:
        for folder, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if not os.path.isjunction(os.path.join(folder, d))]  # по символьным ссылкам os.walk сам не идёт
            for name in files:
                f = Path(folder, name)
                if f.is_symlink():
                    continue
                written += f.stat().st_size
                if written > MAX_UNPACKED:
                    raise EngineError(T("Архив слишком большой после распаковки"))
                out = partial / f.relative_to(src)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, out)
        return _commit_engine(partial, final)
    finally:
        if partial.exists():
            shutil.rmtree(partial, ignore_errors=True)


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
               NIXYZ_EXE=gui_python(),
               NIXYZ_ARGS=subprocess.list2cmdline(self_args("--autostart")),
               NIXYZ_DIR=str(APP_DIR),
               NIXYZ_TASK=TASK_NAME,
               NIXYZ_DESC=T("{}: запуск обхода при входе в Windows", APP_NAME))
    script = """
$ErrorActionPreference = 'Stop'
$u = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$a = New-ScheduledTaskAction -Execute $env:NIXYZ_EXE -Argument $env:NIXYZ_ARGS -WorkingDirectory $env:NIXYZ_DIR
$t = New-ScheduledTaskTrigger -AtLogOn -User $u
$t.Delay = 'PT5S'
$p = New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Highest
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $env:NIXYZ_TASK -Description $env:NIXYZ_DESC -Action $a -Trigger $t -Principal $p -Settings $s -Force | Out-Null
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
        "--window-size=1120,630", "--no-first-run", "--no-default-browser-check",
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
    env = dict(os.environ, NIXYZ_EXE=cmd[0], NIXYZ_ARGS=subprocess.list2cmdline(cmd[1:]),
               NIXYZ_DIR=SYSTEM_DIR, NIXYZ_TASK=task)
    script = """
$ErrorActionPreference = 'Stop'
$u = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$a = New-ScheduledTaskAction -Execute $env:NIXYZ_EXE -Argument $env:NIXYZ_ARGS -WorkingDirectory $env:NIXYZ_DIR
$p = New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Limited
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $env:NIXYZ_TASK -Action $a -Principal $p -Settings $s -Force | Out-Null
try { Start-ScheduledTask -TaskName $env:NIXYZ_TASK; Start-Sleep -Milliseconds 1500 }
finally { Unregister-ScheduledTask -TaskName $env:NIXYZ_TASK -Confirm:$false }
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
    names = (f"{APP_TITLE}.lnk",)
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
        raise EngineError(T("{} — ссылка, а не папка. Переустановите NIXYZ.", DATA_DIR))
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
    import winreg
    try:  # из реестра, а не из вывода sc qc: на русской Windows его подписи переведены и путь там не найти
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SYSTEM\CurrentControlSet\Services\{name}") as k:
            path = str(winreg.QueryValueEx(k, "ImagePath")[0])
    except OSError:
        return False
    return str(ENGINE_DIR.resolve()).lower() in path.strip('"').lower().replace("\\??\\", "")


def remove_system_traces():
    """Всё, что NIXYZ оставляет в Windows, кроме своей папки: автозапуск, свой драйвер,
    ярлыки, запись в «Приложениях»."""
    import winreg
    done = []
    if autostart_enabled():
        set_autostart(False)
        done.append(T("автозапуск"))
    for name in ("WinDivert", "WinDivert14"):
        if not driver_is_ours(name):
            continue
        for _ in range(17):  # до ~5 с: пока движок закрывается, драйвер может отказать, поэтому просим снова
            run_quiet(["sc", "stop", name])
            code, out = run_quiet(["sc", "query", name])
            if code != 0 or "STOPPED" in out:
                break
            time.sleep(0.3)
        # WinDivert сам помечает службу на удаление: после остановки её может уже не быть, и это тоже успех
        if run_quiet(["sc", "delete", name])[0] == 0 or run_quiet(["sc", "query", name])[0] != 0:
            done.append(T("драйвер {}", name))
    code, out = run_quiet(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                           "@(Get-DnsClientNrptRule | Where-Object { $_.Comment -eq 'NIXYZ' }).Count"])  # @: без него одно правило даёт пустой счёт
    if code == 0 and out.strip() not in ("", "0"):
        nrpt_clear()
        done.append(T("правила «Умного обхода»"))
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
    # драйвер, который не удалось выгрузить раньше, держит свой файл: без этого папка не удалится
    loaded = ",".join(n for n in ("WinDivert", "WinDivert14") if driver_is_ours(n))
    env = dict(os.environ, NIXYZ_DIR=str(APP_DIR), NIXYZ_PID=str(os.getpid()),
               NIXYZ_CMD=system_tool("cmd"), NIXYZ_SC=system_tool("sc"), NIXYZ_DRV=loaded)
    script = ("Wait-Process -Id ([int]$env:NIXYZ_PID) -Timeout 120 -ErrorAction SilentlyContinue; "
              "for ($i = 0; $i -lt 40; $i++) { "
              "foreach ($n in ($env:NIXYZ_DRV -split ',')) { if ($n) { & $env:NIXYZ_SC stop $n | Out-Null } }; "
              "& $env:NIXYZ_CMD /d /c rd /s /q $env:NIXYZ_DIR; "
              "if (-not (Test-Path -LiteralPath $env:NIXYZ_DIR)) { break }; Start-Sleep -Milliseconds 750 }")
    subprocess.Popen([system_tool("powershell"), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                      "-Command", script], cwd=SYSTEM_DIR, env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)


UNINSTALL_QUESTION = ("Удалить NIXYZ с компьютера полностью?\n\n"
                      "Будут выключены обход и автозапуск, удалены драйвер WinDivert, движок zapret, "
                      "настройки, ярлыки, запись в «Приложениях» и сама программа.\n\nОтменить это нельзя.")


def backup_names(keys):
    return ", ".join({"dns": "DNS", "wifi": "Wi-Fi", "tcp": "TCP"}.get(k, k) for k in keys)


def restore_network(backup):
    """Вернуть то, что менял экран «Ускорение», когда окна программы нет: DNS, Wi-Fi, TCP.
    Возвращает ключи того, что вернуть не удалось."""
    saved = dict(backup.get("dns") or {})
    for a in net_adapters():
        if a["guid"] in saved and set_dns(a["index"], saved[a["guid"]])[0] == 0:
            del saved[a["guid"]]
    failed = ["dns"] if saved else []
    if "wifi" in backup and not set_wifi_power(*backup["wifi"]):
        failed.append("wifi")
    if "tcp" in backup and not set_tcp_autotuning(backup["tcp"]):
        failed.append("tcp")
    flush_dns()
    return failed


def uninstall_from_windows():
    """Удаление из «Параметры → Приложения» (NIXYZ.exe --uninstall): без окна программы."""
    if not native_confirm(T(UNINSTALL_QUESTION)):
        return
    if FROZEN:  # закрыть открытый NIXYZ (ровно этот exe) — его winws.exe закроется вместе с ним
        for pid in own_processes(sys.executable):
            if pid != os.getpid():
                run_quiet(["taskkill", "/F", "/PID", str(pid)])
        time.sleep(1)
    try:
        settings = load_settings()
        failed = restore_network(settings["net_backup"])
        restore_tcp_timestamps(settings["ts_backup"])
        if failed:
            message(T("Не удалось вернуть: {}. Проверьте это вручную в параметрах сети Windows.", backup_names(failed)), error=True)
    except Exception as e:
        message(T("Не удалось вернуть настройки сети: {}", e), error=True)
    remove_system_traces()
    schedule_removal()
    message(T("NIXYZ удалён с компьютера."))


def message_plain(text, error):
    message(text, error=error)


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
        owner = Form()  # невидимый владелец поверх всех окон — диалог не спрячется за NIXYZ
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
        self._revived = 0.0      # когда сторож в последний раз сам поднимал упавший обход
        self.window_hidden = False
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
        self._net_lock = threading.Lock()   # одно сетевое действие за раз, обход при этом не блокируется
        self._smart_lock = threading.Lock()  # «Умный обход» включается и выключается по одному разу за раз
        self.smart_dns = None                # наш DNS-сервер для имён ИИ, пока «Умный обход» работает
        self.smart_rules = False             # правила NRPT стоят — при выключении и выходе их надо снять
        self._diag_running = False
        self.on_notify = None                # окно задаёт, как показать уведомление Windows (значок в трее)
        self.log_lines = deque(maxlen=400)
        self.bypass = Bypass(lambda line: self.log(line, "engine"))
        apply_lang(self.settings["lang"])
        self.state = {
            "screen": "setup", "power": "off", "title": T(IDLE_TITLE), "sub": self._idle_sub(),
            "strategy": "", "strategies": [], "engine": "", "busy": False, "auto": False,
            "auto_note": "",
            "pills": {svc: {"tone": "idle", "note": ""} for svc in PILLS},
            "toggles": {"game": self.settings["game_filter"], "open": self.settings["start_on_open"],
                        "autostart": False, "smart": self.settings["smart"], "smart_told": self.settings["smart_told"],
                        **{k: self.settings[k] for k in PLAIN_TOGGLES}},
            "setup": {"text": "", "tone": "muted"}, "dialog": None, "admin": is_admin(),
            "update": None, "app_version": APP_VERSION, "on_since": None, "auto_progress": None,
            "lang": LANG, "prefs": {k: self.settings[k] for k in ("lang", "theme", "smart_dns", "smart_doh")},
            "lists": {}, "probe": None, "diag": None,
            "net": {"busy": None, "on": bool(self.settings["net_backup"]), "scanned": False, "dns": [],
                    "dns_cur": None, "best": None, "wifi": None, "tcp": None, "adapters": [],
                    "speed": self.settings["net_speed"] or None, "progress": None, "live": None,
                    "src": None, "sources": None},
        }
        self.log(T("{} {} запущен, права администратора: {}", APP_NAME, APP_VERSION, T('да') if is_admin() else T('нет')))
        self._load_engine()
        threading.Thread(target=lambda: self.set_toggle(autostart=autostart_enabled()),
                         daemon=True).start()
        # правила NRPT от прошлого запуска (если программа тогда упала) снимаются, а включённый
        # «Умный обход» поднимается заново
        threading.Thread(target=self._smart_boot, daemon=True).start()
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

    def set_toggle(self, **kw):
        with self.lock:
            self.set(toggles=dict(self.state["toggles"], **kw))

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
            self._status("off", T(IDLE_TITLE), self._idle_sub())

    def _idle_sub(self):
        # кнопка включает только сам обход, а «Умный обход» живёт отдельно: экран не должен вводить в заблуждение
        return T("Умный обход для ИИ при этом продолжает работать") if self.smart_rules else T(IDLE_SUB)

    def _reset_pills(self):
        self.set(pills={svc: {"tone": "idle", "note": ""} for svc in PILLS})

    def _set_busy(self, v):
        self.is_busy = v
        self.set(busy=v, auto=self._auto_running)

    def watchdog(self):
        """Замечает, если наш winws.exe умер сам."""
        while not self.closing:
            time.sleep(0.3)
            try:
                if not self.is_busy:
                    code = self.bypass.take_exit_code()
                    if code is not None:
                        self._engine_died(code)
            except Exception as e:
                self.log(T("Сторож движка: ошибка {}", e), "err")

    def _engine_died(self, code):
        self.running_name = None
        self.log(T("winws.exe неожиданно завершился (код {})", code), "err")
        self._reset_pills()
        self._status("error", T("Движок остановился"), T("Откройте журнал. Частая причина — антивирус или другой обход."))
        self.notify(T("Обход остановился — YouTube и Discord могут не открываться"))
        # включённый «Сторож» поднимает обход сам, но не чаще раза в 5 минут: если движок убивает антивирус, это бесполезно
        if self.settings["watch"] and time.time() - self._revived > 300:
            self._revived = time.time()
            self.log(T("Сторож: перезапускаю обход"))
            self.start_bypass()

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
        if e and FROZEN and ENGINE_DIR.resolve() not in e.root.resolve().parents:
            e = None  # папка вне программы (осталась от старой версии): её файлы может заменить кто угодно
        if e and self.settings["engine_hashes"]:
            self._set_engine(e)
            return
        if not e and ENGINE_DIR.is_dir():
            for d in sorted(ENGINE_DIR.iterdir(), key=lambda p: natural_key(p.name), reverse=True):
                if not d.name.endswith((".partial", ".old")):
                    e = Engine.find(d)
                    if e:
                        break
            # папка движка сменилась, а настройки остались: файлы совпали с запомненными суммами — спрашивать незачем
            if e and self.settings["engine_hashes"] and not e.verify_binaries(self.settings["engine_hashes"]):
                self._set_engine(e)
                return
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
        else:
            self.set(setup={"text": T("Нажмите «Повторить», чтобы скачать движок заново."), "tone": "muted", "retry": True})

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
        self.set(screen="main", strategies=names, strategy=self.settings["strategy"], engine=self._engine_label(),
                 lists={n: read_user_list(e, n) for n in USER_LISTS})
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
        self.alert(T("Нужны права администратора. Перезапустите NIXYZ."))
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
            if tcp_timestamps() == "disabled" and not self.settings["ts_backup"]:
                self.settings["ts_backup"] = "disabled"  # запоминаем до изменения
                save_settings(self.settings)
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
        self.set(strategy=name, auto_note="")  # итог прошлого подбора к ручному выбору уже не относится
        if self.bypass.running:
            prev = self.running_name
            if self.settings["rollback"] and prev and prev != name:
                return self._pick_with_rollback(prev, name)
            self.start_bypass()

    def toggle(self, key, value):
        value = bool(value)
        if key == "open":
            self.settings["start_on_open"] = value
            save_settings(self.settings)
            self.set_toggle(open=value)
        elif key == "game" and not self.is_busy:
            self.settings["game_filter"] = value
            save_settings(self.settings)
            self.set_toggle(game=value)
            self.log(T("Игровой режим: {}", T('вкл') if value else T('выкл')))
            if self.bypass.running:
                self.start_bypass()
        elif key == "autostart":
            self.toggle_autostart(value)
        elif key in PLAIN_TOGGLES:
            self.settings[key] = value
            save_settings(self.settings)
            self.set_toggle(**{key: value})
        elif key == "smart":
            if value and not self.settings["smart_told"]:  # подсказку при первом включении окно показывает один раз
                self.settings["smart_told"] = True
                self.set_toggle(smart_told=True)
            self.smart_switch(value)

    def pref(self, key, value):
        """Язык, тема окна и выбор способа «Умного обхода»."""
        if key == "smart_doh":
            value = value.strip()
            if value and not doh_target(value):
                return self.log(T("Свой DNS-сервер не похож на адрес DoH или IP: {}", value[:80]), "err")
            # импорт настроек этого сделать не может, и скрипт в окне тоже не должен: только по ответу человека
            if value and value != self.settings[key] and not native_confirm(T(
                    "Запросы к ИИ-сервисам пойдут через этот DNS-сервер:\n\n{}\n\nОн будет видеть, к каким из них вы "
                    "обращаетесь, и сможет подставлять адреса. Указывайте только сервер, которому доверяете.\n\n"
                    "Использовать его?", value[:200])):
                return self.set(prefs=dict(self.state["prefs"]))
        elif value not in {"lang": LANGS, "theme": THEMES, "smart_dns": SMART_DNS}.get(key, ()):
            return
        self.settings[key] = value
        save_settings(self.settings)
        prefs = dict(self.state["prefs"], **{key: value})
        if key.startswith("smart_"):
            self.set(prefs=prefs)
            matters = key == "smart_dns" or (key == "smart_doh" and self.settings["smart_dns"] == "custom")
            if self.settings["smart"] and matters:
                self.smart_switch(True)  # применить новый DNS сразу
            return
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

    # ---- свои списки и проверка сайта

    def list_save(self, name, text):
        """Сохраняет свой список. Возвращает номера неверных строк (тогда ничего не пишется)."""
        if name not in USER_LISTS or not self.engine or len(text) > LIST_MAX:
            return [0]
        bad = list_errors(name, text)
        if bad:
            return bad
        try:
            write_user_list(self.engine, name, text)
        except OSError as e:
            self.log(T("Не удалось сохранить список: {}", e), "err")
            return [0]
        self.set(lists=dict(self.state["lists"], **{name: read_user_list(self.engine, name)}))
        self.log(T("Список «{}» сохранён", USER_LISTS[name]), "ok")
        if self.bypass.running and not self.is_busy:
            self.start_bypass()  # winws читает списки только при запуске
        return []

    def probe(self, domain):
        host = list_host(domain.strip().removeprefix("https://").removeprefix("http://").split("/")[0])
        if not HOST_RE.fullmatch(host):
            return self.set(probe={"domain": domain[:80], "tone": "bad", "key": "lists.badname", "kb": 0})
        self.set(probe={"domain": host, "tone": "wait", "key": "lists.checking", "kb": 0})

        def job():
            tone, key, kb = probe_site(host)
            self.set(probe={"domain": host, "tone": tone, "key": key, "kb": kb})
            self.log(T("Проверка сайта {}: {}", host, {"ok": T("открывается"), "warn": T("обрывается после {} КБ", kb)}
                       .get(tone, T("не открывается"))), "ok" if tone == "ok" else "err")
        threading.Thread(target=job, daemon=True).start()

    # ---- «Почему не работает?»

    def diagnose(self):
        if self._diag_running:
            return
        self._diag_running = True
        threading.Thread(target=self._diagnose, daemon=True).start()

    def _diagnose(self):
        checks = {k: {"state": "wait"} for k in DIAG_CHECKS}
        self.set(diag=dict(checks))

        def put(key, ok, d, args=(), fix=None):
            checks[key] = {"state": "ok" if ok else "problem", "d": d, "args": list(args), "fix": None if ok else fix}
            self.set(diag=dict(checks))

        try:
            if not self.engine:
                put("engine", False, "diag.engine_none", fix="download")
            else:
                changed = self.engine.verify_binaries(self.settings["engine_hashes"])
                put("engine", not changed, "diag.engine_bad" if changed else "diag.engine_d", fix="download")
            admin = is_admin()
            put("admin", admin, "diag.admin_d" if admin else "diag.admin_bad")
            proc = self.bypass.proc
            ours = proc.pid if proc else None
            dpi = other_dpi() + (["zapret"] if service_running("zapret") else []) + \
                (["winws.exe"] if any(pid != ours for pid in winws_pids()) else [])
            put("dpi", not dpi, "diag.dpi_bad" if dpi else "diag.dpi_d", [", ".join(dpi)], fix="dpi")
            bad = dns_spoofed()
            if bad is None:
                put("dns", False, "diag.dns_none")
            else:
                put("dns", not bad, "diag.dns_bad" if bad else "diag.dns_d", fix="boost")
            skew = clock_skew()
            ok = skew is None or skew < 300
            put("time", ok, "diag.time_d" if ok else "diag.time_bad", [] if ok else [round(skew / 60)], fix="time")
            if not self.bypass.running:
                put("strategy", False, "diag.strategy_off", fix="power")
            else:
                res = check_targets(AUTO_TARGETS)
                got, total = score(res), sum(len(v) for v in res.values())
                put("strategy", got == total, "diag.strategy_ok" if got == total else "diag.strategy_bad",
                    [got, total], fix="auto")
            problems = [k for k, v in checks.items() if v["state"] == "problem"]
            self.log(T("Диагностика: {}", T("всё в порядке") if not problems else ", ".join(problems)),
                     "ok" if not problems else "err")
        except Exception as e:
            self.log(T("Диагностика прервалась: {}", e), "err")
        finally:
            for k, v in checks.items():
                if v["state"] == "wait":
                    checks[k] = {"state": "problem", "d": "diag.unknown", "args": [], "fix": None}
            self.set(diag=dict(checks))
            self._diag_running = False

    def diag_fix(self, key):
        if key == "download":
            return self.download()
        if key == "power":
            return self.start_bypass()
        if key == "auto":
            return None if self._auto_running else self.auto()  # auto() — переключатель: идущий подбор не отменять

        def job():
            if key == "dpi":
                for name in other_dpi():
                    run_quiet(["taskkill", "/IM", name, "/F"])
                    self.log(T("Закрыт посторонний обходчик: {}", name))
                if service_running("zapret"):
                    run_quiet(["sc", "stop", "zapret"])
                    self.log(T("Служба zapret остановлена"))
                proc = self.bypass.proc
                ours = proc.pid if proc else None
                for pid in winws_pids():
                    if pid != ours:
                        run_quiet(["taskkill", "/PID", str(pid), "/F"])
            elif key == "time":
                run_quiet(["sc", "start", "w32time"])
                time.sleep(1)
                code, _ = run_quiet(["w32tm", "/resync", "/force"], timeout=30)
                self.log(T("Часы сверены с интернетом") if code == 0 else T("Не удалось сверить часы"),
                         "ok" if code == 0 else "err")
            else:
                return
            time.sleep(1)
            self.diagnose()
        threading.Thread(target=job, daemon=True).start()

    # ---- сторож, автооткат, уведомления

    def notify(self, text):
        if self.settings["notify"] and self.on_notify:
            self.on_notify(text)

    def guard_loop(self):
        """«Сторож» раз в 10 мин и «ночная перепроверка» около 4:00 проверяют YouTube и Discord и сами
        подбирают стратегию, если они перестали открываться (но не когда пропал весь интернет)."""
        next_watch, night_done = time.time() + 600, ""
        while not self.closing:
            time.sleep(30)
            if self.closing or self.is_busy:
                continue
            try:
                today = time.strftime("%Y-%m-%d")
                night = self.settings["nightly"] and time.localtime().tm_hour == 4 and night_done != today
                watch = self.settings["watch"] and time.time() >= next_watch
                if not (night or watch) or not self.bypass.running:
                    continue
                next_watch = time.time() + 600
                if night:
                    night_done = today
                self._guard_check()
            except Exception as e:
                self.log(T("Сторож: ошибка {}", e), "err")

    def _guard_check(self):
        res = check_targets(AUTO_TARGETS)
        got, total = score(res), sum(len(v) for v in res.values())
        if got == total or self.is_busy or not self.bypass.running:
            return
        if not probe("https://www.cloudflare.com"):
            return self.log(T("Сторож: похоже, пропал интернет — подбор не запускаю"))
        self.log(T("Сторож: открывается {} из {} — подбираю стратегию заново", got, total), "err")
        self.notify(T("YouTube или Discord перестали открываться — NIXYZ подбирает новую стратегию"))
        self.auto()

    def _pick_with_rollback(self, prev, name):
        """Ручной выбор при включённом автооткате: новая стратегия хуже прежней — вернуть прежнюю."""
        def job():
            before = score(check_targets(AUTO_TARGETS))
            self._status("starting", T("Запускаю…"), T("Стратегия «{}»", name))
            try:
                self._launch(name)
            except Exception as e:
                self.log(T("Не удалось запустить: {}", e), "err")
                after = -1
            else:
                time.sleep(1.5)
                after = score(check_targets(AUTO_TARGETS))
            if after < before:
                self.log(T("«{}» хуже прежней ({} против {}) — вернул «{}»", name, max(after, 0), before, prev), "err")
                self.notify(T("Новая стратегия оказалась хуже — NIXYZ вернул «{}»", prev))
                self.settings["strategy"] = prev
                save_settings(self.settings)
                self.set(strategy=prev)
                name_now = prev
                try:
                    self._launch(prev)
                except Exception as e:
                    self.log(T("Не удалось запустить: {}", e), "err")
                    return self._status("error", T("Не удалось запустить"), str(e))
            else:
                name_now = name
            self.log(T("Обход работает: «{}»", name_now), "ok")
            self._status("on", T("Обход работает"), T("Стратегия «{}»", name_now))
            return self.check
        self.run_bg(job)

    # ---- отчёт для поддержки, экспорт и импорт настроек

    def report(self):
        s = self.settings
        lines = [f"{APP_NAME} {APP_VERSION}", f"Windows: {platform_name()}",
                 f"zapret: {self._engine_label() if self.engine else '—'}",
                 f"strategy: {s['strategy']}  game: {s['game_filter']}  admin: {is_admin()}",
                 "smart: {} dns={}{}".format(s["smart"], s["smart_dns"], " (свой задан)" if s["smart_doh"] else ""),
                 "watch: {} nightly: {} rollback: {}".format(s["watch"], s["nightly"], s["rollback"]),
                 "pills: " + ", ".join(f"{k}={v['tone']}" for k, v in self.state["pills"].items()),
                 "", "— журнал —", *(f"{t} {text}" for t, text, _ in self.log_lines)]
        text = re.sub(r"(Проверка сайта|Site check) [^:]+:", r"\1 <site>:", "\n".join(lines))
        try:
            path = write_new_file(downloads_dir() / time.strftime("NIXYZ-report-%Y%m%d-%H%M.txt"), scrub(text) + "\n")
        except OSError as e:
            self.log(T("Не удалось сохранить отчёт: {}", e), "err")
            return str(e)
        self.log(T("Отчёт сохранён в «Загрузки»: {} — имя пользователя, компьютера и адреса в сети скрыты", path.name), "ok")
        reveal(path)
        return ""

    def export(self):
        data = {"app": APP_NAME, "version": APP_VERSION, "settings": {k: self.settings[k] for k in EXPORT_KEYS},
                "lists": {n: read_user_list(self.engine, n) for n in USER_LISTS} if self.engine else {}}
        try:
            path = write_new_file(downloads_dir() / time.strftime("NIXYZ-settings-%Y%m%d.json"),
                                  json.dumps(data, ensure_ascii=False, indent=2))
        except OSError as e:
            self.log(T("Не удалось сохранить настройки: {}", e), "err")
            return str(e)
        self.log(T("Настройки сохранены в «Загрузки»: {}", path.name), "ok")
        reveal(path)
        return ""

    def settings_import(self, text):
        """Настройки из файла экспорта. Возвращает "" или текст ошибки."""
        try:
            data = json.loads(text)
        except (ValueError, RecursionError):
            return T("Это не файл настроек NIXYZ")
        if not isinstance(data, dict) or data.get("app") != APP_NAME or not isinstance(data.get("settings"), dict):
            return T("Это не файл настроек NIXYZ")
        new = data["settings"]
        for k in EXPORT_KEYS:
            v = new.get(k)
            if not isinstance(v, type(DEFAULTS[k])):
                continue
            if (k == "lang" and v not in LANGS) or (k == "theme" and v not in THEMES) or \
                    (k == "strategy" and v not in self.state["strategies"]):
                continue
            self.settings[k] = v
        save_settings(self.settings)
        lists = data.get("lists") if isinstance(data.get("lists"), dict) else {}
        skipped = []
        if self.engine:
            for n, body in lists.items():
                if n not in USER_LISTS:
                    continue
                try:
                    if not isinstance(body, str) or len(body) > LIST_MAX or list_errors(n, body):
                        raise ValueError
                    write_user_list(self.engine, n, body)
                except (ValueError, OSError):
                    skipped.append(USER_LISTS[n])
        s = self.settings
        apply_lang(s["lang"])
        self.set_toggle(game=s["game_filter"], open=s["start_on_open"], **{k: s[k] for k in PLAIN_TOGGLES})
        self.set(prefs={k: s[k] for k in ("lang", "theme", "smart_dns", "smart_doh")}, lang=LANG,
                 strategy=s["strategy"],
                 lists={n: read_user_list(self.engine, n) for n in USER_LISTS} if self.engine else {})
        if self.on_theme:
            self.on_theme()
        self.log(T("Настройки загружены из файла"), "ok")
        if self.bypass.running and not self.is_busy:
            self.start_bypass()  # стратегия, игровой режим и списки применяются только при запуске
        if skipped:
            self.log(T("Не загружены списки с ошибками: {}", ", ".join(skipped)), "err")
            return T("Настройки загружены, но не все списки: {}", ", ".join(skipped))
        return ""


    # ---- «Умный обход»

    def smart_switch(self, on):
        self.settings["smart"] = on
        save_settings(self.settings)
        self.set_toggle(smart=on)
        threading.Thread(target=self._smart_apply_shown, daemon=True).start()

    def _smart_boot(self):
        with self._smart_lock:
            code, out = nrpt_clear()
            if code != 0:
                self.log(T("Не удалось снять старые правила DNS: {}", out.strip()[:200]), "err")
        if self.settings["smart"]:
            self._smart_apply_shown()

    def _smart_apply_shown(self):
        self._smart_apply()
        if self.state["power"] == "off":
            self._refresh_status()

    def _smart_apply(self):
        with self._smart_lock:
            self._smart_stop()
            s = self.settings
            if not s["smart"] or self.closing:
                return self.log(T("Умный обход выключен"))
            if not is_admin():
                return self._smart_fail(T("Умному обходу нужны права администратора"))
            own = doh_target(s["smart_doh"]) if s["smart_dns"] == "custom" else None
            if s["smart_dns"] == "custom" and not own:
                self.log(T("Свой DNS-сервер не задан — беру встроенный"), "err")
            if own and own[0] == "ip":
                servers, via = [own[1]], own[1]
            else:
                urls = [own[1]] if own else list(SMART_DOH)
                self.smart_dns = SmartDns(urls)
                try:
                    self.smart_dns.start()
                except OSError as e:
                    self.smart_dns = None
                    return self._smart_fail(T("Не удалось занять адрес {}:53 ({})", SMART_IP, e))
                servers, via = [SMART_IP], urllib.parse.urlsplit(urls[0]).hostname
            code, out = nrpt_set(servers)
            self.smart_rules = True  # даже при ошибке часть правил могла встать — снимем при выключении
            if code != 0:
                self._smart_stop()
                return self._smart_fail(T("Windows не приняла правило DNS: {}", out.strip()[:200]))
            self.log(T("Умный обход: ИИ идут через умный DNS ({})", via), "ok")

    def _smart_stop(self):
        """Снимает правила NRPT и останавливает наш DNS-сервер. Вызывать под _smart_lock."""
        if self.smart_dns:
            self.smart_dns.close()
            self.smart_dns = None
        if self.smart_rules:
            code, out = nrpt_clear()
            if code == 0:
                self.smart_rules = False
            else:
                self.log(T("Не удалось снять правила DNS «Умного обхода»: {}", out.strip()[:200]), "err")

    def _smart_fail(self, text):
        self.log(text, "err")
        self.alert(text)
        self.set_toggle(smart=False)  # настройка остаётся: при следующем запуске NIXYZ попробует снова

    # ---- ускорение интернета

    def _net(self, **kw):
        with self.lock:
            self.set(net=dict(self.state["net"], **kw))

    def _net_bg(self, kind, fn, *args):
        if not self._net_lock.acquire(blocking=False):
            return

        def wrap():
            try:
                fn(*args)
            except Exception as e:
                self.log(T("Ошибка: {}", e), "err")
            finally:
                self._net(busy=None, progress=None, live=None, src=None, on=bool(self.settings["net_backup"]))
                self._net_lock.release()

        self._net(busy=kind)
        threading.Thread(target=wrap, daemon=True).start()

    def _net_admin(self):
        if is_admin():
            return True
        self.alert(T("Чтобы менять настройки сети, запустите NIXYZ от имени администратора."))
        return False

    def _net_save(self):
        save_settings(self.settings)
        self._net(on=bool(self.settings["net_backup"]))

    def net_scan(self):
        self._net_bg("scan", self._net_scan)

    def _net_scan(self):
        adapters = [a for a in net_adapters() if a["up"]]
        backup = self.settings["net_backup"].get("dns", {})
        own = None  # DNS, который был до NIXYZ: вписанный вручную или от роутера
        for a in adapters:
            lst = (backup[a["guid"]] if a["guid"] in backup else a["static"]) or a["dhcp"]
            if lst:
                own = lst[0]
                break
        ids = list(DNS_PROVIDERS)
        servers = [own] + [DNS_PROVIDERS[i][1][0] for i in ids]
        with ThreadPoolExecutor(len(servers)) as pool:
            ms = list(pool.map(lambda x: dns_rtt(x) if x else None, servers))
        cur = next((i for i in ids if adapters and all(a["static"] == list(DNS_PROVIDERS[i][1])
                                                       for a in adapters)), "own")
        rows = [{"id": "own", "name": own or "", "ms": ms[0]}]
        rows += [{"id": i, "name": DNS_PROVIDERS[i][0], "ms": m} for i, m in zip(ids, ms[1:])]
        has_wifi = any(a["wifi"] for a in adapters)
        wp = wifi_power() if has_wifi else None
        tcp = tcp_autotuning()
        self._net(scanned=True, dns=rows, dns_cur=cur, best=self._net_best(rows),
                  wifi=None if wp is None else wp == [0, 0], tcp=None if tcp is None else tcp == "normal",
                  adapters=[{"name": a["name"], "wifi": a["wifi"]} for a in adapters])

    @staticmethod
    def _net_best(rows):
        """Самый быстрый DNS. Чужой выбирается, только если он заметно (на 15 %) быстрее своего."""
        own = rows[0]["ms"]
        fast = min((r for r in rows[1:] if r["ms"] is not None), key=lambda r: r["ms"], default=None)
        return fast["id"] if fast and (own is None or fast["ms"] < own * 0.85) else "own"

    def net_dns(self, choice):
        if choice == "own" or choice in DNS_PROVIDERS:
            self._net_bg("apply", self._net_dns, choice)

    def _net_dns(self, choice):
        if not self._net_admin():
            return
        backup = self.settings["net_backup"]
        if choice == "own":
            saved = backup.get("dns", {})
            for a in net_adapters():
                if a["guid"] in saved:
                    code, out = set_dns(a["index"], saved[a["guid"]])
                    self.log(T("DNS «{}»: как было", a["name"]) if code == 0 else T("DNS «{}»: {}", a["name"], out.strip()),
                             "ok" if code == 0 else "err")
                    if code == 0:  # не вернулось или адаптер сейчас отключён — запись остаётся до следующего раза
                        del saved[a["guid"]]
            if not saved:
                backup.pop("dns", None)
        else:
            adapters = [a for a in net_adapters() if a["up"]]
            saved = backup.setdefault("dns", {})
            for a in adapters:
                saved.setdefault(a["guid"], a["static"] or None)
            self._net_save()  # сначала запомнить, как было, потом менять
            name, servers = DNS_PROVIDERS[choice]
            for a in adapters:
                code, out = set_dns(a["index"], servers)
                self.log(T("DNS «{}»: {}", a["name"], name if code == 0 else out.strip()), "ok" if code == 0 else "err")
        self._net_save()
        flush_dns()
        self._net(dns_cur=choice)

    def net_item(self, key, value):
        if key in ("wifi", "tcp"):
            self._net_bg("apply", self._net_item, key, bool(value))

    def _net_item(self, key, on):
        if not self._net_admin():
            return
        backup = self.settings["net_backup"]
        if key == "wifi":
            if on:
                cur = wifi_power()
                if cur is None:
                    return self.log(T("Не удалось прочитать режим питания Wi-Fi"), "err")
                backup.setdefault("wifi", cur)
                self._net_save()
                ok = set_wifi_power(0, 0)
            elif "wifi" in backup:
                ok = set_wifi_power(*backup["wifi"])
                if ok:
                    del backup["wifi"]
            else:  # так было ещё до NIXYZ: возвращать нечего, и писать «выкл» было бы неправдой
                ok = None
                self.log(T("Wi-Fi: так было ещё до NIXYZ — возвращать нечего"))
            if ok is not None:
                self.log(T("Wi-Fi без энергосбережения: {}", T("вкл") if on else T("выкл")) if ok
                         else T("Не удалось изменить режим питания Wi-Fi"), "ok" if ok else "err")
            wp = wifi_power()
            self._net(wifi=None if wp is None else wp == [0, 0])
        else:
            if on:
                cur = tcp_autotuning()
                if cur and cur != "normal":
                    backup.setdefault("tcp", cur)
                self._net_save()
                ok = set_tcp_autotuning("normal")
            elif "tcp" in backup:
                ok = set_tcp_autotuning(backup["tcp"])
                if ok:
                    del backup["tcp"]
            else:
                ok = None
                self.log(T("TCP: так было ещё до NIXYZ — возвращать нечего"))
            if ok is not None:
                self.log(T("Автонастройка TCP: {}", T("вкл") if on else T("выкл")) if ok
                         else T("Не удалось изменить автонастройку TCP"), "ok" if ok else "err")
            tcp = tcp_autotuning()
            self._net(tcp=None if tcp is None else tcp == "normal")
        self._net_save()

    def net_boost(self):
        self._net_bg("apply", self._net_boost)

    def _net_boost(self):
        if not self._net_admin():
            return
        self.log(T("Ускорение: замеряю DNS-серверы…"))
        self._net_scan()
        n = self.state["net"]
        if n["best"] != n["dns_cur"]:
            self._net_dns(n["best"])
        else:
            self.log(T("DNS уже самый быстрый из доступных"))
        if n["wifi"] is False:
            self._net_item("wifi", True)
        if n["tcp"] is False:
            self._net_item("tcp", True)
        flush_dns()
        self._net_scan()
        self.log(T("Ускорение включено"), "ok")

    def net_restore(self):
        self._net_bg("apply", self._net_restore)

    def _net_restore(self, rescan=True):
        if not self._net_admin():
            return
        backup = self.settings["net_backup"]
        if "dns" in backup:
            self._net_dns("own")
        for key in ("wifi", "tcp"):
            if key in backup:
                self._net_item(key, False)
        if self.settings["ts_backup"]:
            if self.bypass.running:  # стратегиям нужны timestamps, пока движок работает
                self.log(T("TCP timestamps вернутся, когда обход будет выключен"))
            else:
                restore_tcp_timestamps(self.settings["ts_backup"])
                self.settings["ts_backup"] = ""
                self._tcp_done = False
                self._net_save()
        flush_dns()
        if rescan:
            self._net_scan()
        if self.settings["net_backup"]:
            self.log(T("Не всё удалось вернуть: {}. Нажмите «Вернуть» ещё раз, когда сеть будет подключена.",
                       backup_names(self.settings["net_backup"])), "err")
        else:
            self.log(T("Сеть возвращена как было"), "ok")

    def net_speed(self):
        self._net_bg("speed", self._net_speed)

    def _net_speed(self):
        sources, n = {}, len(SPEED_SOURCES)
        for i, src in enumerate(SPEED_SOURCES):
            self.log(T("Замер скорости: {}…", T(SPEED_NAMES[src])))
            self._net(progress=i / n, live=None, src=src, sources=dict(sources))
            try:
                sources[src] = speed_test(src, lambda p, mbps: self._net(
                    progress=round((i + p) / n, 3), live=round(mbps, 1) if p > .05 else None))
                self.log(T("{}: {} Мбит/с, задержка {} мс", T(SPEED_NAMES[src]), sources[src]["down"],
                           sources[src]["ping"]), "ok")
            except Exception as e:
                sources[src] = None
                self.log(T("{}: не удалось ({})", T(SPEED_NAMES[src]), e), "err")
        ok = [r for r in sources.values() if r]
        if not ok:
            self._net(src=None, sources=sources)
            raise EngineError(T("Ни один сервер замера не ответил"))
        # общая скорость — среднее по ответившим источникам, задержка — лучшая
        res = {"down": round(sum(r["down"] for r in ok) / len(ok), 1), "ping": min(r["ping"] for r in ok),
               "sources": sources, "at": int(time.time()), "boost": bool(self.settings["net_backup"])}
        sp = {"prev": self.settings["net_speed"].get("last"), "last": res}
        self.settings["net_speed"] = sp
        save_settings(self.settings)
        self._net(speed=sp, src=None, sources=None)
        self.log(T("Общая скорость {} Мбит/с, задержка {} мс", res["down"], res["ping"]), "ok")

    def net_flush(self):
        def job():
            ok = flush_dns()
            self.log(T("Кэш DNS очищен") if ok else T("Не удалось очистить кэш DNS"), "ok" if ok else "err")

        self._net_bg("apply", job)

    def toggle_autostart(self, v):
        protected = in_program_files(APP_DIR) and in_program_files(gui_python())

        def job():
            if v and not native_confirm(
                    T("NIXYZ будет запускаться при входе в Windows с правами администратора, без запроса.\n\n")
                    + ("" if protected else
                       T("Важно: NIXYZ или сам Python лежат там, куда может писать любая программа вашей "
                         "учётной записи. Вирус, попавший на компьютер, сможет подменить файлы и получить "
                         "права администратора при следующем входе. Надёжнее держать NIXYZ в C:\\Program "
                         "Files и поставить Python «для всех пользователей».\n\n"))
                    + T("Включить автозапуск?")):
                return
            ok, out = set_autostart(v)
            if not ok:
                self.log(T("Не получилось изменить автозапуск: {}", out.strip()), "err")
                self.alert(T("Не получилось изменить автозапуск. Подробности в журнале."))
                return
            self.set_toggle(autostart=v)
            self.log(T("Запуск с Windows: {}", T('вкл') if v else T('выкл')), "ok")

        self.run_bg(job)

    def _show_results(self, res, ai=None):
        pills = dict(self.state["pills"])
        for svc, (tone, loc) in (ai or {}).items():
            pills[svc] = {"tone": tone, "note": loc}
            self.log(f"  {'✓' if tone == 'ok' else '✗'} {svc}: " + (
                T("сервис видит страну {} — закрыт для неё, поможет «Умный обход»", loc) if tone == "geo" else
                T("открывается, страна для сервиса — {}", loc or "?") if tone == "ok" else T("не открывается")),
                "ok" if tone == "ok" else "err")
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
            self.set(pills={svc: {"tone": "wait", "note": "…"} for svc in PILLS})
            with ThreadPoolExecutor(2) as pool:
                ai = pool.submit(check_ai)
                res = check_targets()
                ai = ai.result()
            total = sum(len(items) for items in res.values())
            self._show_results(res, ai)
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
        base = check_targets(AUTO_TARGETS)
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
            res = check_targets(AUTO_TARGETS)
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
                rel = release_to_install(self.engine.version() if self.engine else "")
                self.log(T("Релиз {}: {}, SHA-256 {}", rel['tag'], rel['name'], rel['sha256']))
                e = install_release(rel, lambda p: self.set(
                    setup={"text": T("Скачиваю {} — {}%", rel['name'], int(p * 100)), "tone": "muted",
                           "progress": p, "step": 1}), self.engine)
                self.set(setup={"text": T("Сверяю SHA-256 и запоминаю файлы…"), "tone": "muted", "step": 2})
                manifest = e.manifest()
            except Exception as ex:
                if isinstance(ex, urllib.error.HTTPError) and ex.code in (403, 429):
                    text = T("GitHub временно ограничил запросы. Подождите час и нажмите «Повторить».")
                else:
                    text = f"{ex}\n" + (T("Проверьте интернет и нажмите «Повторить».") if isinstance(ex, OSError)
                                        else T("Нажмите «Повторить»."))
                self.set(setup={"text": text, "tone": "bad", "retry": True})
                raise
            self.log(T("SHA-256 совпал, движок установлен"), "ok")
            self.set(setup={"text": T("Готово — контрольная сумма совпала"), "tone": "ok", "step": 3})
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
            if not confirm_unverified(rel):
                return
            self._status("starting", T("Обновляю движок…"), f"{cur} → {rel['tag']}")
            # Новая версия скачивается и проверяется в свою папку, пока старая работает
            e = install_release(rel, lambda p: self.set(sub=T("Скачиваю {} — {}%", rel['tag'], int(p * 100))), self.engine)
            manifest = e.manifest()
            was_on = self.bypass.running
            self.bypass.stop()
            self.running_name = None
            old_root = self.engine.root if self.engine else None
            self._set_engine(e, manifest)
            self._pending_release = None
            self.log(T("Движок обновлён: {} → {}, SHA-256 совпал", cur, rel['tag']), "ok")
            # убрать прежнюю версию — только если это папка версии, которую ставил сам NIXYZ
            if old_root:
                top = ENGINE_DIR / old_root.relative_to(ENGINE_DIR).parts[0] if ENGINE_DIR in old_root.parents else None
                if top and top.name not in (rel["tag"], "custom") and re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]{0,39}", top.name):
                    shutil.rmtree(top, ignore_errors=True)
            if was_on:
                self._launch(self.settings["strategy"])
                self._status("on", T("Обход работает"), T("Стратегия «{}» · движок {}", self.settings['strategy'], rel['tag']))
            else:
                self._refresh_status()

        if self.run_bg(job, notify=True):
            self.set(update=None)

    def uninstall(self):
        """Удалить NIXYZ полностью: обход, автозапуск, драйвер, движок, настройки, ярлыки, программу."""
        def job():
            if not native_confirm(T(UNINSTALL_QUESTION)):
                return
            self.uninstalling = True  # с этого момента закрытие окна не оборвёт удаление
            try:
                self._status("starting", T("Удаляю NIXYZ…"), T("Выключаю обход и убираю следы в системе"))
                self.stop_flag.set()
                self.bypass.close()
                self.running_name = None
                if self.settings["net_backup"]:
                    try:
                        with self._net_lock:
                            self._net_restore(rescan=False)
                    except Exception as e:  # следы в системе убрать нужно всё равно
                        self.log(T("Ошибка: {}", e), "err")
                    if self.settings["net_backup"]:
                        message(T("Не удалось вернуть: {}. Проверьте это вручную в параметрах сети Windows.",
                                  backup_names(self.settings["net_backup"])), error=True)
                restore_tcp_timestamps(self.settings["ts_backup"])
                done = remove_system_traces()
                self.log(T("Удалено: ") + (", ".join(done) or T("системных следов не было")), "ok")
                self._status("off", T("NIXYZ удалён"), T("Окно закроется само"))
            finally:
                self._uninstall_done.set()
            time.sleep(1.2)
            if self.on_quit:
                self.on_quit()

        self.run_bg(job)

    def folder(self):
        """Своя папка с zapret: после подтверждения движок работает из её копии в папке программы."""
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
            if not native_confirm(T("Эту папку NIXYZ не скачивал и не может проверить её подлинность. "
                                    "Используйте только zapret со страницы github.com/Flowseal.\n\n") +
                                  T("Скопировать эту папку в NIXYZ и запускать движок из копии? Копию обычные "
                                    "программы изменить не смогут.")):
                return
            copy = copy_engine(e.root)
            self._set_engine(copy, copy.manifest())

        self.run_bg(job, notify=True)

    def open_dir(self):
        if self.engine:
            os.startfile(self.engine.root)

    def shutdown(self):
        self.closing = True
        self.stop_flag.set()
        self.bypass.close()  # после этого новый winws уже не запустится, даже из фонового потока
        with self._smart_lock:
            self._smart_stop()  # без программы правила NRPT указывали бы в пустоту — ИИ бы не открывался
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
               "update_apply", "update_later", "update_skip", "uninstall",
               "net_scan", "net_boost", "net_restore", "net_speed", "net_flush",
               "diagnose"}
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
        self._send(code, T("Окно устарело. Закройте его и запустите NIXYZ заново.").encode(),
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
        if not (self._host_ok() and self._session_ok() and self.headers.get("X-NIXYZ") == "1"):
            return self._deny()
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._send(400)
        if not 0 <= n <= LIST_MAX * 4:  # самый большой запрос — импорт настроек с тремя списками
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
        elif action == "net_dns":
            ctl.net_dns(str(body.get("name", "")))
        elif action == "net_item":
            ctl.net_item(str(body.get("key", "")), body.get("value") is True)
        elif action == "probe":
            ctl.probe(str(body.get("domain", ""))[:300])
        elif action in ("report", "export"):
            return self._send(200, json.dumps({"error": getattr(ctl, action)()}).encode())
        elif action == "diag_fix":
            ctl.diag_fix(str(body.get("id", "")))
        elif action == "settings_import":
            err = ctl.settings_import(str(body.get("text", ""))[:LIST_MAX * 4])
            return self._send(200, json.dumps({"error": err}).encode())
        elif action == "list_save":
            bad = ctl.list_save(str(body.get("name", "")), str(body.get("text", "")))
            return self._send(200, json.dumps({"bad": bad}).encode())
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
    вызовы отклоняются, а окно возвращается к себе. Отдавать этот объект в js_api нельзя:
    pywebview ищет метод по имени с точками и подчёркивание не проверяет, так что страница
    дотянулась бы до self._ctl. Поэтому каждый метод открывается отдельно, через window.expose."""

    def __init__(self, ctl):
        self._ctl = ctl
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

    def legal(self, name):
        """Текст соглашения или политики на языке окна. Имя файла из окна не берётся."""
        doc = {"terms": "TERMS", "privacy": "PRIVACY"}.get(name) if self._ok() else None
        if not doc:
            return ""
        base = BUNDLE_DIR / "legal" if FROZEN else APP_DIR.parent
        try:
            return (base / f"{doc}{'' if LANG == 'ru' else '.en'}.md").read_text(encoding="utf-8")
        except OSError:
            return ""

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

    def net_dns(self, name):
        if self._ok():
            self._ctl.net_dns(str(name))

    def net_item(self, key, value):
        if self._ok():
            self._ctl.net_item(str(key), value is True)

    def probe(self, domain):
        if self._ok():
            self._ctl.probe(str(domain)[:300].encode("utf-8", "ignore").decode())  # без непарных суррогатов, иначе состояние не дойдёт до окна

    def list_save(self, name, text):
        return {"bad": self._ctl.list_save(str(name), str(text))} if self._ok() else {"bad": [0]}

    def diag_fix(self, key):
        if self._ok():
            self._ctl.diag_fix(str(key))

    def report(self):
        return {"error": self._ctl.report()} if self._ok() else {"error": "?"}

    def export(self):
        return {"error": self._ctl.export()} if self._ok() else {"error": "?"}

    def settings_import(self, text):
        return {"error": self._ctl.settings_import(str(text)[:LIST_MAX * 4])} if self._ok() else {"error": "?"}


def _bridge_action(name):
    def call(self):
        if self._ok():
            getattr(self._ctl, name)()
    call.__name__ = name  # под этим именем метод увидит окно (window.expose)
    return call


for _name in UiHandler.ACTIONS:
    setattr(Bridge, _name, _bridge_action(_name))


def push_state(ctl, window):
    """Отправляет состояние в окно при каждом изменении (не чаще ~12 раз в секунду)."""
    seen = -1
    while not ctl.closing:
        with ctl.lock:
            if ctl.version == seen or ctl.window_hidden:
                ctl.changed.wait(2)
            if ctl.version == seen or ctl.window_hidden:  # окно в трее: свежий снимок получит, когда откроют
                continue
        try:
            snap = ctl.snapshot()
            seen = snap["version"]
            window.evaluate_js(f"window.__nixyz && window.__nixyz({json.dumps(snap, ensure_ascii=False)})")
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


def exclusive_ports():
    """Встроенные серверы окна занимают порт единолично: с обычным SO_REUSEADDR другая программа
    могла бы сесть на тот же порт и отдать окну свою страницу."""
    import socketserver
    plain_bind = socketserver.TCPServer.server_bind

    def bind(self):
        self.allow_reuse_address = False
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        plain_bind(self)

    socketserver.TCPServer.server_bind = bind


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


SHOW_EVENT = "Local\\NIXYZShowWindow"  # второй запуск ярлыком просит первый показать окно

TRAY_STATUS = {"on": "обход работает", "starting": "запуск…", "error": "ошибка", "off": "обход выключен"}


class Tray:
    """Значок в трее (WinForms NotifyIcon в отдельном STA-потоке). Левый клик — открыть окно,
    правый — меню: открыть, включить/выключить обход, выйти. Выход — только отсюда."""

    def __init__(self, ctl, show, quit):
        self.ctl, self.show, self.quit = ctl, show, quit
        self._icon = None
        self._hint_shown = False
        self._want_hint = False
        self._notes = deque(maxlen=3)   # уведомления Windows ждут показа в потоке значка
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

    def notify(self, text):
        self._notes.append(text)

    def hinted_hide(self):
        """Окно спрятали крестиком — один раз подсказать, где теперь NIXYZ."""
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
        icon_file = Path(sys.executable) if FROZEN else APP_DIR / "packaging" / "nixyz.ico"
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
            text = f"{APP_TITLE} — {T(TRAY_STATUS.get(self.ctl.state['power'], ''))}"[:63]
            if icon.Text != text:
                icon.Text = text
            if self._notes:
                icon.ShowBalloonTip(5000, APP_TITLE, self._notes.popleft(), ToolTipIcon.Info)
            elif self._want_hint:
                self._want_hint, self._hint_shown = False, True
                icon.ShowBalloonTip(4000, APP_TITLE, T("NIXYZ работает в трее. Выйти — правой кнопкой по "
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
    webview.settings["ALLOW_FILE_URLS"] = False
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False
    port = free_port()
    bridge = Bridge(ctl)
    window = webview.create_window(
        APP_TITLE, url=str(UI_DIR / "index.html"), width=1120, height=630,
        min_size=(960, 540), background_color="#000000" if theme_is_dark(ctl.settings["theme"]) else "#F2F2F7", text_select=False, http_port=port,
        hidden=hidden)
    window.expose(*(getattr(bridge, n) for n in dir(Bridge) if not n.startswith("_")))
    bridge._window = window
    quitting = threading.Event()
    ctl.window_hidden = hidden
    seen = {"active": True, "minimized": False, "hooked": False}

    def sync_rest():
        """Анимации идут, только когда на них смотрят. Страница сама этого не узнает: при скрытии окна
        document.hidden остаётся false, а кадры рисуются вхолостую (до целого ядра процессора)."""
        rest = "all" if ctl.window_hidden or seen["minimized"] else "" if seen["active"] else "idle"

        def apply():
            try:
                window.evaluate_js(f"document.documentElement.dataset.rest = '{rest}'; 1")
            except Exception:
                pass

        threading.Thread(target=apply, daemon=True).start()  # события приходят в потоке окна, ждать его же нельзя

    def on_active(active):
        seen["active"] = active
        sync_rest()

    def on_minimized(minimized):
        seen["minimized"] = minimized
        sync_rest()

    def show():
        with ctl.lock:
            ctl.window_hidden = False
            ctl.changed.notify_all()
        sync_rest()
        window.show()
        window.restore()
        paint_title_bar(window, ctl.settings["theme"])

    def quit_app():
        quitting.set()
        window.destroy()

    tray = Tray(ctl, show, quit_app)
    ctl.on_theme = lambda: paint_title_bar(window, ctl.settings["theme"])
    ctl.on_quit = quit_app
    ctl.on_notify = tray.notify

    def on_closing():
        if quitting.is_set() or ctl.uninstalling or tray.session_ending:
            return True
        ctl.window_hidden = True
        sync_rest()
        threading.Thread(target=window.hide, daemon=True).start()  # спрятать после отмены закрытия
        tray.hinted_hide()
        return False

    window.events.closing += on_closing
    window.events.minimized += lambda: on_minimized(True)
    window.events.restored += lambda: on_minimized(False)
    window.events.shown += lambda: paint_title_bar(window, ctl.settings["theme"])

    def on_loaded():
        if not seen["hooked"]:
            seen["hooked"] = True
            window.native.Activated += lambda sender, args: on_active(True)
            window.native.Deactivate += lambda sender, args: on_active(False)
        sync_rest()
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

    if FROZEN and "--install" in sys.argv:  # запуск из установщика (packaging/nixyz.iss)
        import installer
        sys.exit(installer.run_install(APP_DIR, APP_VERSION, message_plain))

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    k32.CreateMutexW(None, False, "Local\\NIXYZApp")  # хэндл живёт до конца процесса
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS: NIXYZ уже работает (может, в трее)
        if not ask_running_copy_to_show():
            message(T("NIXYZ уже запущен — значок в трее рядом с часами."))
        return

    try:
        secure_data_dir()
    except EngineError as e:
        return fatal(str(e))
    autostart = "--autostart" in sys.argv
    exclusive_ports()
    try:
        ctl = Controller(autostart=autostart)
    except Exception as e:
        return fatal(T("Ошибка: {}", e))
    threading.Thread(target=ctl.watchdog, daemon=True).start()
    threading.Thread(target=ctl.guard_loop, daemon=True).start()
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
            except Exception as e:
                ctl.log(T("Окно WebView2 не открылось: {}", e), "err")
                if FROZEN:  # у установленной программы запасного окна нет: Edge без прав не пишет в её папку
                    raise
                run_browser(ctl)
    except Exception as e:
        fatal(T("Не удалось открыть окно: {}\n\nУстановите «Microsoft Edge WebView2 Runtime» с сайта "
                "Microsoft и запустите NIXYZ снова.", e))
    finally:
        if ctl.uninstalling:
            ctl._uninstall_done.wait(30)  # окно закрыли посреди удаления — доделать
        ctl.shutdown()
        if ctl.uninstalling:
            schedule_removal()


if __name__ == "__main__":
    main()
