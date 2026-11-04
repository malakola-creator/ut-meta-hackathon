# Proof register (snapshot)

Taken 2026-11-05 04:14 +0700 from the live platform and `data/proposals.jsonl`. Meta's models propose; the mind decides. Every model proposal below says which checks it passed or failed; every kind the mind knows says how its name was proven.

## Every model proposal and the gate's verdict

| when | task | model | proposed | gate |
|---|---|---|---|---|
| 2026-11-05 02:14 | look_name | meta:muse-spark-1.3 (8.79 s) | cat | ✅ passed |
| 2026-11-05 02:14 | look_name | glimmer:muse-glimmer-30b-q5 (23.8 s) | cat | ✅ passed |
| 2026-11-05 00:08 | rehearse | glimmer:muse-glimmer-30b-q5 (19.05 s) |  | ✅ passed |
| 2026-11-04 19:48 | look_name | meta:muse-spark-1.3 (20.8 s) | robot vacuum | ✅ passed |
| 2026-10-28 08:28 | look_name | baseten:meta-models/muse-spark-open-1026 (2.81 s) | robot vacuum cleaner | ✅ passed |
| 2026-10-28 08:27 | look_name | baseten:meta-models/muse-spark-open-1026 (3.37 s) | cat | ✅ passed |
| 2026-10-28 08:26 | look_name | baseten:meta-models/muse-spark-open-1026 (5.58 s) | dog | ✅ passed |
| 2026-10-28 07:54 | look_name | baseten:meta-models/muse-spark-open-1026 (3.09 s) | pet cat | ✅ passed |
| 2026-10-26 23:52 | compose | glimmer:muse-glimmer-30b-q5 (46.49 s) | turn_toward → drive_forward → turn_clear | ✅ passed |
| 2026-10-26 23:51 | read | glimmer:muse-glimmer-30b-q5 (34.19 s) | 6 lines | ❌ line 0: a word needs desc; line 2: a word needs desc |
| 2026-10-26 23:51 | name | glimmer:muse-glimmer-30b-q5 (14.97 s) | small decorative object | ✅ passed |
| 2026-10-26 23:51 | name | glimmer:muse-glimmer-30b-q5 (14.76 s) | pet | ✅ passed |
| 2026-10-26 23:50 | name | glimmer:muse-glimmer-30b-q5 (14.94 s) | small decorative object | ✅ passed |
| 2026-10-26 20:01 | compose | ollama:llama3.2:3b (14.25 s) | turn_away → scan → drive_forward | ❌ step 1: p1 None is not an integer 0..65535 |
| 2026-10-26 20:00 | read | ollama:llama3.2:3b (125.95 s) | 33 lines | ❌ line 0: th is missing; line 1: th is missing; line 2: th is missing; line 3: th is missing; line 4: th is missing; line 5: th is missing; line 6: th is missing; line 7: th is missing; line 8: th is missing; line 9: th is missing; line 10: th is missing; line 11: th is missing; line 12: th is missing; line 13: th is missing; line 14: th is missing; line 15: th is missing; line 16: th is missing; line 17: th is missing; line 18: th is missing; line 19: th is missing; line 20: th is missing; line 21: th is missing; line 22: th is missing; line 23: th is missing; line 24: th is missing; line 25: th is missing; line 26: th is missing; line 27: th is missing; line 28: th is missing; line 29: th is missing; line 30: th is missing; line 31: th is missing; line 32: th is missing |
| 2026-10-26 19:58 | name | ollama:llama3.2:3b (6.95 s) | plant | ✅ passed |
| 2026-10-26 19:58 | name | ollama:llama3.2:3b (5.81 s) | plant | ✅ passed |
| 2026-10-26 19:58 | name | ollama:llama3.2:3b (9.15 s) | plant | ✅ passed |

## the virtual human (vhum): what the mind knows, and how it was proven

| kind (keyed by what it does) | called | question → answer (by) | met |
|---|---|---|---|
| `neutral|moves=0|food=0|read=0` | a thing that stays put, bumping into it hurts the body (painful bodily feeling), not food | ✅ what is it called → a thing that stays put (furniture, a tree, a bookshelf) (book:things)<br>✅ what is bumping into it like → bumping into it hurts (experience) | 153 |
| `neutral|moves=1|food=0|read=0` | a thing that moves by itself, comes closer, bumping into it hurts the body (painful bodily feeling), not food | ✅ what is it called → a being (a person or a walking body) (book:things)<br>✅ what is bumping into it like → yes (exchange:vcat)<br>✅ does it come toward the body → yes, it comes closer (experience) | 350 |
| `neutral|moves=0|food=0|read=1` | a thing that stays put, bumping into it hurts the body (painful bodily feeling), can be read (books on it), not food | ✅ what is bumping into it like → bumping into it hurts (experience) | 26 |
| `neutral|moves=1|food=0|read=1` | a thing that moves by itself, bumping into it hurts the body (painful bodily feeling), can be read (books on it), not food | ✅ what is it called → a machine (the cleaning robot) (book:things)<br>✅ what is bumping into it like → bumping into it hurts (experience)<br>❓ does it come toward the body | 6 |

Processes a model proposed (H4): the way a model proposed (glimmer:muse-glimmer-30b-q5, tries 0, answered 0, learnt False)

## the meta human (mehum): what the mind knows, and how it was proven

| kind (keyed by what it does) | called | question → answer (by) | met |
|---|---|---|---|
| `neutral|moves=1|food=0|read=0` | a being (a person or a walking body) | ✅ what is it called → a being (a person or a walking body) (exchange:vhum)<br>✅ what is bumping into it like → yes (exchange:vcat)<br>✅ does it come toward the body → yes, it comes closer (experience) | 101 |
| `neutral|moves=0|food=0|read=0` | a thing that stays put (furniture, a tree, a bookshelf) | ✅ what is it called → a thing that stays put (furniture, a tree, a bookshelf) (exchange:vhum)<br>✅ what is bumping into it like → yes (exchange:vhum) | 180 |

## the virtual cat (vcat): what the mind knows, and how it was proven

| kind (keyed by what it does) | called | question → answer (by) | met |
|---|---|---|---|
| `neutral|moves=1|food=0|read=0` | a being (a person or a walking body) | ✅ what is it called → a being (a person or a walking body) (exchange:vhum)<br>✅ what is bumping into it like → bumping into it hurts (experience)<br>✅ does it come toward the body → yes (exchange:vhum) | 168 |
| `neutral|moves=1|food=0|read=1` | a machine (the cleaning robot) | ✅ what is it called → a machine (the cleaning robot) (exchange:vhum)<br>✅ what is bumping into it like → yes (exchange:vhum)<br>❓ does it come toward the body | 6 |
| `neutral|moves=0|food=0|read=0` | a thing that stays put (furniture, a tree, a bookshelf) | ✅ what is it called → a thing that stays put (furniture, a tree, a bookshelf) (exchange:vhum)<br>✅ what is bumping into it like → yes (exchange:vhum) | 252 |
