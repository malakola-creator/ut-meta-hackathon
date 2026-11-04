# ultimateTruth × Meta — Meta's models as the eye, the reading and the deep reasoning of an embodied mind

Entry for the **Meta Global AI Developer Hackathon** (Indie track, theme "Push the Frontier": robotics).
Event: 26 Oct – 4 Nov 2026. **Submissions are due 4 Nov, 9 PM ET.** Times in this repository are UTC+7, where that deadline is 5 Nov 09:00; a "5 Nov" stamp here is 4 Nov, ET.

**Demo video (3 min):** https://youtu.be/O-KUjQ4x2vU · **Code:** this repo · **Proof register:** [docs/proof.md](docs/proof.md) (live page: https://malakola--ut-meta-proof-web.modal.run)

## The idea in one line

A language model may **propose**. The mind **checks** each proposal, and later **rehearses** it before it acts. Every proposal is kept with the reason it was accepted or refused.

**What is new:** everything in this repo was built during the event, from 26 Oct 2026. ultimateTruth is the platform it plugs into: a simulated environment and a **cognitive model** with a **world model** inside it, which predates the event and is not presented as hackathon work ([CONTRIBUTIONS.md](CONTRIBUTIONS.md)).

## What ultimateTruth is (the platform, not part of this entry, not in this repo)

ultimateTruth builds a mind from the irreducible elements of experience: kinds of consciousness, mental factors, and the conditions that link them. It is not a black-box network.

- **Fast loop, the cognitive model:** a mesh chip that runs the mind's table (states of mind, mental factors, decision rows) and emits one command per step. Its modules are generated as RTL from the same tables, and in Verilator the chip matches the software model bit for bit. For now it runs only in simulation; it is sized for an FPGA board.
- **Deep brain, memory and the world model:** a slower process beside the chip, today a stand-in on the same PC. It remembers things, places and what each act led to; it holds the world model it rehearses in before acting (a copy of the simulator, not a learned model); it weighs, then writes new rows into the chip's table.
- **Environment:** three bodies share a MuJoCo house:
  - a **virtual human (vhum)** that eats, dies, and starts a new life that keeps only faint traces of the last;
  - a **meta human (mehum)**, a metal body that runs on electricity;
  - a **virtual cat (vcat)** with a smaller mind of its own.
- **What the bodies do:** they ask about unknown things, walk over, watch, and remember. They read a bookshelf. Each death is logged with its cause.

### How the mind works: a cognitive model with a world model inside, and where the Meta layer sits

