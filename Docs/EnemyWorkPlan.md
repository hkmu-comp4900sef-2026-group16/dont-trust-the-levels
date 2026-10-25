# Enemy Work Plan — three parallel workstreams

**Status (24 Oct 2026):** execution plan for the remaining enemy work. This
file assigns the work, defines the dependency gates and lists the acceptance
tests. It does **not** replace the technical design:

| Authority | File | What it decides |
|---|---|---|
| 1 | **`Docs/EnemyAI.md`** | movement, patrol, aggro, knockback, rescue; wins on conflict |
| 2 | **`Docs/Enemies.md`** | variables, graph recipes, per-enemy mechanics, test matrix |
| 3 | **`Docs/EnemyPlacement.md`** | level placement rules and per-enemy layouts |

**Audience:** Owner A, Owner B, Owner C and their AI assistants. Read this file
first, then the exact sections named in your work card. Do not infer rules from
old summaries.

**Scope:** the nine active enemy mechanics plus the projectile/puddle/shooter
support assets. `BP_PeaPlant` and `BP_EnemyProjectile_Pea` are **out of scope**
unless the design changes.

---

## 0. Owner slots

Fill in the real names before work starts. Do not change asset ownership without
updating this table and taking the Git LFS lock.

| Slot | Name / GitHub | Workstream | Assets | Can start |
|---|---|---|---|---|
| **A** | base owner | base AI + walkers | `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail`, `BP_RockBase`, `BP_Rock1/2/3`, `L_Level_01` | now |
| **B** | groupmate 1 | stationary + flyers | `BP_SpikeTurtle`, `BP_Ghost`, `BP_Bat`, `BP_FloatingSkull` | now |
| **C** | groupmate 2 | support + ranged/walkers | `BP_EnemyProjectile`, `BP_EnemyProjectile_Wood`, `BP_ToxicPuddle`, `BP_ShooterEnemyBase`, `BP_WoodLog`, `BP_ToxicSlime`, `BP_Rhino` | now |

A is the only person allowed to edit `BP_EnemyBase` until the M1 gate is posted.
B and C may build their independent assets in parallel, but **walker children
must wait for M1**. If a base change is needed, send a request to A; do not add
the variable or function to the child.

---

## 1. Read-in order (M0)

Every owner reads:

1. `Docs/EnemyAI.md` §1–2 (locked rules, state model).
2. `Docs/Enemies.md` §3–4 (base variables, functions, event graph).
3. `Docs/EnemyWorkPlan.md` §3–6 (this file: rules, ownership, gates).
4. `Docs/LfsLocking.md` (binary assets cannot merge).

Then read the sections named in your work card in §7. Read
`Docs/EnemyPlacement.md` only when you reach M4 or need a placement answer.

If two documents disagree, **stop and post the conflict** in the status log.
`EnemyAI.md` wins over `Enemies.md`; `EnemyPlacement.md` never overrides either.

---

## 2. Status at the start

**Done and verified**

- All 20 Blueprint shells exist under
  `Content/DontTrustTheLevels/Enemies/Blueprints/`.
- `BP_EnemyBase` has the shared health/damage/death/contact graph.
  `py -3 Scripts\_verify_enemy_base.py` reports **44 PASS / 0 FAIL**.
- `BP_EnemyPlatform` exists and seven auto zones exist in `L_Level_01`.
- `BPI_Killable` is implemented on `BP_EnemyBase`; traps are player-only.

**Not built**

- The shared AI core in `BP_EnemyBase` (`HomePlatform`, patrol, aggro,
  knockback/rescue).
- The projectile/puddle/shooter support graphs.
- Every child-specific AI mechanic.

**Current blockers / cleanup**

- Rename `bEnable` → `bEnabled` in `BP_EnemyPlatform`; the generator temporarily
  accepts both names.
- Do not add `MaxWalkSpeed` as a variable; it is a `CharacterMovement` property.
- Remove the duplicate typo variable `KnowbackForce` if it is still present;
  keep `KnockbackForce`.
- This UE 4.27.2 build has **no Python route to create K2 nodes**. Node
  placement, wiring, compilation and PIE are manual editor work. Python may
  create/configure shells and read T3D for verification, not author graphs.
- `BP_Snail` is currently at `(-451, 9, 225)` and does not match an auto marker.
  Do not treat that placement as a valid home-platform test.

---

## 3. Non-negotiable rules

1. **Lock before editing.** Use Git LFS / UE Source Control for every
   `.uasset` and `.umap`; commit and push promptly to release the lock. Never
   co-edit a Blueprint, and never share one working copy/editor between two
   owners.
2. **One movement authority per asset.**
   - Walkers (`Rocks`, `Snail`, `Slime`, `Rhino`, `WoodLog`) use the base
     `Event Tick` → `PatrolStep` / `ChaseStep`. Do **not** add a second movement
     `Event Tick` to a walker.
   - Stationary/flyers (`SpikeTurtle`, `Ghost`, `Bat`, `FloatingSkull`) set
     `bCanMove=false`; their own `Event Tick` / `LaunchCharacter` is the only
     movement. `ChaseSpeed=0` for Turtle/Ghost/Skull; Bat keeps the inherited
     `ChaseSpeed=300` for `MaxFlySpeed`. This is what stops the shared walker
     loop from also running.
   - `bCanMove` is a shared-AI gate, not a CharacterMovement property. Setting
     it false does not stop `Add Movement Input` or `LaunchCharacter`.
3. **No duplicate variables.** Inherit from `BP_EnemyBase`:
   `bAggro`, `AggroRadius`, `ChaseSpeed`, `MoveSpeed`, `KnockbackForce`,
   `Facing`, all health/contact variables and all three base flipbooks.
   - `BP_Ghost` must not declare `bAggro` or `AggroRadius`.
   - `BP_Bat` must not declare `ChaseSpeed`.
   - `BP_Rhino` must not declare `MoveSpeed`.
   - Child values for inherited variables belong in **Class Defaults**, not in
     a new variable.
