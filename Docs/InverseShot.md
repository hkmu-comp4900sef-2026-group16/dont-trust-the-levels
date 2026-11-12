# InverseShot.md — the inverse shot (the bullet leaves from the back)

**Status: built; one PIE regression open (13 Nov 2026).** `SpawnBehind` is on
`BP_EffectBase`; all five children (`Basic`, `Ricochet`, `Heavy`, `Jammed`,
`Inverse`) inherit it. `BP_Effect_Inverse` exists, is parented to the base, its
CDO has `SpawnBehind = true`, and it is in the kill pool. The `Shoot`
collapsed graph has the typed `Select Vector` / `Select Rotator` fork, and both
are wired correctly: `bPickA` true (SpawnBehind) picks A = rear/reversed, false
picks B = front/normal. `_verify_shooting.py` reports `PASS the inverse spawn
chain: typed Selects <- SpawnBehind (rear + pitch 180)`. There is **no key 5**;
Inverse is acquired only by the kill roll. LMB is **Fire only**; Dash stays on
Spacebar (the short-lived LMB shot-dash was removed because it jerked the
player toward the crosshair on every normal shot). Python cannot author
Blueprint variables or nodes (`Structure.md` section 11), so graph edits are
editor work; the scripted half (`Scripts/_make_shooting.py`) creates the child
asset, writes its CDO defaults and appends it to the kill pool, and
`Scripts/_verify_shooting.py` checks the result.

**Known PIE issue — only the inverse shot moves the player.** The built fork
spawns the bullet at `GunLoc - forward × 60`. `Gun` sits at relative X = ±50, so
the inverse point is only **10uu** from the actor axis. The player capsule is
**34uu** in radius and `BP_Projectile`'s Box is `BlockAllDynamic` with a 20uu
half-extent along the shot. `IgnoreActorWhenMoving` makes the **bullet** ignore
the shooter; it does **not** make the **player** ignore the bullet, so
CharacterMovement can depenetrate the player on spawn. That is the one-frame
jerk, and if the box stays overlapped for a few ticks it reads as a dash.
Normal shots spawn 110uu from the axis and never overlap. The graph-topology
verifier cannot see this; the PIE-safe fix is §3.1, and
`Scripts/_probe_inverse_push.py` prints the live capsule/box geometry.

**Visual build sheet:** open
[`Scripts/inverse_fork_graph.html`](../Scripts/inverse_fork_graph.html) in a
browser — panel 1 is the two wires to delete, panel 2 is the fork plus the
second clearance `Subtract` inside `Shoot`, panel 3 is the compile/save/verify
checklist.

**Before editing:** `git lfs lock` the assets you are about to touch —
`Content/DontTrustTheLevels/Weapons/Blueprints/BP_EffectBase.uasset` (free
today) and `BP_Effect_Inverse.uasset` once `_make_shooting.py` has created it
(`LfsLocking.md`). **`BP_Player.uasset` is currently locked by `DC2828`**
(ID 62706514); the `Shoot` fork has been applied and verified, so do not rebuild
it unless you are changing it deliberately. The editor must be **closed** for
git and **open** for the scripts.

**Concept.** The normal shot starts 60uu in front of the gun, points along the
gun and flies away from the crosshair. The inverse shot is the same line,
traversed backwards: it starts **120uu behind the gun** in the fixed build
(§3.1) and flies **towards** the rear, so aiming up makes the bullet leave below
the player and travel down. The original 60uu version is visually similar but
its spawn point lands inside the player capsule and depenetrates the pawn;
120uu clears horizontal aim, and `AdjustIfPossibleButAlwaysSpawn` covers the
steep angles where the rear arc can still cross the capsule.

```text
normal shot                               inverse shot
  aim ↑                                     aim ↑
      │                                         │
  muzzle ●── +forward × 60 ──► bullet       gun ●
      │                                         │  spawn ●── −forward × 120
     gun                                        │            │
                                                ▼            ▼ bullet travels −forward
```

The trick is that **`BP_Projectile` does not change at all**. Its BeginPlay
already computes `velocity = actor forward × Effect.Speed` (`ProjectileShooting.md`
5.3); give the actor the mirrored location and a rotation whose forward is
`−gunForward`, and the same node produces the reversed shot. Only the fire
chain in the `Shoot` collapsed graph of `BP_Player` learns one new choice.