![How it works: the house feeds the senses; the mesh chip runs the mind's table bit for bit and moves the body; the deep brain beside it remembers, rehearses on a copy of the world and writes rows into the table; the Mind Bridge shows the mind and carries six hooks; the Meta layer may only propose through them, and every proposal is checked and kept in the register](docs/img/how_it_works.svg)

1. **The house feeds the senses.** Eye, ear, nose, tongue and touch arrive as frames on a bus; nothing else enters the mind.
2. **The mesh chip is the cognitive model.** Its table of mental factors and decision rows turns what the senses bring into one of three tendencies: drawn toward, drawn away, or nothing. The chip's RTL is generated from the same tables, and in Verilator it runs the same as the software, bit for bit, so what runs in simulation is what the hardware will run.
3. **The body layer acts.** The chip's two-value command becomes each body's own gait (a human walks, a cat pads, a wheeled robot rolls); the body moves in the house and the senses see the result.
4. **The deep brain keeps what the chip cannot hold, and holds the world model.** Beside the chip, it remembers things, places and what each act led to; it rehearses a way on a copy of the world before trying it (a copy of the simulator, not a learned model); it weighs and then writes new rows into the chip's table. When a thing is unknown it asks aloud.
5. **The Meta layer may only propose.** Through six hooks on the Mind Bridge (the platform's window onto the mind; an API underneath), SAM cuts a thing out of the eye's picture, a Muse or Llama model names it, reads a page or composes a procedure, and a person can point and say. Every proposal passes the gate (form it can check) and is kept in the proof register with its verdict; a name reaches the mind only when the body has watched the thing, a procedure only as a candidate for the deep brain's own rehearsal. The layer never commands the body.

Steps 1–4 are the platform (not in this repo); step 5 is this repo.

## What this repo adds

| Piece | Meta model | Status on 26 Oct |
|---|---|---|
| `utmeta/eye.py`: cut a thing out of the eye's picture from one point | SAM 2.1-tiny now, SAM 3.1 once access is approved | Works offline. IoU **0.73** against the renderer's mask of mehum at 2.5 m; the arms are missed. 1.2 s on CPU. |
| `utmeta/namer.py`: a short Thai + English name from what watching showed | Llama 3.2 3B (local), then a larger Llama or Muse Spark | Runs, and the gate works, but the 3B names are poor: Thai that is not real words, and "plant" for a thing that moves by itself. |
| `utmeta/reader.py`: a page of prose → bookshelf lines (`word` / `note`) | same | Runs. 3B gave no Thai on any line, so all 33 lines were refused (126 s). |
| `utmeta/composer.py`: a procedure from the chip's own primitives | same | Runs. A 3-step "stuck in a corner" plan used only real primitives, with one `p1: null`, so it was refused (14 s). |
| `utmeta/core_client.py`: reads the live mind over HTTP | — | Works: health, agents, `/api/orin/<store>`. |

These are first measurements, not results. Every model answer is in `data/proposals.jsonl` (in this repo), and `docs/proof.md` is its readable snapshot with each body's memory.

### Added 27 Oct – 4 Nov

| Piece | Meta model | What was measured |
|---|---|---|
| **Does a picture help the namer?** (`tools/label_crops.py`, `tools/name_crops.py`, `tools/blender_targets.py`, `tools/blender_shoot.py`, [docs/results_picture_naming.md](docs/results_picture_naming.md)) | Muse Glimmer 30B (llama.cpp on the robot's NVIDIA Jetson GPU, an AGX Orin), pictures with the prompt | Watched only: **0** of 7 and 0 of 8 named. The platform's own eye (MuJoCo primitives, 48×64): picture only **1/7**. The realistic Blender house at 384 px: picture only **5/8**, both **4/8**; the same pictures at 48×64: **2/8**. So the eye must be realistic and larger than a thumbnail, and the picture says what a thing looks like while watching says what it does. |
| **Look and name** (`utmeta/look.py`, `utmeta/sam3.py`, `tools/look_and_name.py`; `tools/sam2_point.py` as the fallback) | **SAM 3.1** on the Meta Model API (text → boxes and masks), Glimmer / Muse Spark for the name | The nearest thing the body still wonders about (hook H6) is photographed from its eye in the realistic house, cut out by SAM 3.1 with noun phrases taken from the words the body has read on its bookshelf, named from the cut-out, checked by the namer's gate, kept as a proposal; given to the mind (H2) only when asked. In the runs so far the shelf's words (cat, kitchen, fruit) did not match the vacuum, so the cut-out came from the fallback, SAM 2.1 at the centre point; on 4 Nov SAM 3.1 found it at once with its own name, "a robot vacuum" (`data/look/look_5_sam3.json`): the loop closes when a person or a book gives the word. On 5 Nov the same chain ran on the cat the body shares the house with, from a frame of its eye with the cat walking: SAM 3.1 found "a cat" (dog, vacuum, bowl: none) in 4.5 s; Glimmer on the robot and Muse Spark 1.3 on the API both named it "cat" from the cut-out and the mind's own observations (moves by itself, comes closer, not food), 23.8 s and 8.8 s, both past the gate, both held as proposals ([docs/results_picture_naming.md](docs/results_picture_naming.md)). The cut-out now takes the found thing nearest the picture's centre when nothing lies under the very centre (`look.centre_radius`). |
| **Point and say** (`utmeta/teach.py`, `tools/teach_server.py`, `web/teach.html`, `web/teach_xr.html`, `web/proof.html`, `android/teach/`) | Glimmer / Muse Spark pull the name out of what was said | A person clicks a thing on a map of the house (browser, WebXR, or the Android app) and says what it is called (Thai speech through the owner's own speech-to-text, or typed). A gate checks the name (a name in each language, Thai in Thai script, short); the kind the body grasped that thing as comes from hook H5; the name goes in through H2 and answers the kind's standing question "what is it called". A thing the body has not watched yet takes no name (409). |
| **Muse Spark 1.3 as the namer** (`tools/name_crops.py --backend meta`, `utmeta/llm.py`; [docs/results_picture_naming.md](docs/results_picture_naming.md)) | Muse Spark 1.3 on the Meta Model API | The same 9 realistic pictures, the same scoring as Glimmer 30B (1/9, 8/9, **9/9**): watched only **0/9**, picture **8/9**, both **7/9**; one answer came back empty twice (the model's reasoning used its whole budget) and counts as a miss. The 28 Oct cut-out of the vacuum (SAM 2.1 at the centre point) named "robot vacuum", accepted. The API model is not better than the open-weight 30B on the robot's own computer here. |
| **Hooks H3–H6** (`core-hooks/*.md`) | — | A book written outside goes on the shelf (H3); a process proposed from outside is only a solver candidate (H4; rehearsed live on 5 Nov with `tools/h4_rehearse.py`: the plan Glimmer composed and the gate accepted ranked 3 of 3 against the mind's own ways and moved 0.0 m, its exits met at once, so the rehearsal caught what the form check cannot; on 27 Oct a hand-made proposal ranked 2 of 3); which kind a thing in the world is (H5); what the body still wonders about (H6). Each is a contract with the added lines only. |

## Run

```bash
# ultimateTruth running on :5000 (its own repo: ./run.sh --room house)
ollama serve &                                   # local Llama 3.2 3B
python -m utmeta health
python -m utmeta name --agent vhum -n 3          # names for kinds the body has learnt
python -m utmeta read data/page.txt              # prose → bookshelf lines
python -m utmeta compose                         # a procedure for "stuck in a corner"

MUJOCO_GL=egl ~/miniforge3/envs/ut/bin/python tools/render_eye.py data/eye/scene.npz
~/miniforge3/envs/comfy24/bin/python tools/eye_compare.py data/eye/scene.npz

python -m pytest tests -q                        # the gates (fake model), the client against the mock, teaching (15 tests)
python tools/mock_core.py                        # no platform? recorded answers on :5055 (set core.url in config.local.json)
```

### Run with nothing but this repo (judges)

The platform is private, so this repo carries a mock of its API with recorded answers (`tools/mock_core.py`, `samples/`), and the tests use a fake model. No GPU, no key, no platform:

```bash
python3 -m venv .venv && . .venv/bin/activate     # Python 3.10 or newer
pip install -r requirements.txt
python -m pytest tests -q                          # 15 tests: the gates with a fake model, the client against the mock, teaching
python tools/mock_core.py &                        # the platform's API from recorded answers, on :5055
printf '{"core": {"url": "http://127.0.0.1:5055"}}\n' > config.local.json
python -m utmeta health                            # the client reads the mock as it would read the live mind
```

`compose` reads the chip's primitives and exit kinds from the platform when it is on the machine, and otherwise from `samples/protocol.json`, a copy of the same enums recorded on 4 Nov. The commands that call a model (`name`, `read`, `compose`) need one: either `ollama serve` with `llama3.2:3b` pulled (the default), or the Meta Model API with `MODEL_API_KEY` set and `"llm": {"backend": "openai"}` added to `config.local.json`. Every answer, accepted or refused, is appended to `data/proposals.jsonl`.

### What needs more than this repo (said plainly)

| Part | Needs | Can a judge re-run it? |
|---|---|---|
| The eye from a point, `utmeta/eye.py`, `tools/sam2_point.py` | `pip install torch transformers` (SAM 2.1-tiny from Hugging Face, CPU is enough) | Yes, on any PNG: `python tools/sam2_point.py PICTURE.png X Y OUT.png`. |
| SAM 3.1 from words, `utmeta/sam3.py` | `pip install openai`, `meta_sam_parser` from Meta's SAM cookbook (07_sam), `MODEL_API_KEY` | Yes, on any PNG: `python tools/sam3_cut.py PICTURE.png OUT.png "a chair" "a lamp"`. |
| The look-and-name chain, `tools/look_and_name.py` | the live platform **and** the team's Blender machine over ssh (`utmeta/look.py` renders the realistic house there) | No: this is the team's own setup. What it produced is in [docs/results_picture_naming.md](docs/results_picture_naming.md) and the video. The two halves can be re-run on the pictures in this repo with a Meta Model API key: the cut-out, `python tools/sam3_cut.py data/blender/crops2/cleaner_5.png OUT.png "a robot vacuum" "a cat"` (the cat frame's result is `data/look/look_cat_sam3.json`), and the naming of all nine pictures three ways, `python tools/name_crops.py data/blender/crops2 --backend meta` (writes `names_thumb.json` beside the originals `names_thumb_spark13.json`). |

| Point and say, `tools/teach_server.py` | the live platform, Flask, a Thai speech-to-text server (salika) for voice, a model | Only the gate: `tests/test_teach.py`. The server has **no login**: it is a demo on the owner's network. Keep it on `--host 127.0.0.1`, or set `TEACH_TOKEN` and open the page with `?token=…` when a phone needs it. |
| The render and label tools, `tools/render_eye.py`, `tools/label_crops.py`, `tools/blender_*.py` | the platform and MuJoCo | No. |
| Hook H4 rehearsed live (`tools/h4_rehearse.py`) | the live platform | No, and it is **one measurement** (n = 1): the plan Glimmer composed ranked 3 of 3 and moved 0.0 m. A win or a loss by the model would need many runs over seeds to mean anything. |
| `meta_sam_parser` | version **0.1.0** (`pip show meta-sam-parser`: "Native Python parsing primitives for the SAM 3 segmentation protocol", home page dev.meta.ai), installed from Meta's SAM cookbook (07_sam) on 4 Nov 2026 | The parser only turns the API's answer into masks; `utmeta/sam3.py` shows the call. |
| The proof page on Modal (`tools/proof_site.py`) | a browser: the rows are drawn by JavaScript from `proofdata` | A plain fetch sees only the headings. `docs/proof.md` is the same register as static text. |

The gates check **form**, not truth: a name in both languages that leans only on what was observed, lines of the shape the shelf takes, a procedure made only of the chip's primitives. A wrong but well-formed name passes the gate; the body's own later experience and the person's "point and say" are what correct it. The rehearsal that would filter a well-formed but useless procedure is the platform's (hook H4); the one measurement so far is in the table above.

### The proof register (every proposal, every verdict): where judges can read it

- **In this repo, no server:** [docs/proof.md](docs/proof.md), a snapshot of the register taken from the live platform on 4 Nov: every model proposal with the gate's verdict, and every kind each body knows with how its name was proven.
- **As a page:** the same register as `web/proof.html` served from a frozen snapshot on Modal, `https://malakola--ut-meta-proof-web.modal.run` (made with `python tools/proof_snapshot.py` then `modal deploy tools/proof_site.py`; nothing on it talks to the platform or holds a key).
- **Live, on the owner's network:** the teach server's `/proof`, refreshed every 3 s from the running mind.

**Remote models.** Put the endpoint in `config.local.json` (git-ignored) under `llm.openai`. Put the key in the environment variable named by `key_env` (default `MODEL_API_KEY`, as in Meta's docs). The Meta Model API (`https://api.meta.ai/v1`, `muse-spark-1.3`) is already the default there; switch with `llm.backend: "openai"`. Keys are never written to files or logs.

## Licence

This repo is released under the **Apache License 2.0** ([LICENSE](LICENSE), [NOTICE](NOTICE)): use it, change it, share it and build on it, commercially or not, keeping the notice. Copyright 2026 malakola-creator.

The platform, ultimateTruth, is not in this repo and is not covered by this licence; its open release, OpenEmo, is Apache-2.0 as well. The models keep their own licences:

## Licences of what is used

- Llama 3.2: Llama 3.2 Community License. Any public demo must show "Built with Llama".
- SAM 2.1: Apache 2.0.
- SAM 3.1: Meta's SAM licence. Read it before any commercial use.
- MuJoCo: Apache 2.0.
