"""Сборка «NIXYZ Setup.exe» одной командой (из папки source):

    .build-venv\\Scripts\\python packaging\\build.py

1. значок из логотипа (make_icon.py);
2. программа NIXYZ.exe (PyInstaller, папкой — так она быстро стартует и не распаковывается
   во временную папку при каждом запуске);
3. установщик на Inno Setup (packaging/nixyz.iss) — один файл со всем внутри.
Готовый файл кладётся в корень репозитория, его SHA-256 — в README.md.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # source
REPO = ROOT.parent
WORK = HERE / "work"
DIST = HERE / "dist"
PY = sys.executable
# версия — одна на всё: берётся из NIXYZ.pyw
VERSION = re.search(r'^APP_VERSION = "([\d.]+)"', (ROOT / "NIXYZ.pyw").read_text(encoding="utf-8"), re.M).group(1)

VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({v}, 0), prodvers=({v}, 0), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('041904B0', [
    StringStruct('CompanyName', 'NIXYZ'),
    StringStruct('FileDescription', '{desc}'),
    StringStruct('FileVersion', '{dotted}'),
    StringStruct('InternalName', '{name}'),
    StringStruct('OriginalFilename', '{name}.exe'),
    StringStruct('ProductName', 'NIXYZ'),
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



LEGAL_DOCS = ("TERMS.md", "TERMS.en.md", "PRIVACY.md", "PRIVACY.en.md")
RUNTIME_PACKAGES = ("pywebview", "pythonnet", "clr_loader", "bottle", "proxy_tools", "cffi", "pycparser", "typing_extensions")


def write_licenses():
    """THIRD_PARTY_LICENSES.txt для собранной программы: тексты лицензий того, что входит в сборку."""
    import importlib.metadata as md
    out = []
    for name in RUNTIME_PACKAGES:
        d = md.distribution(name)
        texts = [Path(f.locate()).read_text(encoding="utf-8", errors="replace") for f in d.files or []
                 if ("licen" in str(f).lower() or "copying" in str(f).lower()) and Path(f.locate()).is_file()]
        out += [f"===== {name} {d.version} =====", *(texts or [str(d.metadata.get("License") or d.metadata.get("Classifier") or "")])]
    py_license = Path(sys.base_prefix) / "LICENSE.txt"
    if py_license.is_file():
        out += ["===== Python =====", py_license.read_text(encoding="utf-8", errors="replace")]
    path = WORK / "THIRD_PARTY_LICENSES.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(out), encoding="utf-8")
    return path


def rtf_license(*docs):
    """Текст для страницы согласия в установщике. RTF с кодами символов не зависит от кодировки системы."""
    def esc(text):
        return "".join(c if ord(c) < 128 and c not in "\\{}" else "\\" + c if ord(c) < 128 else f"\\u{ord(c)}?" for c in text)

    out = ["{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Segoe UI;}}\\f0\\fs18 "]
    for doc in docs:
        for line in (REPO / doc).read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                out.append("\\par\\b " + esc(line.lstrip("# ")) + "\\b0\\par ")
            elif line.startswith("- "):
                out.append("\\u8226? " + esc(line[2:]) + "\\par ")
            elif line.strip():
                out.append(esc(line) + "\\par ")
        out.append("\\par ")
    return "".join(out) + "}"


def find_iscc():
    """Компилятор Inno Setup: установка для всех или только для текущего пользователя."""
    bases = [os.environ.get("LOCALAPPDATA", "") + r"\Programs", os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")]
    for base in bases:
        for name in ("Inno Setup 7", "Inno Setup 6"):
            exe = Path(base) / name / "ISCC.exe"
            if base and exe.is_file():
                return exe
    sys.exit("Не найден Inno Setup (ISCC.exe). Установите его: winget install JRSoftware.InnoSetup.7")


def main():
    if "build-venv" not in PY.replace("\\", "/"):
        sys.exit("Запускайте из .build-venv: .build-venv\\Scripts\\python packaging\\build.py")
    for d in (WORK, DIST):
        shutil.rmtree(d, ignore_errors=True)
    WORK.mkdir(parents=True)
    icon = HERE / "nixyz.ico"
    subprocess.run([PY, str(HERE / "make_icon.py")], check=True)  # всегда свежий значок из логотипа

    print("1/2 NIXYZ.exe…")
    pyinstaller("--windowed", "--uac-admin", "--name", "NIXYZ", "--icon", str(icon),
                "--version-file", str(version_file("NIXYZ", "NIXYZ — настройка сетевых соединений")),
                "--add-data", f"{ROOT / 'ui' / 'index.html'};ui",   # поимённо: черновики из папки ui в сборку не идут
                "--add-data", f"{ROOT / 'ui' / 'app.js'};ui",
                "--add-data", f"{write_licenses()};.",   # BSD и MIT требуют отдавать тексты лицензий вместе с программой
                "--add-data", f"{ROOT.parent / 'THIRD_PARTY_NOTICES.md'};.",
                "--add-data", f"{ROOT.parent / 'LICENSE'};.",
                *(x for d in LEGAL_DOCS for x in ("--add-data", f"{ROOT.parent / d};legal")),
                "--add-data", f"{ROOT / 'NIXYZ.pyw'};source",  # исходный код — рядом с программой
                "--paths", str(HERE), "--hidden-import", "installer",  # установка: «NIXYZ.exe --install»
                "--exclude-module", "PyInstaller",
                "--exclude-module", "tkinter",  # сообщения — системные окна Windows, Tk программе не нужен
                # этого программа и pywebview не загружают: проверено по трассе модулей настоящего окна
                *(x for m in ("asyncio", "multiprocessing", "xml", "decimal", "unittest", "pydoc", "doctest", "pdb")
                  for x in ("--exclude-module", m)),
                str(ROOT / "NIXYZ.pyw"))
    app = DIST / "NIXYZ"
    if not (app / "NIXYZ.exe").is_file():
        sys.exit("NIXYZ.exe не собрался")

    print("2/2 установщик…")
    iscc = find_iscc()
    (WORK / "license.ru.rtf").write_text(rtf_license("TERMS.md", "PRIVACY.md"), encoding="ascii")
    (WORK / "license.en.rtf").write_text(rtf_license("TERMS.en.md", "PRIVACY.en.md"), encoding="ascii")
    subprocess.run([str(iscc), "/Q", f"/DAppVersion={VERSION}", f"/DIcon={icon}", f"/DDist={app}", f"/DOutDir={REPO}", f"/DLegal={WORK}",
                    str(HERE / "nixyz.iss")], check=True)
    out = REPO / "NIXYZ Setup.exe"
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
