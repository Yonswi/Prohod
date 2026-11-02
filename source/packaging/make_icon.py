"""Собирает packaging/prohod.ico из логотипа: Edge в фоне рисует SVG на холстах нужных
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

LOGO = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>
<defs>
<linearGradient id='lg' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#9584FF'/><stop offset='.5' stop-color='#6C72F5'/><stop offset='1' stop-color='#3FA8F5'/></linearGradient>
<linearGradient id='gl' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#fff' stop-opacity='.30'/><stop offset='.55' stop-color='#fff' stop-opacity='0'/></linearGradient>
</defs>
<path d='M32 0C50 0 58 0 61 3s3 11 3 29 0 26-3 29-11 3-29 3-26 0-29-3-3-11-3-29 0-26 3-29S14 0 32 0Z' fill='url(#lg)'/>
<path d='M32 0C50 0 58 0 61 3s3 11 3 29 0 26-3 29-11 3-29 3-26 0-29-3-3-11-3-29 0-26 3-29S14 0 32 0Z' fill='url(#gl)'/>
<path d='M21 47V31a11 11 0 0 1 22 0v16Z' fill='#fff' opacity='.18'/>
<path d='M21 47V31a11 11 0 0 1 22 0v16' fill='none' stroke='#fff' stroke-width='{stroke}' stroke-linecap='round'/>
<circle cx='32' cy='40' r='{dot}' fill='#fff'/>
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
    # на мелких размерах линии толще, чтобы значок читался
    svgs = [[s, LOGO.format(stroke=8.5 if s <= 24 else 7 if s <= 48 else 6.5, dot=5 if s <= 24 else 4.5)]
            for s in SIZES]
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
    (HERE / "prohod.ico").write_bytes(header + entries + blobs)
    (HERE / "prohod-256.png").write_bytes(pngs[256])
    print("prohod.ico:", len(header + entries + blobs), "байт,", len(SIZES), "размеров")


if __name__ == "__main__":
    main()