| | |
|---|---|
| New data | `BP_EffectBase.Spawn Behind` — bool, instance editable, default `false` |
| New child | `BP_Effect_Inverse` — `Spawn Behind = true`, otherwise Basic numbers |
| New graph | 7–8 nodes in the `Shoot` collapsed graph (`BP_Player` EventGraph; two `Select`s, **two `Subtract`s for 120uu rear clearance**, one `Make Rotator`, one `Add/Compose (Rotator)`, one property get, and either one `Bool to Int` or two typed `Select Vector` / `Select Rotator` bool pins) |
| Bullet | **untouched** — `BP_Projectile` / `Bounce` / the hit graph stay exactly as built |
| Pool | append `BP_Effect_Inverse` as the 4th entry (`EffectSwitchOnKill.md` §2) |
| Acquisition | **kill roll only** — `BP_Effect_Inverse` is the 4th pool entry; no number key |
| Shot-dash | **removed** — LMB is Fire only; Dash is Spacebar only (normal shots must not move the player) |

Owner split (`Structure.md` §4): the flag and the child are pillar 3 (the gun
decides what the shot is); the `Shoot` collapsed graph in `BP_Player` is the pillar-1 fire chain that
already owns the muzzle. No cross-pillar cast is added — the player reads a
property off the effect instance it already holds in `Gun Effect`.

---

## 1. `BP_EffectBase` — one new knob

Open `/Game/DontTrustTheLevels/Weapons/Blueprints/BP_EffectBase`.

| Variable (UI) | Name to type | Type | Instance Editable | Default | Why |
|---|---|---|---|---|---|
| `Spawn Behind` | **`SpawnBehind`** | Boolean | ✓ | `false` | spawn this effect's bullet at the mirrored muzzle (`GunLoc − forward×60`) with the rotation pitched 180°, so it leaves from the back and travels down the aim line |

My Blueprint → **Variables → +** → type **`SpawnBehind`** (one word; the editor
renders it as "Spawn Behind", exactly like `CanFire` renders as "Can Fire") →
type **Boolean** → Details → tick **Instance Editable** → default stays
**false** → **Compile + Save**.

> **The knob goes on the base, not on a child.** `BP_Effect_Basic`,
> `BP_Effect_Inverse`, `BP_Effect_Ricochet`, `BP_Effect_Heavy` and
> `BP_Effect_Jammed` are *siblings*; a variable added to Basic is invisible to
> the others. If the knob already exists on `BP_Effect_Basic`, **delete it
> there first**, then add `SpawnBehind` to `BP_EffectBase` — do not duplicate
> it. `_verify_shooting.py` prints `PENDING BP_EffectBase.SpawnBehind` and names
> the child that owns the stray copy until this is fixed.
>
> **Do not type a literal space in the Name field.** The UI's "Spawn Behind" is
> the friendly name it generates from `SpawnBehind`; typing `Spawn Behind`
> stores a different `FName`. It still compiles, but the canonical T3D markers
> and the build card use `SpawnBehind`. Rename it if you already created the
> spaced spelling.

Do **not** put the flag on `BP_Projectile` or in `Shoot` as a hard-coded class
check. The port's rule is that a new effect is *data* on the effect class
(`ProjectileShooting.md` Part 3.1), and every existing child inherits `false`
and keeps the normal muzzle shot with no edit.

`Gun Effect` is the live instance of the class (`BP_Player::Set Effect Class`
spawns it), so reading the flag off `Gun Effect` flips the same frame the class
is switched — exactly like the existing `Can Fire` gate in `Shoot`.

---

## 2. `BP_Effect_Inverse` — the fifth child

The script creates the shell and writes the CDO defaults; by hand it is the
60-second recipe in `ProjectileShooting.md`. Either run
`Scripts/_make_shooting.py` (§6) or:

1. Content Browser → right-click **BP_EffectBase** → **Create Child Blueprint
   Class** → name it `BP_Effect_Inverse` → save in
   `/Game/DontTrustTheLevels/Weapons/Blueprints/`.
2. **Class Defaults** → set:

| Can Fire | Damage | Speed | Bounces | Gravity Scale | Can Hit Shooter | Spawn Behind | Reads as |
|---|---|---|---|---|---|---|---|
| true | 1.0 | 3000 | 0 | 0.0 | false | **true** | the same pistol round, fired out of the character's back |

3. **Compile + Save.**

The child **inherits** `SpawnBehind` from the base; Class Defaults shows it
under the parent's category. If the row is missing, the variable is still on
`BP_Effect_Basic` — delete it there and add it to `BP_EffectBase` (§1) before
setting it here.

Why these values: same speed and damage as Basic so the only new thing is the
direction. `Gravity Scale = 0` keeps the path a straight line — the *same
ballistic*, reversed. If the effect should arc, gravity still pulls world-down
while the bullet travels backwards, so the arc is **not** a mirror image; a
negative gravity scale would make it float. Leave it at `0.0` unless that
weirdness is the point.

