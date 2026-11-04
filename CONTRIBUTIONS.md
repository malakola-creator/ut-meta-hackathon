# What was built during the hackathon, and what was already there

The rules say: *"Your demo has to show only the features, code and functionality your team built during the event. Judges need to be able to tell what's new."* This file is the line between the two. The git history of this repo starts on 26 Oct 2026, the first day of the event.

## Built during the event (26 Oct – 4 Nov 2026): this repo

| Part | Files | First made |
|---|---|---|
| Language backends: local Llama, Muse Glimmer 30B on a llama.cpp server on the robot's NVIDIA Jetson GPU (AGX Orin), OpenAI-compatible Meta APIs | `utmeta/llm.py` | 26 Oct |
| Gates that check every model answer before the mind may see it | `utmeta/namer.py`, `utmeta/reader.py`, `utmeta/composer.py` | 26 Oct |
| SAM eye: cut-out from one point, IoU against ground truth | `utmeta/eye.py`, `tools/render_eye.py`, `tools/eye_compare.py` | 26 Oct |
| The proposals log (accepted / refused, with reasons) | `utmeta/proposals.py` | 26 Oct |
| Client for the platform's HTTP API | `utmeta/core_client.py` | 26 Oct |
| Hooks added to the platform for this project: H1 the eye as a picture, H2 a name given to a learnt kind | `core-hooks/h1-h2-eye-and-names.md` (the contract, the added lines and the new tests, with no platform code around them; checked live on 26 Oct) | 26 Oct |
| Muse Glimmer 30B on a llama.cpp server as a backend; pictures with the prompt on every backend (llama.cpp multimodal, OpenAI `image_url`, Ollama `images`) | `utmeta/llm.py` | 26–27 Oct |
| Does a picture help the namer? A labelled set of the house's things and the measurement (watched only / picture only / both; MuJoCo eye vs the realistic Blender house, 48×64 vs 384 px) | `tools/label_crops.py`, `tools/name_crops.py`, `tools/blender_targets.py`, `tools/blender_shoot.py`, `docs/results_picture_naming.md` | 27 Oct |
| Look and name: the nearest thing the body still wonders about (H6), photographed from its eye in the realistic house, cut out by **SAM 3.1** with noun phrases from the words the body has read (SAM 2.1 from the centre point when no read word matches, which is what the recorded runs did), named from the cut-out, kept as a proposal | `utmeta/look.py`, `utmeta/sam3.py`, `tools/look_and_name.py`, `tools/sam2_point.py` (SAM 2.1 from a point as the fallback) | 27 Oct – 3 Nov |
| Point and say: a person clicks a thing on a map of the house and says (Thai speech, the owner's own STT) or types what it is called; the model pulls out the name, a gate checks it, the name goes to the mind through H5 + H2 | `utmeta/teach.py`, `tools/teach_server.py`, `web/teach.html`, `web/teach_xr.html` (WebXR), `web/proof.html` (the proof register), `android/teach/` (a small Android app: the map in a WebView, the phone's microphone), `tests/test_teach.py` | 28 Oct – 3 Nov |
| Hooks H3–H6 and one platform change, as contracts with only the added lines: H3 a book written outside goes on the shelf, H4 a process proposed from outside is only a solver candidate, H5 which kind a thing in the world is, H6 what the body still wonders about; change 39: kinds are what things do. H4 was rehearsed live again on 5 Nov with `tools/h4_rehearse.py` (the plan Glimmer composed ranked 3 of 3, moved 0.0 m) and the contracts were checked against the live platform on 4–5 Nov | `core-hooks/h3-h4-books-and-proposals.md`, `core-hooks/h5-thing-by-stimulus.md`, `core-hooks/h6-asking.md`, `core-hooks/change-39-kinds-by-function.md`, `tools/h4_rehearse.py` | 27 Oct – 5 Nov |
| The repo runs alone: `requirements.txt`, the judges' run path in the README, the licence | `requirements.txt`, `README.md`, `LICENSE` | 3 Nov |
| Muse Spark 1.3 (Meta Model API) as a naming backend, measured on the same 9 realistic pictures as Glimmer; the client asks once more when a reasoning model answers no content | `utmeta/llm.py`, `tools/name_crops.py`, `docs/results_picture_naming.md` | 4 Nov |
| The proof register as data: frozen from the live platform to `docs/proof.md` (GitHub shows it) and served as a public page on Modal, so judges can read every proposal and verdict without the platform | `utmeta/proof.py`, `tools/proof_snapshot.py`, `tools/proof_site.py`, `web/proof.html` | 4 Nov |

The public repository is one commit of the final state, so these dates cannot be read from `git log`; they come from the author's working history (kept, not published). Dated evidence inside the repo: the proof register `docs/proof.md` (every model proposal with its timestamp, 26 Oct – 5 Nov) and the dated result documents in `docs/`. Dates are UTC+7: the deadline, 4 Nov 9 PM ET, is 5 Nov 09:00 here, so the work stamped 5 Nov (the cat, the live H4 rehearsal, the last snapshot) was done before it.

The prompts in the namer and composer were first tried in a throwaway script on 24 Oct, before the event. The code here was written new on 26 Oct.

**The platform moved on during the event** (its own work, not presented here): a third body, a virtual cat (vcat), the instinct store renamed from DNA to vinst, held intentions, a composer for the deep brain's solver. The hooks this repo uses were checked against the platform of 4 Nov: every route answers as the contracts say (`/api/health`, `/api/agents`, `/api/eye.png`, `/api/orin/things`, `/api/orin/things/asking`, `/api/orin/things/by-stimulus/<id>`, `/api/orin/things/<key>/name`, `/api/orin/proposals`, `/api/shelf/books`, `/api/things/thumb`, `/api/camera.png`). `samples/things.json`, the mock's recorded store, was re-recorded from that platform on 4 Nov (the thing memory's cells are now keyed by what things do, change 39).

## Already there before the event: the platform (not in this repo)

ultimateTruth is the embodied mind this project plugs into: the simulated house, the three bodies (the virtual human vhum, the meta human mehum, the virtual cat vcat), the cognitive model on its chip, the deep brain with its world model, the dashboard. It predates 26 Oct. **None of it is presented as hackathon work.** In the demo video it appears only as the stage, and is labelled "platform". The repo talks to it only over HTTP.

For anyone without the platform, `tools/mock_core.py` serves recorded answers from it, so the gates and the CLI can be run from this public repo alone.
