"""The voice-over as audio files, one per shot, from tools/video/narration.json (edge-tts: Microsoft's neural voices, free, online).
A placeholder until a person records the lines: a file ut-meta-video/voice/<id>.wav that already exists is kept, never overwritten,
so a human take replaces the synthetic one by name.

    python tools/video/tts.py [--out ut-meta-video/voice] [--force]

Prints each line's length beside its slot in the storyboard, so a line that does not fit its seconds is seen before the cut.
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(ROOT, "ut-meta-video", "voice"))
ap.add_argument("--force", action="store_true", help="remake the synthetic files even if a file of that name exists")
ap.add_argument("--only", default=None, help="comma-separated line ids to make; the others are kept as they are")
a = ap.parse_args()
spec = json.load(open(os.path.join(HERE, "narration.json"), encoding="utf-8"))
os.makedirs(a.out, exist_ok=True)


def seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(out.stdout.strip() or 0)


async def make(line, mp3):
    import edge_tts
    for attempt in range(6):                                          # the service sometimes answers with no audio (throttling): wait longer each time
        try:
            words = []
            with open(mp3, "wb") as fh:
                async for chunk in edge_tts.Communicate(line["text"], spec["voice"], rate=spec.get("rate", "+0%"), boundary="WordBoundary").stream():
                    if chunk["type"] == "audio":
                        fh.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":              # offsets in 100-ns units: when each word is spoken
                        words.append({"t": chunk["offset"] / 1e7, "d": chunk["duration"] / 1e7, "w": chunk["text"]})
            if not words:
                raise edge_tts.exceptions.NoAudioReceived("no words")
            json.dump({"id": line["id"], "text": line["text"], "words": words}, open(mp3[:-4] + ".words.json", "w", encoding="utf-8"), ensure_ascii=False)
            return
        except edge_tts.exceptions.NoAudioReceived:
            if attempt == 5:
                raise
            await asyncio.sleep(5.0 * 2 ** attempt)


report = []
for line in spec["lines"]:
    wav = os.path.join(a.out, line["id"] + ".wav")
    if (os.path.exists(wav) and not a.force) or (a.only and line["id"] not in a.only.split(",")):
        report.append((line["id"], seconds(wav), line["slot"], "kept"))
        continue
    mp3 = os.path.join(a.out, line["id"] + ".mp3")
    asyncio.run(make(line, mp3))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ar", "48000", "-ac", "2", wav], check=True)
    os.remove(mp3)
    report.append((line["id"], seconds(wav), line["slot"], "made"))
bad = 0
for lid, s, slot, how in report:
    fit = "ok" if s <= slot - 0.5 else "TOO LONG by %.1f s" % (s - slot)
    bad += fit != "ok"
    print("%-3s %5.1f s in a %2d s slot  %-4s %s" % (lid, s, slot, how, fit))
sys.exit(1 if bad else 0)