`Bounces = 0` and `Can Hit Shooter = false` keep the inverse shot a clean
one-way shot: it starts inside the player's capsule, so a bounce returning
immediately would be hard to read. (Ricochet behavior can be added later by
copying values; the spawn fork does not care.)

---

## 3. `BP_Player` EventGraph → `Shoot` (collapsed graph) — fork the spawn transform

The fork is **built and verified**. The table below is the rebuild recipe, not a
to-do list: the live `Shoot` graph has the two typed Selects with A = rear and
B = front.

The live fire chain is the **`Shoot` collapsed graph**, not a function: it is a
`K2Node_Composite` in `BP_Player`'s EventGraph (at roughly x=736, y=784) whose
`BoundGraph` is `EdGraph "Shoot"`. Its entry/exit are `K2Node_Tunnel` nodes, and
the **Fire** input action (at roughly x=528, y=800) calls it. It therefore does
**not** appear under My Blueprint → Functions. The relevant nodes, named from
the current export, are:

| Existing node | Where | What it feeds today |
|---|---|---|
| `K2_GetComponentLocation(Gun)` | ~944,768 | `Add` A — the gun's world location |
| `K2_GetComponentRotation(Gun)` | ~960,912 | spawn **Rotation**, and `Get Forward Vector` |
| `Get Forward Vector` | ~1280,960 | `Multiply` A |
| `Multiply (Vector × Float)` | ~1568,976, B = `60.0` | `Add` B — the muzzle clearance |
| `Add (Vector + Vector)` | ~1760,816 | spawn **Location** |
| `Spawn Actor from Class` (`BP_Projectile`) | ~2160,592 | `SpawnTransform_Location` / `_Rotation` are split pins |
| `Gun Effect` get → `Get Can Fire` | ~480,544 → ~656,544 | the existing fire gate |

Add these **eight** nodes (step 1 is a new property-get node that targets the
existing `Gun Effect` get). **Already built:** keep this as the recipe for a
rebuild; do not add a second copy of the fork.

| # | Node | Pins |
|---|---|---|
| 1 | **Get `Spawn Behind`** (property get on `BP_EffectBase`) | **Target** ← the existing `Gun Effect` get (the same node that feeds `Get Can Fire`; fan the wire out) · output = bool |
| 2 | **Bool to Int** (`Conv_BoolToInt`) | **InBool** ← step 1 |
| 3 | **Subtract** *(Vector − Vector)* | **A** ← `K2_GetComponentLocation(Gun)` · **B** ← the existing `forward × 60` result (fan out from the `Multiply` output) → the **first** rear point (`−60`) |
| 4 | **Subtract** *(Vector − Vector)* — **PIE clearance** | **A** ← step 3 · **B** ← the **same** `forward × 60` result → the **safe** rear point (`−120`). Do **not** wire step 3 directly to the Select |
| 5 | **Select** *(Vector)* | **Index** ← step 2 · **Option 0** ← the existing `Add` (muzzle) · **Option 1** ← step 4 → **Spawn Transform → Location** |
| 6 | **Make Rotator** | **Pitch** = `180.0` · **Yaw** = `0.0` · **Roll** = `0.0` |
| 7 | **Add** *(Rotator + Rotator)* | **A** ← `K2_GetComponentRotation(Gun)` · **B** ← step 6 |
| 8 | **Select** *(Rotator)* | **Index** ← step 2 · **Option 0** ← `K2_GetComponentRotation(Gun)` · **Option 1** ← step 7 → **Spawn Transform → Rotation** |

Wiring notes:

* Wire **Option 0 first** on each `Select`: the node's option pins are
  wildcards and adopt the type of the first connection (`Vector` / `Rotator`).
  If your palette offers typed `Select Vector` / `Select Rotator` entries, those
  are equivalent.
* The `Index` pin is **int**; that is why the chain uses the same
  **Bool to Int** converter the kill roll uses (`ProjectileShooting.md` 6.4 /
  `EffectSwitchOnKill.md` §3). False → option 0 (normal), true → option 1
  (inverse).
* The spawn actor's `SpawnTransform_Location` / `SpawnTransform_Rotation` pins
  keep their split shape; only the two source wires move from the `Add` /
  `Get Rotation` nodes to the two `Select`s.
* Everything else on the spawn actor stays: class `BP_Projectile`, collision
  handling `AdjustIfPossibleButAlwaysSpawn` (the PIE clearance fix), `Effect
  Class` ← the variable, `Shooter` ← self.

