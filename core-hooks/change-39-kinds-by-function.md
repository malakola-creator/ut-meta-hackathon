# A change on the platform side that affects H2 and H5: kinds are what things do (27 Oct 2026)

**What changed.** The platform's thing memory no longer keys a kind by its first look. That made different things lump together (decision #39, see `h5-thing-by-stimulus.md`). The platform owner decided:

> remember function and properties first, then name it from the knowledge store, or a general term; keep what is unknown as standing questions, answered later from other knowledge, from going on experiencing, or from an exchange.

Only the contract seen from this repo is described here; the platform code stays private.

## Keys you will see

| Key | What it is |
|---|---|
| `kind|neutral|moves=1|food=0|read=0` | **A kind**, made of what the body can tell: moves by itself, is food, can be read (books seen on it). The same key means the same kind for every body. |
| `ask|neutral|<look>` | **A look still being asked about.** It is not a kind yet. It disappears when watching answers it, and the thing joins the kind of what it does. |

## How H2 changed (naming a kind)

- **The key to send is now a `kind|...` key.** A name given through H2 answers the kind's standing question "what is it called" (`asking.name.by = "given:<from>"`).
- **The name stays with the kind.** The old rule "dropped when watching changes the meaning" is gone. A thing that turns out to do otherwise is moved to its own kind, and it leaves the name behind.
- **Removing a name** (`{"th": "", "en": ""}`) opens the question again, unless a book's word names the kind.
- **Naming an `ask|...` key** still answers 409, because the body does not know the thing yet.

## How H5 changed (a thing in the world → its kind)

- **The `cell` H5 returns** is a `kind|...` key, or an `ask|...` key while the thing is still being asked about.
- **A guessed thing** is recognised from its look and not yet confirmed by watching. It already has its kind's key.

## New in the things store (`GET /api/orin/things`)

| Field | What it holds |
|---|---|
| `cells[key].asking` | The standing questions. `name`: "what is it called". `touched`: "what is bumping into it like". `came_closer`: "does it come toward the body", only for a kind that moves by itself. Each has a `status` (open / answered), `by` (`book:<id>`, `given:<who>`, `experience`, `exchange:<body>`) and the answer. |
| `hints` | look → {kind: how often a member showed it}. |
| `label_th` / `label_en` (in the snapshot) | What the kind is called: a book's word, else a given name, else the general description. |

## Why it matters for the demo

**The open `name` questions are exactly where a Meta model can help** (the "other source of knowledge"). The sidecar can do this loop:

1. List the kinds with `asking.name.status == "open"`.
2. Show Glimmer the kind's properties and its members' pictures.
3. Propose a name through H2, or let a person name it in VR.

**The mind still says where each answer came from, and keeps learning by watching.**
