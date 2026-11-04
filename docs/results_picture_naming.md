# Naming from pictures: measured 27 Oct 2026

**Question:** does showing Muse Glimmer 30B a picture of a thing help it name the thing?

**Setup:** Glimmer Q5 runs on the robot's NVIDIA Jetson GPU, an AGX Orin (`glimmer` backend). Each picture is named three ways:
- **A:** what watching shows of that kind, with no picture;
- **B:** the picture alone;
- **C:** both.

**Scoring:** a word match against the true kind (`tools/name_crops.py`, `KEYWORDS`). Every answer is printed beside its score so it can be checked by eye.

## Results

| Pictures | Made by | A watched only | B picture only | C both |
|---|---|---|---|---|
| The platform's own eye (MuJoCo), 48×64 like the eye's thumbnail, 7 things | `tools/label_crops.py` | 0/7 | 1/7 | 0/7 |
| The realistic house (Blender 4.2 on the 4080 machine, Poly Haven assets, 10 AM light), 384×384, 8 things | `tools/blender_targets.py` + `tools/blender_shoot.py` | 0/8 | **5/8** | 4/8 |
| The same realistic pictures cut down to 48×64 | resized | 0/8 | 3/8 | 2/8 |

## What the answers show

**1. The MuJoCo eye draws primitives.** A tree and the threat are the same red capsule, the cleaner is a red disc, and the shelf is a brown box. Glimmer said "marble", "red ball" and "pants leg". The picture cannot tell them apart, so no model could.

**2. In the realistic house, the picture alone names most things.**
- Right: "robot vacuum", "wall-mounted shelf", "tree" ×3.
- Misses that are fair descriptions of what is drawn, but count as misses under the keyword score: the charger is drawn as a glowing pad ("floor light"), and the threat is drawn as a red cone ("red cone").
- A miss caused by the framing: the meta human's (mehum's) picture also holds the charger pad, and the model named the pad.

**3. Size matters.** At the eye's thumbnail size (48×64), the same pictures drop to 3/8: the cleaner becomes a "ball". (The shelf, a "bench" in the 27 Oct run, is a "shelving unit" since the bookshelf was photographed again on 5 Nov, see below.)

**4. Watching alone never names a thing (0 in every run).**
- "Moves by itself, comes closer, not food" fits a pet as well as a robot vacuum.
- With both (C), the observations sometimes pull the answer away from what the picture shows: "mulch ring" instead of "tree", 4/8 vs 5/8.

So the model has to be told that **the picture says what it looks like, and watching says what it does.**

## What follows

- **For naming, the eye must be realistic.** For the demo, that means pictures from the Blender house: Blender's eye camera, or `/api/camera`.
- **For naming, the eye must keep a bigger picture than 48×64.** Ask the platform for a larger crop (`things.recognizer.thumb`), or take a fresh `/api/eye.png` while the thing is in view.
- **One thing per picture.** Cut the thing out before naming. That is the job for SAM 3.1 by text, or SAM 2.1 from a point, giving one crop per thing (as with mehum and the pad).
- **The platform fix found on the way:**
  - The eye's near clipping plane was 2.09 m, so nothing nearer was drawn. Fixed in ultimateTruth `4cf28cf` (`eye_near_m`).
  - The eye is level only, so up close it misses low things. This is decision #38, still open.

## After making the house's things look real (27 Oct, afternoon)

**What changed in the platform's Blender drawing** (all CC0 or built in the script):
- **The threat** is now a cactus in a terracotta pot. The owner chose this: bumping into it really hurts. The Poly Haven model `potted_plant_04` rendered as an aloe, so the cactus is built in the script.
- **The charger** is now a charging station: a post, a lit screen with a ⚡, and a floor pad.
- **The cleaner** is now a robot vacuum: a low disc with a LiDAR turret, a front bumper and a side brush.
- **Fruit** is now the Poly Haven apple (`food_apple_01`), tinted by stage and drawn on the outside of the crown.
- **A bug was fixed on the way:** the per-frame cleanup used to delete the model objects that stand in for the hand-made shapes.