4. **Home platform type.** `HomePlatform` should be a `BP_EnemyPlatform` object
   reference. If it is already an `Actor`, retype it or cast once in
   `FindHomePlatform`; do not cast at every use.
5. **Contact damage uses `ContactBox`**, not the blocking capsule. `ContactBox`
   is already on `BP_EnemyBase` with `Pawn=Overlap` and all other channels
   `Ignore`; do not rebuild it in a child.
6. **Compile + save after every graph or function.** A red compile error in a
   child usually means a missing parent member; do not hide it by duplicating
   the member in the child.
7. **Walkers wait for M1.** Until A posts the base gate (variables, functions,
   `PatrolStep`/`LedgeAhead`, compile clean, 44 PASS, tests 1–9), do not start
   `Snail`, `Rocks`, `Slime`, `Rhino` or the final `WoodLog` aggro wiring.
   Stationary/flyers (B) and the projectile/puddle/shooter support (C) may start
   immediately because they do not read the walker AI.
8. **Shared bases are single-owner.**
   - A only: `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_RockBase`.
   - C only: `BP_ShooterEnemyBase`, `BP_EnemyProjectile*`, `BP_ToxicPuddle`.
   - B never edits a shared base.
9. **Level map is single-owner.** Only A edits `L_Level_01`, and only in M4.
   B/C provide placement coordinates and test results; they do not open the map
   for saving.
10. **No new base classes, no Behavior Tree, no NavMesh, no C++.** No Pea Plant
    work. No Python graph authoring.
11. **Docs are contract files.** A owns edits to `EnemyAI.md`, `Enemies.md` and
    `EnemyPlacement.md`. B/C may append to the status log in this file and may
    propose a correction; they must not rewrite a contract to match their graph.
12. **Definition of done is per asset**, not "the graph looks finished": see §9.

---

## 4. Ownership map

| Asset | Owner | Depends on | Notes |
|---|---|---|---|
| `BP_EnemyBase` | A | — | AI core, M1 |
| `BP_EnemyPlatform` | A | — | rename `bEnable` → `bEnabled` |
| `BP_Snail` | A | M1 | walker; no detection |
| `BP_RockBase` | A | M1 | split logic |
| `BP_Rock1/2/3` | A | M1, `BP_RockBase` | child defaults + split |
| `BP_SpikeTurtle` | B | base health only | stationary |
| `BP_Ghost` | B | base health only | flyer, own Tick |
| `BP_Bat` | B | base health only | flyer, own Tick |
| `BP_FloatingSkull` | B | base health only | bounce, own `Event Hit` |
| `BP_EnemyProjectile` | C | — | support |
| `BP_EnemyProjectile_Wood` | C | projectile base | child defaults |
| `BP_ToxicPuddle` | C | — | support |
| `BP_ShooterEnemyBase` | C | — | support |
| `BP_WoodLog` | C | C support + M1 | walker that stops to shoot |
| `BP_ToxicSlime` | C | M1 + puddle | walker; no detection |
| `BP_Rhino` | C | M1 | walker charger |
| `BP_PeaPlant` | nobody | — | unused; do not place or extend |
| `BP_EnemyProjectile_Pea` | nobody | — | unused shell |
| `L_Level_01` | A | all behavior gates | M4 only |

If a new asset is needed, add it to this table before creating it. Do not create
a second “base” or a manager actor to avoid a dependency. Exact lock paths are
in §4.1; that list is the conflict boundary.

### 4.1 Exact files to lock (no ambiguity)

All enemy Blueprints live in
`Content/DontTrustTheLevels/Enemies/Blueprints/`. Lock the exact `.uasset`
file, never a folder; use the paths below verbatim with `git lfs lock`.

**Owner A**

- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyBase.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyPlatform.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Snail.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_RockBase.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rock1.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rock2.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rock3.uasset`
- `Content/DontTrustTheLevels/Levels/L_Level_01.umap` — **M4 only**
- Docs: `Docs/EnemyAI.md`, `Docs/Enemies.md`, `Docs/EnemyPlacement.md`,
  `Docs/EnemyWorkPlan.md` (contract edits)

**Owner B**

- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_SpikeTurtle.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Ghost.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Bat.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_FloatingSkull.uasset`
- May append only to the status log in `Docs/EnemyWorkPlan.md`

**Owner C**

- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyProjectile.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyProjectile_Wood.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_ToxicPuddle.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_ShooterEnemyBase.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_WoodLog.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_ToxicSlime.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rhino.uasset`
- May append only to the status log in `Docs/EnemyWorkPlan.md`

**Nobody edits**

- `BP_PeaPlant.uasset` and `BP_EnemyProjectile_Pea.uasset` — unused shells.
- `L_Level_00.umap`, `L_Level_02.umap`, `L_Menu.umap` — not part of this work.
- Another owner's file, even for a one-line default change. Send a request
  instead.
- `Saved/`, `Intermediate/`, `DerivedDataCache/`, or probe dumps.

If the file is not listed for you, you do not own it. If a needed asset is
missing, add it to §4 first and tell A before creating it.

---

## 5. Dependency graph

```text
M0  all owners read the docs (no edits)
     |
     +-- A: M1  BP_EnemyBase AI core gate ----------------------+
     |          (blocks every walker)                            |
     |                                                           |
     +-- B: M2  Turtle -> Ghost -> Bat -> Skull                 |
     |          (no base-AI dependency)                          |
     |                                                           |
     +-- C: M2b Projectile -> Puddle -> Shooter -> WoodLog      |
                (support; WoodLog final aggro waits for M1)      |
                                                                 |
     M1 gate ----------------------------------------------------+
     |
     +-- A: M3a Snail -> Rocks
     +-- C: M3c Rhino -> Toxic Slime
     |
     M4  integration, placement, full PIE matrix (A owns the map)
