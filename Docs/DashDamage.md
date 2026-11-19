# DashDamage.md -- dash damage, i-frames and pass-through

**Owner:** Player pillar - **Branch:** `branch/Dennis` - **Status:** prepared
13 Nov 2026 (Blueprint graph work pending; no-knockback damage type added)

**Goal:** dashing is a dodge **and** an attack:

- The player passes through normal enemies, trap triggers, enemy projectiles
  and toxic puddles during the dash.
- The **Spike Turtle** is the exception: its capsule still blocks the dash.
- A dash deals **1 damage** to each enemy it passes through, once per dash.
  Damage uses the same eligibility gate as a bullet, so an invulnerable phase
  (spikes-out turtle, hidden Ghost, ON Floating Skull, Rhino, Snail shell)
  takes nothing.
- Dash damage carries the **`BP_DamageType_Dash`** marker. The enemy still
  loses health, flashes, plays its hit animation and dies normally, but it
  **does not receive the normal knockback**; a dash must not shove an enemy
  along the dash direction. Bullets keep their normal knockback.
- The player is invincible for a few frames at the start of the dash. When the
  i-frame window ends, collision is restored. If the player is still inside a
  dangerous enemy at that moment, the player dies.

This builds on `DashAiming.md`. That document owns movement, aim and the
`Dash` input; this one only adds the collision / damage layer.

**Visual graph:** open [`dash_damage_graph.html`](dash_damage_graph.html) for the
hand-authored `BeginDashInvincibility` / `TryDashDamage` /
`EndDashInvincibility` node wires, the three call-site edits and the enemy
no-knockback branch.

---

## 1. Why this needs no new collision channel or interface

The live collision setup already separates the cases:

| Actor / component | Object type | Response relevant here |
|---|---|---|
| Player `CapsuleComponent` | `Pawn` | profile `Pawn`; blocks `WorldStatic` / `WorldDynamic`, blocks `Pawn` |
| Normal enemy `CollisionCylinder` | `Pawn` | `Pawn = Overlap` (the player passes through and overlaps it) |
| `BP_SpikeTurtle.CollisionCylinder` | `Pawn` | `Pawn = Block` (the only enemy body that stops the player) |
| Enemy `ContactBox` | `WorldDynamic` | `Pawn = Overlap`, all other channels `Ignore` |
| `BP_TrapBase.Trigger` | `WorldDynamic` | `OverlapAllDynamic` |
| `BP_Trap_FakeFloor.TriggerBox` | `WorldDynamic` | `OverlapAllDynamic` |
| `BP_Trap_FakeFloor.FloorBox` | `WorldStatic` | `BlockAll` (the solid floor) |
| `BP_KillVolume.KillBox` | `WorldDynamic` | `OverlapAllDynamic` |
| Enemy projectile collision | `WorldDynamic` | `BlockAllDynamic` |
| `BP_ToxicPuddle.RenderComponent` | `WorldStatic` | `BlockAll` (the one static hazard; handled by tag below) |
| Walls and normal floor | `WorldStatic` | blocked by the player |

Therefore one change is enough:

> **During the dash, set the player capsule's `WorldDynamic` and
> `PhysicsBody` responses to `Ignore`, and set the player `Sprite` collision to
> `NoCollision`.** Restore them when the i-frame timer expires.

The `Sprite` matters even though it is `QueryOnly`: trap triggers and enemy
projectiles fire overlap/hit events when **either** side has collision enabled
and one side generates events. A trigger with `Generate Overlap Events` ticked
would still see the player through the sprite if only the capsule were changed.
Disabling the sprite for the same window is simpler than changing two
responses on a component that has no gameplay role.

