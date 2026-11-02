"""Сборка «Prohod Setup.exe» одной командой (из папки source):

    .build-venv\\Scripts\\python packaging\\build.py

1. значок из логотипа (make_icon.py);
2. программа Prohod.exe (PyInstaller, папкой — так она быстро стартует и не распаковывается
   во временную папку при каждом запуске);
3. папка программы упаковывается в payload.zip;
4. установщик — один файл со всем внутри.
Готовый файл кладётся в корень репозитория, его SHA-256 — в README.md.
"""
import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # source
REPO = ROOT.parent
WORK = HERE / "work"
DIST = HERE / "dist"
PY = sys.executable
# версия — одна на всё: берётся из Prohod.pyw
VERSION = re.search(r'^APP_VERSION = "([\d.]+)"', (ROOT / "Prohod.pyw").read_text(encoding="utf-8"), re.M).group(1)

VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({v}, 0), prodvers=({v}, 0), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('041904B0', [
    StringStruct('CompanyName', 'Prohod'),
    StringStruct('FileDescription', '{desc}'),
    StringStruct('FileVersion', '{dotted}'),
    StringStruct('InternalName', '{name}'),
    StringStruct('OriginalFilename', '{name}.exe'),
    StringStruct('ProductName', 'Prohod'),
    StringStruct('ProductVersion', '{dotted}')])]),
  VarFileInfo([VarStruct('Translation', [0x0419, 1200])])])
"""


def version_file(name, desc):
    nums = ", ".join(VERSION.split("."))
    f = WORK / f"version_{name}.txt"
    f.write_text(VERSION_INFO.format(v=nums, dotted=VERSION, name=name, desc=desc), encoding="utf-8")
    return f


def pyinstaller(*args):
    subprocess.run([PY, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
                    "--workpath", str(WORK / "pyi"), "--specpath", str(WORK), "--distpath", str(DIST), *args],
                   check=True, cwd=ROOT)


def main():
    if "build-venv" not in PY.replace("\\", "/"):
        sys.exit("Запускайте из .build-venv: .build-venv\\Scripts\\python packaging\\build.py")
    for d in (WORK, DIST):
        shutil.rmtree(d, ignore_errors=True)
    WORK.mkdir(parents=True)
    icon = HERE / "prohod.ico"
    subprocess.run([PY, str(HERE / "make_icon.py")], check=True)  # всегда свежий значок из логотипа

    print("1/3 Prohod.exe…")
    pyinstaller("--windowed", "--uac-admin", "--name", "Prohod", "--icon", str(icon),
                "--version-file", str(version_file("Prohod", "Prohod — обход блокировок YouTube и Discord")),
                "--add-data", f"{ROOT / 'ui'};ui",
                "--add-data", f"{ROOT / 'Prohod.pyw'};source",  # исходный код — рядом с программой
                "--exclude-module", "PyInstaller",
                "--exclude-module", "tkinter",  # сообщения — системные окна Windows, Tk программе не нужен
                str(ROOT / "Prohod.pyw"))
    app = DIST / "Prohod"
    if not (app / "Prohod.exe").is_file():
        sys.exit("Prohod.exe не собрался")

    print("2/3 payload.zip…")
    payload = WORK / "payload.zip"
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in sorted(app.rglob("*")):
            if f.is_file():
                zf.write(f, f.relative_to(app))

    print("3/3 установщик…")
    # контрольная сумма программы и версия впаиваются в установщик: он сверит их перед установкой
    payload_sha = hashlib.sha256(payload.read_bytes()).hexdigest()
    src = (HERE / "installer.py").read_text(encoding="utf-8")
    src = src.replace('"__PAYLOAD_SHA256__"', f'"{payload_sha}"').replace('"__VERSION__"', f'"{VERSION}"')
    installer = WORK / "installer.py"
    installer.write_text(src, encoding="utf-8")
    pyinstaller("--onefile", "--windowed", "--uac-admin", "--name", "Prohod-Setup", "--icon", str(icon),
                "--version-file", str(version_file("Prohod-Setup", "Установка программы Prohod")),
                "--add-data", f"{payload};.", "--add-data", f"{icon};.",
                str(installer))
    out = REPO / "Prohod Setup.exe"
    shutil.copy2(DIST / "Prohod-Setup.exe", out)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    readme = REPO / "README.md"
    text, n = re.subn(r"(SHA-256 установщика: `)[0-9a-f]*(`)", lambda m: m[1] + digest + m[2],
                      readme.read_text(encoding="utf-8"))
    if n:
        readme.write_text(text, encoding="utf-8")
    for d in (WORK, DIST):  # промежуточные файлы сборки больше не нужны
        shutil.rmtree(d, ignore_errors=True)
    print(f"Готово: {out} ({out.stat().st_size / 2**20:.1f} МБ)\nSHA-256: {digest}")


if __name__ == "__main__":
    main()
