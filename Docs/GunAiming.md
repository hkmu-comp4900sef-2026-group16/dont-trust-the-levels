# Gun aiming · build guide (BP_Player + M92)

**Concept:** the player carries an **M92 pistol**, always visible, attached to
the body, and it flips left/right (yaw 0 / 180) with the **existing
cursor-facing flip** (CrosshairAiming.md, Part 3). The capsule — the "real"
player — never rotates; the flip is visual, exactly like the character Sprite
flip. Walk left while aiming right: the body back-pedals facing right and the
gun stays muzzle-right with it.

**Two kinds of work:**

| Work | Done by | Status |
|---|---|---|
| Import art, create `T_M92_D` + `SPR_M92` | `Scripts/_import_m92.py` (live editor) | ✅ done, idempotent — re-run any time |
| Add the Gun component to `BP_Player` | **human**, editor UI | Part 2 below |
| Flip-graph wiring | **human**, editor UI | Part 3 below |

Per Structure.md §11: Python handles *assets and properties*; humans handle
*graphs and components*. `unreal.BlueprintEditorLibrary` is not exposed in
this project's Python (verified live), and components added by script never
instantiate on spawn — so Parts 2–3 are manual by design.

**Ownership:** `Weapons/` is pillar 3's folder (Structure.md §4) — the new
assets stay there. `BP_Player` is pillar 1's asset: one owner at a time,
commit with the editor closed.

---

## Part 1 — Assets (scripted, done)

`Assets/PixelGuns/M92.png` — 16×16 px, muzzle points **right** (art default,
like the character frames):

```text
    #
  #############
 ###############
################
##############
 ############
 ###### #
 #######
#####
#####
######
 #####
```

(Empty top/bottom rows are intentional — the sprite trims them.)

Facts, read back live from the editor (`Scripts/_import_m92.py` re-asserts
them on every run):

| Asset | Path | Settings |
|---|---|---|
| `T_M92_D` | `/Game/DontTrustTheLevels/Weapons/Textures/` | Nearest / TC_EditorIcon / No mipmaps / sRGB — Structure.md §10.2 pixel-art rules |
| `SPR_M92` | `/Game/DontTrustTheLevels/Weapons/Sprites/` | source `T_M92_D`, source 16×16, PPU **0.16**, pivot **center (8,8)** |

- **PPU 0.16** matches every player frame, so the pistol keeps the project's
  pixel scale: 16 px art = **100uu** (player frames: 32 px = 200uu).
- The baked geometry trims the empty rows: the render quad is **100×75uu**
  (the 16×12 px opaque region), normalized UVs — same T3D shape as the
  healthy player frames. Verified by export.
- **Pivot is center, on purpose.** The Gun component sits at the player's
  midsection, so a yaw-180 flip mirrors the art **about the component
  origin**: the muzzle swaps side and the gun box stays exactly where it was
  — no location change is needed when flipping. (A grip pivot silently
  reverts unless `pivot_mode = CustomPivot`, and would force offset-swapping
  logic for no visual gain.)

## Part 2 — Add the Gun component (BP_Player, manual)

1. **Lock first** (source control), then open `Player/Blueprints/BP_Player`.
2. **Components** panel → **Add** → **Paper Sprite Component**. Rename it
   **`Gun`**.
3. With `Gun` selected, Details:
   - **Sprite** (Source Sprite) = `SPR_M92`
   - **Location** = (X **0**, Y **20**, Z **10**) to start — tuned by eye
     after Part 3 to (X **±50**, Y **20**, Z **−40**); X is **mirrored by
     the flip chain** (Part 3), so it cannot be baked into one fixed value
   - **Rotation** = (0, 0, 0) — yaw 0 is the art's default, muzzle right
4. **Compile + Save.**

Why those numbers:

| Value | Reason |
|---|---|
| X = ±Xg (tuned ±50) | forward hand offset; **X must mirror with the facing** (Part 3 step 4): True → +Xg, False → −Xg |
| Y = +20 | both cameras look along **-Y** (`DTL_RoomCamera` sits at Y=+1000 yaw 270; the dead-zone camera's root is yaw -90), so **positive Y puts the gun in front of the body** — it renders over the chest, not behind it |
| Z = −40 (tuned) | hip height relative to the body center — nudged by eye after Part 3 |
| no scale | PPU already sizes the art; scaling breaks pixel-perfect |

## Part 3 — Flip the gun with the body (graph, manual)

The cursor-facing flip lives in the collapsed **Flipping Direction** region
of `BP_Player`'s EventGraph, nested one level deeper than it looks (verified
from the live T3D export):