`BP_ToxicPuddle.RenderComponent` is the one `WorldStatic` hazard. Ignoring
`WorldStatic` globally would make the player dash through walls and floors, so
the dash instead calls `IgnoreActorWhenMoving` on every actor tagged
`Enemy.Hazard` (the puddle's documented tag); the solid `WorldStatic` world
remains untouched.

That makes the player pass through:

- enemy `ContactBox` components (so their contact `Kill` cannot fire),
- trap `Trigger` / `TriggerBox` volumes,
- enemy projectile and toxic-puddle collision,
- the `BP_KillVolume` box.

It deliberately does **not** touch `Pawn`:

- normal enemies are `Pawn = Overlap`, so the player already passes through
  them and the player capsule still receives `BeginOverlap` events;
- the Spike Turtle is `Pawn = Block`, so it still stops the dash.

It also leaves `WorldStatic` alone, so walls and the real floor still stop the
dash. **Never put walkable ground on `WorldDynamic`** -- a dash would fall
through it.

There is no `BPI_DashDamage` interface. `ApplyDamage` already reaches
`BP_EnemyBase.Event AnyDamage`, whose first gate is:

```text
if bIsDead OR bInvulnerable OR bIFrameActive OR NOT bUseHealth -> return
```

That is exactly "only enemies, or the enemy phase that a bullet can hurt".
A dash hit therefore reuses the bullet contract instead of adding a second
damage path that could drift from it.

The one enemy-side difference is the damage type. The dash passes
`BP_DamageType_Dash` and `BP_EnemyBase.Event AnyDamage` branches on it at the
end of its non-lethal path, before `SET bWasKnockedBack` and `LaunchCharacter`.
The health / hit-reaction / death chain above has already run, so the hit is
still a normal hit; only the shove is skipped. Section 8.1 has the exact graph
change.

---

## 2. Variables on `BP_Player` (Category `Dash`)

Add these four in **My Blueprint -> Variables**:

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `bDashInvincible` | Boolean | `false` | blocks `Kill` and is the timer's live flag |
| `DashIFrameDuration` | Float | `0.20` | length of the i-frame / pass-through window; keep it **>= `DashDuration`** (`0.15`) |
| `DashDamage` | Float | `1.0` | damage per enemy per dash; same value as a Basic bullet |
| `DashHitActor` | Array of Actor | empty | one hit per enemy per dash |

`DashHitActor` is cleared at the start of every dash, not at the end: a dash
that is stopped early by a wall still completes its i-frame window, and a later
dash must start with a fresh list.

## 3. Start of the dash: begin the i-frame window

In `BP_Player -> Functions -> Dash Logic`, continue the existing chain **after**
`SET bIsDashing = true` (S3) and before it starts moving the player. In the
current graph the next exec pin is `LaunchCharacter`; the per-tick
`AddActorWorldOffset` lives in `Dashing Logic`, so the call is already in place
before movement begins.

Add a new function **`BeginDashInvincibility`** (no inputs, no outputs) with
this body:

| # | Node | Wiring |
|---|---|---|
| 1 | **Clear** (Array) | Target = `DashHitActor` |
| 2 | **SET bDashInvincible** | value `true` |
| 3 | **CapsuleComponent -> Set Collision Response to Channel** | Channel = `WorldDynamic`, New Response = `Ignore` |
| 3a | **Sprite -> Set Collision Enabled** | `NoCollision` (it is `QueryOnly` normally; this stops it re-triggering traps/projectiles/puddles) |
| 4 | **CapsuleComponent -> Set Collision Response to Channel** | Channel = `PhysicsBody`, New Response = `Ignore` |
| 5 | **Set Timer by Function Name** | Function Name = `EndDashInvincibility`, Time = `DashIFrameDuration`, Looping = false |
| 5a | **Get All Actors with Tag** | Tag = `Enemy.Hazard`; output -> `ForEachLoop` |
| 5b | **ForEachLoop `Array Element` -> CapsuleComponent -> Ignore Actor When Moving** | `Actor` = element, `bShouldIgnore` = `true`; skips the `WorldStatic` toxic puddle without touching walls/floors |
| 6 | **CapsuleComponent -> Get Overlapping Actors** | Class Filter = `BP_EnemyBase`; output -> `ForEachLoop` |
| 7 | **ForEachLoop `Array Element` -> `TryDashDamage`** | handles an enemy that was already touching the player when the dash began |

Chain: `Entry -> 1 -> 2 -> 3 -> 3a -> 4 -> 5 -> 5b (ForEach loop) -> 6 (ForEach loop) -> 7 -> Return`.

`Get All Actors with Tag` (5a) and `Get Overlapping Actors` (6) are **pure data
nodes** in 4.27: they have no exec pins. Wire their array output into the
`ForEachLoop`, and send the exec wire from `5` into the loop, not into the
getter. The same rule applies to the end-of-window loop in §5.

Call `BeginDashInvincibility` from the `Dash Logic` chain immediately after
`SET bIsDashing = true` and before `LaunchCharacter`. Do **not** call it from
`EndDash`: `EndDash` runs on a wall hit and on normal completion, while the
i-frame window is time-based.

> Why step 6 is needed: `Actor Begin Overlap` (or `OnComponentBeginOverlap`)
> only fires when an overlap *begins*. If the player starts a dash already
> standing inside a normal enemy, no new overlap event occurs. The initial
> `GetOverlappingActors` loop covers that case.

---

## 4. Dash damage: one hit per enemy per dash

### 4.1 `TryDashDamage` function

New function on `BP_Player`:

| # | Node | Wiring |
|---|---|---|
| 1 | **Actor Has Tag** | Target = `Other Actor`; Tag = `Enemy` |
| 2 | **Branch** | Condition = result of #1. False -> return. True -> continue |
| 3 | **Array Contains** | Target = `DashHitActor`; Item to Find = `Other Actor` |
| 4 | **Branch** | Condition = result of #3. True -> return (already hit this dash). False -> continue |
| 5 | **Add Unique** | Target = `DashHitActor`; New Item = `Other Actor` |
| 6 | **Apply Damage** | Damaged Actor = `Other Actor`; Base Damage = `DashDamage`; Damage Causer = **Self**; Event Instigator = **Self -> Get Controller**; Damage Type Class = **`BP_DamageType_Dash`** |

Chain: `Entry -> 1 -> 2 (False return / True) -> 3 -> 4 (True return / False) -> 5 -> 6 -> Return`.

`Other Actor` must be an **Actor** object reference, not `BP_EnemyBase`.
`Get Overlapping Actors` is declared as `TArray<AActor>`; its `Class Filter`
only filters the results, so the loop's `Array Element` is still an `Actor` and
cannot be wired into a `BP_EnemyBase` input without an explicit Cast.

`Actor Has Tag "Enemy"` covers every enemy, including the Spike Turtle. The
turtle is still filtered out of damage by its own `bInvulnerable` /
`bUseHealth = false` gate. It does not matter that the turtle is also blocked:
if a future change lets the player reach it, `ApplyDamage` still does nothing.

`ApplyDamage` is intentional, not `Kill`. It reaches `AnyDamage`, applies the
enemy's health, plays its hit reaction and lets its `bInvulnerable` phase
decide whether the hit exists at all. Do **not** call `Kill` from the dash;
that would ignore health and turn every dash into a one-shot.

Set the `Apply Damage` node's **Damage Type Class** pin to
`BP_DamageType_Dash` (the saved asset is
`Content/DontTrustTheLevels/Player/Blueprints/BP_DamageType_Dash.uasset`).
It is a plain Blueprint child of `DamageType` with no variables and no graph.
Do not leave the pin at its default `DamageType`: the enemy uses this class to
skip knockback. The pin is a class pin, so there is no extra node to add in
`TryDashDamage`.

### 4.2 Player overlap event

In `BP_Player`'s event graph, use **Actor Begin Overlap** (the event currently
wired in the graph). It fires for the player capsule's overlaps and supplies
`Other Actor`. Binding `CapsuleComponent` -> **On Component Begin Overlap** is
an equivalent alternative if you want the event scoped to that component.

