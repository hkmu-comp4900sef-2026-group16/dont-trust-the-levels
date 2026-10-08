# Crosshair & cursor-facing · build guide (BP_Player)

**Concept:** the player always aims where the OS cursor is. A crosshair sits
exactly on the cursor, and the character sprite flips left/right to face it —
**independent of movement**. Walk left while aiming right and you back-pedal,
facing right.

**Two phases:**

| Phase | What | New assets | Pillars touched |
|---|---|---|---|
| 1 | Hardware crosshair cursor + cursor-driven facing | `BP_PlayerController` (Core) | 1 only — can ship today |
| 2 | Pixel-art crosshair (`WBP_Crosshair`, `T_Crosshair_D`) | UI assets | 1 + **6 (UI)** — needs pillar 6's OK |

Phase 1 needs no art and creates nothing in another pillar's folder. Phase 2
replaces the OS cursor with a pixel-art crosshair; `UI/` is pillar 6's folder
(Structure.md §4), so agree with its owner before creating anything there.

---

## THE RULES (read first)

1. **Never drag a wire onto a node's non-exec pin area** — stray parameters are
   created silently and fed zeros at runtime. After building each graph: click
   the start node → **Details → Inputs must be empty** (except real inputs).
2. **Lock before editing.** Have source control connected in the editor; it
   locks on first edit. `BP_Player` and `BP_GameMode` are existing assets —
   someone else must not be holding their locks.
3. **One flip mechanism only.** The character *currently* faces based on the
   `MoveRight` axis. That wiring is **removed** in Part 3. If both remain, the
   input flip and the cursor flip fight every frame.
4. **Don't aim with world-space traces.** See *Why screen-space* below — in
   this project a visibility trace under the cursor fails over the background.

---

## Part 1 — `BP_PlayerController` (Core/Blueprints)

1. Content Browser → `DontTrustTheLevels/Core/Blueprints/` → right-click →
   **Blueprint Class** → expand **All Classes** → search `Player Controller` →
   pick **Player Controller** → name it **`BP_PlayerController`**.
2. Open it → **Class Defaults** → **Mouse** section:
   - **Show Mouse Cursor** ✓
   - **Default Mouse Cursor** = **Crosshairs**
3. **Compile + Save.**

Leave Click/Touch events off — nothing in the game clicks yet.

⚠️ `Core/` is shared (Structure.md §4 rule 4): pillar 1 owns it, but if you
are not pillar 1, agree before committing.

## Part 2 — Assign it in `BP_GameMode`

1. Open `Core/Blueprints/BP_GameMode` → **Class Defaults** → **Classes**:
   - **Player Controller Class** = `BP_PlayerController_C`
2. **Compile + Save.**

⚠️ If `L_Level_00` overrides the GameMode (**World Settings → Game Mode
Override**), the level wins. Either clear the override or set the PC class
in the level's World Settings as well.

## Part 3 — `BP_Player`: facing follows the cursor

### 3.1 What exists today

The EventGraph currently contains this chain — **facing is wired to movement**:

```text
MoveRight (axis) → Branch (AxisValue ≠ 0) → Branch (AxisValue > 0)
                                                  ├─ True  → SetRelativeRotation(Sprite, 0,0,0)   ← right
                                                  └─ False → SetRelativeRotation(Sprite, 0,0,180) ← left
                                                                       └────────┬─────────┘
                                                                        AddMovementInput
```

### 3.2 Remove the movement-facing wiring

1. Open `BP_Player` → **EventGraph**.
2. **Delete:** the `(AxisValue > 0)` Branch and the **two** old
   `Set Relative Rotation` nodes (yaw 0 / yaw 180).
3. **Rewire:** `(AxisValue ≠ 0)` Branch → **True** →
   `Add Movement Input` (so movement still works).

Don't touch the leftover template sub-graphs (`InpActEvt_Jump_*`,
`InpAxisEvt_MoveRight_*`, `ReceiveTick`, …) — they are harmless. Don't touch
the animation Composite either; it reads velocity/jump state, not facing.

### 3.3 Build the cursor-facing chain

Right-click in the main EventGraph → **Add Event → Tick** (if a Tick node
already exists in this graph, reuse it). Then:

| Node | Pin | Wire to |
|---|---|---|
| `Event Tick` | exec | `Branch → execute` |
| `Get Player Controller` | Return Value | `Get Mouse Position → Target` **and** `Project World Location to Screen → Target` |
| `Get Mouse Position` | Position X | `Greater → A` |
| `Get Actor Location` | Return Value | `Project World Location to Screen → World Location` |
| `Project World Location to Screen` | Screen Position | `Break Vector 2D → in` |
| `Break Vector 2D` | X | `Greater → B` |
| `Greater` (float) | Return Value | `Branch → Condition` |
| `Branch` | True | `Set Relative Rotation` **#1** |
| `Branch` | False | `Set Relative Rotation` **#2** |
| `Set Relative Rotation` #1 | Target | **Sprite** variable get · New Rotation = (Roll 0, Pitch 0, **Yaw 0**) |
| `Set Relative Rotation` #2 | Target | **Sprite** variable get · New Rotation = (Roll 0, Pitch 0, **Yaw 180**) |

- **Sprite** = the Paper Sprite Component variable (the same one the old flip
  targeted — drag it from **My Blueprint → Variables**).
- Split `New Rotation` into Roll/Pitch/Yaw floats and fill 0 / 180 — same
  shape as the nodes you deleted.
- Yaw 0 is the art's default facing (right); yaw 180 is left — exactly the
  values the old movement flip used, so nothing about the art changes.

## Part 4 — Verify (PIE on `L_Level_00`)

