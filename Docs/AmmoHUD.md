# Ammo, HUD counter and ammo pickups - build guide

**Status (20 Nov 2026):** art, sprite and the `BP_AmmoPickup` shell exist (made
by `Scripts/_make_ammo_assets.py`). The variables, the fire gate and the HUD
text are hand work - this guide is the exact build sheet.

**Rule:** the player starts every level with **3** ammo. Each shot spends **1**.
At **0** the LMB does nothing (no bullet, and *not* the Jammed effect). An
ammo pickup placed in the level gives **+5** when the player overlaps it.

---

## 1. Behaviour

```text
level starts / level reloads   -> new BP_Player -> Ammo = 3
LMB pressed, Can Fire && Ammo > 0 -> spawn BP_Projectile -> Ammo = Ammo - 1
LMB pressed, Ammo == 0         -> nothing at all (no projectile, no jam)
walk into BP_AmmoPickup        -> Ammo = Ammo + 5, pickup destroys itself
```

Why this shape:

- `Ammo` lives on **BP_Player**, so a level load or a death reload creates a
  fresh pawn and the counter is 3 again for free. No reset code anywhere.
- The fire gate reuses the existing `Can Fire` branch in the `Shoot` graph, so
  the Jammed effect keeps working and an empty gun is *not* a jam.
- The pickup calls one function (`AddAmmo`) instead of writing the player's
  variable directly. Later "max ammo" or "ammo type" rules change one function.

---

## 2. What already exists (scripted)

| Asset | Path | State |
|---|---|---|
| `T_AmmoPickup_D` | `/Game/DontTrustTheLevels/Weapons/Textures/` | 16x16, Nearest, no mips, sRGB |
| `SPR_AmmoPickup` | `/Game/DontTrustTheLevels/Weapons/Sprites/` | source 16x16, PPU `0.16`, center pivot, natural size `100x100` uu |
| `BP_AmmoPickup` | `/Game/DontTrustTheLevels/Weapons/Blueprints/` | parent `PaperSpriteActor`; `RenderComponent` uses `SPR_AmmoPickup`, `NoCollision`, scale `1`, relative location `(0,0,50)` |

The sprite offset means the **actor origin is the bottom centre** of the
pickup, the same convention the traps use: drop the actor on the floor and the
art sits on top of it.

Source art: `Assets/Weapons/AmmoPickup (16x16).png` (placeholder crate; replace
when real art exists).

---

## 3. BP_Player: the `Ammo` variable and `AddAmmo`

Open `/Game/DontTrustTheLevels/Player/Blueprints/BP_Player`.

### 3.1 Variable

My Blueprint -> Variables -> **+**:

| Field | Value |
|---|---|
| Variable Name | `Ammo` |
| Variable Type | **Integer** |
| Default Value | **3** |
| Instance Editable | **off** (the player always starts at 3) |
| Category | `Weapon` |
| Tooltip | `Shots left. Resets to 3 whenever a level starts.` |

Do not add a max-ammo cap: the spec is "+5 per pickup", uncapped.

### 3.2 Function `AddAmmo`

My Blueprint -> Functions -> **+** -> name it `AddAmmo`.

| Step | Node | Pins |
|---|---|---|
| 0 | Input | `Amount` (Integer) |
| 1 | **Set Ammo** (variable set) | value <- **Add** (Integer) A = `Get Ammo`, B = `Amount` |

That is the whole function. The pickup is the only caller today.

---

## 4. BP_Player: spend one ammo per shot

The fire chain lives in the **`Shoot` collapsed graph** (double-click the
`Shoot` box to the right of the `Fire` input event). The existing `Branch`
already holds `Gun Effect.Can Fire`.

### 4.1 Gate the branch on ammo

Insert an **AND (Boolean)** node between `Can Fire` and the branch:

| Node | Pins |
|---|---|
| **AND** (search `AND`) | A <- existing `Can Fire` wire |
| **Greater** (Integer `>`) | A <- `Get Ammo`, B = `0` |
| | AND's B <- the `Greater` result |
| **Branch** | `Condition` <- AND's result |

Result: fires only while `Can Fire` **and** `Ammo > 0`. At 0 both paths are
identical to a jammed effect (the False pin stays empty), so **no projectile is
spawned** - exactly the requested behaviour, without switching effects.

### 4.2 Spend the ammo

After the existing **Spawn Actor from Class** (`then` pin, currently empty):

| Step | Node | Pins |
|---|---|---|
| 1 | **Set Ammo** (variable set) | value <- **Subtract** (Integer) A = `Get Ammo`, B = `1` |

Put the setter on the spawn's `then`, not on the branch, so a shot that fails
to spawn does not cost ammo.

**Compile + Save.** One shot = one ammo, in the same graph that spawns the
bullet.

> The Spawn Actor node still has `Collision Handling Override =
> AdjustIfPossibleButAlwaysSpawn` and the `SpawnBehind` fork - do not touch
> those; only the exec output changes.

---

## 5. WBP_LevelHUD: the counter