```text
Actor Begin Overlap
  -> Other Actor
  -> Branch: bIsDashing?
       False -> (return)
       True  -> TryDashDamage(Other Actor)
```

The event only matters while dashing: the capsule overlaps a **normal** enemy's
Pawn capsule, while enemy `ContactBox` overlaps are ignored during the dash, so
the dash cannot be mistaken for contact damage.

## 5. End of the i-frame window: restore collision and check the exit

Create function **`EndDashInvincibility`** (no inputs, no outputs). It is the
timer target from step 3.5.

| # | Node | Wiring |
|---|---|---|
| 1 | **SET bDashInvincible** | value `false` |
| 2 | **CapsuleComponent -> Set Collision Response to Channel** | Channel = `WorldDynamic`, New Response = `Block` |
| 2a | **Sprite -> Set Collision Enabled** | `QueryOnly` (restore its `CharacterMesh` profile) |
| 3 | **CapsuleComponent -> Set Collision Response to Channel** | Channel = `PhysicsBody`, New Response = `Block` |
| 3a | **Get All Actors with Tag** | Tag = `Enemy.Hazard`; output -> `ForEachLoop` |
| 3b | **ForEachLoop `Array Element` -> CapsuleComponent -> Ignore Actor When Moving** | `Actor` = element, `bShouldIgnore` = `false` |
| 4 | **CapsuleComponent -> Get Overlapping Actors** | Class Filter = `BP_EnemyBase`; output -> `ForEachLoop` |
| 5 | **Cast To BP_EnemyBase** | Object = loop `Array Element` |
| 6 | **Branch** | Condition = `NOT bIsDead AND bDealContactDamage` |
| 7 | **Kill (Message)** | Target = **Self**; reached only on the True pin of #6 |

