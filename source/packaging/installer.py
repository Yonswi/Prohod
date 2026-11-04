"""Установка NIXYZ: запускается как «NIXYZ.exe --install» из временной папки установщика.

Установщик на Inno Setup только распаковывает программу в свою защищённую папку и запускает её с этим
флагом (nixyz.iss), а всё остальное делает этот код:
  1. закрывает уже запущенный NIXYZ (только сам NIXYZ.exe из Program Files);
  2. ставит программу в C:\\Program Files\\NIXYZ; настройки и движок (папка data) при
     обновлении переносятся в новую версию;
  3. создаёт ярлыки «NIXYZ» в «Пуске» и на рабочем столе и запись в «Параметры → Приложения»;
  4. запускает NIXYZ — дальше он сам скачает движок, подберёт стратегию и включит обход.
"""
import ctypes
import os
import shutil
import subprocess
import time
import winreg
from pathlib import Path

APP_NAME = "NIXYZ"
APP_TITLE = "NIXYZ"
EXE_NAME = "NIXYZ.exe"
UNINSTALL_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
NO_WINDOW = subprocess.CREATE_NO_WINDOW


def known_folder(csidl):
    buf = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) != 0:
        raise OSError(f"Windows не сообщил системную папку {csidl:#x}")
    return Path(buf.value)


SYSTEM_DIR = known_folder(0x25)                       # C:\Windows\System32
INSTALL_DIR = known_folder(0x26) / APP_NAME           # C:\Program Files\NIXYZ
SHORTCUTS = [known_folder(0x17) / f"{APP_TITLE}.lnk",   # «Пуск» для всех пользователей
             known_folder(0x19) / f"{APP_TITLE}.lnk"]   # общий рабочий стол


def tool(name):
    sub = ("WindowsPowerShell", "v1.0") if name == "powershell" else ()
    return str(SYSTEM_DIR.joinpath(*sub, name + ".exe"))


def run(args, env=None, timeout=60):
    p = subprocess.run([tool(args[0]), *args[1:]], capture_output=True, timeout=timeout,
                       creationflags=NO_WINDOW, cwd=SYSTEM_DIR, env=env)
    return p.returncode, (p.stdout + p.stderr).decode("oem", errors="replace")


