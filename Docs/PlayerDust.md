# Player dust — puffs on run, jump and landing · build guide

**Goal (19 Oct):** "when player is jumping and running I want dust particles on
the ground". Dust belongs at the **feet**, on the floor the player is standing
on — not on the sprite's centre and not following the player through the air.

**Status:** `T_Dust_D`, `M_Dust` and `PS_Player_Dust` exist, and the emitter
inside `PS_Player_Dust` is **built and configured** — `Scripts/_verify_dust.py`
passes its five `PS ...` checks. What is left is the `BP_Player` graph.

**Graph map:** `Scripts/player_exec_graph.html` — generated from the current
`BP_Player.T3D` by `py -3 Scripts/gen_bp_graph.py`. Three tabs (ReceiveTick /
OnLanded / Jump input); collapsed graphs open on click, red dashed dots are free
exec pins. It draws the asset as it is now: `OnLanded → Set bAirDashUsed`, and
`Jump` is an **InputAction** whose Pressed pin calls `Jump` — there is no
`OnJumped` event node in `BP_Player`.

| Step | Can 4.27 Python do it? |
|---|---|
| add Cascade modules / emitters | **No** — `UParticleSystem::Emitters` is **protected** and no `ParticleModule*` class is exposed (`Scripts/_probe_dust_build.py`), so the module *list* is added in Cascade (§2.2) |
| set an existing module's values | **Yes** — every module is a package subobject (`…:ParticleModuleRequired_0`), and its `UPROPERTY`s read and write reflectively; that is what `Scripts/_configure_dust_ps.py` does |
| `BP_Player` graph | **No** — `unreal.EdGraph` / `BlueprintEditorLibrary` / K2 node classes are absent from this build |

Everything else — texture, material, folder, settings, verification — is done.

---

## 1. What plays when

| Moment | Trigger | Result |
|---|---|---|
| **Running** | `Event Tick`, grounded, `VSize(Get Velocity) > 10` | one small puff at the feet every **0.15 s** |
| **Jump (takeoff)** | `Event On Jumped` | one puff at the feet |
| **Landing** | `Event On Landed` (already exists) | one puff at the feet |
| Idle, mid-air, dead | — | nothing |

`On Jumped` is `ACharacter::OnJumped` (BlueprintImplementableEvent, called by
`Jump()` only when the jump actually starts), so pressing jump in mid-air with
no jumps left does **not** puff. `On Landed` already exists on `BP_Player`
(it resets `bAirDashUsed` for the air-dash).

The three moments all call one tiny function, `SpawnDust`, so the feet
calculation exists once. Spawned emitters are **world** emitters with
`Auto Destroy` on: the puff stays where the feet were and cleans itself up.

---

## 2. Assets

### 2.1 Already in the project (re-runnable)

```
Content/DontTrustTheLevels/Player/FX/
├── T_Dust_D      16×16 puff imported from the PixelAdventure pack
│                 (`Assets/PixelAdventure/Free/Other/Dust Particle.png`)
│                 TC_EditorIcon / TF_Nearest / NoMipmaps / sRGB  (pixel-art rules)
├── M_Dust        unlit, translucent, two-sided particle material
└── PS_Player_Dust  sprite emitter: Required · Spawn · Lifetime · Initial
                    Location · Initial Velocity · Initial Size · Color Over
                    Life, values applied by `Scripts/_configure_dust_ps.py`
```

`M_Dust` is the standard particle graph (same shape as
`/Engine/EngineMaterials/DefaultParticle`):

```
TextureSample (T_Dust_D).RGB  ×  ParticleColor.RGB   -> Emissive Color
TextureSample (T_Dust_D).A    ×  ParticleColor.A     -> Opacity
```

The `ParticleColor` half is what makes Cascade's **Color Over Life** fade the
puff out; without it the particles pop away at full opacity. The material also
has **Used with Particle Sprites** ticked — a Cascade sprite emitter using a
material without that flag renders nothing.

Regenerate all three at any time (idempotent — an existing `PS_Player_Dust`
is left untouched so a hand-built emitter survives):