The branch is what makes the rule exact: if the player finishes the dash
inside a live, contact-dangerous enemy, the enemy must not get a free pass
because its `BeginOverlap` already happened while collision was ignored.
`bDealContactDamage` is the same flag the enemy's own contact chain uses, so
the late check cannot kill the player through a harmless phase:

| Enemy state | `bDealContactDamage` | Late check |
|---|---|---|
| Snail / walker / rock / bat (after trigger) | `true` | player dies |
| Ghost visible | `true` | player dies |
| Ghost hidden | `false` | safe |
| Floating Skull ON | `true` | player dies |
| Floating Skull OFF | `false` | safe (it can be hit, not touched) |
| Spike Turtle, spikes out | `true` | player dies if the contact box still overlaps |
| Spike Turtle, spikes in | `false` | safe |
| Dead enemy | `bIsDead = true` | skipped |

Trap triggers and enemy projectiles are `WorldDynamic`; step 2 restores them
and their own `BeginOverlap` / `Hit` event fires on the next overlap update.
The toxic puddle is restored by releasing its `IgnoreActorWhenMoving` entries
in step 3a/3b. The explicit late check is for enemy `ContactBox`es because they
are `QueryOnly` and are the component most likely to remain overlapped without
a fresh event. If a trap needs the same guarantee later, give its trigger
component a `DashHazard` component tag and add that tag to the late check;
do not add the tag to the whole trap actor (the Fake Floor's solid sprites
would match it).

---

## 6. `Kill` gate

While `bDashInvincible` is true, the player must ignore any `Kill` that was
already in flight before collision was turned off. In the existing
`BP_Player -> Kill Logic` composite, the first `Branch` currently reads
`bIsDead`. Replace its condition with:

```text
(bIsDead) OR (bDashInvincible)
```

Both True and False outputs keep their existing destinations: **True -> return**
(no death), **False -> continue** with the normal death chain. Use an **OR**
node; do not add a second Branch before the timer, because `bIsDead` must still
short-circuit a real death.

Do **not** replace the player's `Kill` with `ApplyDamage`: the player has no
health today (`Enemies.md` §2.2). `bDashInvincible` is only an i-frame gate;
the normal `Kill` -> level reload path is unchanged when the flag is false.

## 7. Collision matrix (what the player touches during the dash)

| Thing | Channel | Dash response | Result |
|---|---|---|---|
| Wall / normal floor | `WorldStatic` | `Block` (unchanged) | dash stops at the wall/floor |
| Player `Sprite` (second collider) | all channels | `NoCollision` | the sprite cannot re-trigger a trap/projectile/puddle while the capsule is intangible |
| Normal enemy body | `Pawn` | `Block` on player, `Overlap` on enemy | no push; overlap event -> `TryDashDamage` |
| Spike Turtle body | `Pawn` | `Block` on both | **dash stops**; no pass-through |
| Enemy `ContactBox` | `WorldDynamic` | `Ignore` | no contact `Kill` during the dash |
| Trap `Trigger` / `TriggerBox` | `WorldDynamic` | `Ignore` | trap does not pop / drop during the dash |
| Enemy projectile | `WorldDynamic` | `Ignore` | projectile passes through |
| Toxic puddle | `WorldStatic` | `IgnoreActorWhenMoving` (`Enemy.Hazard`) | no puddle contact during the dash; walls/floors are not ignored |
| `BP_KillVolume.KillBox` | `WorldDynamic` | `Ignore` | dash may cross the pit volume |
| Fake Floor `FloorBox` | `WorldStatic` | `Block` | still a solid floor; only its trigger is dodged |
| Fake Floor sprite components | `WorldDynamic` | `Ignore` | pass through the visual slab |
| Spike Trap sprite | `NoCollision` | unchanged | no effect (already non-colliding) |