```

M1 is the only hard gate. B's four assets and C's projectile/puddle/shooter
work do not read the walker AI and may run while A builds the base. C may build
the Wood Log defaults and firing graph early, but must not wire or PIE-test its
aggro/patrol until M1 is green.

---

## 6. Milestones and gates

### M0 — Read-in (all owners; no edits)

- Read §1 and your work card.
- Confirm your asset list and locks.
- **Comprehension check:** ask your AI to restate its slot, its exact §4.1
  files, its first asset, its dependency gate, its first three tasks and its
  stop conditions. If it cannot, it has not read enough; do not let it edit.
- Post one line in the status log: `M0 done`, your slot, and the first asset.
- If you find a doc conflict, post it before touching an asset.

### M1 — `BP_EnemyBase` AI core gate (A; blocks walkers)

**Read:** `EnemyAI.md` §3–7 and §10; `Enemies.md` §3–4.

**Work**

1. Rename `bEnable` → `bEnabled` in `BP_EnemyPlatform`, compile and save.
2. Add the new `EnemyAI.md` §4 variables; `MoveSpeed` already exists, so do not
   add it again. `HomePlatform` typed as `BP_EnemyPlatform`; remove
   `KnowbackForce`; do not add `MaxWalkSpeed`.
3. Build functions in this order:
   - `PointInPlatformZone`, `PointInPlatformXZ`, `FindHomePlatform`,
     `AdoptPlatform`.
   - `LedgeAhead`, `PatrolStep`.
   - `IsPlayerOnHomePlatform`, `IsPlayerInAggroBox`, `ChaseStep`, `UpdateAggro`.
   - `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`.
4. Wire `BeginPlay` → `FindHomePlatform`; `Landed` → `ResolveKnockback`;
   `Tick` → the state loop; `AnyDamage` sets `bWasKnockedBack` before
   `LaunchCharacter`.
5. The `Event Tick` gate must be:
   `bIsDead OR bStranded OR NOT bCanMove` → return, then
   `bWasKnockedBack` → return, then `ChaseSpeed <= 0` → `PatrolStep` and return.
   This is what makes stationary/flyers safe and Snail/Slime patrol-only.
6. `UpdateAggro` must skip to `PatrolStep` when `ChaseSpeed <= 0`; do not let a
   no-detection walker set `bAggro`.

**M1 acceptance gate**

- Parent and every compiled child have no red errors.
- `py -3 Scripts\_verify_enemy_base.py` holds **44 PASS / 0 FAIL**.
- PIE tests 1–9 from `EnemyAI.md` §11 pass on a temporary `BP_Rock1` placed on
  P_02 (z ≈ `506.25`) or `BP_Snail` on P_00 (z ≈ `875`). Do not save level
  tuning yet.
- Specifically verify: patrol edge turns, same-platform-only aggro, de-aggro,
  knock-off platform adoption, stair stranding/rescue.
- Commit + push, then post `M1 GREEN` with the verifier output. Only then may
  A start Snail/Rocks and C start Slime/Rhino/final Wood Log aggro.

Existing auto-zone surfaces in `L_Level_01` (world X / Z / width):
P_00 `x=-400, z=800, w=800` · P_01 `x=950, z=600, w=500` ·
P_02 `x=-800, z=400, w=800` · P_03 `x=350, z=400, w=500` ·
P_04 `x=-1750, z=100, w=300` · P_05 `x=-1300, z=0, w=600` ·
P_06 `x=550, z=0, w=2700`. Use these for the M1 smoke test; add more zones
only in M4.

### M2 — Independent specials (B; can start now)

Order: `BP_SpikeTurtle` (warm-up) → `BP_Ghost` (highest risk) → `BP_Bat` →
`BP_FloatingSkull`.

- None of these use `PatrolStep`, `LedgeAhead`, `IsPlayerOnHomePlatform` or the
  walker aggro loop.
- Set `bCanMove=false` on all four. `ChaseSpeed=0` for Turtle/Ghost/Skull;
  Bat keeps `ChaseSpeed=300` for `MaxFlySpeed`. Turtle and Skull have no child
  movement Tick; Ghost and Bat use their own Tick.
- Compile + save after each graph; PIE each asset before moving to the next.

**M2 acceptance:** tests 10, 12, 13, 14; Skull's extended test from
`Enemies.md` §7.3; no base-verifier regression.

### M2b — Support graphs (C; can start now)

Order: `BP_EnemyProjectile` (+ `_Wood`) → `BP_ToxicPuddle` →
`BP_ShooterEnemyBase` → `BP_WoodLog` defaults/fire graph.

- `BP_EnemyProjectile_Pea` is untouched.
- `BP_ShooterEnemyBase` is C-only. `TryFire` sets `bCanShoot=false` and
  `bCanMove=false` before spawning; `EndAttack` restores both.
- Wood Log's patrol/aggro is not wired until M1. Building its defaults and
  horizontal `TryFire` early is allowed.

**M2b acceptance:** projectile hits walls, ignores its shooter, self-destructs
at 5 s and calls `Kill` on the player; puddle self-destructs at 3 s and kills
only the player; shooter base compiles with no red errors.

### M3 — Walkers (after M1)

**A:** `BP_Snail` → `BP_RockBase`/`BP_Rock1/2/3`.

**C:** `BP_Rhino` → `BP_ToxicSlime` → finish `BP_WoodLog` aggro/patrol.

- A walker must not add its own movement Tick. Use base `PatrolStep`,
  `ChaseStep` and `UpdateAggro`; override only the state-specific parts.
- Snail and Slime set `ChaseSpeed=0` (no detection). Rocks, Rhino and Wood Log
  set a positive `ChaseSpeed`.
- Snail's shell uses the same base `PatrolStep` with `MoveSpeed=ShellSpeed`;
  do not add the old shell Tick.
- Wood Log overrides `ChaseStep` to stand and shoot; it does not chase.
- Rhino overrides `UpdateAggro` only to maintain `bCharging` after calling
  `Parent: UpdateAggro`; detection itself stays in the base.

**M3 acceptance:** tests 11, 15, 16 plus the Snail/Toxic Slime checks in
`Enemies.md` §7.3; split pieces adopt their landing platform; shell stays on
platform; Rhino dies on the 4th wall hit.

### M4 — Integration, placement and tuning (all; A owns the map)

- A places the test enemies and any additional `BP_EnemyPlatform` zones in
  `L_Level_01`; B/C report coordinates and do not save the map.
- Run the full `EnemyAI.md` §11 matrix (1–16) plus the extended checks in
  `Enemies.md` §7.3.
- Tune `AggroHalfWidth/Height`, `ChaseSpeed`, `DeAggroTime`, `RescueRadius`,
  `MinPatrolWidth` and per-enemy speeds in Class Defaults, not in duplicated
  child variables.
- Re-run `_verify_enemy_base.py`; hold **44 PASS / 0 FAIL**.
- Commit docs + assets; clean probe files; release all locks.

---

## 7. Work cards

Each card is the assignment. The card tells you **what to build and how to
prove it**; the linked sections contain the exact pin-level recipes. Do not
invent a third source.

### A1 — `BP_EnemyBase` AI core (Owner A)

**Read:** `EnemyAI.md` §3–7, §10; `Enemies.md` §3–4.

**Depends:** none. **Blocks:** every walker.

**Tasks**

- [ ] Rename `bEnable` → `bEnabled` in `BP_EnemyPlatform`; compile/save.
- [ ] Add the new §4 variables, including typed `HomePlatform`; `MoveSpeed`
      already exists; remove `KnowbackForce`; do not add `MaxWalkSpeed`.
- [ ] Build `PointInPlatformZone`, `PointInPlatformXZ`, `FindHomePlatform`,
      `AdoptPlatform`.
- [ ] Build `LedgeAhead`, `PatrolStep`.
- [ ] Build `IsPlayerOnHomePlatform`, `IsPlayerInAggroBox`, `ChaseStep`,
      `UpdateAggro`.
- [ ] Build `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`.
- [ ] Wire `BeginPlay`, `Landed`, `Event Tick`, and the `AnyDamage`
      `bWasKnockedBack` flag.
- [ ] Add the Top gate: `bIsDead OR bStranded OR NOT bCanMove` → return;
      `bWasKnockedBack` → return; `ChaseSpeed <= 0` → `PatrolStep` → return.

**Done when:** `_verify_enemy_base.py` = 44 PASS / 0 FAIL; tests 1–9 pass;
compile clean; committed; `M1 GREEN` posted.

---

### B1 — `BP_SpikeTurtle` (Owner B)

**Read:** `EnemyAI.md` §8.1; `Enemies.md` §6.1; `EnemyPlacement.md` §4.1.
**Depends:** base health/contact only. **No base AI.**

**Tasks**

- [ ] Add only the eight child variables: `bSpikesOut`, `SpikeInterval`,
      `SpikeChangeTime`, `SpikesOutFlipbook`, `SpikesInFlipbook`,
      `IdleFlipbookA`, `IdleFlipbookB`, `bIdleAlt`.
- [ ] Class Defaults: `bCanMove=false`, `ChaseSpeed=0`, `bUseHealth=false`,
      `bInvulnerable=true`, `ContactDamage=1`, `MaxHealth=3`, turtle flipbooks.
- [ ] `BeginPlay` → `InitEnemy`; loop timers `SpikeCycle` (`SpikeInterval`) and
      `ToggleIdle` (`1.4`).
- [ ] `SpikeCycle` → toggle `bSpikesOut`; play the in/out flipbook; start
      `FinishSpikeChange` (`SpikeChangeTime`, one-shot).
- [ ] `FinishSpikeChange` → `bDealContactDamage = bSpikesOut`;
      `ContactDamage=1.0`; `RefreshStateFlipbook`.
- [ ] `ToggleIdle` → flip `bIdleAlt`; `RefreshStateFlipbook`.
- [ ] Override `RefreshStateFlipbook` to choose the spike/idle flipbook.

**Done when:** test 10 passes: stationary, no detection, no patrol Tick, bullets
and `Kill` do nothing, contact only while spikes are out, `KillVolume` destroys.

**Do not:** add a patrol Tick, detection, `bCanMove=true`, or health damage.

---

### B2 — `BP_Ghost` (Owner B)

**Read:** `EnemyAI.md` §8.4; `Enemies.md` §6.4; `EnemyPlacement.md` §4.4.
**Depends:** base health/contact only. **No base AI.**

**Tasks**

- [ ] Add only the unique variables: `bInvisible`, `VisibleTime`,
      `InvisibleTime`, `FadeTime`, `AppearFlipbook`, `DisappearFlipbook`.
      **Do not** declare `bAggro` or `AggroRadius`; inherit them.
- [ ] Class Defaults: `bCanMove=false`, `ChaseSpeed=0`, `AggroRadius=550`,
      `MaxHealth=2`, `MoveSpeed=80`, `ContactDamage=1`, ghost flipbooks.
- [ ] `BeginPlay` (child addition): `InitEnemy`; `bInvisible=true`;
      `Sprite0` hidden; `CollisionCylinder` NoCollision; `ContactBox` off;
      `bInvulnerable=true`; `bDealContactDamage=false`; `bAggro=false`.
- [ ] Own `Event Tick`: when `NOT bAggro`, valid player and
      `VSize(Player - Self)` in the XZ plane `<= AggroRadius` → `StartAggro`.
      Once aggroed, move directly at the player in X/Z.
- [ ] `StartAggro`: visible sprite, collision on with `WorldStatic=Ignore`,
      `ContactBox` on, vulnerable, contact on, play `AppearFlipbook`, start
      `StartDisappear` (`VisibleTime`).
- [ ] Build the visible/hidden loop exactly as `Enemies.md` §6.4:
      `StartDisappear`, `BecomeInvisible`, `StartAppear`, `BecomeVisible`.
- [ ] Hidden phase turns off **both** the capsule and `ContactBox`; visible
      phase restores both. No `bInvulnerableWhileInvisible` variable.
- [ ] Override `RefreshStateFlipbook`: hidden = do nothing; visible = idle loop.

**Done when:** tests 12–13 pass: hidden = no collision/contact/chase; trigger
= visible phase, through-wall chase, loop forever, no de-aggro.

**Do not:** add base walker Tick behavior, set `WorldStatic=Block`, or add a
de-aggro branch.

---

### B3 — `BP_Bat` (Owner B)

**Read:** `EnemyAI.md` §8.8; `Enemies.md` §6.8; `EnemyPlacement.md` §4.8.
**Depends:** base health/contact only. **No base AI.**

**Tasks**

- [ ] Add only the unique variables: `bTriggered`, `bChasing`,
      `TriggerRadius`, `CeilingInFlipbook`, `CeilingOutFlipbook`,
      `FlyingFlipbook`, `HangingFlipbook`. **Do not** declare `ChaseSpeed`;
      inherit it and set it to `300` in Class Defaults.
- [ ] Class Defaults: `bCanMove=false`, `ChaseSpeed=300`, `TriggerRadius=300`,
      `MaxHealth=2`, `ContactDamage=1`, bat flipbooks.
- [ ] `BeginPlay`: `InitEnemy`; `bDealContactDamage=false`; play
      `CeilingInFlipbook`; start `HangIdle` (`0.6`).
- [ ] `HangIdle` → loop `HangingFlipbook`.
- [ ] Own `Event Tick`: trigger only when the player is valid and within the
      `300` sphere; set `bTriggered=true`, contact on, play `CeilingOutFlipbook`,
      start `StartChase` (`0.5`).
- [ ] `StartChase` → `bChasing=true`; `MaxFlySpeed=ChaseSpeed`; loop
      `FlyingFlipbook`.
- [ ] Chase step: direct X/Z `Add Movement Input`; keep collision with walls
      and floors. No de-aggro.
- [ ] Override `RefreshStateFlipbook`: flying while `bChasing`, hanging
      otherwise.

**Done when:** test 14 passes; two hits kill it; contact only after trigger;
it collides with walls/floors and never de-aggros.

**Do not:** set `WorldStatic=Ignore` (that is Ghost-only) or add pathfinding.

---

### B4 — `BP_FloatingSkull` (Owner B)

**Read:** `EnemyAI.md` §8.7; `Enemies.md` §6.7; `EnemyPlacement.md` §4.7.
**Depends:** base health/contact only. **No base AI.**

**Tasks**

- [ ] Add only the unique variables: `bPoweredOn`, `OnIdleFlipbook`,
      `OffIdleFlipbook`, `HitWallFlipbookA`, `HitWallFlipbookB`,
      `bUseWallAlternate`, `BounceSpeed`.
- [ ] Class Defaults: `bCanMove=false`, `ChaseSpeed=0`, `MaxHealth=2`,
      `ContactDamage=1`, `MoveSpeed=300`, skull flipbooks.
- [ ] `BeginPlay`: `InitEnemy`; `bPoweredOn=true`; `bInvulnerable=true`;
      `bDealContactDamage=true`; play `OnIdleFlipbook`; launch
      `(Facing * BounceSpeed, 0, BounceSpeed * 0.5)` with XY/Z override.
- [ ] Own `Event Hit`: ignore non-wall/floor normals; play alternating
      `HitWallFlipbookA/B`; `TogglePower`; `BackToSkullIdle` (`0.35`);
      reflect the X/Z velocity through `LaunchCharacter`.
- [ ] `TogglePower`: flip `bPoweredOn`; `bInvulnerable=bPoweredOn`;
      `bDealContactDamage=bPoweredOn`; `RefreshStateFlipbook`.
- [ ] Override `RefreshStateFlipbook`: ON idle vs OFF idle.

**Done when:** ON ignores bullets and kills on contact; OFF is harmless and
shootable; wall/floor hit toggles; no detection/chase; no gravity; pit
`KillVolume` destroys it.

**Do not:** add a patrol Tick or a platform zone; it is a flying hazard.

---

### C1 — `BP_EnemyProjectile` + `BP_EnemyProjectile_Wood` (Owner C)

**Read:** `Enemies.md` §5.2 and §5.3.
**Depends:** none.

**Tasks**

- [ ] Add `SphereCollision` (radius `8`, `BlockAllDynamic`, generate hit
      events) and `ProjectileMovement` (initial/max speed `0`, gravity `0`,
      no bounce).
- [ ] Add `Speed=900`, `Damage=1`, `Direction=(1,0,0)`, `Shooter` (Actor).
- [ ] `InitProjectile(Direction, Speed, Damage, Shooter)` sets the four values
      and `Set Velocity = Direction * Speed`.
- [ ] `BeginPlay` → `Set Life Span(5.0)`; apply velocity if `Speed` is set.
- [ ] `On Component Hit (SphereCollision)`: ignore `Shooter`; if other actor is
      the player and implements `BPI_Killable`, call `Kill` then `Destroy Actor`;
      otherwise `Destroy Actor` for walls/floors.
- [ ] Set `BP_EnemyProjectile_Wood` defaults; leave `_Pea` untouched.

**Done when:** projectile hits a wall and destroys itself, never self-hits,
expires at 5 s, and kills the player through `BPI_Killable`.

**Do not:** use `ApplyPointDamage` on the player (the player has no health).

---

### C2 — `BP_ToxicPuddle` (Owner C)

**Read:** `Enemies.md` §5.4.
**Depends:** none.

**Tasks**

- [ ] Add `ToxicBox` (`BoxComponent`, extent `(100,50,20)`,
      `OverlapAllDynamic`, generate overlaps).
- [ ] Keep `InitialLifeSpan=3.0`.
- [ ] `Event ActorBeginOverlap`: if `OtherActor == Get Player Character(0)` and
      it implements `BPI_Killable`, call `Kill`.
- [ ] Optional 0.5 s repeated damage while standing; clear timer on end overlap.
      This is not required for the one-hit player.

**Done when:** puddle disappears at 3 s; player dies on contact; enemies are
unaffected; no graph in the slime is needed for the lifetime.

---

### C3 — `BP_ShooterEnemyBase` (Owner C)

**Read:** `Enemies.md` §5.1 and §5.3.
**Depends:** C1.

**Tasks**

- [ ] Add `ProjectileClass`, `FireInterval`, `NextFireTime`, `MuzzleOffset`,
      `ProjectileSpeed`, `ProjectileDamage`, `AttackFlipbook`, `bCanShoot`,
      `bRequireLineOfSight`.
- [ ] `BeginPlay` → `InitShooter`: `InitEnemy`; set `NextFireTime`; loop
      `TryFire` every `0.2 s`.
- [ ] `TryFire`: return if dead, `NOT bCanShoot`, or before `NextFireTime`;
      require a valid player; face the player; play `AttackFlipbook`; set
      `bCanShoot=false` and `bCanMove=false`; spawn the projectile at the
      muzzle with `(Facing,0,0)` direction; set `NextFireTime`; start
      `EndAttack` (`0.5 s`).
- [ ] `EndAttack` → `bCanShoot=true`, `bCanMove=true`, `RefreshStateFlipbook`.

**Done when:** Wood Log compiles and fires; no Pea Plant work; no self-hit.

---

### C4 — `BP_WoodLog` (Owner C)

**Read:** `EnemyAI.md` §8.9; `Enemies.md` §5.3; `EnemyPlacement.md` §4.9.
**Depends:** C3 + M1. **Allowed early:** defaults and `TryFire` graph.

**Tasks**

- [ ] Class Defaults: `ProjectileClass=BP_EnemyProjectile_Wood`,
      `FireInterval=2.5`, `MuzzleOffset=(90,0,10)`,
      `AttackFlipbook=FLB_Trunk_Attack`, `MaxHealth=3`, `MoveSpeed=90`,
      `ChaseSpeed=90`, `AggroHalfWidth=1400`, `AggroHalfHeight=500`,
      `DeAggroTime=2.0`.
- [ ] Do not add a second `BeginPlay`; the shooter base starts the fire timer.
- [ ] Override `ChaseStep` to **stand and shoot**: face the player, do not move
      toward them, keep `bAggro` from the base.
- [ ] `TryFire` from C3 already gates on `bAggro`; verify it fires only
      horizontally and only inside the rectangle.
- [ ] On de-aggro, `EndAttack` restores movement; base `PatrolStep` resumes.
- [ ] Override `RefreshStateFlipbook`: attack flipbook while firing,
      run while moving, idle otherwise.

**Done when:** test 16 passes: stops inside `1400×500`, fires only
horizontally, de-aggros after `2 s`, resumes patrol, no vertical aim.

**Do not:** chase around the platform, fire at any range, or add a Pea Plant.

---

### A2 — `BP_Snail` (Owner A)

**Read:** `EnemyAI.md` §8.3; `Enemies.md` §6.3; `EnemyPlacement.md` §4.3.
**Depends:** M1. No detection.

**Tasks**

- [ ] Add only the unique variables: `bShellPhase`, `ShellSpeed`,
      `ShellContactDamage`, `ShellLifetime`, `ShellIdleFlipbook`,
      `ShellWallHitFlipbook`, `ShellTopHitFlipbook`, `WithoutShellFlipbook`.
- [ ] Class Defaults: `ChaseSpeed=0`, `MaxHealth=2`, `MoveSpeed=50`,
      `ContactDamage=1`, snail flipbooks.
- [ ] Normal state: use base `PatrolStep` / `LedgeAhead`; no child Tick.
- [ ] `Die` override: if already `bShellPhase`, return; otherwise set shell
      flags (`bShellPhase=true`, `bIsDead=false`, `bInvulnerable=true`,
      `bDealContactDamage=true`, `bAggro=false`), `ContactDamage=1`,
      `MoveSpeed=ShellSpeed`, `MaxWalkSpeed=ShellSpeed`, `bCanMove=true`, play
      shell idle, `Set Life Span(ShellLifetime)`. **Do not call `Parent: Die`.**
- [ ] Shell movement uses the same base `PatrolStep` and `LedgeAhead`; do not
      add a second shell Tick.
- [ ] `Event Hit` handles the wall/edge reaction and plays
      `ShellWallHitFlipbook` → `BackToShellIdle` (`0.25`); ensure normal-state
      wall reversal is not lost.
- [ ] Override `RefreshStateFlipbook`: shell idle while `bShellPhase`; otherwise
      walk/idle.

**Done when:** kill → shell, no destruction; shell sweeps and turns at the
platform edge; shell ignores bullets; contact `1`; destroys itself after `8 s`.

**Do not:** add detection, call `Parent: Die`, or let the shell walk off an edge.

---

### A3 — `BP_RockBase` + `BP_Rock1/2/3` (Owner A)

**Read:** `EnemyAI.md` §8.2; `Enemies.md` §6.2; `EnemyPlacement.md` §4.2.
**Depends:** M1.

**Tasks**

- [ ] `BP_RockBase`: add `RockTier`, `ChildRockClass`, `bCanSplit`,
      `SplitImpulse`, `SplitOffset`, `MaxPieces`.
- [ ] Child Class Defaults: health `3/2/1`, `MoveSpeed` `100/140/180`, tier
      `1/2/3`, `ChildRockClass` `Rock2/Rock3/None`, `bCanSplit` `true/true/false`,
      rock flipbooks, positive `ChaseSpeed` per tier (start `120/160/200`).
- [ ] Use base `PatrolStep` / `ChaseStep` / `UpdateAggro`; no child movement
      Tick. Aggro rectangle `700×500`, `DeAggroTime=2.0`.
- [ ] `Die` override: if `bCanSplit` and `ChildRockClass` is valid and the live
      `BP_RockBase` count is `<= MaxPieces - 1`, spawn two children at
      `±SplitOffset`, launch them with `SplitImpulse`; then `Parent: Die`.
- [ ] Split pieces rely on `Landed` / `ResolveKnockback` to adopt the landing
      platform; do not copy the parent's `HomePlatform`.
- [ ] Override `RefreshStateFlipbook`: run when `Abs(Velocity.X) > 10`, else idle.

**Done when:** test 11 passes; kill tier 1 → 2× tier 2; kill tier 2 → 4× tier 3;
tier 3 does not split; live count stays ≤ 8; pieces adopt their landing platform.

**Do not:** copy the stationary turtle; add a second Tick; or assume the parent
platform remains valid.

---

### C5 — `BP_Rhino` (Owner C)

**Read:** `EnemyAI.md` §8.6; `Enemies.md` §6.6; `EnemyPlacement.md` §4.6.
**Depends:** M1.

**Tasks**

- [ ] Add only the unique variables: `bCharging`, `ChargeSpeed`,
      `ChargeDirection`, `WallHitCooldown`, `LastWallHitTime`, `RunFlipbook`,
      `HitWallFlipbook`. **Do not** declare `MoveSpeed`; inherit it.
- [ ] Class Defaults: `MoveSpeed=120`, `ChaseSpeed=600`, `ChargeSpeed=600`,
      `MaxHealth=4`, `CurrentHealth=4`, `bUseHealth=true`,
      `bInvulnerable=true`, `ContactDamage=1`, `AggroHalfWidth=1200`,
      `AggroHalfHeight=500`, `DeAggroTime=2.0`.
- [ ] `BeginPlay`: `InitEnemy`; keep `bInvulnerable=true`; contact on;
      `SetFacing(ChargeDirection)`; `MaxWalkSpeed=MoveSpeed`; idle loop.
- [ ] Override `UpdateAggro`: call `Parent: UpdateAggro`, then set
      `bCharging=bAggro` (do not duplicate detection).
- [ ] `Event Hit`: ignore the player; require `Abs(Normal.X)>0.7`; enforce
      `WallHitCooldown`; subtract 1 health; `SetFacing(-Facing)`; play
      `HitWallFlipbook`; if health `<=0`, `bInvulnerable=false` then `Die`;
      else `EndWallHit` (`0.3`).
- [ ] `EndWallHit` resumes charge/patrol and refreshes the flipbook.
- [ ] Override `RefreshStateFlipbook`: `RunFlipbook` while `bCharging`, else idle.

**Done when:** test 15 passes: bullets do nothing; 4 wall hits kill; it turns
after each hit; contact kills the player; `KillVolume` still destroys it.

**Do not:** add health damage from bullets, vertical movement, or a second
detection box.

---

### C6 — `BP_ToxicSlime` (Owner C)

**Read:** `EnemyAI.md` §8.5; `Enemies.md` §6.5; `EnemyPlacement.md` §4.5.
**Depends:** M1 + C2.

**Tasks**

- [ ] Add only the unique variables: `PuddleClass`, `PuddleInterval`,
      `NextPuddleTime`, `PuddleOffset`, `bLeaveTracks`.
- [ ] Class Defaults: `ChaseSpeed=0`, `MaxHealth=3`, `MoveSpeed=70`,
      `ContactDamage=1`, slime flipbooks.
- [ ] `BeginPlay`: `InitEnemy`; `NextPuddleTime = Get Game Time in Seconds`.
- [ ] Use base `PatrolStep` / `LedgeAhead`; no detection, no child movement Tick.
- [ ] Own `Event Tick` for the puddle only: return if dead, tracks off, or
      `Abs(Velocity.X) < 10`; when the cooldown expires, spawn `PuddleClass` at
      `ActorLocation + PuddleOffset`, then set `NextPuddleTime += PuddleInterval`.
- [ ] Override `RefreshStateFlipbook`: `FLB_Slime_IdleRun` while alive.

**Done when:** puddles spawn only while moving, each disappears after `3 s`,
player dies on contact, no detection, and the slime never walks off a ledge.

**Do not:** add a second movement Tick or a chase branch.

---

## 8. AI assistant handoff prompt

Give your AI assistant the whole repository, then paste the block for your slot.
Replace `<SLOT>` with `A`, `B` or `C` and `<ASSET>` with the first asset.

```text
You are the AI assistant for Owner <SLOT> on the Unreal Engine 4.27.2 project
"Don't Trust The Levels". The project is Blueprint-only, Paper2D, no C++, no
Behavior Tree, no NavMesh, no EQS.