- **Flipping Direction** (outer): input tunnel → **Branch**. True/False route
  into the collapsed **Updating Sprite Direction** box; the Branch condition
  comes from the collapsed **Direction Flipping Condition** box (cursor
  left/right via `Get Mouse Position` vs `Project World Location to Screen`).
- **Updating Sprite Direction** (inner): the two `Set Relative Rotation`
  nodes on the **Sprite** component — yaw 0 (True) and yaw 180 (False).
  Their exec-out (`then`) pins are free.

Visual reference: `py -3 Scripts/_rexport.py` then
`py -3 Scripts/_gun_flip_graph_html.py` → `Scripts/gun_flip_graph.html`
shows the current graph plus dashed **NEW** ghost nodes for what you add here.

Duplicate that flip for the Gun — same Branch, two more nodes per path
(rotation + mirrored location), added inside **Updating Sprite Direction**:

1. Open the **Flipping Direction** collapsed region (double-click it), then
   double-click the collapsed **Updating Sprite Direction** box inside it —
   that's where the two Sprite `Set Relative Rotation` nodes live.
2. On the **True** path, after the existing Sprite `Set Relative Rotation`
   (yaw 0): add a `Set Relative Rotation`, Target = **Gun** (variable get —
   My Blueprint → Variables, it appeared when you added the component),
   New Rotation = (Roll 0, Pitch 0, **Yaw 0**).
3. On the **False** path, after the existing Sprite `Set Relative Rotation`
   (yaw 180): add a `Set Relative Rotation`, Target = **Gun**,
   New Rotation = (Roll 0, Pitch 0, **Yaw 180**).
4. **Mirror the X offset** — without this the gun renders behind the
   character's back after flipping (rotation mirrors the art *around the
   component position*, but the position itself does not move). Add a
   `Set Relative Location` after each Gun rotation node: True path
   New Location = (**+Xg**, 20, −40), False path = (**−Xg**, 20, −40) —
   X flips sign with the facing, Y/Z stay (Xg = your forward hand offset,
   tuned to 50).

Fastest way: **Ctrl+drag** each existing `Set Relative Rotation` to duplicate
it, wire its exec input from the original's exec output, change only the
**Target** to `Gun` — the rotation values are already correct on each path
(True side has 0, False side has 180).

Note: **Part 5 replaces the two Gun rotation nodes** with a single aim
chain — build them as described here first; Part 5 step 1 deletes them.

| Node | Pin | Wire to |
|---|---|---|
| `Set Relative Rotation` (Sprite, yaw 0) — existing | exec (out) | → `Set Relative Rotation` **Gun#1** execute |
| `Set Relative Rotation` **Gun#1** | Target | **Gun** variable get · New Rotation = (0, 0, **0**) |
| `Set Relative Rotation` (Sprite, yaw 180) — existing | exec (out) | → `Set Relative Rotation` **Gun#2** execute |
| `Set Relative Rotation` **Gun#2** | Target | **Gun** variable get · New Rotation = (0, 0, **180**) |
| `Set Relative Rotation` **Gun#1** | then (out) | → `Set Relative Location` **Loc#1** execute |
| `Set Relative Location` **Loc#1** | Target | **Gun** variable get · New Location = (**+Xg**, 20, −40) |
| `Set Relative Rotation` **Gun#2** | then (out) | → `Set Relative Location` **Loc#2** execute |
| `Set Relative Location` **Loc#2** | Target | **Gun** variable get · New Location = (**−Xg**, 20, −40) |

> **THE RULES still apply** (CrosshairAiming.md): never drag a wire onto a
> node's non-exec pin area. After building, click each new node → Details →
> inputs must be empty except the real ones.

4. **Compile + Save.**

## Part 4 — Verify