The matrix is why `Pawn` must not be ignored: doing that would also remove the
Spike Turtle's body collision, and "except the turtle" would be lost.

---

## 8. Enemy phase eligibility (same as a bullet)

`BP_EnemyBase.Event AnyDamage` is the single decision point:

| Enemy / phase | Can dash damage it? | Why |
|---|---|---|
| Walker, rock, bat (after trigger), visible Ghost, OFF Skull, Snail outside shell | yes | `bInvulnerable = false`, `bUseHealth = true` |
| Spike Turtle | **no** | `bInvulnerable = true`, `bUseHealth = false`; body also blocks |
| Rhino | **no** | `bInvulnerable = true`; only wall hits reduce its 4 health |
| Ghost hidden | **no** | `bInvulnerable = true` and collision off |
| Floating Skull ON | **no** | `bInvulnerable = true`; OFF = vulnerable |
| Snail shell phase | **no** | `bInvulnerable = true` during the shell |
| Dead enemy | **no** | `bIsDead = true` |

A dash never bypasses a phase gate. If a future enemy adds a new invulnerable
phase, it only has to set `bInvulnerable`; this feature needs no per-enemy
change.

### 8.1 No knockback for dash damage

`BP_EnemyBase` has one shared `Event AnyDamage`; all enemy children inherit it
(verified 13 Nov 2026: only `BP_EnemyBase` has a `ReceiveAnyDamage` graph). The
knockback is the block after the `Update State For Hit` composite:

```text
Update State For Hit -> Non-lethal
  -> SET bWasKnockedBack = true
  -> SET bAggro = false
  -> SET bStranded = false
  -> SET MaxWalkSpeed = MoveSpeed
  -> SET UnreachableTime = 0
  -> LaunchCharacter(...)
```

Insert a `Branch` between the composite's **`Non-lethal`** pin and
`SET bWasKnockedBack`:

```text
DamageType -> Get Class -> Class Is Child Of (Parent Class = BP_DamageType_Dash)
                         -> Branch.Condition

Update State For Hit -> Non-lethal -> Branch
  True  (dash damage)     -> (end; no knockback state, no LaunchCharacter)
  False (bullet / other)  -> SET bWasKnockedBack -> ... -> LaunchCharacter
```

> **Do not reverse these two exec wires.** The **True** pin must stay
> unconnected and **False** must go to the existing `SET bWasKnockedBack`.
> If **True** is wired to `SET bWasKnockedBack`, the dash still launches the
> enemy even though the class check is correct. `Scripts/_verify_dash_no_knockback.py`
> checks this polarity explicitly.

The `DamageType` event pin is currently unconnected; this is the one new data
wire. `Class Is Child Of` is true for the `BP_DamageType_Dash_C` class and
false for the default `DamageType` object that a bullet passes, so ordinary
damage keeps the existing launch.

The branch must stay **after** `Update State For Hit`: health subtraction, the
red flash, hit flipbook, `LastDamageTime`, i-frames, `Die`, and the
`bIsDead / bInvulnerable / bIFrameActive / bUseHealth` gate have already run.
Do not branch before the `Should Take Damage?` gate, or dash damage would
ignore an invulnerable phase.

The True path may be left unconnected: this is an event graph, not a function,
and the hit is already complete. Leaving it open is also why the enemy keeps
its current aggro and movement instead of being stopped by `bAggro = false` and
`MaxWalkSpeed = MoveSpeed`.

---

## 9. Verification

### 9.1 Live probe (read-only, editor open)

`py -3 Scripts/_run_py.py Scripts/_probe_dash_collision.py`

Expected:

- `BP_Player` capsule: profile `Pawn`, object type `PAWN`, `Pawn = BLOCK`.
- `BP_Player` sprite: profile `CharacterMesh`, object type `PAWN`,
  `WorldDynamic = BLOCK` (this is why the sprite must be changed too).