Open `/Game/DontTrustTheLevels/UI/WBP_LevelHUD`. The Designer already has an
empty `WeaponStatusPanel` (Vertical Box, bottom-right, `Collapsed`) - it was
left there for exactly this.

### 5.1 Designer

1. Select `WeaponStatusPanel` -> Details -> **Visibility = Self Hit Test
   Invisible** (visible, but it never eats mouse clicks).
2. Drag a **Text** block into `WeaponStatusPanel`, rename it **`AmmoText`**.
3. `AmmoText` details:
   - Text: `AMMO 3` (placeholder; the binding replaces it at runtime)
   - Font Size: `28`
   - Justification: **Right**
   - Outline Size: `2`, Outline Color: black (so it reads over any background)
4. Optional: a second Text block under it for a future weapon name.

**Anchoring - do this or the text drifts when the window resizes.** Select
`WeaponStatusPanel` and set its **Canvas Panel Slot**:

| Field | Value |
|---|---|
| Anchors | preset **Bottom Right** (Min `1,1`, Max `1,1`) |
| Alignment | `1, 1` (the widget's bottom-right corner is the anchor point) |
| Offset Left | `-24` (24 px from the right edge) |
| Offset Top | `-150` (above the `[A] [D] Move ...` guide row) |
| Size To Content | **on** (`bAutoSize`) |

The Text block inside the Vertical Box then needs no anchor of its own: the
panel sizes to its children and stays 24 px from the bottom-right corner at
every resolution.

If you leave `AmmoText` as a direct child of `CanvasPanel_0` instead (the
Designer drops it there if you drag into the viewport), give **that** slot the
same anchors, alignment and offset, and tick **Size To Content** - a canvas
child with a zero size is invisible.

The counter must sit **above** the control-guide row (`TextBlock_1`, bottom
left, top at `-137`). If it shares that row, a narrow window makes the two
overlap: the guide grows from the left and the counter grows from the right
until they meet. `Top = -150` with `Size To Content` keeps the counter's bottom
edge above the guide's top edge at every width.

Quick check: change the Designer's **Screen Size** (1920x1080 -> 1280x720 ->
800x600 -> 600x900); the counter must stay in the corner with the same margin
and must never touch the guide text.

### 5.2 Binding function

With `AmmoText` selected: Details -> Content -> **Text** -> **Bind** ->
**Create Binding**. UE creates a function (named `GetText_0`); rename it
**`GetAmmoText`**. Build:

| Step | Node | Pins |
|---|---|---|
| 0 | Entry | return type **Text** |
| 1 | **Get Player Character** | Player Index = `0` |
| 2 | **Cast To BP_Player** | Object <- step 1 |
| 3 | **Get Ammo** | Target <- `As BP Player` |
| 4 | **To Text (Integer)** | <- step 3 |
| 5 | **Format Text** | Format = `AMMO {0}`, argument 0 <- step 4 |
| 6 | **Return Node** | Return Value <- step 5 `Result` |

Leave the cast's **Cast Failed** pin unconnected: it returns an empty text, and
the HUD is only created in gameplay where the pawn is a `BP_Player`.

Binding functions are evaluated every frame; this one is three cheap nodes, no
Tick graph needed.

### 5.3 Optional: colour at zero

If the number should turn red at 0, bind `AmmoText`'s **Color and Opacity**
with a second function: `Get Ammo` -> **Equal (Integer, 0)** -> **Select**
(A = red, B = white). Not required by the spec.

---

## 6. BP_AmmoPickup: collision, variable, graph

Open `/Game/DontTrustTheLevels/Weapons/Blueprints/BP_AmmoPickup` (the shell
already has the sprite).

### 6.1 Component

Components -> **+ Add** -> **Box Collision**, rename **`PickupBox`**:

| Setting | Value |
|---|---|
| Parent | `RenderComponent` (the sprite root) |
| Relative Location | `(0, 0, 50)` |
| Box Extent | `(45, 45, 50)` |
| Collision Presets | **OverlapAllDynamic** |
| Collision Enabled | **Query Only** |
| Generate Overlap Events | **on** |
| Hidden in Game | on (it is only a sensor) |

`45x45x50` is slightly larger than the 100 uu art so walking into it is
forgiving; shrink it if pickups feel magnetic.

### 6.2 Variable

My Blueprint -> Variables -> **+**:

| Field | Value |
|---|---|
| Variable Name | `AmmoAmount` |
| Variable Type | **Integer** |
| Default Value | **5** |
| Instance Editable | **on** (so one pickup can give 10 in a later level) |
| Category | `Pickup` |

### 6.3 Event graph

| Step | Node | Pins |
|---|---|---|
| 1 | **On Component Begin Overlap** (`PickupBox`) | Other Actor |
| 2 | **Cast To BP_Player** | Object <- `Other Actor` |
| 3 | True -> **AddAmmo** | Target <- `As BP Player`, Amount <- `Get AmmoAmount` |
| 4 | **Destroy Actor** | Target <- **self** |