Read, in this order:
1. Docs/EnemyWorkPlan.md (the assignment, gates and acceptance tests).
2. Docs/EnemyAI.md sections 1-2, 4, 6, 10-11 and the section for your asset.
3. Docs/Enemies.md sections 3-4 and the section for your asset.
4. Docs/EnemyPlacement.md only for placement or M4.
5. Docs/LfsLocking.md before touching a .uasset or .umap.

Current asset: <ASSET>.
Your ownership is exactly the file list for your slot in
Docs/EnemyWorkPlan.md section 4.1. Only edit those exact .uasset paths, plus
the status-log lines the plan allows. Do not edit BP_EnemyBase,
BP_ShooterEnemyBase, BP_RockBase, any shared base, any other owner's asset, or
a level map unless the plan explicitly lists it for your slot.

Hard rules:
- Lock the asset with Git LFS / UE Source Control before editing. Never co-edit.
- This build cannot create K2 nodes from Python. Do not attempt graph authoring
  with Python. Build nodes, wires, variables and functions manually in the editor.
- One movement authority per asset. Walkers use the base Event Tick; stationary/
  flyers set bCanMove=false and use their own Tick/Launch. ChaseSpeed=0 for
  Turtle/Ghost/Skull; Bat keeps ChaseSpeed=300 for MaxFlySpeed.
