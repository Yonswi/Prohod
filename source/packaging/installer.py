"""Установщик Prohod — один файл, всё сам.

Запуск (Windows спросит права администратора один раз):
  1. сверяет SHA-256 вложенной программы (впаян при сборке) — в памяти, без временных файлов;
  2. закрывает уже запущенный Prohod (только сам Prohod.exe из Program Files);
  3. ставит программу в C:\\Program Files\\Prohod; настройки и движок (папка data) при
     обновлении переносятся в новую версию;
  4. создаёт ярлыки «Prohod» в «Пуске» и на рабочем столе и запись в «Параметры → Приложения»;
  5. запускает Prohod — дальше он сам скачает движок, подберёт стратегию и включит обход.
"""
import ctypes
import hashlib
import io
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import winreg
import zipfile
from pathlib import Path

APP_NAME = "Prohod"
APP_TITLE = "Prohod"
APP_VERSION = "__VERSION__"          # подставляет build.py
PAYLOAD_SHA256 = "__PAYLOAD_SHA256__"  # подставляет build.py
EXE_NAME = "Prohod.exe"
UNINSTALL_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
NO_WINDOW = subprocess.CREATE_NO_WINDOW
MAX_UNPACKED = 512 * 1024 * 1024


def known_folder(csidl):
    buf = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) != 0:
        raise OSError(f"Windows не сообщил системную папку {csidl:#x}")
    return Path(buf.value)


SYSTEM_DIR = known_folder(0x25)                       # C:\Windows\System32
INSTALL_DIR = known_folder(0x26) / APP_NAME           # C:\Program Files\Prohod
SHORTCUTS = [known_folder(0x17) / f"{APP_TITLE}.lnk",   # «Пуск» для всех пользователей
             known_folder(0x19) / f"{APP_TITLE}.lnk"]   # общий рабочий стол
PAYLOAD = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "payload.zip"


def sanitize_environment():
    """Переменные, которые чужая программа может прописать пользователю, чтобы влезть
    в процесс администратора (.NET-профилировщики, свои модули PowerShell и т.п.)."""
    for key in list(os.environ):
        if key.upper().startswith(("COR_", "COMPLUS_", "DOTNET_", "CORECLR_", "WEBVIEW2_")):
            del os.environ[key]
    os.environ["PSModulePath"] = str(SYSTEM_DIR / "WindowsPowerShell" / "v1.0" / "Modules")


def tool(name):
    sub = ("WindowsPowerShell", "v1.0") if name == "powershell" else ()
    return str(SYSTEM_DIR.joinpath(*sub, name + ".exe"))


def run(args, env=None, timeout=60):
    p = subprocess.run([tool(args[0]), *args[1:]], capture_output=True, timeout=timeout,
                       creationflags=NO_WINDOW, cwd=SYSTEM_DIR, env=env)
    return p.returncode, (p.stdout + p.stderr).decode("oem", errors="replace")


def already_installed():
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, UNINSTALL_KEY))
        return True
    except OSError:
        return False


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


def verified_payload():
    """Программа внутри установщика читается целиком в память и сверяется с суммой,
    впаянной при сборке. Распаковка идёт из тех же байт — подменить файл между
    проверкой и распаковкой нельзя."""
    data = PAYLOAD.read_bytes()
    if not PAYLOAD_SHA256.isalnum() or len(PAYLOAD_SHA256) != 64:
        raise RuntimeError("Установщик собран без контрольной суммы")
    if hashlib.sha256(data).hexdigest() != PAYLOAD_SHA256:
        raise RuntimeError("Содержимое установщика повреждено или подменено — установка отменена")
    return data


