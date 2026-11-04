"""SAM 3.1 on any picture, from words: the piece of the look-and-name chain that runs on any machine with a Meta Model API key.

    MODEL_API_KEY=... python tools/sam3_cut.py PICTURE.png OUT.png "a chair" "a lamp" ["a table" ...]

Every phrase goes to SAM 3.1 (utmeta/sam3.py, text → masks) at once; the smallest mask over the picture's centre is taken as the
thing looked at, cut out with the rest dimmed, and saved to OUT.png. When no phrase finds anything there, SAM 2.1 from the centre
point is tried (needs torch and transformers; otherwise the picture is saved as it is). Prints what each phrase found, as JSON.

Needs: pip install openai, plus meta_sam_parser from Meta's SAM cookbook (07_sam), and the key in MODEL_API_KEY (or the variable
named by config llm.openai.key_env). The key is read at call time and never written.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utmeta import config
from utmeta.look import cut_out

ap = argparse.ArgumentParser()
ap.add_argument("picture")
ap.add_argument("out")
ap.add_argument("phrases", nargs="+", help="noun phrases SAM 3.1 looks for, e.g. 'a chair'")
a = ap.parse_args()

png = open(a.picture, "rb").read()
res = cut_out(config.load(), png, list(a.phrases))
open(a.out, "wb").write(res["crop"])
print(json.dumps({k: v for k, v in res.items() if k != "crop"}, ensure_ascii=False, indent=1))