> **Typed `Select Vector` / `Select Rotator` variant (the current build).**
> These nodes take a bool `bPickA`, so `Bool to Int` is unnecessary. In UE4,
> `bPickA` **true returns A**, **false returns B**. Therefore A must be the
> **rear/reversed** option and B the **front/normal** option:
> Vector A = the **second `Subtract`** (120uu rear), B = `Add` (muzzle);
> Rotator A = `Compose Rotators` / `Add (Rotator)` (pitch 180), B =
> `Get Component Rotation`. The earlier 60uu build used the first `Subtract`
> directly and passed the topology verifier, but pushed the player in PIE
> (§3.1). If you rebuild it, keep A = rear and B = front; swapping them
> makes every normal shot spawn behind the player.

### Click path (the parts the table does not show)

1. Open `BP_Player` → **EventGraph**. Find the **Fire** input action (roughly
   x=528, y=800). The node immediately to its right, titled **`Shoot`**, is a
   collapsed graph. **Double-click `Shoot`** to open it — it is *not* under
   My Blueprint → Functions, because it is a `K2Node_Composite`, not a function.
   If you cannot spot it, press **Ctrl+F** (Find in Blueprints), search
   `Shoot`, and double-click the result; that selects the composite in the
   EventGraph. Do **not** create a new function called `Shoot` — the Fire event
   calls this composite, not a function of that name.
