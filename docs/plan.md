# Plan: 27 Oct – 4 Nov 2026

## Baseline measured on 26 Oct

All runs used local Llama 3.2 3B and SAM 2.1-tiny on this PC (RTX 4060 8 GB, shared with ComfyUI and F5-TTS).

| Task | Result |
|---|---|
| Eye: SAM from one click vs the renderer's mask (the meta human, mehum, at 2.5 m) | IoU 0.73. The trunk is right and the arms are missed. 1218 ms on CPU. |
| Name 3 known kinds | 3 / 3 passed the gate, but the names are wrong. All three are "plant", including a thing that moves by itself, and the Thai is not real words. 6–9 s each. |
| Read one prose page | 0 / 33 lines usable: no Thai on any line, and the model split the text into single words. 126 s. |
| Compose "stuck in a corner" | Refused. Only real primitives and exit kinds were used, but one step had `p1: null`. 14 s. |

**What this shows:**
1. **The gates are needed.** They caught every malformed answer.
2. **The gates are not enough.** A well-formed but wrong name ("plant") and non-words written in Thai script both got through. The name check needs a second judgement, either a consistency pass or a Thai word list.
3. **3B is too small for Thai.** The language side needs a larger model.

### Muse Glimmer 30B on the robot's NVIDIA Jetson GPU (AGX Orin), 26 Oct (same tasks)

The model is Q5 on llama.cpp, the server already running for the gateway. The answer is forced onto the user channel, with no long reasoning first, at ~6 tokens/s. The server's own LoRA is off for these requests.

| Task | Result |
|---|---|
| Name 3 known kinds | 3 / 3 passed. The Thai names are real words. The moving thing (the cleaning robot) became "pet", which is a plausible guess but wrong. 15 s each. |
| Read one prose page | 4 / 6 lines usable, all in good Thai. Two "word" lines had no `desc`. One line is wrong in meaning, which no gate can catch: the page says a rotten fruit takes energy away, but the model wrote it down as `food: true`. 34 s. |
| Compose "stuck in a corner" | Passed the gate: only real primitives, and every value an integer. But it does not make sense as written (`turn_toward` with `p1: 0`, `drive_forward` at `p1: 0`). 47 s. |
| One short name, no schema extras | "a small robot". 4.4 s (21 tokens). |

**What this shows:**
1. **The language problem is solved:** Glimmer writes real Thai.
2. **What is left is judgement.** The gates check form, not sense. A wrong guess ("pet"), a wrong fact (rotten fruit as food) and a procedure that makes no sense all got through. This is the case for the next two layers:
   - **H4 rehearsal:** a procedure must work in the mental copy of the world before the chip may use it.
   - **Experience over words:** watching overrides a given name, and the first real meal overrides a book line. The platform already does this for book lines; H2 now does it for given names.
3. **Images should help naming.** Show Glimmer the thumbnail the eye kept, not only the observations (next step).

## What Meta offers (dev.meta.ai docs, read 26 Oct)

**On the Meta Model API** (`https://api.meta.ai/v1`, OpenAI-compatible, key in `MODEL_API_KEY`, $150 credit):

| Model | What it does | Use here |
|---|---|---|
| `muse-spark-1.3` | Text, image, video, PDF in → text out | Deep-brain language: naming, reading, composing |
| `sam-3.1` | Text prompt + image → boxes and masks | The eye, by name ("person", "bookshelf"). No Hugging Face approval needed. |
| `muse-image-1.0` | Pictures for the books | Matching a word to a look |

**Open weights** (bonus: Best Build on Meta Open Weight Models, $10k):
- **Muse Glimmer 30B** (text + image → text): about 16–17 GB at Q4, through llama.cpp, Ollama or vLLM.
  - Too big for the RTX 4060 8 GB here or the RTX 4080 12 GB on .44.
  - It fits the robot's **NVIDIA Jetson AGX Orin 64 GB** GPU board, the deep brain's real home. A Meta open-weight model as the robot's on-board deep brain is a strong story for that bonus.