def own_processes(exe):
    """PID процессов, запущенных ровно из этого файла, а не просто с таким же именем."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_wchar_p,
                                               ctypes.POINTER(ctypes.c_uint32)]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    _, out = run(["tasklist", "/FI", f"IMAGENAME eq {exe.name}", "/FO", "CSV", "/NH"])
    found = []
    for line in out.splitlines():
        parts = [x.strip('"') for x in line.split('","')]
        if len(parts) < 2 or not parts[1].isdigit():
            continue
        h = k32.OpenProcess(0x1000, False, int(parts[1]))
        if not h:
            continue
        buf, size = ctypes.create_unicode_buffer(1024), ctypes.c_uint32(1024)
        try:
            if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)) and \
                    os.path.normcase(buf.value) == os.path.normcase(str(exe)):
                found.append(int(parts[1]))
        finally:
            k32.CloseHandle(h)
    return found


def close_running_app():
    exe = INSTALL_DIR / EXE_NAME
    for pid in own_processes(exe):
        run(["taskkill", "/F", "/PID", str(pid)])  # его winws.exe закроется вместе с ним
    for _ in range(20):
        if not own_processes(exe):
            return
        time.sleep(0.25)


def rename_retry(src, dst):
    """Переименование папки: движок или антивирус могут отпустить файлы не сразу."""
    for attempt in range(20):
        try:
            return src.rename(dst)
        except OSError:
            if attempt == 19:
                raise
            time.sleep(0.25)


def place_program(source):
    """Копирует программу из source в Program Files. Прежняя версия заменяется целиком и только
    после того, как новая полностью легла рядом; при сбое возвращается на место."""
    new = INSTALL_DIR.with_name(APP_NAME + ".new")
    old = INSTALL_DIR.with_name(APP_NAME + ".old")
    keep = INSTALL_DIR / "data"  # настройки и движок — при обновлении сохраняем
    # прошлая установка оборвалась посередине: сначала вернуть рабочую копию и данные, и только потом чистить
    if not INSTALL_DIR.exists() and old.exists():
        old.rename(INSTALL_DIR)
    for leftover in (old / "data", new / "data"):
        if leftover.is_dir() and not keep.exists():
            INSTALL_DIR.mkdir(exist_ok=True)
            leftover.rename(keep)
    shutil.rmtree(new, ignore_errors=True)
    shutil.rmtree(old, ignore_errors=True)
    shutil.copytree(source, new, ignore=shutil.ignore_patterns("data"))
    if not (new / EXE_NAME).is_file():
        raise RuntimeError("В установщике нет NIXYZ.exe — файл повреждён или его изменил антивирус")
    if INSTALL_DIR.exists():
        rename_retry(INSTALL_DIR, old)
    try:
        rename_retry(new, INSTALL_DIR)
    except OSError:
        if old.exists() and not INSTALL_DIR.exists():
            old.rename(INSTALL_DIR)  # вернуть прежнюю версию
        raise
    if (old / "data").is_dir():
        try:
            rename_retry(old / "data", keep)
        except OSError as e:  # старая папка остаётся: следующий запуск установщика вернёт данные
            raise RuntimeError(f"Программа обновлена, но настройки остались в {old}. Запустите установку ещё раз.") from e
    shutil.rmtree(old, ignore_errors=True)


def make_shortcuts():
    exe = INSTALL_DIR / EXE_NAME
    script = ("$ErrorActionPreference = 'Stop'; $w = New-Object -ComObject WScript.Shell; "
              "foreach ($p in ($env:NIXYZ_LNK -split '\\|')) { $s = $w.CreateShortcut($p); "
              "$s.TargetPath = $env:NIXYZ_EXE; $s.WorkingDirectory = $env:NIXYZ_DIR; "
              "$s.IconLocation = $env:NIXYZ_EXE + ',0'; $s.Description = 'Настройка сетевых соединений'; $s.Save() }")
    env = dict(os.environ, NIXYZ_LNK="|".join(str(s) for s in SHORTCUTS), NIXYZ_EXE=str(exe),
               NIXYZ_DIR=str(INSTALL_DIR))
    code, out = run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-Command", script], env=env)
    if code != 0:
        raise RuntimeError(out.strip()[:200])


def register_uninstall(version):
    exe = INSTALL_DIR / EXE_NAME
    size_kb = sum(f.stat().st_size for f in INSTALL_DIR.rglob("*") if f.is_file()) // 1024
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, UNINSTALL_KEY, 0, winreg.KEY_WRITE) as k:
        for name, value in (("DisplayName", APP_TITLE), ("DisplayVersion", version),
                            ("Publisher", APP_TITLE), ("DisplayIcon", f'"{exe}",0'),
                            ("InstallLocation", str(INSTALL_DIR)),
                            ("UninstallString", f'"{exe}" --uninstall')):
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
        for name, value in (("NoModify", 1), ("NoRepair", 1), ("EstimatedSize", size_kb)):
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, value)


def install(source, version):
    """Возвращает список предупреждений (некритичных проблем)."""
    warnings = []
    close_running_app()
    place_program(source)
    try:
        make_shortcuts()
    except Exception as e:
        warnings.append(f"ярлыки не созданы ({e})")
    try:
        register_uninstall(version)
    except OSError as e:
        warnings.append(f"запись в «Приложениях» не создана ({e})")
    subprocess.Popen([str(INSTALL_DIR / EXE_NAME)], cwd=INSTALL_DIR)
    return warnings


def run_install(source, version, message):
    """Точка входа из NIXYZ.pyw. Запускать можно только из папки установщика, не из самой программы.
    Возвращает код выхода для установщика."""
    if Path(source).resolve() == INSTALL_DIR.resolve():
        message("Эта команда работает только из установщика NIXYZ.", True)
        return 1
    try:
        warnings = install(Path(source), version)
    except Exception as e:
        message(f"Установка не удалась:\n\n{e}", True)
        return 1
    if warnings:
        message("NIXYZ установлен, но:\n\n" + "\n".join(warnings), False)
    return 0