- Do not add a variable that already exists in a parent. Use inherited
  bAggro, AggroRadius, ChaseSpeed, MoveSpeed, KnockbackForce, Facing and the
  base health/contact/flipbook variables. Do not add MaxWalkSpeed.
- Do not add KnowbackForce. Keep KnockbackForce.
- Contact damage goes through ContactBox, not the capsule.
- Compile and save after every function or graph. Never leave a red error.
- Run `py -3 Scripts\_verify_enemy_base.py` after any base-adjacent change;
  the accepted result is 44 PASS / 0 FAIL.
- Walkers may not start before Owner A posts M1 GREEN.
- If a parent member is missing, stop and report it. Do not duplicate it in the
  child. If two docs disagree, EnemyAI.md wins; report the conflict.

Pre-flight, before any edit:
- State your slot and list the exact `.uasset` paths from §4.1 that you will
  touch.
- Run `git lfs locks` and `git status --short`. If a target is locked by someone
  else, or the working tree contains another owner's changes, stop.
- If any intended path is not in your §4.1 list, stop; do not “just fix” it.
- Never write, rename, move or delete `.uasset`/`.umap` with Python or shell;
  only the Unreal Editor may save them.
- Never run `git add -A`, `git commit -a`, `git reset`, `git clean`,
  `git checkout --`, or `git restore`. Stage only your exact files.
