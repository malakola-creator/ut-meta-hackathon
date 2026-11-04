"""The overlays as transparent PNG frames: tools/video/overlay.html drawn at every frame time by headless Chromium (Playwright),
from ut-meta-video/build/data.json (tools/video/prepare_data.py).

    python tools/video/render_overlays.py [--fps 24] [--from 0 --to 180] [--out ut-meta-video/build/overlay]
    python tools/video/render_overlays.py --sample 7,20,31,45,65,95,120,150,175 --out ut-meta-video/build/preview   # single frames to look at

Frames are named ov_<n>.png with n = round(t * fps) + 1, so ffmpeg reads them as a sequence (tools/video/build.py).
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

ap = argparse.ArgumentParser()
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--from", dest="t0", type=float, default=0.0)
ap.add_argument("--to", dest="t1", type=float, default=180.0)
ap.add_argument("--out", default=os.path.join(ROOT, "ut-meta-video", "build", "overlay"))
ap.add_argument("--sample", default=None, help="comma-separated seconds: render only these, named sample_<t>.png")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
data = json.load(open(os.path.join(ROOT, "ut-meta-video", "build", "data.json"), encoding="utf-8"))

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--allow-file-access-from-files"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page.goto("file://" + os.path.join(HERE, "overlay.html"))
    page.evaluate("d => UT.setup(d)", data)
    page.wait_for_timeout(300)
    t_start = time.time()
    if a.sample:
        for t in (float(x) for x in a.sample.split(",")):
            page.evaluate("t => UT.render(t)", t)
            page.wait_for_timeout(60)                                  # let the images in
            page.screenshot(path=os.path.join(a.out, "sample_%05.1f.png" % t), omit_background=True)
        print("samples →", a.out)
    else:
        n0, n1 = int(round(a.t0 * a.fps)), int(round(a.t1 * a.fps))
        for n in range(n0, n1):
            t = n / a.fps
            page.evaluate("t => UT.render(t)", t)
            if n in (n0, n0 + 1):
                page.wait_for_timeout(200)
            page.screenshot(path=os.path.join(a.out, "ov_%05d.png" % (n + 1)), omit_background=True)
            if (n - n0) % (10 * a.fps) == 0 and n > n0:
                print("  %5.1f s rendered (%.0f ms/frame)" % (t, 1000 * (time.time() - t_start) / (n - n0)), flush=True)
        print("overlay frames %d–%d → %s in %.0f s" % (n0 + 1, n1, a.out, time.time() - t_start))
    browser.close()