```
py -3 Scripts/_make_dust_assets.py
```

### 2.2 `PS_Player_Dust` — the emitter

Two halves: the **module list** is hand work in Cascade (Python cannot add
modules), the **values** are applied by a script (Python *can* write an existing
module's properties).

```
py -3 Scripts/_configure_dust_ps.py     # Material / Duration / Loops / Lifetime / Start Size
py -3 Scripts/_read_dust_ps.py          # print every value the asset holds
```

`_configure_dust_ps.py` is idempotent — it writes only what differs and prints
before/after. It sets the plain module values plus the two distributions that
shape the puff:

| Property | Value | Why |
|---|---|---|
| `Required.Material` | `M_Dust` | Cascade otherwise renders with `/Engine/EngineMaterials/DefaultParticle` and `T_Dust_D` is never sampled |
| `Required.Emitter Duration` | `0.3` | one-shot emission window; with the Spawn `Rate` of `20/s` that is **~6 particles per puff** |
| `Required.Emitter Loops` | `1` | `0` = infinite, so `Auto Destroy` never fires and puffs pile up |
| `Size.Start Size` Min/Max | `(40, 40, 40)` | puff diameter in cm — 0.4 of a 100 uu tile. Edit `START_SIZE` at the top of the script to retune it |

Double-click `PS_Player_Dust` to look at the emitter. The rest of this section is
the reference for rebuilding it from scratch. (If the asset was deleted:
Content Browser → right-click → **FX → Particle System** — some menus call it
*Effects* — and keep the name, then re-run both scripts.)

#### Where the buttons are

```
┌──────────┬───────────────────────────────┬──────────────┐
│ Emitters │ Modules of the selected       │  Details     │
│  (left)  │ emitter  (the module stack)   │  (selected   │
│          │                               │   module)    │
└──────────┴───────────────────────────────┴──────────────┘
          Curve Editor · Bounds · Performance (bottom dock)
```

* **Emitters** — the emitter list (empty in a fresh asset). Right-click its grey area → **Add Emitter** →
  **Empty Emitter**. (If your build's submenu also lists *Sprite Emitter*, that is
  the same thing — sprite is the default renderer when no Type Data module is
  present.)
* **Module stack** — the emitter's modules, one row each.
* **Details** — properties of whatever module row is selected.

There is **no "+" toolbar button** in 4.27. Every module is added the same way:

> **right-click in the module stack → `Add Module` → `<category>` → `<module>`**

Right-clicking the emitter name in the Emitters column opens the same menu in
most builds, and a few builds also show a small **+** at the bottom of the module
stack — all three lead to the same list.

Two UI habits that save time:

* **Click a module row** to select it; otherwise the Details panel is empty.
* A value that can be a *distribution* has a small dropdown at the right end of
  its row. Pick **Constant** / **Uniform** / **Constant Curve** *first* — until
  then the row only lets you choose a type, you cannot type a number.

#### The seven modules

An **Empty Emitter** arrives with **2 of the 7** (Required, Spawn). **Four are
required** — Lifetime, Initial Velocity, Initial Size, Color Over Life — and
**Initial Location is optional**: it only spreads the puff a few centimetres
around the spawn point. If your `Add Module` menu does not offer a `Location`
category (or offers *Sphere* / *Cylinder* instead of *Initial Location*), **skip
row 4** and carry on — nothing else depends on it, and with ~6 particles plus
the velocity spread you will not see the difference.

The *Value* column is what `PS_Player_Dust` holds today — print it with
`Scripts/_read_dust_ps.py`. `Material`, `Emitter Duration`, `Emitter Loops`
and the `Lifetime` / `Start Size` Min/Max are written by
`Scripts/_configure_dust_ps.py`; everything else is a Cascade edit.

| # | Module | How it gets there | Setting | Value |
|---|---|---|---|---|
| 1 | **Required** | built in | `Material` | `M_Dust` (drag it from the Content Browser onto the slot) |
| | | | `Screen Alignment` | `PSA_Square` (the default — leave it) |
| | | | `Emitter Duration` | `0.3` |
| | | | `Emitter Loops` | `1` — one-shot; **must not loop**, or `Auto Destroy` never fires |
| 2 | **Spawn** | built in | `Rate` (the label is just **Rate**, not "Spawn Rate") | Constant `20` → `20/s × 0.3 s` ≈ **6 particles per puff** |
| | | | `Burst` | **leave empty** — see the note below |
| 3 | **Lifetime** | `Add Module → Lifetime → Lifetime` | `Lifetime` | **Uniform** Min `0.3`, Max `0.45` — a `0.1` minimum makes particles die on the frame they spawn, so the puff looks sparse |
| 4 | **Initial Location** *(optional)* | `Add Module → Location → Initial Location` | `Start Location` | **Uniform**: Min `(-8, -8, 0)`, Max `(8, 8, 0)` |
| 5 | **Initial Velocity** | `Add Module → Velocity → Initial Velocity` | `Start Velocity` | **Uniform**: Min `(-45, -10, 15)`, Max `(45, 10, 60)` |
| 6 | **Initial Size** | `Add Module → Size → Initial Size` | `Start Size` | **Uniform**: both `(40, 40, 40)` — 40 cm, 0.4 of a 100 uu tile |
| 7 | **Color Over Life** | `Add Module → Color → Color Over Life` | `Color Over Life` | leave white |
| | | | `Alpha Over Life` | **Constant Curve**: t `0` → `1`, t `1` → `0` |

**You do not need a `Burst` entry.** A burst is an array whose columns are
`Time`, `Count` and `Count Low` — there is **no "Count High"** — and it only
takes effect with `Rate = 0`. The `Rate × Emitter Duration` pair above gives the
5–7 particles this guide asks for using plain number fields. If you want an
*instant* puff instead of a 0.3 s emission window, set `Rate` to `0` and add one
burst: `Time 0`, `Count 7`, `Count Low 5`.

Module order does not matter for these seven (Cascade sorts by execution phase,
not by row position).

**`Start Location` is a vector distribution, not a sphere.** After adding the
module, **expand its row** (the ▸ on the left of `Initial Location`, or click it
and read the **Details** panel) — a collapsed module shows only its name, which
is why the property can look missing. The first property is `Start Location`;
switch its dropdown to **Uniform** and it gives you `Min` / `Max` vectors
(that is the whole "spread the puff a little" feature — ±8 cm around the feet).

If your `Location` menu offers **Sphere** instead of / as well as
*Initial Location*, that is the module that has a `Start Radius` (`8`). It also
has six `Positive X/Y/Z` · `Negative X/Y/Z` flags that must all stay ticked for a
round spread, so the box version above is the one with fewer ways to go wrong.
If neither entry is in your menu, skip row 4 — it is optional and the emitter
works without it.

**The one fiddly setting — the fade curve.** `Alpha Over Life` is a *curve*
distribution, so it is edited in the **Curve Editor**, not by typing:

1. In the **Color Over Life** row, set the `Alpha Over Life` dropdown to
   **Constant Curve**.
2. Click the `Alpha Over Life` row itself. The **Curve Editor** docks at the
   bottom of the Cascade window and shows two keys — `t=0, v=1` and `t=1, v=1`.
3. Click the key at **t = 1**, then set its **Value** to `0` (key-value table at
   the bottom-right of the curve editor, or drag the key down to the axis).
4. The row now reads a straight line from 1 to 0 — the puff fades out over its
   `0.45 s` life. (If the bottom dock is hidden, click the distribution again —
   the Curve Editor tab only appears while a curve distribution is selected.)

`X` is the side-scroller's forward axis, `Z` is up — the velocities spread the
puff sideways and slightly upward, so it reads as dust kicked off the floor.
`Initial Size` is in **centimetres** (the sprite grid is 100 uu per tile).

Save (`Ctrl+S`). Nothing else on this asset is needed for the first pass; the
tuning knob table in §6 lists what to touch if the puff is too big or too slow.

**Previewing it inside the asset is worth 30 seconds:** select the emitter in the
Emitters column, then click **Restart** (the circular-arrow button in the viewport
toolbar, next to *Play*/*Pause*/*Loop*). The emitter runs for `0.3 s`, so hit Restart
again to see it — a handful of soft white puffs expanding outward and fading.
`Auto Preview` in the same toolbar makes it loop if you want to watch it
continuously.

---

## 3. `BP_Player` — the `SpawnDust` function

My Blueprint panel → **Functions** → **+** → rename to **`SpawnDust`**
(no inputs, no outputs). It spawns one puff at the feet:

| # | Node | Wiring |
|---|---|---|
| 1 | `Get Actor Location` | — |
| 2 | `Get Scaled Capsule Half Height` — drag **`Capsule Component`** from the Components panel into the graph, then pull this off it (`ACharacter` itself has no such node in 4.27; the capsule component does) | capsule |
| 3 | `Make Vector` | `X = 0`, `Y = 0`, `Z ← Get Scaled Capsule Half Height` |
| 4 | `Subtract` (Vector − Vector) | `A ← Get Actor Location`, `B ← Make Vector` |
| 5 | `Spawn Emitter at Location` | exec ← function entry; `Emitter Template ← PS_Player_Dust`; `Location ← Subtract`; `Rotation ← Get Actor Rotation`; `Auto Destroy` ✔ |
| 6 | Function **Return Node** | exec ← `Spawn Emitter at Location` |

`Get Actor Location` is the **capsule centre**, so subtracting the (scaled)
half height puts the puff exactly on the floor line the capsule stands on.
Hard-coding a number here would drift the moment the capsule is resized.

> Do **not** use `Spawn Emitter Attached`: an attached emitter follows the
> sprite, so a run puff would slide along with the player instead of staying on
> the floor. `Spawn Emitter at Location` + `Auto Destroy` is the world-space
> version.

Compile the function; that graph is done.

---

## 4. Wiring the three moments (`BP_Player` → EventGraph)

Coordinates below only keep the graph tidy — the existing graph has `Event Tick`
at (608, 96) → `Sequence` at (816, 96) → composites at x≈976, and
`Event On Landed` at (608, 304) → `SET bAirDashUsed` at (816, 320). The area
below y≈600 and right of x≈1300 is empty.

### 4.1 Landing

`Event On Landed` already ends in `SET bAirDashUsed = false` at (816, 320).

```
Event On Landed → SET bAirDashUsed (then) → SpawnDust        ← add at (1000, 320)
```

Drag the **white exec pin** of the `SET bAirDashUsed` node to the new call's
exec input. Nothing else changes — the air-dash reset stays first.

### 4.2 Takeoff

1. Right-click the EventGraph → search **`On Jumped`** → pick the **red Event**
   node (`Character` category), place it at (608, 560).
2. `Event On Jumped (then) → SpawnDust` at (816, 576).

That event fires only when `Jump()` actually launches the character — it is not
the jump *input*, so a rejected jump (no jumps left, not grounded) makes no
dust.

### 4.3 Running (Tick)

The Tick chain is a `Sequence` at (816, 96) with `then_0/1/2` already going to
the animation / aim / `Dash` composites. **Do not touch those pins.**

1. Right-click `K2Node_ExecutionSequence_0` → **Add Pin**. A `then_3` appears.
2. Place the cluster below the Tick chain, starting at (1100, 620):

| # | Node | Wiring |
|---|---|---|
| 1 | `SET DustTimer` | exec ← `then_3`; value ← `Add` (Float + Float) = `DustTimer` + **`Delta Seconds`** (from the `Event Tick` node) |
| 2 | `Branch` — "Running?" | exec ← `SET DustTimer`; `Condition ← AND` |
| | `AND` (BooleanAND) | `A ← NOT ← CharacterMovement → Is Falling`; `B ← Greater (>) ← VSize(Get Velocity)` / `10.0` |
| 3 | `Branch` — "Dust ready?" | "Running?" **True** → `Condition ← Greater or Equal (>=) : DustTimer / 0.15` |
| 4 | `SET DustTimer = 0` | "Dust ready?" **True** → this `SET` → `SpawnDust` |
| 5 | `SET DustTimer = 0` (second node) | "Running?" **False** → this `SET` |

Two `SET DustTimer = 0` nodes are needed because an exec **input** pin takes
one wire only: one serves the "spawned, restart the clock" path, the other the
"not running, reset" path. Either way the next run starts with a puff
immediately instead of after a 0.15 s delay.

Why these conditions:

| Condition | Reason |
|---|---|
| `NOT CharacterMovement → Is Falling` | the anim graph already uses `Is Falling`; grounded = `NOT IsFalling` |
| `VSize(Get Velocity) > 10` | the **same threshold** the anim composite uses to pick `Run` over `Idle`, so dust and the run cycle start together |
| `DustTimer >= 0.15` | ~7 puffs/second at 60 fps; one puff per 9–10 frames |

`DustTimer` is one new variable: **Float**, default `0.0`, on `BP_Player`.

Compile, then save (`Ctrl+S`).

---

## 5. Verify

### 5.1 The scripted check

```
py -3 Scripts/_verify_dust.py
```

It exports `BP_Player` to T3D and checks, in this order:

| Check | What counts as pass |
|---|---|
| assets present | `T_Dust_D`, `M_Dust`, `PS_Player_Dust` all exist |
| `M_Dust` render setup | Translucent + Unlit + two-sided + **Used with Particle Sprites** |
| `M_Dust` graph | Emissive Color and Opacity both fed (by the two `Multiply` nodes) |
| `T_Dust_D` import | Nearest, NoMipmaps, sRGB |
| `PS_Player_Dust` modules | the seven modules exist as package subobjects |
| `PS` material | `Required.Material` is `M_Dust` |
| `PS` one-shot | `Emitter Duration > 0` and `Emitter Loops == 1` |
| `PS` lifetime | `Lifetime` is Uniform `0.3`–`0.45` |
| `PS` fade | `Alpha Over Life` starts at `1` and ends at `0` |
| spawn exists | a `Spawn Emitter at Location` (or `SpawnDust` call) whose template pin names `PS_Player_Dust` |
| landing hook | a spawn is reachable from the `OnLanded` event |
| takeoff hook | a spawn is reachable from the `OnJumped` event |
| run hook | a spawn is reachable from `ReceiveTick`, and **every** exec path from the tick event to it passes a `Branch` |
| timer | `DustTimer` is read and written in `BP_Player` |

The check is **exec topology**, not node presence — a `SpawnDust` node sitting
in the graph unconnected is a FAIL (same rule as `Scripts/_verify_traps.py`).

The emitter is checked too, even though `Emitters` is protected: each module
is a named subobject (`…:ParticleModuleRequired_0`), so the script reads its
properties directly — that is how the five `PS ...` rows above work. Want the
numbers next to the Cascade window? `py -3 Scripts/_read_dust_ps.py`.

### 5.2 PIE checklist (`L_Level_00`)

| Test | Expected |
|---|---|
| stand still | no dust |
| hold right/left | small puffs at the feet, ~7/s, left behind as you move |
| jump (W) | one puff the moment the jump starts |
| double-jump (W in air) | one puff at the feet in mid-air (`On Jumped` fires) |
| land from a jump or a fall | one puff on touchdown |
| dash (Space) | ground dash leaves dust; air-dash leaves the takeoff puff only |
| die on spikes | **no** dust after death (the level reloads) |
| fire the gun while standing | no dust (only movement spawns it) |

The puff must **stay where it spawned**. If it travels with the player, the
emitter is attached — re-check §3 node 5.

---

## 6. Tuning

| Knob | Where | Effect |
|---|---|---|
| `0.15` in "Dust ready?" | `BP_Player` → Tick cluster | puff frequency while running |
| `10.0` in "Running?" | `BP_Player` → Tick cluster | speed below which no dust (match the Run/Idle threshold) |
| `Rate` × `Emitter Duration` | `PS_Player_Dust` → Spawn / Required | particles per puff (`20/s × 0.3 s` ≈ 6) |
| `Lifetime` | Lifetime module | how long a puff lingers |
| `Start Size` | Initial Size module | puff size in cm (40 = 0.4 tile; edit `START_SIZE` in `Scripts/_configure_dust_ps.py` to retune) |
| `Start Location` Min/Max | Initial Location module | how wide the puff is (± cm around the feet; `0` = all particles out of one point) |
| `Start Velocity` | Initial Velocity module | how far the dust spreads |
| `Alpha Over Life` curve | Color Over Life module | fade shape (linear now) |
| `Screen Alignment` | Required module | `PSA_Square` is correct for a side-scroller; `PSA_FacingCamera` would rotate the texture in 3D |

Run and landing share one emitter, so this is the only place that scales a
puff. To make landing punchier, either raise `Rate` (it affects both) or use
the optional burst above with a higher `Count`.

---

## 7. Troubleshooting

| Symptom | Cause |
|---|---|
| `Add Module` is missing from the right-click menu | nothing is selected in the Emitters column — click the emitter first (the module menu belongs to the emitter) |
| a module row shows only its name, no properties | the row is collapsed — click the ▸/triangle at its left, or select the row and read the **Details** panel |
| no `Initial Location` / `Sphere` in the menu | row 4 is **optional** — skip it; the puff still works (particles just all start from the same point at the feet). The four that matter are Lifetime, Initial Velocity, Initial Size, Color Over Life |
| a module row offers only a distribution type | switch its dropdown to `Constant` / `Uniform` / `Constant Curve` first, then type the number |
| the `Burst` array asks for a "Count High" | it does not exist — the columns are `Time`, `Count`, `Count Low`, and a burst only works with `Rate = 0`. You do not need one: `Rate × Emitter Duration` gives the same particle count |
| the curve editor never shows up | click the *distribution row* (`Alpha Over Life`) after setting it to `Constant Curve`; the tab only exists while a curve is selected |
| nothing renders anywhere | `M_Dust` lacks **Used with Particle Sprites** (re-run §2.1 script), or the **Required** module's `Material` slot is still `DefaultParticle` / empty — `py -3 Scripts/_configure_dust_ps.py` |
| pink/black squares | material is unlit; the Emissive input must be connected (it is, in the generated asset — this is a symptom of a hand-edited material) |
| puffs pop out instead of fading | `ParticleColor` was removed from the material, or `Alpha Over Life` is a constant `1` |
| dust appears at the player's waist | `SpawnDust` is using `Get Actor Location` without the capsule half-height subtract |
| dust hangs in the air forever / editor slows down | `Emitter Loops` is `0` (infinite), so `Auto Destroy` never fires. Set `Emitter Loops = 1` |
| dust only at spawn point, no spread | `Initial Velocity` left at `0` |
| puffs slide with the player | `Spawn Emitter Attached` was used instead of `Spawn Emitter at Location` |
| dust while standing still | the "Running?" branch condition is unwired (defaults to true) or `VSize` is fed a constant |
| no dust while running, dust on jump/landing | exec not wired to `Sequence.then_3`, or the Tick cluster sits after a Branch instead of on the Sequence pin |

---

## 8. Related

- `Docs/CrosshairAiming.md` — the anim composite's `VSize > 10` Run/Idle test
  (this guide reuses the threshold deliberately)
- `Docs/DashAiming.md` §`Event Landed` — the existing `OnLanded` chain this
  guide appends to
- `Docs/Structure.md` — asset prefixes (`PS_` for Cascade systems, `M_` for
  materials, `T_*_D` for textures)
- `Scripts/_make_dust_assets.py` — texture, material, empty PS (idempotent)
- `Scripts/_configure_dust_ps.py` — writes the PS values that are plain
  module properties (Material / Emitter Duration / Emitter Loops / Lifetime
  Min-Max / Start Size Min-Max)
- `Scripts/_read_dust_ps.py` — prints every value the emitter holds
- `Scripts/_verify_dust.py`, `Scripts/_probe_dust_build.py` (why the module
  list cannot be scripted)