1. Press **Play**.
2. Checklist:
   - the Windows **cross** cursor is visible and follows the mouse
   - mouse right of the character → faces **right**; left → faces **left**
   - hold **A** (walk left) with the mouse on the right → character walks
     left **facing right** (back-pedal)
   - flip is visual only — collisions don't change (expected)
3. Report what you actually ran, per CLAUDE.md.

## Part 5 — Optional polish (not required to ship)

| Improvement | How |
|---|---|
| Skip redundant rotation sets | Boolean `bFacingRight`; only call Set Relative Rotation when `Greater` result ≠ `bFacingRight`, then SET it |
| Deadzone (flip twitch when cursor parks on the character) | `Greater → B` = player screen X **+ 4** (px tolerance) |
| Gamepad-only sessions | mouse never moved → `Get Mouse Position` returns (0,0) → always faces left. Aim is mouse-only by design; accept or blend with movement-facing later |

---

# Phase 2 — pixel-art crosshair (`WBP_Crosshair`)

**Coordinate with pillar 6 first** — these assets live in `UI/`, their folder.

## Part 6 — Art

Import a 16×16 crosshair PNG → `UI/Textures/T_Crosshair_D` (every texture
carries `_D`), with the §10.2 pixel-art settings: Filter **Nearest**,
Compression **UserInterface2D (TC_EditorIcon)**, Mip Gen **No Mipmaps**, sRGB ✓.

## Part 7 — `WBP_Crosshair` (UI/)

1. Right-click `UI/` → **User Interface → Widget Blueprint** → parent
   **User Widget** → name **`WBP_Crosshair`**.
2. **Designer:** keep the Canvas Panel root. Add an **Image**, name it
   `Crosshair`. Slot: **Anchors top-left (0,0)**, **Position (0,0)**,
   **Size X/Y = 16/16**. Brush → Image = `T_Crosshair_D`.
3. **Graph** — the widget positions itself on the cursor every tick:

| Node | Pin | Wire to |
|---|---|---|
| `Event Tick` | exec | `Set Position in Viewport → execute` |
| `Get Owning Player` | Return Value | `Get Mouse Position → Target` |
| `Get Mouse Position` | Position X | `float - float` (B = **8**) → `Make Vector 2D → X` |
| `Get Mouse Position` | Position Y | `float - float` (B = **8**) → `Make Vector 2D → Y` |
| `Set Position in Viewport` | Position | `Make Vector 2D → Return Value` |

The offset (8) is **half the image size** (16 px). Change the art size →
change both offsets. Because the Image is anchored top-left at (0,0), the
widget itself is 16×16, so `mouse − half` centres the art exactly on the
cursor.

4. **Compile + Save.**

## Part 8 — Show it from `BP_Player`

Add to the EventGraph's **BeginPlay** (create one if none exists):

| Node | Pin | Wire to |
|---|---|---|
| `Event BeginPlay` | exec | `Create Widget → execute` |
| `Create Widget` | Class | `WBP_Crosshair` |
| | Owning Player | `Get Player Controller → Return Value` |
| | Return Value | `Add to Viewport → execute` **and** SET variable `CrosshairWidget` |
| `Add to Viewport` | ZOrder | `10` |

New variable: `CrosshairWidget` (**User Widget** object reference) — keep the
reference so it can be hidden/removed later (e.g. death screen).

Then in `BP_PlayerController` → Class Defaults: **uncheck Show Mouse Cursor**.
The OS cross/arrow disappears and the widget replaces it. `Get Mouse Position`
keeps working with the cursor hidden; if the crosshair only moves after you
click, the viewport just lost focus — click it once.

## Part 9 — Verify (PIE)

- crosshair follows the mouse with no OS arrow visible
- character still faces the crosshair (Part 3 chain unchanged)
- crosshair drawn **above** level art (ZOrder 10) at any window size

---

## Why screen-space, not world-space (the trap)

The obvious node is `Get Hit Result Under Cursor` → compare world X with the
player's X. **It fails here:** the background tilemap has **no collision**
(Structure.md §2a — by design), so most of the screen is empty sky to a
visibility trace. The trace misses → no hit → facing freezes whenever the
cursor isn't over floor/walls/traps.

`Project World Location to Screen` + a screen-X comparison needs no hits, no
camera math, and survives camera changes (fixed camera today, dead-zone
camera tomorrow). For pure left/right facing, screen space *is* the truth.

**For pillar 3 (weapons):** projectiles need the cursor's *world* point. The
clean way is not a visibility trace either — deproject the cursor and
intersect the ray with the gameplay plane (Y = player's Y). Keep aim data in
the PlayerController so weapons can call it without casting to `BP_Player`
(Structure.md §9: systems talk through interfaces, not casts).

## Troubleshooting

| Symptom | Fix |
|---|---|
| No crosshair cursor at all | `BP_PlayerController` not set in `BP_GameMode`; or the level's World Settings override the GameMode |
| Facing never updates | start-node stray pins — Details → Inputs must be empty (THE RULE 1) |
| Facing updates only after clicking | PIE viewport lost mouse focus — click the viewport once |
| Faces wrong direction vs the cursor | yaw values swapped — 0 = right, 180 = left (matches the old movement flip) |
| Character flips but collisions behave one-sided | expected — the flip rotates the Sprite component only; the capsule never flips |
| Old flip still fires sometimes | the `(AxisValue > 0)` Branch wasn't deleted — see 3.2 |
| Both OS arrow and crosshair visible (Phase 2) | uncheck **Show Mouse Cursor** on `BP_PlayerController` |
| Crosshair sits off-centre | offset must equal half the image size (8 px for 16 px art) |
| Crosshair lags one frame behind | normal (widget ticks with the game); invisible in practice |

## Commit

One feature per commit, editor closed:

```
feat: cursor crosshair + character faces cursor (Player)
```

Include this file in the same commit.