- **Llama 3.2 3B** (works now, but weak in Thai) and **SAM 2.1** (local) are also open weights.

**Other bonus prizes worth aiming at:**
- Best Agentic Use-Case, $5k: an embodied agent.
- Most Viral, $20k: post the demo on X by 8 Nov.
- Community Vote, $10k: opens 9 Nov.

**Judges look at the video, the code and the live product.** So the demo needs a link that works during judging. The plan is a public read-only page from this repo: the proposals log and the gates' verdicts, plus recorded clips. The platform stays private, behind the sidecar.

**Live sessions** (noon–1 PM ET):
- 27 Oct: Agents 101
- 28 Oct: Agents 102
- 30 Oct: Fireworks inference and training

## Hooks needed on the core's side (ultimateTruth, in its own repo)

The sidecar can read the mind today. It cannot yet give anything back. These are generic endpoints that do not mention Meta:

| Hook | What it does | Where in the core |
|---|---|---|
| **H1 eye** | `GET /api/eye.png?agent=` renders the body's eye on the simulation thread. `POST /api/eye/segments` gives the recognizer a mask to crop by, in place of the renderer's root-id picture. | `dashboard/app.py`, `recognizer.py` (`_crop`) |
| **H2 names** | `POST` a name for a thing cell. It is kept like a word read in a book: the name comes from language, the meaning from watching. Experience still overrides it. | `things.py`, `reading.py` words |
| **H3 reading** | `POST` lines for a page, which `reading.py` takes like a shelf book (word and note lines). | `reading.py`, `spec/books.json` shape |
| **H4 procedures** | `POST` a proposed procedure. It is rehearsed in the mental copy of the world against the solver's own candidates. Only a winner becomes a variant the deep brain may write into the chip. | `solver.py`, `rehearsal.py` |

Each hook keeps the core's standing rules:
- the chip stays bit-exact;
- no thresholds are hard-coded (config only);
- labels are in Thai and English;
- tests are added, and a test that is not yet met is marked xfail with the measured reason.

## Days

| Day | Work | Done when |
|---|---|---|
| 27 Oct | Claim the $150 credit. Rerun the baseline on `muse-spark-1.3`. Try Muse Glimmer 30B Q4 on the robot's NVIDIA Jetson GPU if it is reachable. Add a consistency pass to the namer. | Names make sense for 3 / 3, and the Thai is real words. Muse Spark and Glimmer measured side by side. |
| 28 Oct | `sam-3.1` over the API, with text prompts taken from the bookshelf's words, on live frames from `/api/eye.png` (H1, done 26 Oct). Compare with SAM 2.1 local. | IoU on 5 scenes for both |
| 29–30 Oct | H2 + H3. Muse Image illustrates each book word; the eye matches the picture to looks it has seen (DINO embedding, tried on 24 Oct). | A word read in a book names a thing the body has watched |
| 31 Oct – 1 Nov | H4. Measure a model-proposed unstuck procedure against the solver's own, over the same seeds. | A table: wins / losses / refusals, reported as measured |
| 2 Nov | The live product: a public read-only page from this repo (proposals, gate verdicts, rehearsal outcomes, clips). In the private dashboard, a "Meta" card. | A link judges can open during judging (4–8 Nov) |
| 3 Nov | Record the demo video (≤ 3 min), write the submission text, show "Built with Llama" | Video + text ready |
| 4 Nov | Spare day. Submit before 9 PM ET. | Submitted |

## Risks

- **Not accepted, or no API credit.** Then use local Llama only. Llama 3.1 8B on .44 is the fallback.
- **Glimmer does not fit or run on the robot's NVIDIA Jetson GPU.** Then use Muse Spark over the API, plus Llama and SAM 2.1 for the open-weight part.
- **The GPU on this PC is shared** with ComfyUI and F5-TTS. Do not stop them; heavy inference goes to .44.