- `BP_SpikeTurtle.CollisionCylinder`: profile `Custom`, object type `PAWN`,
  `Pawn = BLOCK`.
- `BP_SpikeTurtle.ContactBox`: object type `WORLD_DYNAMIC`, `Pawn = OVERLAP`.
- `BP_Trap...Trigger` / `TriggerBox`: object type `WORLD_DYNAMIC`.
- `BP_Trap_FakeFloor.FloorBox`: object type `WORLD_STATIC`.

If the turtle capsule is not `Pawn = Block`, stop: the exception cannot work.

### 9.2 PIE matrix (`L_Level_01`)

| # | Test | Expected |
|---|---|---|
| 1 | Dash through a 2+ health walker | player passes through; enemy loses 1 health, plays Hit, survives; it does **not** slide or launch along the dash direction |
| 2 | Dash through a 1-health enemy | enemy dies on the dash hit |
| 3 | Dash into the Spike Turtle | player stops at the turtle; no damage to it; if spikes are out, late check kills the player |
| 4 | Dash through active spikes | trap does **not** pop; player is not killed during the i-frame window |
| 5 | Dash through an enemy projectile | projectile passes through; no hit, no reload |
| 6 | Dash into a visible Ghost | Ghost takes 1 damage |
| 7 | Dash into a hidden Ghost | no damage; player passes through |
| 8 | Dash into a Floating Skull while ON | no damage |
| 9 | Dash into a Floating Skull while OFF | 1 damage |
| 10 | Dash into the Rhino | no damage; it keeps charging |
| 11 | End the dash inside a live walker | player dies immediately after the i-frame window |
| 12 | End the dash on a harmless phase (hidden Ghost) | player survives |
| 13 | Dash into a wall / floor | dash stops; no tunneling |
| 14 | Dash over a toxic puddle | no puddle death during the dash; walls/floor still block |
| 15 | Normal walk / jump / shoot after a dash | unchanged; collision is restored |
| 16 | Dash-hit a walker and watch its feet | it stays on its platform; only its normal AI movement resumes |
| 17 | Shoot the same walker | normal bullet knockback still launches it (the dash exception is not a global knockback removal) |

### 9.3 Static graph check after the build

`py -3 Scripts/_verify_dash_damage.py` (read-only, editor open) first checks the
three live collision premises above, then exports `BP_Player` and checks the
graph markers below. Until the `Damage Type Class` pin is set, the one expected
FAIL is `dash damage type`. The two turtle rows are PENDING, not FAIL, when
`L_Level_01` is not the open level.

Fresh export of `BP_Player` should contain:

- variables `bDashInvincible`, `DashIFrameDuration`, `DashDamage`,
  `DashHitActor`;
- functions `BeginDashInvincibility`, `TryDashDamage`,
  `EndDashInvincibility`;
- `SetCollisionResponseToChannel` on `CapsuleComponent` with
  `ECC_WorldDynamic` / `ECC_PhysicsBody`, `Ignore` at start and `Block` at end;
- `Sprite -> Set Collision Enabled` `NoCollision` at start and `QueryOnly` at
  end;
- `GetAllActorsWithTag("Enemy.Hazard")` + `IgnoreActorWhenMoving` true/false;
- `Set Timer by Function Name("EndDashInvincibility", DashIFrameDuration)`;
- `GetOverlappingActors`, `Actor Has Tag("Enemy")`, `Array Contains`,
  `Add Unique`, `ApplyDamage`;
- the `ApplyDamage` node's `DamageTypeClass` default contains
  `BP_DamageType_Dash`;
- `Kill Logic`'s first condition contains `bDashInvincible`.

The no-knockback half has its own checker:
`py -3 Scripts/_verify_dash_no_knockback.py` (read-only, editor open). It
exports both Blueprints and checks that:

- `BP_DamageType_Dash` exists and is a child of `DamageType`;
- `BP_Player.TryDashDamage.ApplyDamage.DamageTypeClass` points at it;
- `BP_EnemyBase.EventGraph` links `DamageType -> Get Class -> Class Is Child
  Of(BP_DamageType_Dash)` into a Branch;
