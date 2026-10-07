# BP_Trap_FakeFloor — the paintable collapsing floor · build guide

**Concept (Level Devil's collapsing floor):** a strip of floor tiles that looks
exactly like the real floor. When the player steps on it, its collision
vanishes and the strip drops out of the world. The player falls through into
the pit.

**Design goal:** ONE blueprint for every level. Each cell can have a different
texture ("paintable"), the grid can be any width and any number of rows, the
floor any height. All of that is per-instance data — no per-level copies.

```
BP_Trap_FakeFloor (Actor)
├── DefaultSceneRoot
├── FloorBox      (Box Collision)   BlockAll     ← the solid floor the player walks on
├── TriggerBox    (Box Collision)   Overlap      ← detects the player stepping on
└── [N × PaperSpriteComponent]      ← spawned by the Construction Script, one per cell
```

**The paintable model:**

```
TileSprites = [SPR_GrassFloor_Mid, SPR_DirtFloor_Mid_Center]   ← the PALETTE (unique)
CellPaint   = [0, 0, 1, 1]                                     ← the PAINTING (per cell)
                 cell0 cell1 cell2 cell3
                 grass grass dirt  dirt
```

Palette holds the art (Paper Sprites, NOT Texture2D — sprites carry the
16px @ 0.16 PPU scaling that makes a tile exactly 100 uu). `CellPaint` holds
one palette-index per cell, in reading order (left→right, top→bottom).

---

## THE RULE (read first — this broke earlier attempts)

**Never drag a wire onto a node's non-exec pin area / a function's start
node.** Stray parameters get created silently, are fed zeros at runtime, and
the logic dies while still compiling clean. After building each graph: click
the start node → **Details → Inputs must be empty**.

---

## Part 1 — Variables (hand work)

My Blueprint → **Variables** → `+` for each row. Set the type in Details, tick
**Instance Editable** where marked. **Compile** after all rows exist.

| # | Name | Variable Type | Container | Default | Instance Editable |
|---|---|---|---|---|---|
| 1 | `TileSprites` | **Paper Sprite** | **Array** | len 1, `[0]` = `SPR_GrassFloor_Mid` | ✓ |
| 2 | `CellPaint` | **Integer** | **Array** | len 1, `[0]` = `0` | ✓ |
| 3 | `ColumnsAcross` | Integer | single | `1` | ✓ |
| 4 | `FloorThickness` | Float | single | `100.0` | ✓ |
| 5 | `FallSpeed` | Float | single | `900.0` | ✓ |
| 6 | `FallDistance` | Float | single | `2000.0` | ✓ (0 = fall forever) |
| 7 | `DropDelay` | Float | single | `0.0` | ✓ |
| 8 | `bFalling` | Boolean | single | `false` | internal |
| 9 | `FallenZ` | Float | single | `0.0` | internal |

**Choosing the type:** search `Paper Sprite` → pick the Paper2D **asset**
class. NOT `Texture2D` (no slice/scale), NOT `Paper Sprite Component`.

**Setting array defaults:** select the variable → Details → **Default Value**
→ set the array **length** → fill element 0.

---

## Part 2 — Components (hand work)

Components panel → **+ Add** for each. (No hand Sprite — the Construction
Script spawns one PaperSpriteComponent per cell.)

| Component | Class | Settings |
|---|---|---|
| `FloorBox` | **Box Collision** | Collision Presets = **BlockAll** (size/position set by the CS) |
| `TriggerBox` | **Box Collision** | **OverlapAllDynamic** · Collision Enabled = **Query Only** · Generate Overlap Events ✓ |

**Compile + Save.**

---

## Part 3 — Construction Script (the builder)

The CS **runs in the editor too**: set `ColumnsAcross = 2` on a placed instance
and the grid appears instantly; change `TileSprites` and the art swaps live.

Two lanes. **Lane A (paint)** hangs off the ForLoop's **Loop Body** pin.
**Lane B (boxes)** hangs off the ForLoop's **Completed** pin.

### 3.1 Lane A — paint (ForLoop Loop Body)

```
ForLoop (First = 0, Last = Length(CellPaint) − 1)
  LoopBody →
    Add PaperSpriteComponent              (search: "add paper sprite component")
       Return Value ────────────────────► Set Sprite.Target
    GET CellPaint → Clamp(0, Len−1) → Get (a copy) [ForLoop Index]
       Return Value = palette index
    GET TileSprites → Get (a copy) [palette index]
       Return Value ────────────────────► Set Sprite.New Sprite
    Multiply(Index × 100) → Fmod / Divide for col & row  (see 3.2)
       ─────────────────────────────────► Set Relative Location.New Location
```

Exec chain inside the body: `Add PaperSpriteComponent → Set Sprite → Set Relative Location`.

### 3.2 The 2D grid position math

```
col = Index  %  ColumnsAcross        (Fmod)
row = Index  /  ColumnsAcross        (integer Divide)
X   = col × 100
Z   = −(row × 100)                   (rows go DOWN)
```

`Set Relative Location.New Location` ← `Make Vector (X, 0, Z)`.

**Geometry:** sprite pivot is TOP_LEFT, so cell *i*'s top-left sits at
`(col×100, 0, −row×100)` relative to the actor origin (which is the grid's
TOP surface).

### 3.3 Lane B — boxes (ForLoop Completed)

```
Rows = Length(CellPaint) / ColumnsAcross        (integer Divide)
CX   = ColumnsAcross × 50
rowsZ = Rows × 50

#1 MakeVector → Set Box Extent (FloorBox)          (CX, 50, rowsZ)
#2 MakeVector → Set Relative Location (FloorBox)   (CX, 0, −rowsZ)
#3 MakeVector → Set Box Extent (TriggerBox)        (CX−5, 55, 10)
#4 MakeVector → Set Relative Location (TriggerBox) (CX, 0, 10)
```

All four Make Vector nodes are titled "Make Vector" in UE — tell them apart by
where their Return Value goes. Right-click each → **Add Comment** to label them.

**Compile.** Click the Construction Script start node → **Inputs must be empty**.

---

## Part 4 — Event Graph (the behaviour)

Two chains, both required. See diagram §9.

### 4.1 Chain A — overlap (fires once, when the player lands)

```
OnComponentBeginOverlap (Target = TriggerBox)
  → Does Implement Interface (Target = Other Actor, Interface = BPI_Killable)
  → Branch
      True → ① FloorBox.SetCollisionEnabled(NoCollision)
             ② SET bFalling = true
```

Place the event by clicking **TriggerBox** in the Components panel → Details →
**+ On Component Begin Overlap**.

### 4.2 Chain B — tick (fires every frame while falling)

```
Event Tick
  → Branch (Condition = GET bFalling)
      True → ① SET FallenZ = FallenZ + (FallSpeed × DeltaSeconds)
             ② Add Actor World Offset (Target = SELF,
                    Delta = MakeVector(0, 0, −(FallSpeed × DeltaSeconds)))
             ③ Branch ( FallDistance > 0  AND  FallenZ ≥ FallDistance )
                    True → Destroy Actor
```

**Data wiring — the pins that matter:**

| Node | Pin | From |
|---|---|---|
| `Multiply` | A | `Event Tick → Delta Seconds` ← **commonly mis-wired** |
| | B | `GET FallSpeed` |
| `Add` | A | `GET FallenZ` |
| | B | `Multiply → Return Value` (stepZ) |
| `Negate` | A | `Multiply → Return Value` |
| `Make Vector` | X = `0`, Y = `0`, Z | `Negate → Return Value` |
| `Greater Equal` | A | `GET FallenZ` |
| | B | `GET FallDistance` |
| `Greater` | A | `GET FallDistance`, B = `0` |
| `AND` | A | `Greater` Return Value |
| | B | `Greater Equal` Return Value |

### ⚠️ Two failure modes, and their symptoms

| Symptom | Cause |
|---|---|
| **Floor never falls** | `stepZ` is 0 → `Delta Seconds` is NOT reaching `Multiply.A` |
| **Floor vanishes instantly** | the destroy branch fired on frame 1 → `FallDistance = 0` with no `AND` guard |

**`FallDistance = 0` means "fall forever"** — but only with the `AND` guard in
place. Without it, `FallenZ(0) ≥ 0` is true and the actor destroys itself on
the first frame.

### ⚠️ The key node

`Add Actor World Offset` with **Target = SELF** moves the **actor**. Every
CS-spawned sprite is attached to the actor, so **the whole grid moves with it**.
Target the actor (Self), NOT a component — otherwise only one piece moves.

---

## Part 5 — Place and use

1. Drag `BP_Trap_FakeFloor` into the level
2. **Position:** actor origin = **top-left of cell 0**, at the floor's TOP
   surface Z. Leave those cells **unpainted** in the tilemap (the actor fills
   the gap until stepped on).
3. Set `ColumnsAcross` → the grid rebuilds live
4. "Paint": edit `CellPaint` — one palette index per cell, reading order
5. Per-level look → re-point `TileSprites`; per-level height → move the actor

**Pit death:** the player falls into the pit. Put `BP_Trap_Spikes` at the pit
bottom, or build a reusable `BP_KillVolume` (same overlap→BPI_Killable→Kill
chain, one box) for every future pit.

---

## Part 6 — Verify (Python)

With the editor open and PIE stopped:

```bat
py -3 Scripts\_fakefloor_state.py      :: components + variables on a spawned instance
py -3 Scripts\_fall_test.py            :: forces bFalling and watches the Z fall
```

Expected: `FloorBox` + `TriggerBox` on spawn, all 9 variables present, and the
spawned actor's Z decreasing ~900 uu/s once `bFalling` is set.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| CS runs, tiles don't appear | clamp the `CellPaint` index / lengthen the array |
| Tiles misaligned horizontally | `X = col × 100`, no `+50` (TOP_LEFT pivot) |
| Tiles misaligned vertically | `Z = −row × 100`, no `−50` |
| Wrong texture per cell | palette index off by one; palette must be unique entries |
| Player falls through before stepping | `FloorBox` must be BlockAll + CS must size it |
| Nothing happens on step | `TriggerBox` OverlapAllDynamic + Query Only + events ✓ + chain wired |
| Floor drops but player doesn't fall | `Set Collision Enabled` target must be **FloorBox** |
| Floor never falls | `Delta Seconds` not reaching `Multiply.A` |
| Floor vanishes instantly | missing `AND` guard with `FallDistance = 0` |
| Placed instance shows stale tiles | instances pin their own array copies — edit the arrays on the placed actor |

---

## Why Paper Sprite (not Texture2D)

The floor art lives as sliced sprites (`SPR_*`), each carrying texture + UV +
**Pixels Per Unreal Unit = 0.16** — which is what makes 16px art render at
exactly 100 uu per tile. A `Texture2D` is raw pixels: no slice, no scale.
With Paper Sprites the CS is one node per cell (`Set Sprite`). The sprite IS
the paintable unit.