1. `py -3 Scripts/_verify_gun.py` — asset-side checks (paths, pixel-art
   settings, sprite source/pivot/PPU, baked geometry) **and** the wiring:
   it re-exports `BP_Player.T3D` and verifies the flip chains
   (Sprite yaw 0/180 → then → mirrored Set Relative Location pair) plus,
   after Part 5, the aim chain (Get Mouse Position → Project → Gun
   rotation, Pitch from Atan2 degrees, Yaw from the Sprite's rotation).
   It still **cannot** check the Gun component's transform
   (Structure.md §11 — the SCS is not script-readable), so also:
2. PIE on `L_Level_00`:
   - gun visible at the midsection, **in front of** the body, muzzle right
   - move the cursor left of the character → body AND gun flip together,
     muzzle left; capsule/collision unchanged (visual flip only)
   - walk left while aiming right → back-pedal facing right, gun follows
   - no flicker while the cursor parks on the character

## Part 5 — Aim the gun at the crosshair (graph, manual)

The flip keeps the gun on the muzzle side. This part makes the muzzle
**track the crosshair every tick**, and it **replaces** the two Gun
`Set Relative Rotation` nodes from Part 3: one aim chain sets the whole
rotation (Pitch = cursor angle, Yaw = the Sprite's own yaw), so flip and
aim can never disagree.

Math (screen space; both cameras are yaw-only, so screen X ≈ world X and
screen Y ≈ −world Z; `Get Mouse Position` and
`Project World Location to Screen` are both viewport pixels — no
conversion needed):

```text
dx       = MouseX − GunScreenX         (subtract: A = mouse, B = screen)
dyUp     = GunScreenY − MouseY         (screen Y grows DOWN, so up = +)
sign     = Cos(SpriteYaw)              (+1 facing right 0°, −1 facing left 180°)
dxSigned = dx × sign                    (mirror the angle on the left side)
Pitch    = Atan2(dyUp, dxSigned)       (degrees; UE pitch > 0 = muzzle up)
Gun rotation = Roll 0, Pitch, Yaw = SpriteYaw
```

1. **Delete + rewire.** In **Updating Sprite Direction**, delete the two
   Gun `Set Relative Rotation` nodes (Part 3). Reconnect the dangling
   white wires: Sprite yaw 0 → `then` → `Set Relative Location` **Loc#1**
   execute; Sprite yaw 180 → `then` → **Loc#2** execute. The aim chain
   writes the yaw itself — the old pair is dead weight.
2. **Add the aim chain** — 11 nodes in the same box, below the two chains
   (position doesn't matter, wires do). **Nodes 1–10 are pure** (blue
   data nodes with NO exec pins — exactly like the `Get Player
   Controller` / `Get Mouse Position` / `Project World Location to
   Screen` already working in the Direction Flipping Condition box;
   leave that box alone — this chain gets its own copies). The only
   exec-wired node is #11. Splits (right-click the pin → **Split
   Structured Pin**): `ScreenPosition` on the Project node,
   `ReturnValue` on Get Relative Rotation, `New Rotation` on the Gun
   rotation node.
3. Wire per the table, then **Compile + Save**.

| # | Node (search) | Pin | Wire / value |
|---|---|---|---|
| 1 | `Get Player Controller` | — | pure (no exec wire); Player Index 0 |
| 2 | `Get Mouse Position` (drag off 1's output) | Target | ← 1 |
| | | Location X | → 6.A |
| | | Location Y | → 9.B |
| 3 | `Get Location` (drag off Gun get → search `get location`) | Target | Gun variable get (pure — NO exec wire; a pure GetWorldLocation works too — it must have NO exec pins) |
| | | (ReturnValue) | → 4 World Position |
| 4 | `Project World Location to Screen` (drag off 1's output — same node as in Direction Flipping Condition) | Player | ← 1 |
| | | World Position | ← 3 |
| | | ScreenPosition X (split) | → 6.B |
| | | ScreenPosition Y (split) | → 9.A |
| 5 | `Get Relative Rotation` (drag off Sprite get) | Target | Sprite variable get (pure) |
| | | Yaw (split ReturnValue) | → 7.A **and** → 11 Yaw |
| 6 | `Subtract` | A − B | A ← 2 Location X, B ← 4 ScreenPosition X → 8.A |
| 7 | `Cos (degrees)` | A | ← 5 Yaw → 8.B |
| 8 | `Multiply` | A × B | A ← 6, B ← 7 → 10 X |
| 9 | `Subtract` | A − B | A ← 4 ScreenPosition Y, B ← 2 Location Y → 10 Y |
| 10 | `Atan2 (degrees)` | Y, X | Y ← 9, X ← 8; ReturnValue → 11 Pitch |
| 11 | `Set Relative Rotation` | Target | Gun variable get |
| | | execute | ← **Loc#1 `then` AND Loc#2 `then`** — two wires into the SAME exec pin |
| | | Roll (split) | 0.0 |
| | | Pitch (split) | ← 10 ReturnValue |
| | | Yaw (split) | ← 5 Yaw |

> **THE RULES still apply** (CrosshairAiming.md): drag onto the exact
> pin. Nodes 1–10 are **pure** — this chain has NO exec pins except on
> node 11; the ONLY exec wires are Loc#1/Loc#2 `then` → 11 `execute`.
> Wrong search picks: plain `Cos` / `Atan2` are **radians** — you want
> the **(degrees)** variants; a Get Location / GetWorldLocation variant
> **with exec pins** never runs unwired — pick the pure one.

Per tick, both facings: Sprite flip → Set Relative Location → node 11
executes, and node 11 lazily pulls nodes 2–10 for Pitch and Yaw. The
Sprite's yaw was set earlier this same tick, so node 5 always reads the
current facing.

4. **Verify.** `py -3 Scripts/_verify_gun.py` (editor open — it
   re-exports `BP_Player.T3D` and checks the whole chain: node set, exec
   wiring, split pins, Atan2/Cos/Multiply sources, subtract A/B order).
   Visual reference: `py -3 Scripts/_gun_flip_graph_html.py` — the dashed
   NEW nodes show the aim chain before you build it.
5. PIE on `L_Level_00`:
   - cursor above the gun → muzzle tilts up smoothly; below → down
   - sweep across the character → flips with the body; muzzle keeps
     pointing at the crosshair on both sides
   - the aim is continuous — the chain re-runs every tick, no snapping

Polish ideas (later, not now): clamp Pitch to ±80° so the muzzle never
points straight up; move the sprite pivot from center (8, 8) to the grip
for a more natural rotation origin.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Gun renders behind the body | Y must be **positive** (+20): the cameras look along -Y, so negative Y = behind |
| Gun doesn't flip with the character | the new `Set Relative Rotation` nodes aren't in the **Updating Sprite Direction** exec chains (collapsed box *inside* Flipping Direction) — re-check Part 3 |
| Body flips but gun doesn't (or vice versa) | one exec chain got rewired — True→yaw 0, False→yaw 180, for **both** Sprite and Gun |
| Gun ends up behind the character's back after flipping | X isn't mirrored — the False-path `Set Relative Location` must be (**−Xg**, 20, −40); rotation mirrors the art, not the position |
| Gun points into the chest | yaw values swapped: 0 = muzzle right (art default), 180 = left |
| Gun jitters against the body | increase Y (20 → 40); distinct Y depths sort translucent sprites deterministically |
| Gun aims backwards on the left side | the Multiply or Cos node is missing — dx must be negated when facing left (Multiply B = Cos(SpriteYaw)) |
| Gun tilts down when the cursor is up | Subtract order swapped: node 9 must be A = ScreenPosition Y, B = Location Y |
| Gun tilts at a garbage/spinning angle | radians nodes — must be **Atan2 (degrees)** and **Cos (degrees)**, not plain Atan2/Cos |
| Gun stops flipping after Part 5 | the aim Set Relative Rotation's Yaw pin isn't wired from Get Relative Rotation (Sprite) |
| Gun never tilts (pitch stuck at 0) | node 11's execute isn't fed by BOTH Set Relative Location then pins, or you picked a GetWorldLocation variant WITH exec pins — use the pure Get Location |
| Verify FAILs "3 rotation nodes" | the two old Gun Set Relative Rotation nodes from Part 3 are still in the graph — delete them (Part 5 step 1) |
| Assets missing / verify FAILs | editor must be open for the scripts; re-run `py -3 Scripts/_import_m92.py` (idempotent) |
| Gun visible in editor, gone in PIE | BP not compiled since the component was added — Compile + Save, then re-PIE |

## Commit

One feature per commit, editor closed:

```
feat: attach M92 gun sprite to player with cursor-facing flip
```

Files: `Assets/PixelGuns/M92.png`,
`Content/DontTrustTheLevels/Weapons/Textures/T_M92_D.uasset`,
`Content/DontTrustTheLevels/Weapons/Sprites/SPR_M92.uasset`,
`Content/DontTrustTheLevels/Player/Blueprints/BP_Player.uasset`,
this file.

First commit is in (d583b0f). Second commit after Part 5:

```text
feat: point gun at crosshair with per-tick pitch
```

Files: `Content/DontTrustTheLevels/Player/Blueprints/BP_Player.uasset`,
this file.

(`Scripts/` is gitignored — Structure.md §11 — the import/verify scripts
travel with the person, not the repo.)