The cast is the enemy filter: an enemy walking through the box does nothing
because it is not a `BP_Player`.

**Compile + Save.**

### 6.4 Floating animation (optional)

The crate bobs up and down so it reads as a pickup. Two ways; the first needs
no Timeline asset.

**A. Tick + Sine (recommended)**

```
Event Tick
  -> Get Game Time in Seconds
  -> Multiply (float)     B = 2.2        // 2*pi/2.86s -> one bob every ~2.9 s
  -> Sin
  -> Multiply (float)     B = 12.0       // amplitude, +-12 uu
  -> Add (float)          B = 50.0       // base height (the sprite's Z offset)
  -> Set Relative Location  (Target = RenderComponent)
       New Location = Make Vector (X = 0, Y = 0, Z = the Add result)
```

`Sin` in Blueprint takes **radians**, so the first Multiply is the angular
speed. `50` is the sprite's authored Z offset from section 2 - if you change
that offset, change this constant too.

`RenderComponent` is the root, so the whole pickup (and its `PickupBox` child)
bobs by 12 uu. That is intentional: the trigger stays around the art.

Knobs worth exposing as instance-editable floats if you tune per level:
`FloatAmplitude` (default `12`) and `FloatSpeed` (default `2.2`); replace the
two literals with `Get` nodes.

**B. Timeline (no Tick)**

Add a Timeline component named `Float`, length `1.0`, **Loop** on, float track
`Alpha` with keys `(0s, 0.0)` and `(0.5s, 1.0)` and `(1.0s, 0.0)`:

```
Event BeginPlay -> Float (Play from Start)
Float Update  -> Lerp (A = 38, B = 62, Alpha = Alpha)
              -> Set Relative Location (RenderComponent, (0,0,Lerp))
```

Both give the same result; A is fewer assets, B is cheaper per frame if you
place dozens of pickups.

---

## 7. Placing pickups in a level

1. Open the level, drag `BP_AmmoPickup` from the Content Browser.
2. Drop it with its **origin on the floor** (sprite bottom at the origin).
3. Per instance, set `AmmoAmount` (default 5).
4. Duplicate as needed; each copy is independent and destroys itself on pickup.

---

## 8. Reset rules

| Event | Ammo |
|---|---|
| Level starts (Open Level from the menu or the exit door) | **3** |
| Player dies -> level reloads (`BP_Player.Kill`) | **3** |
| Retry from the result popup -> level reloads | **3** |
| Walk over a pickup | **+5** |
| Shoot | **-1** |

This is the requested "reset every level" behaviour and needs no extra graph:
`Ammo` is a plain variable on the pawn, and a new level spawns a new pawn.

If you later want ammo to survive level changes, move `Ammo` (and the
`AddAmmo` function) to `BP_GameInstance` and have `BP_Player.BeginPlay` copy it
in. Do not add that until the base behaviour is tested.

---

## 9. PIE checklist

1. Start a level -> HUD shows **AMMO 3**.
2. Fire once -> HUD shows `2`, exactly one bullet spawned.
3. Fire three times -> `1`, `0`; the total is exactly three bullets.
4. At `0`, press LMB repeatedly -> **no bullet, no sound of a shot, no jam
   switch**; HUD stays `0`.
5. Walk into a pickup -> HUD shows `5`, the pickup disappears.
6. Walk past a pickup without touching its box -> nothing happens.
7. Two pickups in a row -> `3 -> 8 -> 13`.
8. Finish the level / take the exit -> next level starts at **AMMO 3**.
9. Die in a pit -> level reloads -> `AMMO 3`.
10. Let an enemy walk through a pickup -> pickup stays, enemy unaffected.
11. Switch to a Jammed effect (`4`) with ammo left -> still cannot fire (jam
    wins); switch back to Basic -> fires and spends ammo.
12. Compile both Blueprints with no errors or warnings.

---

## 10. Verifier

With the editor open and PIE stopped:

```
py -3 Scripts/_verify_ammo.py
```

It is read-only and checks:

- `BP_Player.Ammo` exists, is an Integer, default `3`
- `AddAmmo` exists and has an `Amount` input
- the `Shoot` branch is gated by an `AND` that contains `Ammo > 0`
- the spawn is followed by a `Set Ammo` that subtracts 1
- `WBP_LevelHUD` has `AmmoText` inside `WeaponStatusPanel`, the panel is not
  collapsed, and the text is bound to a function that reads `Ammo`
- `BP_AmmoPickup` has `PickupBox` (OverlapAllDynamic, overlap events on),
  `AmmoAmount` default `5`, and the overlap -> `AddAmmo` -> `Destroy Actor`
  chain
- the sprite/texture assets exist with the documented settings

`PENDING` means "not built yet"; `FAIL` means "built but contradicts this
guide". Run it again after the PIE pass.

Baseline with the assets just created: **9 PASS | 0 FAIL | 0 WARN | 12 PENDING**.
Every PENDING is one of the hand steps in sections 3-6.
