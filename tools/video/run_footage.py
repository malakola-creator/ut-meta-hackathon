"""Render the footage on the GPU machine and bring it back: copies the recording, the shots and tools/video/blender_footage.py to the
machine named in config.local.json (blender.host, blender.live_dir), runs Blender there in the background, waits, and fetches
ut-meta-video/footage/<shot>.mp4 and <shot>.json.

    python tools/video/run_footage.py --scenes ut-meta-video/footage/scene_long.jsonl.gz [--shots tools/video/shots.json]
                                      [--size 1920x1080] [--fps 24] [--samples 16] [--only NAME] [--frames N] [--fetch-only]

Everything about the machine comes from config.local.json (never committed): blender.host, blender.exe, blender.live_dir (the live
script and the cat models live there). The render log is footage/render.log on that machine and ut-meta-video/footage/render.log here.
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from utmeta import config

ap = argparse.ArgumentParser()
ap.add_argument("--scenes", default="ut-meta-video/footage/scene_long.jsonl.gz")
ap.add_argument("--shots", default=os.path.join(HERE, "shots.json"))
ap.add_argument("--size", default="1920x1080")
ap.add_argument("--fps", default="24")
ap.add_argument("--samples", default="16")
ap.add_argument("--only", default=None)
ap.add_argument("--frames", default=None)
ap.add_argument("--hide", default="vhum", help="bodies kept out of every clip (comma-separated agent keys); '' for none")
ap.add_argument("--engine", default="eevee", help="eevee (fast) or cycles (path traced, denoised: prettier, several times slower)")
ap.add_argument("--tag", default="", help="a name for this run: its own render_<tag>.log and out_<tag>/ on the machine, so two runs may overlap")
ap.add_argument("--fetch-only", action="store_true")
a = ap.parse_args()
b = config.load().get("blender") or {}
host, exe, live_dir = b["host"], b["exe"], b["live_dir"].rstrip("/")
work = live_dir + "/footage"
out_dir = work + ("/out_%s" % a.tag if a.tag else "/out")
log = work + ("/render_%s.log" % a.tag if a.tag else "/render.log")
shots_remote = work + ("/shots_%s.json" % a.tag if a.tag else "/shots.json")
local = os.path.join(ROOT, "ut-meta-video", "footage")
os.makedirs(local, exist_ok=True)


def ps(command, timeout=120):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, 'powershell -NoProfile -Command "%s"' % command], capture_output=True, text=True, timeout=timeout)


if not a.fetch_only:
    ps("New-Item -ItemType Directory -Force -Path '%s' | Out-Null" % out_dir)
    scenes_remote = work + "/" + os.path.basename(a.scenes)
    subprocess.run(["scp", "-q", os.path.join(HERE, "blender_footage.py"), a.scenes, "%s:%s/" % (host, work)], check=True)
    subprocess.run(["scp", "-q", a.shots, "%s:%s" % (host, shots_remote)], check=True)
    extra = "".join(" --only %s" % o for o in a.only.split(",")) if a.only else ""
    extra += " --frames %s" % a.frames if a.frames else ""
    extra += " --hide %s" % a.hide if a.hide else ""
    extra += " --engine %s" % a.engine
    # the render command as a script file on the machine (no quoting through two shells), started detached with -File
    script = "cd '%s'\n& '%s' -b -P blender_footage.py -- --live '%s/siamese/ultimatetruth_live.py' --scenes '%s' --shots '%s' --out '%s' --size %s --fps %s --samples %s%s 2>&1 | Out-File -FilePath '%s' -Encoding utf8\n" % (
        work, exe, live_dir, scenes_remote, shots_remote, out_dir, a.size, a.fps, a.samples, extra, log)
    ps1_local = os.path.join(local, "render_%s.ps1" % (a.tag or "run"))
    open(ps1_local, "w", encoding="utf-8").write(script)
    ps1_remote = work + "/render_%s.ps1" % (a.tag or "run")
    subprocess.run(["scp", "-q", ps1_local, "%s:%s" % (host, ps1_remote)], check=True)
    # run it inside this ssh session (a detached Start-Process from an ssh session never came up); this script stays up until it ends
    proc = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=30", host,
                             "powershell -NoProfile -ExecutionPolicy Bypass -File '%s'" % ps1_remote], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(25)
    r = ps("tasklist /FI 'IMAGENAME eq blender.exe' | Out-String")
    if "blender.exe" not in r.stdout:
        raise SystemExit("Blender did not start on the machine; its log: %s" % log)
    print("render started on %s → %s (log: %s)" % (host.split("@")[-1][:3] + "…", out_dir, log), flush=True)
    t0 = time.time()
    while True:
        time.sleep(60)
        r = ps("if (Test-Path '%s') { Get-Content '%s' -Tail 400 | Out-String -Width 220 }" % (log, log))
        lines = [l for l in r.stdout.splitlines() if l.strip() and (l.startswith("shot ") or l.strip() == "done" or "Traceback" in l or l.startswith("Fra:"))]
        lines = [l for l in lines if not l.startswith("Fra:")] + [l for l in lines if l.startswith("Fra:")][-1:]
        print("  %4.0f min: %s" % ((time.time() - t0) / 60, lines[-1][:140] if lines else "(rendering)"), flush=True)
        if any(l.strip() == "done" for l in lines) or any("Traceback" in l for l in lines):
            break
        if proc.poll() is not None:                                    # the session ended: whatever Blender wrote is what there is
            print("  the render session ended (code %s)" % proc.returncode, flush=True)
            break
subprocess.run(["scp", "-q", "%s:%s" % (host, log), local], check=False)
r = subprocess.run(["scp", "-q", "%s:%s/*.mp4" % (host, out_dir), local], capture_output=True, text=True)
subprocess.run(["scp", "-q", "%s:%s/*.json" % (host, out_dir), local], capture_output=True, text=True)
print("fetched:", sorted(p for p in os.listdir(local) if p.endswith((".mp4", ".json"))))
