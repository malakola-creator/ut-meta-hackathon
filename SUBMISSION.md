# Submission: rules, scope and checklist

**Due:** Wed 4 Nov, 9:00 PM ET, at https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit.

**What to hand in:**
- a public repo;
- a working demo video link (3 minutes);
- every team member added (solo is fine).

## The rules that shape this project

| Rule | What it means here |
|---|---|
| **New work only**: everything presented is built 26 Oct – 4 Nov | Present only this repo. It was started on 26 Oct; the date of each piece is in CONTRIBUTIONS.md. The platform (ultimateTruth) predates the event, so it is never presented as hackathon work. |
| **Identify your contributions**: judges must tell what's new, or the project is disqualified | [CONTRIBUTIONS.md](CONTRIBUTIONS.md) draws the line, and the README says what is new. The video opens by saying what the platform is and that the Meta layer is the hackathon's work, labels every platform shot "platform", and names the new parts. |
| **Public repo** | This repo goes public. The platform stays private (decision #37, keep the split). `tools/mock_core.py` and `samples/` make the CLI and the tests run without it. The two platform hooks built for this project are described in `core-hooks/*.md`, with only the lines that were added. |
| **Demo video, 3 min**: one of the main scores | See the outline below. |
| **No code, data or assets without rights** | No `res/`, no CC BY-NC scenes, no GTA content. Llama: show "Built with Llama". SAM 2.1: Apache 2.0. SAM 3.1: Meta's SAM licence. |
| **Not generic**: no basic RAG, no simple image analyser, and so on | The point is a mind that gates a language model's ideas through checks and rehearsal before acting. That is not an analyser or a chatbot. |
| **Theme: Push the Frontier** (robotics), names Muse Spark, Glimmer, SAM 3 | Llama and SAM 2.1 are Meta models and allowed. Moving to Muse Spark and SAM 3.1 would score better on "Use of Meta AI tooling" (25%). |

## Building on an existing project: answered by the organisers' FAQ

> **Q:** I have an existing project I want to build on. How do I make sure my new contributions are clearly identified?
> **A:** Your submitted repo must be a standalone extract.
> **Repo:** A fresh repo containing only work done during the event. Keep your existing codebase out of it.
> **Demo:** Open your 3-minute video with one line stating what was pre-existing and what you built this week.

So building on ultimateTruth is allowed, on two conditions:
- **Repo:** this repo holds only event work. No platform code, not even as context lines in a diff, so the hooks are kept as their contract plus the added lines (`core-hooks/*.md`).
- **Video:** the first line says what was there before and what is new (see the outline below).

## Checklist

**Before going public**
- [x] Get the organisers' answer on building over pre-existing work (FAQ above: allowed, as a standalone extract).
- [x] No platform code anywhere in the repo. The hook diff was replaced by `core-hooks/*.md` on 26 Oct, and git history was rewritten so the diff is gone from it too.
- [x] Licence: **Apache-2.0** (`LICENSE`, `NOTICE`, README "Licence"), chosen 5 Nov in place of PolyForm Noncommercial: the rules ask for a public repo, not an open-source licence, and an open licence is the more useful one for the community. Llama 3.2 ("Built with Llama") and SAM 3.1 (Meta's SAM licence) keep their own terms.
- [x] Judges can run the demo from the README with nothing but this repo: `requirements.txt`, the mock platform, the fake model (README "Run with nothing but this repo"; verified in a fresh venv on 3 Nov).
- [x] The published commit holds no token, key, email or private path (checked over the whole working history on 4 Nov before publishing; the one LAN address that was in `config.json` was moved to the git-ignored `config.local.json`).
  rewritten out of the history, the live addresses live in the git-ignored `config.local.json`; the commit author is the GitHub noreply identity).
- [x] What a judge cannot re-run is said plainly in the README ("What needs more than this repo"): the Blender machine, the live platform, the speech server; what they can re-run on any picture with their own key (`tools/sam3_cut.py`, `tools/sam2_point.py`); `compose` runs without the platform from `samples/protocol.json`.
- [x] The proof register is readable without the platform: `docs/proof.md` (snapshot of 4 Nov) and the Modal page from `tools/proof_site.py` (deploy: `modal deploy tools/proof_site.py` after `python tools/proof_snapshot.py`); the video's "judges, open this link" points there, not at the LAN teach server.
- [x] Public since 4 Nov 21:32 UTC: **https://github.com/malakola-creator/ut-meta-hackathon** (Apache-2.0). **The repository is published as a single commit of the final state**; the working history (83 commits, 26 Oct – 5 Nov) is kept by the author and is not on GitHub. The dates judges can check inside the repo are the timestamps of the proof register (`docs/proof.md`: proposals from 26 Oct to 5 Nov) and the dated result documents; `CONTRIBUTIONS.md` gives the date each piece was first made. Hand in the **repo link only**. Never a zip or a copy of the working folder: `config.local.json` (addresses of this network) and `data/` (keys' paths, proposals, certificates) are in it, and `.gitignore` protects nothing in a zip.
- [x] Create the GitHub repo and push, then make it public before the deadline (done 4 Nov 21:32 UTC): `gh` is logged in on this machine, so
  `gh repo create malakola-creator/ut-meta-hackathon --public --source ~/aiworkspace/ut-meta-hackathon --remote origin --push`
  (or `--private` first and `gh repo edit --visibility public` when the video is ready).

**Scoring** (Impact 30%, Use of Meta AI tooling 25%, Technical depth 20%, Demo 25%)
- [x] **Impact:** a language model's ideas pass through checks and rehearsal before a robot moves, and every decision can be traced.
- [x] **Meta tooling beyond a basic call:**
  - SAM replaces simulator ground truth;
  - SAM 3 text prompts come from words read on the bookshelf;
  - Llama / Muse Spark name, read and compose under gates;
  - Muse Image illustrates the books.
- [x] **Technical depth:** measured numbers. Accepted / refused, rehearsal wins, IoU.

**Video**
- [x] Opens with one line that says what was pre-existing and what is new: "ultimateTruth is a platform: a virtual environment and a thinking system. The Meta layer is my work for the Meta Global AI Developer Hackathon." The same line is on the title card; every platform shot carries a "platform" label; README and CONTRIBUTIONS.md draw the line file by file.
- [x] 3 minutes (a 180 s cut), every platform shot labelled "platform", "Built with Llama" in the credits. Uploaded 5 Nov (UTC+7): **https://youtu.be/O-KUjQ4x2vU** (unlisted; the link is in the README and goes into the submission form).
- [x] Nothing secret on screen: no tokens, no email, no private files (every shot reviewed; English only).

## Video outline (3:00)

| Time | Shot | Label |
|---|---|---|
| 0:00–0:12 | One line, spoken and on screen: "ultimateTruth: a virtual environment and a thinking system. The Meta layer, for the Meta Global AI Developer Hackathon: a model's guess must be proven before the body believes it." | required opening line |
| 0:12–0:42 | The stakes, the log of wrong names that passed the form check, and how the mind works: an animated diagram of the environment, the cognitive model on the mesh chip, the deep brain with its world model, the Mind Bridge and the Meta layer | "platform" label |
| 0:20–0:50 | SAM cuts mehum out of the eye's picture, compared with ground truth (IoU) | **new** |
| 0:50–1:30 | Llama names a kind the body watched. One name refused and why; one accepted, then shown in the house | **new** |
| 1:30–2:10 | A page of prose read into shelf lines; the body uses a word it read | **new** |
| 2:10–2:45 | A proposed procedure: refused by the gate, then one rehearsed and used, with numbers | **new** |
| 2:45–3:00 | What's new, in one table | **new** |