- Do not pull with unsaved editor changes. Close the editor before pulling.

Work one asset at a time. For each asset:
1. Post the lock and the first task.
2. Build the variables and defaults from the work card.
3. Build one function at a time; compile after each.
4. Run the card's PIE acceptance test.
5. Report exact PASS/FAIL, compile status, verifier status and files changed.
6. Commit, push, release the lock, and append a status line.

Stop immediately and report if:
- a parent member is missing or a compile error points at `BP_EnemyBase`;
- a fix would require editing another owner's file;
- the plan and a work card disagree;
- you cannot acquire the lock.

Do not claim a test passed unless you ran it in PIE. Do not invent variable
names, function names or defaults that are not in the linked sections.
```

Owner A should also add: `M1 is the gate; post M1 GREEN with verifier output
before starting walkers.` Owner B should add: `Your four assets do not depend on
M1; Turtle -> Ghost -> Bat -> Skull.` Owner C should add: `Support first;
Wood Log patrol/aggro waits for M1; Rhino before Slime.`

---

## 9. Definition of done (per asset)

An asset is **DONE** only when all are true:

- [ ] Compile is clean and the asset is saved.
- [ ] Every variable in the card exists once, with the exact name, type and
      default; inherited names are not duplicated.
- [ ] Every function/event in the card is wired; no orphan or disabled node that
      the card requires.
- [ ] `BP_EnemyBase` still reports **44 PASS / 0 FAIL**.
- [ ] The card's PIE acceptance test passes; record what you actually observed.
- [ ] No regression in an already-done enemy (contact, health, death, split).
- [ ] The asset is committed and pushed, and the LFS lock is released.
- [ ] The status log has the asset line and any doc deviation.
- [ ] Any changed contract was updated in `EnemyAI.md` / `Enemies.md` by A in the
      same commit.

A graph that compiles but has no PIE evidence is **not done**.

---

## 10. Status log

Append one line per asset; do not rewrite another owner's line. Keep the table
sorted by date. Use `PASS`, `FAIL`, `BLOCKED` or `DONE` explicitly.

| Date | Owner | Asset | State | Verifier | PIE test | Commit / note |
|---|---|---|---|---|---|---|
| 24 Oct 2026 | A | plan created | DONE | — | — | `Docs/EnemyWorkPlan.md` |
| 25 Oct 2026 | B | M0 done | DONE | — | — | read-in complete (WorkPlan §3-6, EnemyAI §1-2/§4/§8/§10-11, Enemies §3-4/§6/§7.3, LfsLocking, EnemyPlacement §4.1/4.4/4.7/4.8); merged origin/branch/Dennis into branch/Jones; first asset BP_SpikeTurtle |
|  |  |  |  |  |  |  |

**Current gate:** `M1` is not green. Base AI functions are not built yet; do not
start walkers.

---

## 11. Commit and lock checklist

1. `git lfs locks` — confirm the asset is not locked by someone else.
2. Lock the exact path from **§4.1** in UE Source Control (or
   `git lfs lock <path>`). Do not lock a folder or another owner’s file.
3. Edit; compile; save; PIE; run the verifier.
4. `git status --short` — only your asset, its child, and approved docs.
5. `git add <your exact files>`; never `git add -A` or `git commit -a`.
   Commit with a scoped message:
   `feat(enemy): implement Ghost aggro/visibility loop`
   `feat(enemy): add Rock split tiers`
   `feat(enemy): add projectile and toxic puddle`
   `docs(enemy): sync AI work plan and duplicate variable rules`
6. `git push` — this releases the LFS lock; verify with `git lfs locks`.
7. Append the status line and tell A if a contract changed.

Never commit `Saved/`, `Intermediate/`, `DerivedDataCache/`, `__pycache__/`,
probe dumps, or a `.umap` you do not own.

---

## 12. Priority and scope if time slips

The full target remains all nine mechanics. If the schedule slips, keep this
order:

1. **Must-have V1:** M1 base gate, `BP_Snail`, `BP_Rock1/2/3`, `BP_WoodLog`,
   `BP_Ghost`, `BP_Bat`, `BP_Rhino`.
2. **Cheap and worth keeping:** `BP_SpikeTurtle` (mostly timers, no movement).
3. **Defer last:** `BP_FloatingSkull`, `BP_ToxicSlime`.

Do not “save time” by skipping M1, duplicating movement into a child, or letting
a walker ignore a ledge. Those shortcuts create the exact bugs the AI design
exists to prevent.

---

## 13. Open decisions locked by this plan

These are deliberate, and the technical docs must agree with them:

- `bCanMove` is the shared walker-AI gate. Stationary/flyers set it false; their
  own movement still works.
- `ChaseSpeed <= 0` means “no detection”: Snail and Slime patrol only.
- Snail's shell uses base `PatrolStep`; there is no second shell Tick.
- Wood Log stops by setting `bCanShoot=false` and `bCanMove=false` in
  `TryFire`; `EndAttack` restores both. It overrides `ChaseStep` to stand.
- Ghost inherits `bAggro` and `AggroRadius`; Bat inherits `ChaseSpeed`; Rhino
  inherits `MoveSpeed`.
- `BP_PeaPlant` and `BP_EnemyProjectile_Pea` remain unused shells.
- The first PIE gate is a temporary `BP_Rock1` on P_02 or `BP_Snail` on P_00,
  not the current Snail placement at `(-451, 9, 225)`.

If implementation proves a decision wrong, A updates this list and the matching
contract in the same commit. B/C do not fork the design silently.
