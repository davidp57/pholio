from pathlib import Path
import sys, zlib
sys.path.insert(0, "src")
from pholio.layout import LayoutResult
from pholio.pdf_export import generate_pdf

# 3 pages, no images, with watermark
result = LayoutResult(placements=[], page_count=3)
pdf_bytes = generate_pdf(result, Path("."), page_w_mm=210.0, page_h_mm=297.0, watermark_text="FOOTER_TEST")

# Save for inspection
Path("debug_watermark.pdf").write_bytes(pdf_bytes)
print(f"PDF size: {len(pdf_bytes)} bytes")

# Find and decompress all content streams
wm = b"FOOTER_TEST"
found = 0
i = 0
while i < len(pdf_bytes) - 6:
    if pdf_bytes[i:i+1] == b"x" and pdf_bytes[i+1:i+2] in (b"\x9c", b"\xda", b"\x01"):
        for size in (512,1024,2048,4096,8192,16384,32768):
            try:
                d = zlib.decompress(pdf_bytes[i:i+size])
                if wm in d:
                    found += 1
                    print(f"  Found FOOTER_TEST in stream at offset {i}, stream size {len(d)}")
                    print(f"  Context: {d[max(0,d.index(wm)-30):d.index(wm)+50]}")
                break
            except Exception:
                pass
    i += 1

print(f"Total occurrences in streams: {found}")
