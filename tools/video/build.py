"""Compose the demo: background footage per shot + the overlay frames + the voice-over + the stamp sounds → one H.264 file.

    python tools/video/build.py [--out ut-meta-video/out/demo_1080p.mp4] [--overlay ut-meta-video/build/overlay] [--draft]

The timeline is tools/video/timeline.json: one entry per span of seconds, each a clip (ut-meta-video/footage/<name>.mp4 from
tools/video/run_footage.py, with an offset into it) or a still (zoomed slowly), or black. A clip that is not there yet falls back to
the still named beside it, so the cut can be built before the GPU machine is done. --draft builds at 960x540 for a quick look.
Sounds: the voice lines from ut-meta-video/voice/<id>.wav at their narration.json start; a soft "ding" on each green stamp and a low
"buzz" on each red one, at the seconds listed under "sfx" in the timeline (synthesised with ffmpeg, no files to credit).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
V = os.path.join(ROOT, "ut-meta-video")

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(V, "out", "demo_1080p.mp4"))
ap.add_argument("--overlay", default=os.path.join(V, "build", "overlay"))
ap.add_argument("--timeline", default=os.path.join(HERE, "timeline.json"))
ap.add_argument("--draft", action="store_true")
ap.add_argument("--no-overlay", action="store_true")
ap.add_argument("--split", action="store_true", help="also cut the result into one file per shot (D1…D8) beside it, under shots/")
a = ap.parse_args()
tl = json.load(open(a.timeline, encoding="utf-8"))
fps, W, H = tl["fps"], (960 if a.draft else 1920), (540 if a.draft else 1080)
os.makedirs(os.path.dirname(a.out), exist_ok=True)
build = os.path.join(V, "build")
os.makedirs(build, exist_ok=True)


def have(path):
    return path and os.path.exists(path) and os.path.getsize(path) > 0


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2500:], file=sys.stderr)
        raise SystemExit("ffmpeg failed: " + " ".join(cmd[:6]))


# 1. the background: one file per span, all the same size and rate, then concatenated
parts = []
for i, sp in enumerate(tl["spans"]):
    dur = float(sp["to"]) - float(sp["from"])
    out = os.path.join(build, "bg_%02d.mp4" % i)
    clip = os.path.join(V, "footage", sp["clip"] + ".mp4") if sp.get("clip") else None
    still = os.path.join(ROOT, sp["still"]) if sp.get("still") else None
    if have(clip):
        off = float(sp.get("offset", 0))
        vf = "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=%d,format=yuv420p" % (W, H, W, H, fps)
        run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % off, "-t", "%.3f" % dur, "-i", clip, "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", out])
        src = "clip %s @%.1f" % (sp["clip"], off)
    elif have(still):
        z = float(sp.get("zoom", 1.08))
        n = int(round(dur * fps))
        # a slow push-in on a still (zoompan works on a stream of frames; the still is read once per output frame)
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d," % (W * 2, H * 2, W * 2, H * 2) +
              "zoompan=z='1+(%f-1)*on/%d':d=%d:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=%dx%d:fps=%d,format=yuv420p" % (z, n, n, W, H, fps))
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", still, "-t", "%.3f" % dur, "-vf", vf, "-r", str(fps), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", out])
        src = "still %s" % sp["still"]
    else:
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=%s:s=%dx%d:r=%d" % (sp.get("color", "black"), W, H, fps), "-t", "%.3f" % dur, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out])
        src = "colour %s (no clip %s / still)" % (sp.get("color", "black"), sp.get("clip"))
    print("  span %5.1f–%5.1f  %s" % (sp["from"], sp["to"], src), flush=True)
    parts.append(out)
lst = os.path.join(build, "bg.txt")
open(lst, "w").write("".join("file '%s'\n" % p for p in parts))
bg = os.path.join(build, "bg.mp4")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", bg])

# 2. the sound: the voice lines at their starts, a small set of synthesised sounds at the overlay's moments, a quiet room tone
SFX = {   # kind -> (lavfi source, gain): nothing recorded, nothing to credit
    "ding":    ("sine=frequency=1320:duration=0.5,volume='0.9*exp(-6*t)':eval=frame,aformat=channel_layouts=stereo", 0.30),
    "chime":   ("aevalsrc='0.5*sin(2*PI*1320*t)+0.35*sin(2*PI*1980*t)+0.2*sin(2*PI*2640*t)':d=0.9:s=48000,volume='exp(-4*t)':eval=frame,aformat=channel_layouts=stereo", 0.28),
    "buzz":    ("aevalsrc='0.6*sin(2*PI*110*t)+0.3*sin(2*PI*220*t)+0.1*sin(2*PI*330*t)':d=0.45:s=48000,volume='if(lt(t,0.05),t*20,exp(-5*(t-0.05)))':eval=frame,aformat=channel_layouts=stereo", 0.45),
    "pop":     ("sine=frequency=700:duration=0.12,volume='exp(-30*t)':eval=frame,aformat=channel_layouts=stereo", 0.30),
    "tick":    ("sine=frequency=2200:duration=0.05,volume='exp(-60*t)':eval=frame,aformat=channel_layouts=stereo", 0.12),
    "whoosh":  ("anoisesrc=color=pink:duration=0.6:sample_rate=48000,bandpass=f=900:width_type=o:w=2,volume='sin(PI*t/0.6)':eval=frame,aformat=channel_layouts=stereo", 0.18),
    "shutter": ("anoisesrc=color=white:duration=0.09:sample_rate=48000,highpass=f=2500,volume='exp(-40*t)':eval=frame,aformat=channel_layouts=stereo", 0.22),
    "count":   ("sine=frequency=1600:duration=0.03,volume='exp(-80*t)':eval=frame,aformat=channel_layouts=stereo", 0.10),
}
sfx_dir = os.path.join(build, "sfx")
os.makedirs(sfx_dir, exist_ok=True)
for kind, (src, gain) in SFX.items():
    wav = os.path.join(sfx_dir, kind + ".wav")
    if not have(wav):
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-ar", "48000", "-ac", "2", wav])
FILES = {"meow": 0.9}                                                 # recorded sounds in ut-meta-video/sfx/<kind>.wav (credits in sfx/CREDITS.txt)
for kind, gain in FILES.items():
    wav = os.path.join(V, "sfx", kind + ".wav")
    if have(wav):
        SFX[kind] = (None, gain)
        shutil.copyfile(wav, os.path.join(sfx_dir, kind + ".wav"))
nar = json.load(open(os.path.join(HERE, "narration.json"), encoding="utf-8"))
starts = {l["id"]: float(l["start"]) for l in nar["lines"]}
total = float(tl["spans"][-1]["to"])
inputs, filters, labels = [], [], []
k = 0
for line in nar["lines"]:
    wav = os.path.join(V, "voice", line["id"] + ".wav")
    if not have(wav):
        continue
    inputs += ["-i", wav]
    filters.append("[%d:a]adelay=%d|%d,volume=1.0[v%d]" % (k, int(line["start"] * 1000), int(line["start"] * 1000), k))
    labels.append("[v%d]" % k)
    k += 1
events = []
for e in tl.get("sfx", []):
    t0 = (starts[e["shot"]] + float(e["at"])) if "shot" in e else float(e["t"])
    n, every = int(e.get("repeat", 1)), float(e.get("every", 0.1))
    for j in range(n):
        events.append((t0 + j * every, e["kind"], float(e.get("gain", 1.0))))
for j, (t, kind, g) in enumerate(events):
    if kind not in SFX or t < 0 or t > total:
        continue
    inputs += ["-i", os.path.join(sfx_dir, kind + ".wav")]
    filters.append("[%d:a]adelay=%d|%d,volume=%.3f[s%d]" % (k, int(t * 1000), int(t * 1000), SFX[kind][1] * g, j))
    labels.append("[s%d]" % j)
    k += 1
bed = tl.get("bed")
if bed:                                                               # a quiet room tone under everything, in and out softly
    inputs += ["-f", "lavfi", "-t", "%.3f" % total, "-i", "anoisesrc=color=brown:sample_rate=48000,lowpass=f=400,aformat=channel_layouts=stereo"]
    filters.append("[%d:a]volume=%.4f,afade=t=in:st=0:d=2,afade=t=out:st=%.3f:d=3[bed]" % (k, float(bed.get("gain", 0.04)), total - 3))
    labels.append("[bed]")
    k += 1
audio = os.path.join(build, "audio.wav")
if labels:
    fc = ";".join(filters) + ";" + "".join(labels) + "amix=inputs=%d:normalize=0:dropout_transition=0,apad=whole_dur=%.3f,atrim=0:%.3f[out]" % (len(labels), total, total)
    run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", fc, "-map", "[out]", "-ar", "48000", "-ac", "2", audio])
    print("  sound: %d voice lines, %d sound events%s" % (len([l for l in labels if l.startswith("[v")]), len([l for l in labels if l.startswith("[s")]), ", a room tone" if bed else ""))
else:
    audio = None

# 3. the overlay on the background, the sound on top (every input first, then the filter and the maps)
cmd = ["ffmpeg", "-v", "error", "-y", "-i", bg]
n_in, ov_idx, a_idx = 1, None, None
if not a.no_overlay and os.path.isdir(a.overlay) and any(f.startswith("ov_") for f in os.listdir(a.overlay)):
    cmd += ["-framerate", str(fps), "-start_number", "1", "-i", os.path.join(a.overlay, "ov_%05d.png")]
    ov_idx, n_in = n_in, n_in + 1
if audio:
    cmd += ["-i", audio]
    a_idx, n_in = n_in, n_in + 1
if ov_idx is not None:
    cmd += ["-filter_complex", "[%d:v]scale=%d:%d[ov];[0:v][ov]overlay=0:0:eof_action=pass:format=auto[v]" % (ov_idx, W, H), "-map", "[v]"]
else:
    cmd += ["-map", "0:v"]
if a_idx is not None:
    cmd += ["-map", "%d:a" % a_idx, "-c:a", "aac", "-b:a", "192k"]
cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", a.out]
run(cmd)
print("→", a.out, "(%dx%d, %d fps)" % (W, H, fps))

# 4. one file per shot, to look at each on its own (the spans of narration.json)
if a.split:
    sdir = os.path.join(os.path.dirname(a.out), "shots")
    os.makedirs(sdir, exist_ok=True)
    for line in nar["lines"]:
        dst = os.path.join(sdir, "%s_%s.mp4" % (line["id"], "draft" if a.draft else "1080p"))
        run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % line["start"], "-t", "%.3f" % line["slot"], "-i", a.out,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", dst])
        print("  shot %s  %5.1f–%5.1f s → %s" % (line["id"], line["start"], line["start"] + line["slot"], dst))
