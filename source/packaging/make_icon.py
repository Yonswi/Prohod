"""Собирает packaging/nixyz.ico и nixyz-256.png из логотипа: Edge в фоне рисует SVG на холстах нужных
размеров и отдаёт PNG, а здесь они упаковываются в .ico. Без сторонних библиотек."""
import base64
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]

# знак владельца из «Звезда.svg»: та же форма и тот же ночной фон, что и у логотипа в окне программы
MARK = "M5.66451 11.2258C5.59875 9.90566 5.37991 9.07512 4.94735 8.50076C4.47062 7.8679 3.25155 7.78469 1.39239 8.25921C1.05333 8.34544 0.61256 8.47151 0.412208 8.53908C0.21237 8.60666 0.0274302 8.66112 0.00123037 8.66061C-0.0244558 8.66011 0.355186 8.45537 0.845277 8.20576C3.0137 7.09989 4.39664 6.20985 5.09428 5.47059C5.36141 5.18719 5.49806 4.9754 5.78164 4.40557C6.2106 3.54377 6.46129 2.86502 6.88203 1.42533L6.95549 1.17319L6.96115 1.76117C6.97347 3.15447 7.37983 3.99862 8.15915 4.25278C8.69701 4.42826 9.30732 4.32438 12.1806 3.56596C15.4674 2.69861 18.1675 1.977 19.9378 1.49239C20.2486 1.40768 20.6996 1.28514 20.9395 1.22059C21.1794 1.15655 21.5498 1.0562 21.7615 0.997703C21.9731 0.939208 22.528 0.787927 22.9944 0.66085C23.4609 0.533774 24.2001 0.330553 24.6378 0.209023C25.825 -0.120266 25.7762 -0.0617701 24.4842 0.393587C23.242 0.831295 19.2571 2.32343 17.5233 2.99966C13.7793 4.46054 10.4539 5.92746 8.99549 6.76102C8.15093 7.24411 7.28479 7.98489 6.86508 8.58396C6.42328 9.2143 5.99535 10.4185 5.74465 11.7377C5.70869 11.9263 5.69533 11.8395 5.66451 11.2258Z"
LOGO = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>
<defs><linearGradient id='lg' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#2A2F6E'/><stop offset='.55' stop-color='#11143A'/><stop offset='1' stop-color='#07081C'/></linearGradient></defs>
<path d='M32 0C50 0 58 0 61 3s3 11 3 29 0 26-3 29-11 3-29 3-26 0-29-3-3-11-3-29 0-26 3-29S14 0 32 0Z' fill='url(#lg)'/>
<path d='M32 .5C50 .5 57.8.5 60.6 3.4s2.9 10.6 2.9 28.6-.1 25.8-2.9 28.6S50 63.5 32 63.5 6.2 63.5 3.4 60.6.5 50 .5 32 .5 6.2 3.4 3.4 14 .5 32 .5Z' fill='none' stroke='#fff' stroke-opacity='.14'/>
<path transform='translate(32 32) scale({scale}) translate(-12.9 -5.95)' d='{mark}' fill='#fff' stroke='#fff' stroke-width='{stroke}' stroke-linejoin='round'/>
</svg>"""

PAGE = """<!doctype html><meta charset=utf-8><body><script>
const svgs = %s;
(async () => {
  const out = [];
  for (const [size, svg] of svgs) {
    const img = new Image();
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    await img.decode();
    const c = document.createElement("canvas"); c.width = c.height = size;
    const g = c.getContext("2d"); g.imageSmoothingQuality = "high";
    g.drawImage(img, 0, 0, size, size);
    out.push(size + ":" + c.toDataURL("image/png").split(",")[1]);
  }
  const pre = document.createElement("pre"); pre.id = "out"; pre.textContent = out.join("\\n");
  document.body.append(pre);
})();
</script>"""


def find_edge():
    for root in (r"C:\Program Files (x86)", r"C:\Program Files"):
        p = Path(root) / "Microsoft/Edge/Application/msedge.exe"
        if p.is_file():
            return p
    sys.exit("Не найден Microsoft Edge")


def main():
    import json
    # на мелких размерах знак крупнее и чуть толще, иначе в трее от тонких лучей ничего не останется
    def sized(size):
        scale, stroke = (2.25, .55) if size <= 24 else (2.1, .28) if size <= 48 else (1.96, 0)
        return LOGO.format(mark=MARK, scale=scale, stroke=stroke)
    svgs = [[s, sized(s)] for s in SIZES]
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "icon.html"
        page.write_text(PAGE % json.dumps(svgs), encoding="utf-8")
        dom = subprocess.run([str(find_edge()), "--headless=new", "--disable-gpu", "--no-first-run",
                              f"--user-data-dir={tmp}\\profile", "--virtual-time-budget=5000", "--dump-dom",
                              page.as_uri()], capture_output=True, text=True, encoding="utf-8").stdout
    pngs = {int(sz): base64.b64decode(b64) for sz, b64 in re.findall(r"(\d+):([A-Za-z0-9+/=]+)", dom)}
    if sorted(pngs) != SIZES:
        sys.exit(f"Edge отрисовал не все размеры: {sorted(pngs)}")
    # ICO: заголовок, каталог, затем PNG-картинки подряд
    header = struct.pack("<HHH", 0, 1, len(SIZES))
    offset = 6 + 16 * len(SIZES)
    entries, blobs = b"", b""
    for sz in SIZES:
        data = pngs[sz]
        entries += struct.pack("<BBBBHHII", sz % 256, sz % 256, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    (HERE / "nixyz.ico").write_bytes(header + entries + blobs)
    (HERE / "nixyz-256.png").write_bytes(pngs[256])
    print("nixyz.ico:", len(header + entries + blobs), "байт,", len(SIZES), "размеров")


if __name__ == "__main__":
    main()