def safe_extract(data, dest):
    dest = dest.resolve()
    written = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if target != dest and dest not in target.parents:
                raise RuntimeError(f"Опасный путь в архиве: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                while chunk := src.read(1 << 20):
                    written += len(chunk)
                    if written > MAX_UNPACKED:
                        raise RuntimeError("Архив программы слишком большой")
                    out.write(chunk)


def place_program(data):
    new = INSTALL_DIR.with_name(APP_NAME + ".new")
    old = INSTALL_DIR.with_name(APP_NAME + ".old")
    if not INSTALL_DIR.exists() and old.exists():
        old.rename(INSTALL_DIR)  # прошлая установка оборвалась посередине — вернуть рабочую копию
    shutil.rmtree(new, ignore_errors=True)
    if INSTALL_DIR.exists():
        shutil.rmtree(old, ignore_errors=True)
    safe_extract(data, new)
    if not (new / EXE_NAME).is_file():
        raise RuntimeError("В установщике нет Prohod.exe — файл повреждён или его изменил антивирус")
    keep = INSTALL_DIR / "data"  # настройки, движок, подобранная стратегия — при обновлении сохраняем
    if keep.is_dir():
        shutil.move(str(keep), str(new / "data"))
    if INSTALL_DIR.exists():
        INSTALL_DIR.rename(old)
    try:
        new.rename(INSTALL_DIR)
    except OSError:
        if old.exists() and not INSTALL_DIR.exists():
            old.rename(INSTALL_DIR)  # вернуть прежнюю версию
        if (new / "data").is_dir() and not keep.exists():
            shutil.move(str(new / "data"), str(keep))  # и её настройки
        raise
    shutil.rmtree(old, ignore_errors=True)


def make_shortcuts():
    for lnk in SHORTCUTS:  # ярлыки версии 1.1.0 назывались «Проход.lnk» — убираем, чтобы не было двух
        try:
            lnk.with_name("Проход.lnk").unlink()
        except OSError:
            pass
    exe = INSTALL_DIR / EXE_NAME
    script = ("$ErrorActionPreference = 'Stop'; $w = New-Object -ComObject WScript.Shell; "
              "foreach ($p in ($env:PROHOD_LNK -split '\\|')) { $s = $w.CreateShortcut($p); "
              "$s.TargetPath = $env:PROHOD_EXE; $s.WorkingDirectory = $env:PROHOD_DIR; "
              "$s.IconLocation = $env:PROHOD_EXE + ',0'; $s.Description = 'Обход блокировок YouTube и Discord'; $s.Save() }")
    env = dict(os.environ, PROHOD_LNK="|".join(str(s) for s in SHORTCUTS), PROHOD_EXE=str(exe),
               PROHOD_DIR=str(INSTALL_DIR))
    code, out = run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-Command", script], env=env)
    if code != 0:
        raise RuntimeError(out.strip()[:200])


def register_uninstall():
    exe = INSTALL_DIR / EXE_NAME
    size_kb = sum(f.stat().st_size for f in INSTALL_DIR.rglob("*") if f.is_file()) // 1024
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, UNINSTALL_KEY, 0, winreg.KEY_WRITE) as k:
        for name, value in (("DisplayName", APP_TITLE), ("DisplayVersion", APP_VERSION),
                            ("Publisher", APP_TITLE), ("DisplayIcon", f'"{exe}",0'),
                            ("InstallLocation", str(INSTALL_DIR)),
                            ("UninstallString", f'"{exe}" --uninstall')):
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
        for name, value in (("NoModify", 1), ("NoRepair", 1), ("EstimatedSize", size_kb)):
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, value)


def install(report):
    """Возвращает список предупреждений (некритичных проблем)."""
    warnings = []
    report("Проверяю целостность…")
    data = verified_payload()
    report("Закрываю прежнюю версию…" if already_installed() else "Готовлю установку…")
    close_running_app()
    report("Копирую программу в Program Files…")
    place_program(data)
    report("Создаю ярлыки…")
    try:
        make_shortcuts()
    except Exception as e:
        warnings.append(f"ярлыки не созданы ({e})")
    try:
        register_uninstall()
    except OSError as e:
        warnings.append(f"запись в «Приложениях» не создана ({e})")
    report("Запускаю Prohod…")
    subprocess.Popen([str(INSTALL_DIR / EXE_NAME)], cwd=INSTALL_DIR)
    return warnings


def main():
    sanitize_environment()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    root = tk.Tk()
    root.title(f"{APP_TITLE} — установка")
    root.configure(bg="#0B0B0F")
    root.resizable(False, False)
    scale = root.winfo_fpixels("1i") / 96
    w, h = int(380 * scale), int(150 * scale)
    root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 2}")
    try:
        root.iconbitmap(str(Path(getattr(sys, "_MEIPASS", ".")) / "prohod.ico"))
    except tk.TclError:
        pass
    tk.Label(root, text=APP_TITLE, fg="#F5F5F7", bg="#0B0B0F",
             font=("Segoe UI Variable Display", 18, "bold")).pack(pady=(int(22 * scale), 4))
    status = tk.Label(root, text="Подготовка…", fg="#A1A1AA", bg="#0B0B0F", font=("Segoe UI", 10))
    status.pack()
    result = {}

    def report(text):
        root.after(0, lambda: status.configure(text=text))

    def work():
        try:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                raise RuntimeError("Нужны права администратора — запустите установщик ещё раз и нажмите «Да».")
            result["warnings"] = install(report)
        except Exception as e:
            result["error"] = str(e)
        root.after(0, finish)

    def finish():
        from tkinter import messagebox
        if "error" in result:
            messagebox.showerror(f"{APP_TITLE} — установка", f"Установка не удалась:\n\n{result['error']}")
            root.destroy()
            return
        if result.get("warnings"):
            messagebox.showwarning(f"{APP_TITLE} — установка",
                                   "Prohod установлен, но:\n\n" + "\n".join(result["warnings"]))
        report("Готово")
        root.after(900, root.destroy)

    threading.Thread(target=work, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    main()