**Same tool, same model** (Glimmer Q5 on the robot's NVIDIA Jetson GPU), 384 px pictures, 10 AM light:

| Pictures | A watched only | B picture only | C both |
|---|---|---|---|
| Realistic house, first pass (8 things) | 0/8 | 5/8 | 4/8 |
| **Realistic house, real-looking things (9 things)** | 1/9 | **8/9** | **9/9** |

**What the answers were:**
- Right: "charging pad", "robot vacuum cleaner", "potted cactus", "wall-mounted shelf", and "tree" ×4.
- The one miss with the picture alone was mehum, named "sofa": a sofa was in the frame. With the observations as well, it became "mannequin", which counts as a hit.
- The cactus keywords were added to the threat's accepted words because the threat *is* drawn as a cactus now. Before, it was a red cone, and no answer could have said "cactus".
- **Fruit is not in this run.** The world's fruit ripens, rots and is eaten within minutes, and the fruit picked was gone by the time its turn came. The shooting tool now labels each picture with the stage at the moment it was drawn. Fruit still needs a run of its own.

## Muse Spark 1.3 on the Meta Model API: the same 9 pictures (4 Nov)

**Setup:** the same tool (`tools/name_crops.py --backend meta`), the same 9 pictures of the realistic house with real-looking things (384 px), the same scoring. The model is `muse-spark-1.3` on the Meta Model API (`https://api.meta.ai/v1`, the `meta` backend), which reasons before it answers (826 reasoning tokens for a one-line question). Glimmer's row is the 27 Oct run above.

| Model | A watched only | B picture only | C both | seconds per answer (median / max) |
|---|---|---|---|---|
| Muse Glimmer 30B Q5 on the robot's NVIDIA Jetson GPU (27 Oct) | 1/9 | 8/9 | **9/9** | 17.6 / 35.2 |
| Muse Spark 1.3, Meta Model API (4 Nov) | 0/9 | 8/9 | 7/9 | 12.6 / 36.0 |

**What the answers were (Spark 1.3):**
- Picture alone: "charging station", "robot vacuum", "shelf", "cactus", "tree" ×4: right. mehum was "sofa" (a sofa is in the frame), the same miss as Glimmer's.
- Both: mehum became "mouse" (Glimmer: "mannequin"). The fruiting tree got **no answer**: the model spent its whole budget on reasoning twice (empty content with 4000 and then 8000 tokens of room), which the run counts as a miss. Asked once more afterwards it said "twig", a miss by the word list as well, so 7/9 stands either way.
- Watched only: "cat", "shoe", "small animal", "rock", "thorn", "small object" / "small stone". Nothing is named from behaviour alone, as before; "thorn" for the thing that hurts when touched is the nearest, and the word list does not count it.
- The first pass was stopped after 10 answers when two came back empty; the client was changed to ask once more with twice the room (`utmeta/llm.py`), and the run was repeated from the start. The table holds the repeated run only.

**What it says:** the picture does the work for both models. The larger API model is not better here than the 30B open-weight model on the robot's own computer, and it is less dependable: its reasoning can eat its answer. The look-and-name chain's cut-out of the vacuum (28 Oct; SAM 2.1 at the centre point, because none of the words the body had read matched it), named by Spark 1.3 on 4 Nov: "robot vacuum", accepted by the gate (in the proof register, `docs/proof.md`).

## SAM 3.1 on the eye's picture of the vacuum, by words (4 Nov)

`tools/sam3_cut.py data/look/look_5.png … "cat" "kitchen" "ripe fruit" "robot" "furniture" "a robot vacuum"`: the words the body had read (cat, kitchen, ripe fruit) and the general words (robot, furniture) find **nothing** in the picture; **"a robot vacuum" finds it** (box 147,162,233,238; 3.8 s). That is why the 28 Oct look-and-name runs fell back to SAM 2.1 at the centre point: the shelf had no word for the thing. Once a person teaches the word (point and say) or a book carries it, SAM 3.1 finds the thing by name (`data/look/look_5_sam3.json`, `data/look/look_5_sam3_a_robot_vacuum_cut.png`).


## The bookshelf, photographed again (5 Nov)

The 27 Oct shelf picture was taken from the shelf's side, and the shelf model of that day had its books outside the planks, so the picture showed a brown board with books floating beside it. The bookshelf was photographed again from its front in daylight after the shelf was fixed (`data/blender/crops2/shelf_4.png`; the old picture is kept beside it as `shelf_4_before.png`), and only that picture was named again; the other eight pictures and their answers are unchanged.

| namer | A watching only | B picture only | C both |
|---|---|---|---|
| Muse Glimmer 30B on the robot, 384 px | "small statue" | "bookshelf" ✓ | "bookshelf" ✓ |
| Muse Spark 1.3 on the Meta API, 384 px | "rock" | "bookshelf" ✓ | "bookshelf" ✓ |
| Muse Glimmer 30B, the same picture at 48×64 | "stuffed animal" | "shelving unit" ✓ | "shelf" ✓ |

The full-size scores do not move (the old shelf was already "wall-mounted shelf" / "shelf"); the thumbnail scores move from 2/8 and 1/8 to 3/8 and 2/8.

## The cat, by the same chain (5 Nov)

A frame of the Blender follow shot of the virtual cat walking in the kitchen (`ut-meta-video/build/cat/cat_frame_b.png`, 1920×1080) went through the look chain as the body's eye would: SAM 3.1 with the words "a cat", "a dog", "a robot vacuum", "a bowl" at once; the found thing nearest the picture's centre is cut out (`data/look/look_cat_cut.png`, result in `data/look/look_cat_sam3.json`); then two namers with the mind's own observations of that kind (`kind|neutral|moves=1|food=0|read=0`: moves by itself, comes closer, bumping into it hurts, not food).

| step | result | seconds |
|---|---|---|
| SAM 3.1 by words | a cat 1 · a dog 0 · a robot vacuum 0 · a bowl 0 (the pink bowl at the cat's feet was not found) | 4.5 |
| Muse Glimmer 30B on the robot, picture + observations | cat, gate passed: "white animal with dark points on ears, tail and legs, about 0.5 m, moves by itself" | 23.8 |
| Muse Spark 1.3 on the Meta API, the same | cat, gate passed: "white four-legged animal with tail and cat shape, moves by itself, not food" | 8.8 |

Both rows are in `data/proposals.jsonl` (kind `look_name`). The name reached nobody: it is a proposal until the body watches the cat do what the models said (the mind already holds the kind by what it does; the word is what the models add). A rule was added to the cut-out on this day: when no found thing lies under the very centre of the picture, the found thing nearest the centre (within `look.centre_radius`, 0.25 of the width) is taken, because the eye aims at a thing without always being dead on it; before this, the frame fell back to SAM 2.1 from the centre point and cut out the floor.