2. **Get `Spawn Behind`:** drag the existing **`Gun Effect`** getter's blue
   output into empty graph space and release. In the context menu type
   `Spawn Behind`; pick **Get Spawn Behind**. The new node's **Target** is
   already wired to `Gun Effect`. (A right-click search only lists the current
   Blueprint's own variables; the drag-from-the-object-pin menu is what lists a
   *target's* properties.)
3. **`Bool to Int`:** search the palette for `Bool to Int`; wire
   `Spawn Behind` → **In Bool**.
4. **First `Subtract`:** search `Subtract` and choose the **Vector** variant
   (gold A/B pins). Put it near `Multiply`. Wire the existing
   **Get Component Location** output → **A** (fan out; keep the wire to the
   old `Add`) and the existing **Multiply (Forward × 60)** output → **B**
   (fan out again).
4b. **Second `Subtract` — the PIE clearance fix:** add another **Vector
   `Subtract`**. **A** ← the first `Subtract` output · **B** ← the **same**
   `Multiply (Forward × 60)` output. This produces `GunLoc − forward × 120`.
   Wire this second Subtract to the Select, **not** the first one. With the
   gun at ±50 the rear point moves from 10uu to 70uu from the actor axis on a
   horizontal shot, outside the 34uu capsule; Fix A (spawn-adjust) covers the
   steep angles where the rear arc can still cross it (§3.1).
5. **`Select` (Vector):** search `Select`. **Connect the existing `Add`
   output to `Option 0` first** — that types the wildcard. Then connect the
   **second `Subtract`** (step 4b) → `Option 1`, `Bool to Int` return →
   `Index`, and the `Select` return → **SpawnTransform_Location**. The spawn
   pin now has one wire (the Select), not the old `Add` wire.
6. **`Make Rotator`:** search `Make Rotator`; set **Pitch = 180**, Yaw = 0,
   Roll = 0. If the pins read X/Y/Z, X=Roll, Y=Pitch, Z=Yaw — set **Y = 180**.
7. **`Add` (Rotator):** search `Add` and pick the **Rotator** variant. Wire
   the existing **Get Component Rotation** output → **A** (fan out; keep the
   wire to `Get Forward Vector`) and `Make Rotator` → **B**.
8. **`Select` (Rotator):** search `Select`. Connect the existing
   **Get Component Rotation** output to `Option 0` first, then
   `Add (Rotator)` → `Option 1`, the same `Bool to Int` return → `Index`, and
   the `Select` return → **SpawnTransform_Rotation**. The direct
   `Get Rotation` → spawn wire is replaced.
9. **Compile + Save.** The two `Select`s must both take their `Index` from the
   **same** `Bool to Int`; do not add a second converter.

```text
GunEffect ─Target─► [Get Spawn Behind] ─► [Bool to Int] ─Index─► [Select Vector]
                                                  └────Index─► [Select Rotator]

GunLoc ─► [Subtract] A (B <- Forward x 60) ─► [Subtract] A (B <- same Forward x 60)
                                                   └─Option 1─► [Select Vector]
[Add muzzle] ─────Option 0─► [Select Vector] ─Return─► SpawnTransform_Location

GunRot ───────────► [Add (Rotator)] A   (B <- Make Rotator: Pitch 180) ─Option 1─► [Select Rotator]
GunRot ───────────Option 0─► [Select Rotator] ─Return─► SpawnTransform_Rotation
```


### 3.1 Spawn clearance — why only Inverse pushes the player

This is not a `Shoot` movement node and it is not Dash. It is a collision
depenetration caused by spawning a blocking projectile inside the player.

| Quantity | Current 60uu build | 120uu build (horizontal aim) |
|---|---|---|
| `Gun` relative X (flips with facing) | ±50 | ±50 |
| Rear offset from `Multiply` | 60 | 60 × 2 = 120 |
| Inverse point from actor axis | `abs(50 − 60)` = **10uu** | `abs(50 − 120)` = **70uu** |
| Player capsule radius | **34uu** | 34uu |
| `BP_Projectile` Box half-extent along the shot | 20uu | 20uu |
| Result | box starts inside the capsule → **overlap** | nearest box edge ≈ 50uu → **clear on a horizontal shot** |

`BP_Projectile.BeginPlay` calls `IgnoreActorWhenMoving(shooter, true)`. That
makes the **projectile's sweep** ignore the player. It does **not** add the
projectile to the player capsule's ignore list, so the player still sees a
`BlockAllDynamic` box overlapping it and CharacterMovement resolves the
penetration. Because the projectile leaves on its own tick, the result is a
one-frame position snap ("jerk"); if it spawns against a wall or the box stays
overlapped, the snap repeats and reads as a dash. Normal shots are at
`|50| + 60 = 110uu` and never overlap, which is why the bug looked
Inverse-only.

> **120 is not a universal cure.** The rear point travels on a circle around
> the gun. With `Gun` at ±50 and the capsule at 34uu, a steep up/down aim can
> still put the arc back through the capsule even at 120. The robust fix is to
> stop the player from resolving the projectile, not just to move it farther
> away.

**Fix A (robust, one dropdown): let the engine clear the spawn.** Set the
`Spawn Actor from Class` node's **Collision Handling Override** to
`AdjustIfPossibleButAlwaysSpawn` (it must stay "AlwaysSpawn" at the end of the
name so a blocked rear still produces a bullet). The engine finds a nearby
non-overlapping spawn before the projectile ticks. The bullet may be nudged a
few uu off the exact rear line, but the player can no longer be depenetrated.

**Fix B (also recommended): add the second Subtract from §3 step 4b.** Keep the
normal muzzle at 60; the inverse point becomes 120uu from the gun. This removes
the overlap for horizontal/near-horizontal aim, so the engine adjustment in
Fix A rarely has to move the bullet. It is a visual-clearance improvement, not
a proof for every aim angle.

**Fix C (exact rear distance): make the player ignore the projectile.** In
`BP_Projectile.BeginPlay`, cast `shooter` to `Character`, get its
`CapsuleComponent`, and call `IgnoreActorWhenMoving(self, true)`; optionally
remove it in `EndPlay`. This preserves the 60/120uu rear point for every aim
angle but adds a cast + call and a cleanup path.

**Do not increase the existing `Multiply` B to 120.** That node also feeds the
normal `Add` muzzle, so every normal shot would start `170uu` from the actor
instead of `110uu`. Add the second Subtract so only the inverse branch grows.

### Why pitch 180 and not yaw 180

For a rotator `(Pitch, Yaw)` the forward vector is
`(cosP·cosY, cosP·sinY, sinP)`. Adding **180 to pitch** negates all three
components:

```text
forward(P+180, Y) = (−cosP·cosY, −cosP·sinY, −sinP) = −forward(P, Y)
```

Adding 180 to **yaw** keeps `sinP` unchanged, so aiming up would still shoot
up — only mirrored left/right. That is the tempting wrong answer; the sanity
check is "aim straight up → the bullet must go down", which only pitch+180
satisfies.

The bullet's sprite is rotated with the actor, so the art points along its
travel. Pitch 180 also turns the sprite 180° in the view plane; for a small
ammo sprite this reads fine. If a future bullet has readable top/bottom detail,
set the `Sprite` component's relative rotation by 180° roll when the effect is
inverse — do not change the velocity math.

### Why not a `Branch` with two spawn nodes

The fire chain already has one `Spawn Actor` node carrying the class, the
collision override, `Effect Class` and `Shooter`. A Branch would duplicate all
four pins and the two copies would drift apart on the next fix. Two pure
`Select`s keep one spawn path and no new exec wire — nothing in the exec chain
(`Tunnel → Branch → Spawn`) changes.

### Why not a negative `Speed`

Setting `Speed = −3000` does reverse the velocity, but the bullet still
**spawns at the front muzzle** and flies backwards through the player: it is
visible in front for a frame and the sprite points the wrong way. The spec is
"comes from the back", so the spawn point has to move too. The flag covers
both halves in one place.

### Who owns what — why the fork is in `Shoot`

The five effects are **not** implemented inside `BP_Player.Shoot`:

| Piece | Asset | Owns |
|---|---|---|
| Trigger + fire gate + spawn transform | `BP_Player.Shoot` (collapsed graph) | `Can Fire`, the gun's transform, spawning **one** `BP_Projectile` with `Effect Class` and `Shooter` |
| Projectile lifecycle | `BP_Projectile` | spawns one effect instance per bullet, velocity/gravity, hit → damage/kill, bounce |
| Effect data + wall policy | `BP_EffectBase` + five child CDOs | `CanFire`, `Damage`, `Speed`, `Bounces`, `GravityScale`, `CanHitShooter`, `SpawnBehind`, `OnWallHit` |

The only effect-specific thing in `Shoot` is reading `SpawnBehind` to choose the
spawn point/rotation. That is deliberate: the **spawner** owns the transform,
and the **effect** owns the data. The effect cannot spawn itself without a world
context, and duplicating the spawn actor into five child graphs would drift.

If you want *zero* effect-specific branches in `Shoot`, the cleaner data model is:

* add `Spawn Offset` (Vector) and `Spawn Rotation Offset` (Rotator) to
  `BP_EffectBase`;
* `Shoot` always applies `GunLoc + forward×60 + effect.SpawnOffset` and
  `ComposeRotators(GunRot, effect.SpawnRotationOffset)`;
* `BP_Effect_Inverse` sets `SpawnOffset = (−180, 0, 0)` (the base is +60, so the
  rear point is −120 and clears the capsule) and
  `SpawnRotationOffset = (Pitch 180)`;
* every other effect leaves both at zero.

That removes both `Select`s and the `SpawnBehind` read from `Shoot`; the
Inverse data lives entirely on its CDO. It needs two new Blueprint variables and
a rewire, so it is editor work (`Structure.md` §11), not something the Python
scripts can author.

---

## 4. Add it to the kill pool

The kill roll reads `BP_Player.Effect Classes` (`EffectSwitchOnKill.md` §2).
Add `BP_Effect_Inverse` as the **4th** entry; the roll graph is data-driven and
needs **no** edit.

Either:

* run `py -3 Scripts/_make_shooting.py` — §7b appends the child to the pool if
  it is missing (it prints `pool: appended BP_Effect_Inverse (4 entries)`), or
* `BP_Player` → **Class Defaults** → `Effect Classes` → `+` → pick
  `BP_Effect_Inverse` → **Compile + Save**.

Consequences:

* The pool is `Basic · Ricochet · Heavy · Inverse` (Jammed stays out — a kill
  must not leave the gun silent).
* The existing "exclude the live class" rule still holds, so each kill is now
  **1-in-3** for each of the other effects; two kills in a row can never roll
  the same class.
* Adding a fifth effect later is one more CDO entry, same as this one.

---

## 5. No debug key — the kill roll is the switch

There is no `Effect_Inverse` input mapping and no `Effect_Inverse` event in
`BP_Player`. `Inverse` is acquired the same way as the other three effects:
kill an enemy, let `RandomizeEffectClass` pick from `Effect Classes`
(`EffectSwitchOnKill.md`), then fire. The old keys `1`–`4` remain only as
existing debug shortcuts; they are not part of this effect's acceptance path.

If you add a temporary local key event while testing, do **not** commit it and
do **not** make the verifier require it.

---

## 6. Verify

Editor open, PIE stopped:

```text
py -3 Scripts/_make_shooting.py          # creates BP_Effect_Inverse, CDO values, pool entry
py -3 Scripts/_verify_shooting.py        # live readback + fresh T3D exports + markers
py -3 Scripts/_verify_effect_on_kill.py  # the pool line should list 4 classes
```

Before §1's variable is on **the base**, `_make_shooting.py` prints
`PENDING SpawnBehind -> True` for `BP_Effect_Inverse` (the property does not
exist on the child) — re-run it after moving the knob. If the knob is still on
`BP_Effect_Basic`, `_verify_shooting.py` prints `PENDING BP_EffectBase.SpawnBehind`
and names the child that owns the stray copy. The current verifier output is:

```text
PASS  BP_EffectBase.SpawnBehind variable
PASS  BP_Effect_Inverse.SpawnBehind == True
PASS  BP_Effect_Inverse parent is BP_EffectBase
PASS  Dash -> SpaceBar
PASS  Dash is not on LeftMouseButton (LMB is Fire only)
PASS  Spawn Behind get (fire chain)
PASS  reversed rotation (Add/Compose)
PASS  the inverse spawn chain: typed Selects <- SpawnBehind (rear + pitch 180)
WARN  inverse rear clearance is still one Subtract (60uu): the spawn is 10uu
      from the actor axis, inside the 34uu capsule; the player can jerk/dash in
      PIE. Set Collision Handling Override to AdjustIfPossibleButAlwaysSpawn
      and add the second Subtract (InverseShot.md 3.1 / step 4b)
PASS  every debug key present calls Set Effect Class (the function)
```

After the robust §3.1 fix it becomes:

```text
PASS  inverse spawn uses AdjustIfPossibleButAlwaysSpawn (the engine moves it
      out of the player capsule); rear Subtracts: 2
```

If you only changed the override and skipped Fix B, the last part reads
`rear Subtracts: 1`; that is still a PASS because the spawn is adjusted.

If you only add the second Subtract and leave `AlwaysSpawn`, the check stays a
WARN on purpose: 120uu clears horizontal aim, but a steep up/down aim can still
put the rear arc through the capsule.

The topology check (`_inverse_chain` in `_verify_shooting.py`) follows the
wires, not merely node presence. It accepts the generic `Select` + `Bool to
Int` shape and the typed `Select Vector` / `Select Rotator` shape. For the
typed shape it requires both `bPickA` pins to share one `SpawnBehind`, true/A
to be `Subtract_VectorVector`, false/B to be `Add_VectorVector`, true/A on the
rotator to be `ComposeRotators` / `Add_RotatorRotator`, false/B to be
`K2_GetComponentRotation`, and `Make Rotator` to carry pitch 180. A wrong yaw
flip, a Select fed by a constant, or **swapped A/B options** FAILs.

**The topology check cannot see spawn clearance.** A 60uu rear point passes
`_inverse_chain` because it is still a `Subtract`; only PIE shows the player
depenetration. After the §3.1 Fix B, `Shoot` should contain **two**
`Subtract_VectorVector` nodes in the inverse branch; the primary Fix A is the
`AdjustIfPossibleButAlwaysSpawn` dropdown, which the verifier also reads. Run
the read-only geometry probe too:

```text
py -3 Scripts/_probe_inverse_push.py
```

It prints the live player capsule radius, the projectile Box extents and the
current `Fire`/`Dash` mappings; the inverse point is inside the capsule when
`|GunX − rearOffset| < capsuleRadius` and the Box overlaps. Expected after the
fix: center 70uu from the actor axis, nearest box edge 50uu, i.e. 16uu outside
the 34uu capsule.

Manual graph dump (offline, no editor needed once exported):

```text
py -3 Scripts/_dump_graph.py <BP_Player.T3D> _tmp_player_dump.txt BP_Player
```

Then look for `MemberName="SpawnBehind"`, `Subtract_VectorVector`,
`ComposeRotators` / `Add_RotatorRotator`, and either the two `K2Node_Select`
nodes or the typed `SelectVector` / `SelectRotator` calls inside `Shoot`.

---

## 7. PIE checklist

> **Before this list: Compile + Save `BP_Player`, stop PIE, then start PIE again.**
> A graph edit does not update a running PIE session. Input mappings are read at
> editor start; Dash is Spacebar only, and LMB is Fire only (no shot-dash).

| # | Do | Expect |
|---|---|---|
| 0 | **Deterministic fork test:** temporarily set `BP_Player` Class Defaults → `Effect Classes` to `BP_Effect_Basic` + `BP_Effect_Inverse` only, then kill an enemy while Basic is live | the next class **must** be Inverse (1-of-1); revert the pool to all four afterward |
| 1 | Kill an enemy until the roll lands on Inverse | the next LMB is an inverse shot (the pool has 4 entries) |
| 1b | **Clearance test:** with Inverse live, stand still and LMB repeatedly while aiming left, right, up, down and diagonally | the **player does not jerk or slide/dash**; only the bullet moves. If the player snaps, set `Spawn Actor → Collision Handling Override` to `AdjustIfPossibleButAlwaysSpawn` (the robust fix), add §3 step 4b for horizontal clearance, Compile + Save, and restart PIE |
| 2 | Aim straight up with Inverse live, LMB | the bullet starts below the player and travels **down** |
| 3 | Aim down with Inverse live, LMB | the bullet starts above the player and travels **up** |
| 4 | Face left / right and repeat | the rear point follows the **aim line**, not the body facing; the shot always leaves opposite the crosshair |
| 5 | Walk backwards until the back touches a wall, then fire | the bullet still spawns (`AdjustIfPossibleButAlwaysSpawn` keeps the Always-Spawn fallback); it may die immediately on the wall — acceptable, not a crash |
| 6 | Fire normally with a non-Inverse effect | normal muzzle shot still leaves the front; the player does **not** move |
| 7 | Kill again while Inverse is live | the roll skips Inverse and picks one of the other three |
| 8 | After shooting, check the World Outliner | no leftover `BP_Effect_*` actors (the 5.6 cleanup still runs) |
| 9 | Watch the player's HP while firing backwards | the shooter ignore still applies; an inverse bullet must not kill its owner |

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| The knob appears on `BP_Effect_Basic` but not on `BP_Effect_Inverse` / Ricochet / Heavy / Jammed | It was added to a **child**, not the base. Siblings do not inherit from each other: delete it from Basic, add `SpawnBehind` to `BP_EffectBase`, compile the base **and** the children, then re-run `_make_shooting.py`. `_verify_shooting.py` prints `PENDING BP_EffectBase.SpawnBehind` until this is fixed. |
| The graph verifies PASS but PIE looks unchanged | Compile + Save `BP_Player`; stop PIE and start a fresh session. A running PIE keeps the old compiled class even after the graph is edited. Confirm the roll actually changed the gun (`SetEffectClass` destroys and respawns `Gun Effect`). |
| The variable was typed as `Spawn Behind` (with a space) | The UI's "Spawn Behind" is the friendly name generated from `SpawnBehind`; a literal space stores a different `FName`. Rename it to `SpawnBehind` (the UI keeps displaying "Spawn Behind"). The verifier accepts either spelling, but `SpawnBehind` is the canonical name in the T3D markers and this build card. |
| The bullet still leaves the front | With typed `Select Vector` / `Select Rotator`, `bPickA` true must pick **A = rear/reversed**; if A is the front option the fork is inverted. Swap A/B on both nodes. Also check the `Spawn Behind` get targets **Gun Effect**, not the class. |
| Aiming up still shoots up (only mirrored sideways) | The rotation was built with **yaw** 180. Use **pitch** 180 (§3). |
| The bullet leaves the front but flies backwards | The location Select is correct but the rotation Select uses `Get Component Rotation` on both options. The reversed option must be `Compose Rotators` / `Add (Rotator)`. |
| **Only Inverse jerks the player, and sometimes looks like a dash** | The inverse spawn is inside the player capsule: `Gun` ±50 and rear 60 gives a point 10uu from the actor axis; the capsule is 34uu and the projectile Box is 20uu. `IgnoreActorWhenMoving` only protects the bullet's sweep, not the player. **Robust fix:** set `Spawn Actor → Collision Handling Override` to `AdjustIfPossibleButAlwaysSpawn`; **also** add the second `Subtract` from §3 step 4b so horizontal aim starts 120uu back. This is **not** Dash: a stale LMB→Dash would move **every** shot, not only Inverse. Run `py -3 Scripts/_probe_inverse_push.py` to print the capsule/box geometry. |
| Normal LMB shot moves the player | `Dash` is still mapped to `LeftMouseButton`. Remove that line from `DefaultInput.ini`, restart the editor, and run `_verify_shooting.py`; it must print `PASS Dash is not on LeftMouseButton (LMB is Fire only)` with no `live Dash mappings: 2` warning. |
| No dash when Spacebar is pressed | `DefaultInput.ini` is read at editor start. Restart the editor after the `Dash -> SpaceBar` mapping. |
| Inverse never appears after many kills | Watch `Gun Effect` in the World Outliner after each kill: if its class never changes, `RandomizeEffectClass` is not reaching `SetEffectClass` (stale compiled `BP_Player` is the usual cause). If it does change but never to Inverse, use the deterministic row 0 above or re-check the 4-entry pool. |
| A kill never rolls Inverse | `BP_Effect_Inverse` is missing from `BP_Player.Effect Classes` (Class Defaults), or the pool read is stale in the running editor — re-run the make script and check the pool line. |
| The player dies on its own inverse shot | You removed/modified the hard-coded `Ignore Actor When Moving(Shooter, true)` in `BP_Projectile` BeginPlay (5.3 step 6). That ignore keeps the bullet from hitting its owner; it is separate from the spawn-clearance fix in §3.1. |
| The bullet is stuck where it spawns | The rear point is inside geometry (back against a wall) and the first sweep hit something. Not a graph bug; add clearance if it becomes common. |

---

## 9. Commit (editor closed)

```text
feat: inverse-shot effect — Spawn Behind knob, BP_Effect_Inverse, kill-roll pool
```

The scripted half created `BP_Effect_Inverse.uasset`; the manual half added the
`Spawn Behind` variable and the eight-node `Shoot` fork (including the second
clearance `Subtract`). Re-export both T3Ds
before committing so the verifier can read the built state.

Before staging, check the stray-knob cleanup:

```text
git diff -- Content/DontTrustTheLevels/Weapons/Blueprints/BP_Effect_Basic.uasset
```

If the only change there was the `Spawn Behind` variable added to Basic (§1),
delete it, save Basic, and then restore the asset so it is not part of the
commit:

```text
git checkout -- Content/DontTrustTheLevels/Weapons/Blueprints/BP_Effect_Basic.uasset
```

`BP_Player.uasset` must be committed by the lock owner (`DC2828`) or after the
lock is released; do not commit an unrelated locked asset.