- the Branch's True pin is empty (dash ends) and its False pin feeds
  `SET bWasKnockedBack` (the existing chain); `LaunchCharacter` is still
  present for ordinary damage;
- only `BP_EnemyBase` has a `ReceiveAnyDamage` graph, so no child needs a
  duplicate branch.

`Scripts/_verify_shooting.py` and `Scripts/_verify_effect_on_kill.py` remain
the regression checks for the projectile and effect contracts.

## 10. Troubleshooting

| Symptom | Cause -> fix |
|---|---|
| Dash passes through the Spike Turtle | `Pawn` was set to `Ignore`; only `WorldDynamic` and `PhysicsBody` may be ignored |
| Dash stops on a normal enemy | that enemy's capsule is `Pawn = Block`; it must be `Pawn = Overlap` (turtle is the deliberate exception) |
| Player still dies during the dash | `Kill Logic` does not test `bDashInvincible`, or a stale `Kill` arrives before `BeginDashInvincibility` runs; call the begin function immediately after `SET bIsDashing` |
| Player cannot dash through traps/projectiles | `WorldDynamic` is not `Ignore` on the capsule, or the `Sprite` is still `QueryOnly`; check the capsule response nodes and `Sprite -> Set Collision Enabled (NoCollision)` |
| Player cannot dash through a toxic puddle | `Enemy.Hazard` tag is missing from `BP_ToxicPuddle`, or the `IgnoreActorWhenMoving` loop is absent; do **not** solve it by ignoring `WorldStatic` globally |
| Player never takes damage after the dash | `EndDashInvincibility` did not restore the capsule responses / `Sprite = QueryOnly` / `IgnoreActorWhenMoving(false)`, or the late enemy check was omitted |
| Enemy takes repeated damage from one dash | `DashHitActor` is not cleared at dash start, or `Array Contains` is wired before `Add Unique` wrongly |
| Enemy takes no damage | missing `Actor Has Tag "Enemy"` gate, `ApplyDamage` target not `Other Actor`, or the enemy is in an invulnerable phase |
| Turtle takes damage | `AnyDamage` gate is broken; dash must reuse `ApplyDamage`, not `Kill` |
| Enemy still slides in the dash direction | `ApplyDamage`'s Damage Type Class is still the default `DamageType`, or the `Non-lethal -> Class Is Child Of -> Branch` rewire is missing; the True path must skip `SET bWasKnockedBack` and `LaunchCharacter` |
| Bullet knockback disappeared too | the dash Branch was put before `Should Take Damage?`, or its False path was not restored to the old knockback chain; only the non-lethal dash path skips it |
| Player falls through the floor during a dash | the floor is `WorldDynamic`; walkable ground must be `WorldStatic` (or the player's `WorldStatic` response was changed) |
| Dash damage hits through a wall | player capsule overlap is too large or the wall is on an ignored channel; keep walls `WorldStatic` and use the capsule, not a sphere trace |
| Normal contact damage stops working | `WorldDynamic` was left as `Ignore` after the timer; verify `EndDashInvincibility` runs and restores it |

---

## 11. Commit

**Status:** prepared; graph work is still editor-only (Python cannot create
Blueprint variables, functions or nodes -- `Structure.md` §11). The
`BP_DamageType_Dash` marker asset is already created and saved. Finish the two
graph edits (apply-damage type pin + enemy branch), compile and save both
`BP_Player` and `BP_EnemyBase`, then run PIE §9.2 before committing.

- Suggested message:
  `feat(player): dash damage + i-frame pass-through, no dash knockback`
- Files: `Content/DontTrustTheLevels/Player/Blueprints/BP_Player.uasset` ·
  `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyBase.uasset` ·
  `Content/DontTrustTheLevels/Player/Blueprints/BP_DamageType_Dash.uasset` ·
  `Docs/DashDamage.md` · `Docs/DashAiming.md` · `Docs/Enemies.md`
- The Spike Turtle exception is still its `Pawn = Block` capsule; do not edit
  `BP_SpikeTurtle` for this feature. Every enemy inherits the one
  `BP_EnemyBase` AnyDamage branch.
- Close the editor before `git add` / commit (`CLAUDE.md` hard rule 3).
