# Enemy Work Plan — three-slot parallel execution

**Status (4 Nov 2026):** execution plan for the remaining enemy work. Owner **B
has been retired**; their four assets and their milestone (`M2`) now belong to
**A2**. The live slots are **A1, A2, C**. This file assigns the work, defines
the dependency gates and lists the acceptance tests. It does **not** replace the
technical design:

| Authority | File | What it decides |
|---|---|---|
| 1 | **`Docs/EnemyAI.md`** | movement, patrol, aggro, knockback, rescue; wins on conflict |
| 2 | **`Docs/Enemies.md`** | variables, graph recipes, per-enemy mechanics, test matrix |
| 3 | **`Docs/EnemyPlacement.md`** | level placement rules and per-enemy layouts |

**Audience:** Owner A1, Owner A2, Owner C and their AI assistants. Read this file
first, then the exact sections named in your work card. Do not infer rules from
old summaries. **Owner B no longer exists:** anything in this file that used to
say `B` now says `A2`, including the four stationary/flyer assets and
`L_Level_Testing`.

**Scope:** the nine active enemy mechanics plus the projectile/puddle/shooter
support assets. `BP_PeaPlant` and `BP_EnemyProjectile_Pea` are **out of scope**
unless the design changes.

---

## 0. Owner slots

Fill in the real names before work starts. Do not change asset ownership without
updating this table and taking the Git LFS lock.

| Slot | Name / GitHub | Workstream | Assets | Can start |
|---|---|---|---|---|
| **A1** | base owner | shared base AI + first walker | `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail`, contract docs | now |
| **A2** | rocks + stationary/flyers + level | rock split, the four no-walker assets, level integration | `BP_RockBase`, `BP_Rock1/2/3`, `BP_SpikeTurtle`, `BP_Ghost`, `BP_Bat`, `BP_FloatingSkull`, `L_Level_01`, `L_Level_Testing` | now |
| **C** | groupmate 2 | support + ranged/walkers | `BP_EnemyProjectile`, `BP_EnemyProjectile_Wood`, `BP_ToxicPuddle`, `BP_ShooterEnemyBase`, `BP_WoodLog`, `BP_ToxicSlime`, `BP_Rhino` | now |

**Owner B is retired (4 Nov 2026).** Everything B owned moved to A2:
`BP_SpikeTurtle`, `BP_Ghost` and `BP_Bat` are **DONE** and become A2 regression
assets (do not rebuild them); `BP_FloatingSkull` is the one remaining build;
`L_Level_Testing` is now A2's scratch PIE map. A2 therefore carries the largest
load, and §4.2 / §6 fix a hard order for A2: Skull first, then Rocks, then the
maps.

A1 is the only person allowed to edit `BP_EnemyBase`, `BP_EnemyPlatform` and
`BP_Snail`. A2 is the only person allowed to edit the Rock assets, the four
stationary/flyer assets and both level maps. A1 may prepare Snail
variables/defaults/art; A2 may prepare Rock and Skull variables/defaults/art and
stage static map/platform instances immediately, but **walker graphs and walker
PIE wait for M1 GREEN**. If a base change is needed, A2 sends a request to A1;
do not add the variable or function to the child. C builds the
projectile/puddle/shooter support and the ranged walkers in parallel.

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
  `py -3 Scripts\_verify_enemy_base.py` reports **52 PASS / 0 FAIL**.
- `BP_EnemyPlatform` exists and seven auto zones exist in `L_Level_01`.
- `BPI_Killable` is implemented on `BP_EnemyBase`; traps are player-only.

**Built in `BP_EnemyBase` (re-verified from the export + live CDO, 4 Nov 2026)**

- All **13/13** AI functions exist: `PointInPlatformZone`, `PointInPlatformXZ`,
  `FindHomePlatform`, `AdoptPlatform`, `LedgeAhead`, `PatrolStep`,
  `IsPlayerOnHomePlatform`, `IsPlayerInAggroBox`, `ChaseStep`, `UpdateAggro`,
  `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`. The asset has **21
  function graphs** in total (`InitEnemy`, `Die`, `RefreshStateFlipbook`,
  `SetFacing`, `ClearIFrames`, `RecoverFromHit`, `PlayStateFlipbook`, …).
- All 25 §4 variables exist with the documented defaults:
  `py -3 Scripts\_check_enemy_ai_vars.py` reports **25 PASS / 0 FAIL** live
  (the 25th, `bAggroOnHit`, landed with the aggro-on-hit change; the two rename
  failures of 27 Oct are gone).
- `Event Tick` is wired, and `ContactBox` exists with the contact chain bound to
  it — the 25 Oct defect report below is resolved.

**Proven in PIE (the three A2 assets inherited from B)**

- `BP_SpikeTurtle` — test 10 PASS · `BP_Ghost` — tests 12–13 PASS ·
  `BP_Bat` — test 14 PASS (`TriggerRadius=1000`, `ChaseSpeed=1000`,
  `KnockbackForce=0`).

**Not built**

- ~~The **M1 walker PIE gate (tests 1–9)**~~ — **DONE 8 Nov 2026: `M1 GREEN` is
  posted in §10.** Tests 1–7 passed in `L_Level_01`, 8 through the spawn variant
  of the rescue, 9 is N/A there. Walker graphs and walker PIE are unblocked;
  `A1b` (`BP_Snail`) is the next A1 card.
- Every child-specific mechanic. Live CDO check on 4 Nov 2026:
  `BP_Rock1/2/3`, `BP_WoodLog`, `BP_Rhino`, `BP_ToxicSlime` and
  `BP_FloatingSkull` all still held the **base defaults** (`ChaseSpeed=150`,
  `MoveSpeed=100`, `MaxHealth=3`, `AggroHalfWidth=600`, `AggroHalfHeight=500`,
  `ContactDamage=1`) and declared **zero** own variables, so none of them had
  started. **8 Nov 2026 correction:** the Skull is no longer in that list —
  `bb3627d` (B, 5 Nov) built it (`MoveSpeed=300`, `ChaseSpeed=0`, `MaxHealth=2`,
  seven own variables; evidence in `A2e`). Wood Log, Rhino and Slime still hold
  the base defaults — the Rocks are also no longer in that list: Jones built the
  tier-1/2/3 split chain on 8 Nov 2026 (see `A2a`). `BP_Snail` now overrides the
  aggro values (`ChaseSpeed=250`, both
  aggro halves `0`, `bAggroOnHit=true`; saved 5 Nov), but its health, movement
  and snail flipbooks are still on the base defaults (`MaxHealth=3`,
  `MoveSpeed=100`, `IdleFlipbook`/`HitFlipbook`/`DeathFlipbook` unset) — the
  remaining A1b Class Defaults work is still open.
- The projectile/puddle/shooter support graphs.

**Current blockers / cleanup**

- **DONE 24 Oct** — `bEnable` → `bEnabled` in `BP_EnemyPlatform`; live check:
  `bEnabled=true`, `Zone` extent `(50,50,20)`, `NoCollision`, hidden,
  `PatrolInset=80`. The generator alias is kept for compatibility.
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
     `ChaseSpeed=1000` for `MaxFlySpeed`. This is what stops the shared walker
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
7. **Walkers wait for M1.** Until A1 posts the base gate (variables, functions,
   `PatrolStep`/`LedgeAhead`, compile clean, 52 PASS, tests 1–9), do not wire
   `Snail`, `Rocks`, `Slime`, `Rhino` or the final `WoodLog` aggro wiring.
   A1 may prepare Snail unique variables/defaults; A2 may prepare Rock and Skull
   unique variables/defaults, art and static map/platform instances. No walker
   graph or walker PIE before M1. Stationary/flyers (A2) and the
   projectile/puddle/shooter support (C) may start immediately because they do
   not read the walker AI.
8. **Shared bases are single-owner.**
   - A1 only: `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail`.
   - A2 only: `BP_RockBase`, `BP_Rock1/2/3`, `BP_SpikeTurtle`, `BP_Ghost`,
     `BP_Bat`, `BP_FloatingSkull`.
   - C only: `BP_ShooterEnemyBase`, `BP_EnemyProjectile*`, `BP_ToxicPuddle`.
   - A2 never edits a shared base: the four stationary/flyer assets extend the
     base, they do not modify it. A base change is an A1 request.
9. **Level maps are single-owner.** Only A2 edits `L_Level_01` (M1 smoke-test
   staging and M4) and `L_Level_Testing` (A2's scratch PIE map for the
   stationary/flyer assets). A1 and C provide placement coordinates and test
   results; they never save a map. A2 stages and removes the temporary M1 test
   actor at A1's request.
10. **No new base classes, no Behavior Tree, no NavMesh, no C++.** No Pea Plant
    work. No Python graph authoring.
11. **Docs are contract files.** A1 owns edits to `EnemyAI.md`, `Enemies.md` and
    `EnemyPlacement.md`. A2 and C may append to the status log in this file and
    may propose a correction; they must not rewrite a contract to match their
    graph.
12. **Definition of done is per asset**, not "the graph looks finished": see §9.

---

## 4. Ownership map

| Asset | Owner | Depends on | Notes |
|---|---|---|---|
| `BP_EnemyBase` | A1 | — | AI core, M1 |
| `BP_EnemyPlatform` | A1 | — | DONE — `bEnabled=true`, Zone verified |
| `BP_Snail` | A1 | M1 | walker; hit-only aggro (zero box, `bAggroOnHit`) |
| `BP_RockBase` | A2 | M1 | split logic |
| `BP_Rock1/2/3` | A2 | M1, `BP_RockBase` | child defaults + split |
| `BP_SpikeTurtle` | A2 | base health only | DONE (was B) — stationary, no detection |
| `BP_Ghost` | A2 | base health only | DONE (was B) — flyer, own Tick |
| `BP_Bat` | A2 | base health only | DONE (was B) — flyer, own Tick |
| `BP_FloatingSkull` | A2 | base health only | was B — bounce, own `Event Hit`; the only remaining A2 special |
| `BP_EnemyProjectile` | C | — | support |
| `BP_EnemyProjectile_Wood` | C | projectile base | child defaults |
| `BP_ToxicPuddle` | C | — | support |
| `BP_ShooterEnemyBase` | C | — | support |
| `BP_WoodLog` | C | C support + M1 | walker that stops to shoot |
| `BP_ToxicSlime` | C | M1 + puddle | walker; no detection |
| `BP_Rhino` | C | M1 | walker charger |
| `BP_PeaPlant` | nobody | — | unused; do not place or extend |
| `BP_EnemyProjectile_Pea` | nobody | — | unused shell |
| `L_Level_01` | A2 | all behavior gates + A1 M1 smoke test | M1 staging + M4 only |
| `L_Level_Testing` | A2 | — | A2 scratch PIE map (was B's); never a shipped-level edit |

If a new asset is needed, add it to this table before creating it. Do not create
a second “base” or a manager actor to avoid a dependency. Exact lock paths are
in §4.1; that list is the conflict boundary.

### 4.1 Exact files to lock (no ambiguity)

All enemy Blueprints live in
`Content/DontTrustTheLevels/Enemies/Blueprints/`. Lock the exact `.uasset`
file, never a folder; use the paths below verbatim with `git lfs lock`.

**Owner A1 — `A1` (shared base) + `A1b` (Snail)**

- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyBase.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyPlatform.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Snail.uasset`
- Docs: `Docs/EnemyAI.md`, `Docs/Enemies.md`, `Docs/EnemyPlacement.md`,
  `Docs/EnemyWorkPlan.md` (contract edits)

**Owner A2 — rocks + stationary/flyers + level** (absorbed all of Owner B on
4 Nov 2026)

- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_RockBase.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rock1.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rock2.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Rock3.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_FloatingSkull.uasset`
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_SpikeTurtle.uasset` —
  **DONE; regression only**
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Ghost.uasset` —
  **DONE; regression only**
- `Content/DontTrustTheLevels/Enemies/Blueprints/BP_Bat.uasset` —
  **DONE; regression only**
- `Content/DontTrustTheLevels/Levels/L_Level_01.umap` — **M1 test staging and M4 only**
- `Content/DontTrustTheLevels/Levels/L_Level_Testing.umap` — A2 scratch PIE map
  (formerly B's; never a shipped-level edit)
- May append only to the status log in `Docs/EnemyWorkPlan.md`; request contract
  changes from A1

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
missing, add it to §4 first and tell A1 before creating it.

### 4.2 A1/A2 parallel boundary

This split is conflict-free only while both owners stay on their side of the
boundary:

| A1 may edit/save | A2 may edit/save |
|---|---|
| `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail` | `BP_RockBase`, `BP_Rock1/2/3`, `BP_FloatingSkull`, `BP_SpikeTurtle`, `BP_Ghost`, `BP_Bat` |
| contract docs in §4.1 | `L_Level_01`, `L_Level_Testing` |
| — | status-log lines only; request contract changes from A1 |

- A1 never saves `L_Level_01` or a Rock child. A1 may PIE-test the map after
  A2 saves a test setup, but must not save the map.
- A2 never opens `BP_EnemyBase`, `BP_EnemyPlatform` or `BP_Snail` for saving. If
  the base, platform or Snail class needs a change, A2 posts a request to A1.
- A2 stages the map instance of the temporary M1 smoke-test actor (`BP_Rock1` on
  P_02 or `BP_Snail` on P_00), commits/pushes the map and releases the lock so A1
  can pull it. A2 never edits the Snail asset. A1 runs PIE without saving; A2
  removes the actor after M1 and pushes the cleanup. A1 never saves the map.
- A1 may prepare Snail variables/defaults/art; A2 may prepare Rock and Skull
  variables/defaults/art and static map/platform placement. Walker graphs and
  walker PIE wait for `M1 GREEN`.
- `BP_EnemyPlatform` is frozen for A2 placement after M1. If A1 must change the
  class, A2 re-saves the affected map instances and re-runs the walker smoke test.

No file in the left column overlaps a file in the right column. A Git LFS lock
conflict means one of these rules was broken, not that the split is wrong.

A1's post-M1 work is Snail; A2's is Skull, then Rocks, then the two maps. A2 now
carries both the M2 specials and the M4 map block, so the order in §6 is a hard
sequence for A2, not a menu: finish `BP_FloatingSkull` before opening
`L_Level_01`, and hand Rock placement to M4 after the Rocks compile. A1 hands
over exact placement coordinates and PIE results but must not save a map.

---

## 5. Dependency graph

```text
M0  all owners read the docs (no edits)
     |
     +-- A1: M1  BP_EnemyBase AI core gate ---------------------+
     |           (blocks every walker)                          |
     |                                                          |
     +-- A2: M2  FloatingSkull                                  |
     |          (Turtle/Ghost/Bat already DONE - regression only)|
     |          (no base-AI dependency)                         |
     |                                                          |
     +-- A2: prep Rock vars/defaults + static map placement     |
     |          (no walker graph or walker PIE before M1)       |
     |                                                          |
     +-- C: M2b Projectile -> Puddle -> Shooter -> WoodLog      |
                (support; WoodLog final aggro waits for M1)      |
                                                                 |
     M1 gate ----------------------------------------------------+
     |
     +-- A1: M3a Snail
     +-- A2: M3b Rocks
     +-- C: M3c Rhino -> Toxic Slime
     |
     M4  integration, placement, full PIE matrix
         (A2 owns both maps; A1 owns base verifier + contract docs)
```

M1 is the only hard gate. A1 may prep Snail and A2 may do Rock/map preparation
while A1 builds the base, but walker graphs and walker PIE wait for M1 GREEN.
A2's specials (only `BP_FloatingSkull` is left) and C's
projectile/puddle/shooter work do not read the walker AI and may run
immediately. C may build the Wood Log defaults and firing graph early, but must
not wire or PIE-test its aggro/patrol until M1 is green.

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

### M1 — `BP_EnemyBase` AI core gate (A1; blocks walkers)

**Read:** `EnemyAI.md` §3–7 and §10; `Enemies.md` §3–4.

**Work**

1. **DONE 24 Oct** — rename `bEnable` → `bEnabled` in `BP_EnemyPlatform`,
   compile and save. Live check: `bEnabled=true`, `Zone` `NoCollision`/hidden.
2. **DONE 4 Nov 2026; re-verified 5 Nov** — the §4 variables exist;
   `_check_enemy_ai_vars.py` = **25 PASS / 0 FAIL**. `MoveSpeed` was never
   duplicated, `HomePlatform` is typed, `KnowbackForce` is gone and `MaxWalkSpeed`
   was not added as a variable. If a step below still looks open, trust this line:
   the asset was re-read.
3. **DONE 4 Nov 2026** — all four function batches exist (13/13 AI functions,
   21 function graphs in the asset):
   - `PointInPlatformZone`, `PointInPlatformXZ`, `FindHomePlatform`,
     `AdoptPlatform`.
   - `LedgeAhead`, `PatrolStep`.
   - `IsPlayerOnHomePlatform`, `IsPlayerInAggroBox`, `ChaseStep`, `UpdateAggro`.
   - `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`.
4. **Verify in PIE** — `BeginPlay` → `FindHomePlatform`; `Landed` →
   `ResolveKnockback`; `Tick` → the state loop (wired); `AnyDamage` sets
   `bWasKnockedBack` before `LaunchCharacter`.
5. The `Event Tick` gate must be:
   `bIsDead OR bStranded OR NOT bCanMove` → return, then
   `bWasKnockedBack` → return, then `ChaseSpeed <= 0` → `PatrolStep` and return.
   This is what makes stationary/flyers safe and Snail/Slime patrol-only.
6. `UpdateAggro` must skip to `PatrolStep` when `ChaseSpeed <= 0`; do not let a
   no-detection walker set `bAggro`.
7. **DONE 5 Nov 2026, A1** — the aggro-on-hit change (`bAggroOnHit`, the existing
   `DeAggroTime` reused as the post-hit window, `Reachable` formula) from §7 `A1`
   and §13 landed before the Rock/WoodLog/Snail CDO flips. `UpdateAggro` is 54
   nodes with the three corrected links, and `_verify_enemy_base.py` now fails if
   any of the three old links returns.

**M1 acceptance gate**

- Parent and every compiled child have no red errors.
- `py -3 Scripts\_verify_enemy_base.py` holds **52 PASS / 0 FAIL**.
- PIE tests 1–9 from `EnemyAI.md` §11 pass on a temporary `BP_Rock1` placed on
  P_02 (z ≈ `506.25`) or `BP_Snail` on P_00 (z ≈ `875`). A2 stages, commits and
  pushes the test setup, then A1 pulls and runs PIE. A1 never saves the map; A2
  removes the test actor after M1. Do not save level tuning yet.
- Specifically verify: patrol edge turns, same-platform-only aggro, de-aggro,
  knock-off platform adoption, stair stranding/rescue.
- Commit + push, then post `M1 GREEN` with the verifier output. Only then may
  A1 start Snail, A2 start Rocks and C start Slime/Rhino/final Wood Log aggro.

Existing auto-zone surfaces in `L_Level_01` (world X / Z / width):
P_00 `x=-400, z=800, w=800` · P_01 `x=950, z=600, w=500` ·
P_02 `x=-800, z=400, w=800` · P_03 `x=350, z=400, w=500` ·
P_04 `x=-1750, z=100, w=300` · P_05 `x=-1300, z=0, w=600` ·
P_06 `x=550, z=0, w=2700`. Use these for the M1 smoke test; add more zones
only in M4.

### M2 — Independent specials (A2; only the Skull's PIE is left)

Order: ~~`BP_SpikeTurtle` (warm-up) → `BP_Ghost` (highest risk) → `BP_Bat`~~
(these three are **DONE**, see §10) → ~~`BP_FloatingSkull`~~ **build DONE 5 Nov
2026** (`bb3627d`); only its PIE gate is open (see `A2e`).

- None of these use `PatrolStep`, `LedgeAhead`, `IsPlayerOnHomePlatform` or the
  walker aggro loop.
- Set `bCanMove=false` on all four. `ChaseSpeed=0` for Turtle/Ghost/Skull;
  Bat keeps `ChaseSpeed=1000` for `MaxFlySpeed`. The Skull asset does carry an
  enabled `ReceiveTick` sub-graph even though this line used to say it has none —
  `A2e` has the open item to keep or remove it.
- Compile + save after each graph; PIE each asset before moving to the next.
- New to A2: do **not** rebuild the three DONE assets. Touching them is a
  regression risk with no upside; only open one if a PIE retest fails, and then
  treat it as a defect, not a task.

**M2 acceptance:** nothing needs re-proving on Turtle/Ghost/Bat — tests 10, 12,
13 and 14 are already PASS and stay as regressions. The open item is Skull's
extended test from `Enemies.md` §7.3, plus no base-verifier regression.

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

**A1:** `BP_Snail`.

**A2:** `BP_RockBase`/`BP_Rock1/2/3` — only after `BP_FloatingSkull` is done in
M2, because A2 is now single-threaded across both milestones.

**C:** `BP_Rhino` → `BP_ToxicSlime` → finish `BP_WoodLog` aggro/patrol.

- A walker must not add its own movement Tick. Use base `PatrolStep`,
  `ChaseStep` and `UpdateAggro`; override only the state-specific parts.
- Toxic Slime sets `ChaseSpeed=0` (no detection). Rocks, Rhino and Wood Log set
  a positive `ChaseSpeed`. Snail is the §13 exception: `ChaseSpeed=250` with
  `AggroHalfWidth=0` / `AggroHalfHeight=0` and `bAggroOnHit=true`, so it only
  reacts to being shot.
- Snail's shell uses the same base `PatrolStep` with `MoveSpeed=ShellSpeed`;
  do not add the old shell Tick.
- Wood Log overrides `ChaseStep` to stand and shoot; it does not chase.
- Rhino overrides `UpdateAggro` only to maintain `bCharging` after calling
  `Parent: UpdateAggro`; detection itself stays in the base.

**M3 acceptance:** tests 11, 15, 16 plus the Snail/Toxic Slime checks in
`Enemies.md` §7.3; split pieces adopt their landing platform; shell stays on
platform; Rhino dies on the 4th wall hit.

### M4 — Integration, placement and tuning (all; A2 owns both maps, A1 owns verifier/docs)

- A2 places the test enemies and any additional `BP_EnemyPlatform` zones in
  `L_Level_01`; A1 and C report coordinates and do not save the map.
- A2 coordinates the full `EnemyAI.md` §11 matrix (1–16) plus the extended
  checks in `Enemies.md` §7.3; each owner runs its own asset's PIE checks. A2
  also re-runs tests 10/12/13/14 as regressions on the three inherited assets.
- Tune `AggroHalfWidth/Height`, `ChaseSpeed`, `DeAggroTime`, `RescueRadius`,
  `MinPatrolWidth` and per-enemy speeds in Class Defaults, not in duplicated
  child variables. A1 owns base/platform/Snail defaults; A2 owns Rock + Skull
  defaults.
- A1 re-runs `_verify_enemy_base.py`; hold **52 PASS / 0 FAIL**. A1 also owns
  the aggro-on-hit contract change (`bAggroOnHit`, with `DeAggroTime` reused as
  the post-hit window); it is landed in the base, so the
  Rock/WoodLog/Snail CDO flips can proceed.
- A1 commits contract docs + Snail; A2 commits both maps + Rocks + Skull; all
  owners clean probe files and release their locks.

---

## 7. Work cards

Each card is the assignment. The card tells you **what to build and how to
prove it**; the linked sections contain the exact pin-level recipes. Do not
invent a third source.

Cards are numbered by asset group, not grouped by owner, so use this index:

| Owner | Cards | State |
|---|---|---|
| **A1** | `A1` (`BP_EnemyBase`), `A1b` (`BP_Snail`) | `A1` **DONE** — `M1 GREEN` 8 Nov 2026 (13/13 functions, 25/25 vars, 52 PASS, tests 1–9 closed). `A1b` **PARTIAL** — aggro CDO done (250 / 0 / 0, `bAggroOnHit=true`); shell graph, remaining Class Defaults and art open |
| **A2** | `A2a` (Rocks), `A2b` (Turtle), `A2c` (Ghost), `A2d` (Bat), `A2e` (Skull) | 3 of 5 done (Turtle, Ghost, Bat). `A2e` **BUILT 5 Nov 2026** (`bb3627d`, B's own commit) — seven variables + Class Defaults + `RefreshStateFlipbook` verified live 8 Nov; only its PIE gate is open. `A2a` **BUILT 8 Nov 2026** (`f37473b`, Jones, merged as `320f0de`) — Class Defaults and logic verified; split defects 1–3 fixed and re-verified 9 Nov 2026 (static export + a Simulate kill), only PIE test 11 (a live player) is open. The `A2`/`C` rows are the 4 Nov 2026 snapshot, see §10 for later rows |
| **C** | `C1`–`C6` | nothing started |

Owner B has no cards; `A2b`–`A2e` are the transferred ones. A card owns its
**asset**: `A1` may not tick Snail work and `A1b` may not tick base work, even
though one person owns both.

### A1 — `BP_EnemyBase` AI core (Owner A1)

**Read:** `EnemyAI.md` §3–7, §10; `Enemies.md` §3–4.

**Depends:** none. **Blocks:** every walker.

**Scope:** edit only `BP_EnemyBase`, `BP_EnemyPlatform` and the contract docs.
Never save `L_Level_01`; A2 stages/removes the M1 test actor. `BP_Snail` is the
`A1b` card — Snail work is ticked there, never here.

**Tasks**

- [x] **DONE 24 Oct** — rename `bEnable` → `bEnabled` in `BP_EnemyPlatform`;
      compile/save. Live check: `bEnabled=true`, `Zone` extent `(50,50,20)`,
      `NoCollision`, hidden.
- [x] Add the new §4 variables, including typed `HomePlatform`; `MoveSpeed`
      already exists; remove `KnowbackForce`; do not add `MaxWalkSpeed`.
      **DONE 4 Nov 2026; re-verified 5 Nov** — all 25 §4 variables exist with the
      documented defaults; `Scripts\_check_enemy_ai_vars.py` = **25 PASS / 0 FAIL**
      (both October renames landed; `bAggroOnHit` is the 25th).
- [x] Build `PointInPlatformZone`, `PointInPlatformXZ`, `FindHomePlatform`,
      `AdoptPlatform`.
- [x] Build `LedgeAhead`, `PatrolStep`.
- [x] Build `IsPlayerOnHomePlatform`, `IsPlayerInAggroBox`, `ChaseStep`,
      `UpdateAggro`. **DONE 4 Nov 2026** — all four function graphs exist
      (21 function graphs in the asset, 13/13 AI functions).
- [x] Build `ResolveKnockback`, `MeasurePlatformWidth`, `TryRescue`.
      **DONE 4 Nov 2026.**
- [x] Wire `BeginPlay`, `Landed`, `Event Tick`, and the `AnyDamage`
      `bWasKnockedBack` flag. **`Event Tick` is a wired event node.**
- [x] **DONE 5 Nov 2026 — aggro on hit** (`EnemyAI.md` §6.2/§6.3). Base side only:
      `bAggroOnHit` (Boolean, `false`) and the hit term in `UpdateAggro` (54 nodes
      then, 61 after the 7 Nov acquire/keep split); it reuses `DeAggroTime` and
      skips the same-platform/Z gate. The per-child CDO flips (`BP_Rock1/2/3`,
      `BP_WoodLog`, `BP_Snail`) are child-card work and are ticked there — `A1b`
      for the Snail, `A2a` for the Rocks, `C` for the Wood Log. `BP_Bat` needs its
      own `RefreshStateFlipbook` hit branch because it never runs the walker loop.
- [x] **DONE 7 Nov 2026 — `LaunchCharacter` Z override.** The `AnyDamage` launch
      now has `bZOverride = true`, so a zero `KnockbackForce` sends a zero vector
      and `HandlePendingLaunch()` returns early. `BP_Bat` (the only
      `KnockbackForce=0` child) keeps `MOVE_Flying` / `MaxFlySpeed` after a hit;
      grounded walkers are unchanged (`Vz ≈ 0`). Evidence: §10 row of 7 Nov,
      `Scripts/_check_bat_hit_knockback.py` → `PASS (A)`,
      `_verify_enemy_base.py` 52 PASS / 0 FAIL.
- [x] **Gate:** verify the Top gate
      (`bIsDead OR bStranded OR NOT bCanMove` → return; `bWasKnockedBack` →
      return; `ChaseSpeed <= 0` → `PatrolStep` → return) in PIE with tests 1–9.
      All three AI halves now exist, so this is a verification task, not a build
      task. **DONE 8 Nov 2026 — 1–7 PASS in `L_Level_01`, 8 PASS via the spawn
      variant of the rescue, 9 N/A there. `M1 GREEN` posted in §10.**

- [x] **Step 4 of the A2a fix plan — refresh the flipbook from the movement
      loops** (defect 3 there; this one blocks *every* walker, not just the
      rocks). Four single-node inserts, two drags each, no re-paste. Right-click
      an empty spot next to the target, type `Refresh State Flipbook`, Enter —
      it is this blueprint's own function, so there is no cast and no `self` wire:

      | graph | insert after | new node's `then` goes to |
      | ----- | ------------ | ------------------------- |
      | `ChaseStep` | `AddMovementInput` (walk branch; its `then` is open) | nothing — leave it open |
      | `ChaseStep` | `StopMovementImmediately` | the existing `FunctionResult` |
      | `PatrolStep` | `AddMovementInput` | `FunctionResult_0` |
      | `PatrolStep` | the final `SetFacing` (`Direction 0.0`) | `FunctionResult_1` |

      Wiring, per insert: drag `target.then` → the new `execute` (that *moves*
      the wire), then drag the new `then` → the old consumer when there was one.
      Never drop the node onto the wire and never drag a wire end onto another
      wire: both splice a reroute node, which is how the `BP_RockBase` loopback
      survived two repairs (see `A2a` above). Current graph from
      `Scripts/_bp_enemy_dump.txt` (8 Nov): `ChaseStep` 16 nodes — Entry →
      SetFacing → LedgeAhead → Branch, whose **then** pin goes to
      AddMovementInput (and that `then` is open) and whose **else** pin goes to
      StopMovementImmediately → FunctionResult_0. `PatrolStep` 28 nodes — Entry →
      Branch(IsValid HomePlatform) (its **else** is open) → Branch A (out of the
      patrol range): **then** → SetFacing(1.0) → Branch B, **else** → Branch B;
      Branch B: **then** → SetFacing(-1.0) → LedgeAhead, **else** → LedgeAhead;
      LedgeAhead → Branch C, **then** → AddMovementInput → FunctionResult_0,
      **else** → SetFacing(0.0) → FunctionResult_1.

      Gate (no PIE without it):

          py -3 Scripts/_export_bp_enemy.py                 # live T3D -> _bp_enemy_dump.txt
          py -3 Scripts/_check_step4_live.py --self-test    # needs 10 PASS / 0 FAIL

      `Scripts/_check_step4_live.py` requires two `Refresh State Flipbook` calls
      per graph, each one *the very next* exec node after its insertion point and
      each ending the function (open `then`, or straight into the
      `FunctionResult`); no exec cycle; no reroute. `--self-test` splices the four
      refreshes into a copy of the same graph and requires `10 PASS`, so green
      means the wires are really there. On the asset as it stands it prints
      `4 PASS / 6 FAIL`:

          [FAIL] 1  ChaseStep: 0 Refresh State Flipbook calls, expected 2
          [FAIL] 1  PatrolStep: 0 Refresh State Flipbook calls, expected 2
          [FAIL] 2  ChaseStep after move: after fn AddMovementInput comes <nothing> ...
          [FAIL] 2  ChaseStep after stop: after fn StopMovementImmediately comes
                    K2Node_FunctionResult_0(fn ChaseStep) ...
          [FAIL] 3  PatrolStep after move: after fn AddMovementInput comes
                    K2Node_FunctionResult_0(fn PatrolStep) ...
          [FAIL] 3  PatrolStep after final SetFacing: after fn SetFacing comes
                    K2Node_FunctionResult_1(fn PatrolStep) ...

      PIE: the rocks in A2a's test 11 must switch to `Run` while they chase (their
      override reads `Abs(Velocity.X) > 10`) and no walker may still show `Idle`
      while patrolling/chasing (tests 1–7 in `L_Level_01`); `PlayStateFlipbook`
      no-ops when nothing changed, so the four extra calls cost nothing.
      **8 Nov 2026: APPLIED by the owner.** The live export is 18 / 30 nodes and
      `Scripts/_check_step4_live.py --self-test` prints `10 PASS / 0 FAIL`; the
      exec trace is exactly the table above. **Step 4b below is required before
      PIE**: on its own the four calls freeze the sprite.

- [ ] **Step 4b of the A2a fix plan — the four refreshes must be no-ops**
      (regression, found in PIE on 8 Nov 2026: every enemy "stands still and
      glides"). `BP_EnemyBase.RefreshStateFlipbook` plays `IdleFlipbook`, and
      four of the five overrides start with `Parent: Refresh State Flipbook` and
      then play their own sheet:

      ```
      Parent: Refresh State Flipbook  ->  SetFlipbook(IdleFlipbook)
      Branch(|Velocity.X| > 10)       ->  SetFlipbook(RunFlipbook)
      ```

      `UPaperFlipbookComponent::SetFlipbook` (4.27,
      `Engine/Plugins/2D/Paper2D/Source/Paper2D/Private/PaperFlipbookComponent.cpp`
      line 379) does `AccumulatedTime = 0.0f` every time the asset differs. With a
      refresh on every exit of `ChaseStep` / `PatrolStep` that is twice per frame,
      so the sprite is pinned to frame 0 of the last sheet and slides across the
      floor. `Play()` (line 434: `Activate(); bReversePlayback = false;
      bPlaying = true;`) and `SetLooping()` (line 578: one bool, no restart) are
      harmless per frame — `SetFlipbook()` is not.

      | asset | state 8 Nov 2026 | fix |
      | ----- | ---------------- | --- |
      | `BP_RockBase` | `Entry -> Parent -> Branch -> Idle/Run` | delete the `Parent: Refresh State Flipbook` node, wire `Entry.then` -> the Branch's `execute` (its `else` already plays `IdleFlipbook`) |
      | `BP_SpikeTurtle` | `Entry -> Parent -> Branch -> IdleFlipbookA/B` | same |
      | `BP_FloatingSkull` | `Entry -> Parent -> Branch -> On/OffIdleFlipbook` | same |
      | `BP_Bat` | `Entry -> Branch(bWasKnockedBack) -> 5 x Set -> Parent -> Branch(bChasing) -> Flying/Hanging` — the parent call is on **both** paths, but no per-frame refresh reaches it (events only), so it costs one reset per hit and not a freeze | optional: delete it, then wire `Set MaxFlySpeed.then` and `Branch(bWasKnockedBack).else` to `Branch(bChasing).execute` |
      | `BP_Ghost` | `Entry -> Parent -> Branch` with the `Condition` pin **unwired** (default `true`), so `then` is empty and the parent's Idle is the only sheet | finish the branch (`bInvisible` -> return, else `PlayStateFlipbook(FLB_Ghost_Idle)`) first, then delete the parent call; tracked under `A2c` |

      Exact wires as exported on 8 Nov 2026 (`py -3
      Scripts/_dump_refresh_graphs.py <BP>` prints this straight from the asset):

          BP_RockBase       Entry.then -> Parent.execute, Parent.then -> Branch.execute
                            Branch.then -> PlayStateFlipbook(RunFlipbook)   @(1024,-160)
                            Branch.else -> PlayStateFlipbook(IdleFlipbook)  @(1024, 128)
                            Branch.Condition <- Greater_FloatFloat(Abs(BreakVector(GetVelocity).X) > 10)

          BP_SpikeTurtle    Entry.then -> Parent.execute, Parent.then -> Branch.execute
                            Branch.Condition <- Get bSpikesOut
                            Branch.then -> PlayStateFlipbook(IdleFlipbookA)
                            Branch.else -> PlayStateFlipbook(IdleFlipbookB)

          BP_FloatingSkull  Entry.then -> Parent.execute, Parent.then -> Branch.execute
                            Branch.Condition <- Get bPoweredOn
                            Branch.then -> PlayStateFlipbook(OnIdleFlipbook)
                            Branch.else -> PlayStateFlipbook(OffIdleFlipbook)

          BP_Bat            Entry.then -> Branch(bWasKnockedBack).execute
                            ...then -> Set bWasKnockedBack/bTriggered/bChasing/bDealContactDamage
                                       -> Set MaxFlySpeed -> Parent.execute
                            ...else -> Parent.execute
                            Parent.then -> Branch(bChasing).execute
                            Branch(bChasing).then -> PlayStateFlipbook(FlyingFlipbook)
                            Branch(bChasing).else -> PlayStateFlipbook(HangingFlipbook)

          BP_Ghost          Entry.then -> Parent.execute, Parent.then -> Branch.execute
                            Branch.Condition OPEN, Branch.then OPEN,
                            Branch.else -> PlayStateFlipbook(NewFlipbook OPEN)

      So in all three fixable assets the edit is the same two steps: **delete the
      `Parent: Refresh State Flipbook` node**, then **drag `Entry.then` onto the
      `Branch.execute` pin**. The two `PlayStateFlipbook` calls, their `Get
      *Flipbook` feeds and the Branch `Condition` do not change.

      Gate (read-only, editor open):

          py -3 Scripts/_check_refresh_reset.py --self-test
          py -3 Scripts/_check_refresh_reset.py --reuse --self-test

      It exports the six flipbook-selecting BPs to `Scripts/_child_refresh_export/`
      and then, per BP: no `Parent: Refresh State Flipbook` in the unconditional
      prologue (entry up to the first Branch), every Branch output reaches a
      `PlayStateFlipbook` of its own, no reroute in the prologue. `--self-test`
      injects a fake Parent node (rule 1 must catch it) and drops the parent call
      from a broken copy (the failure must clear), so green is not a rubber stamp.
      **9 Nov 2026: `BP_RockBase`, `BP_SpikeTurtle` and `BP_FloatingSkull` are
      fixed** — the run prints `16 PASS / 2 FAIL` (`22 PASS / 2 FAIL` with
      `--self-test`) and both failures are `BP_Ghost` rules 1 + 2: its override
      still enters through `Parent: Refresh State Flipbook` and
      `Branch.then` reaches no `PlayStateFlipbook` of its own. Every walker
      (rocks included) is past this gate; `0 FAIL` is still the target, and the
      Ghost's branch has to be finished before its parent call can go. Tooling note:
      `Scripts/_children_export2/` holds 12 KB stub T3Ds from the 21:19 audit that
      contain no function graphs at all — a "this BP has no `RefreshStateFlipbook`"
      reading from it is wrong, export again before believing it.

      PIE after the fix: walkers animate while they patrol, the rocks switch to
      `FLB_Rock<n>_Run` (14 frames @ 14 fps) while they chase, and no
      `Infinite loop` / `Runaway loop` line appears in the log.

- [x] **Step 4c of the A2a fix plan — the standing-still window must play `Idle`**
      (report, 8 Nov 2026: "the rock de-aggroes and stands still for a while, but
      it keeps playing `Run` instead of `Idle`"). `ChaseStep` and `PatrolStep`
      refresh on every exit (step 4), but `UpdateAggro` has a third way to stand
      still that neither function sees — the `DeAggroTime` wait:

      ```
      Branch_2 (bAggro).then -> Set MaxWalkSpeed = MoveSpeed -> Branch_3
          Branch_3.then  (player unreachable >= DeAggroTime)
              -> Set bAggro=false -> Set_5 -> Set_6 -> Refresh State Flipbook -> Return
          Branch_3.else  (still waiting, < DeAggroTime)
              -> StopMovementImmediately -> SetFacing(0.0) -> function ends   <- no refresh
      ```

      The rock is motionless for up to `DeAggroTime` (2 s) holding the sheet it
      chased with (`FLB_Rock<n>_Run`), and only after the countdown expires does
      `Idle` appear. Motion is already zero (`StopMovementImmediately`), so this
      is the "stand still and keep walking" the report describes. Fix is a
      **base** change, so it covers every walker (rocks, snail, wood log, rhino):

      ```
      UpdateAggro:  SetFacing.then -> Refresh State Flipbook     (then left open)
      ```

      Per-frame is safe for the same reason as step 4b: the velocity is zero
      before the call, so the child override's `Abs(Velocity.X) > 10` is false and
      it re-selects the sheet it already plays — `SetFlipbook` is never called,
      `AccumulatedTime` is not reset.

      Gate (read-only): `py -3 Scripts/_check_idle_gap.py [--export]` must print
      `2 PASS / 0 FAIL`. **9 Nov 2026: APPLIED and green** — `2 PASS / 0 FAIL`,
      and its built-in self-test is `2 PASS / 0 FAIL` too (it splices the wire into
      a copy of the graph and requires rule 1 to flip, so green is not a rubber
      stamp). Before the fix the same run printed `1 PASS / 1 FAIL` and named the
      gap: `K2Node_CallFunction_17` (`SetFacing`) was fed by
      `StopMovementImmediately` with nothing after it.

- [ ] **Step 4d — `BP_Ghost` contact is dead while it chases** (report, 8 Nov
      2026: "the ghost is just chasing me but not killing the player"). The base
      contact chain is **not** the problem: `_verify_enemy_base.py` is
      `52 PASS / 0 FAIL`, including "ContactBox overlap kills the player after the
      player-only gate". The kill is a `ContactBox` `On Component Begin Overlap`
      (`EnemyAI.md` §9), so it only happens while the ghost's own overlaps are
      updated — and `BP_Ghost` is the only enemy whose `CollisionCylinder` is
      `NoCollision`, with no phase enabling it again:

      | graph | capsule | `ContactBox` | `bInvulnerable` | `bDealContactDamage` |
      |---|---|---|---|---|
      | `Init Ghost Hidden Logic` | NoCollision | NoCollision | **false** (spec: true) | false |
      | `StartAggro Logic` | **never touched** | QueryOnly | false | true |
      | `StartAppear Logic` | **never touched** | QueryOnly | **true** (spec: false) | true |
      | `BecomeInvisible Logic` | NoCollision | **never touched** (spec: off) | true | false |

      That is the opposite of `EnemyAI.md` §8.4 and `Enemies.md` §6.4 ("visible =
      capsule and `ContactBox` on with `WorldStatic=Ignore`; hidden = both off").
      A `Character` whose root capsule has no collision does not update its child
      overlaps, so the box never sees the player and the base kill never fires.
      The `BecomeVisible` `IsOverlappingActor -> Kill(player)` hack only covers
      the single frame the ghost reappears on top of the player, which is why
      test 13 passed while normal contact stayed dead. The two inverted
      `bInvulnerable` literals are the same class of bug: shotable while
      invisible, immortal once it reappears.

      Fix (five edits in the editor):

      1. Class Defaults → `CollisionCylinder`: preset `Custom`, `Pawn = Overlap`,
         `WorldStatic = Ignore`, `WorldDynamic = Ignore`, `Visibility = Ignore`,
         `Collision Enabled = No Collision` (the graphs switch it on/off).
      2. `StartAggro Logic`: add `CollisionCylinder → Set Collision Enabled
         (QueryOnly)` between `Sprite.SetVisibility(true)` and
         `Set bInvulnerable = false`.
      3. `StartAppear Logic`: the same node in the same place.
      4. `BecomeInvisible Logic`: after `CollisionCylinder → Set Collision Enabled
         (NoCollision)` add `ContactBox → Set Collision Enabled (NoCollision)`, so
         the hidden phase is fully intangible as specified.
      5. Literals: `Init Ghost Hidden Logic` `bInvulnerable` → **true** (it is
         `false` today); `StartAppear Logic` `bInvulnerable` → **false** (it is
         `true` today).

      Gate (read-only): `py -3 Scripts/_check_ghost_phases.py` must print
      `16 PASS / 0 FAIL`. Today it prints `11 PASS / 5 FAIL`: no capsule call in
      `StartAggro`/`StartAppear`, no `ContactBox` off in `BecomeInvisible`, and
      both `bInvulnerable` literals inverted. Its built-in self-test injects one
      **defect** per rule into a copy of the parsed graphs and requires that rule
      to fail (`6 PASS`), so it still proves detection now that the asset is
      correct — injecting the fix into an already-fixed graph moves nothing.

      PIE: walk into the sphere, stay in the open; while visible, touching the
      ghost must kill the player, bullets must pass through it while it is
      hidden, and 2 hits must still kill it after several visible/hidden cycles.


- [ ] **Step 4e — the actual reason the ghost never damages the player: it flies on
      a different Y plane** (confirmed live, 8 Nov 2026, *after* step 4d was
      applied). Correction to 4d: the capsule was **not** the blocker. With 4d in
      place the live ghost is correct while visible (`bInvisible=false`,
      `bDealContactDamage=true`, `ContactBox=QueryOnly`) yet
      `get_overlapping_actors()` stays empty and the 3D distance to the player
      never drops below **~291** while it flies at `MaxFlySpeed=250`.

      `Aggro Trigger Logic` drops Y on purpose (`MakeVector(X = dX, Y = 0,
      Z = dZ)` → `Normal` → `AddMovementInput`), and `BP_Ghost` is placed at
      **Y = 280** in `L_Level_01` while `PlayerStart`, `BP_Bat` and
      `BP_SpikeTurtle` are on **Y = 0** (`BP_Rock1` is at 10). In an orthographic
      side view Y is depth, so the ghost looks like it is on the player while it
      is 280 uu away in depth — more than `ContactBox`'s world Y half-extent
      (44 × 2.34 ≈ 103) plus the player capsule. No overlap is possible, so the
      base kill can never fire.

      Proof: setting the live ghost's Y to 0 mid-chase made its box report
      `overlaps=['BP_Player_C_0']` on the next call, and the level instantly
      reloaded (`Kill` → `OpenLevel`) with the player back at `PlayerStart`.

      Fix (one field, no graph change): select `BP_Ghost` in `L_Level_01` and set
      `Location Y = 0`, then save the level. Keep the 4d edits — they are
      required too (before them the box was `NoCollision` in the visible phase).

      Gate (read-only, editor open): `py -3 Scripts/_run_py.py
      Scripts/_check_enemy_plane.py` must print `4 PASS / 0 FAIL`. It compares
      every placed enemy's Y with `PlayerStart` and fails when the offset exceeds
      that enemy's `ContactBox` world Y half-extent; on the unfixed level it
      prints `3 PASS | 1 FAIL` (`BP_Ghost Y=280 dY=280 boxY±75 tol=80`).

      Robustness (optional, A1 ruling): a ghost placed off-plane in a future level
      reproduces this silently. Either keep every enemy on `Y = 0` (level rule) or
      change `MakeVector` in `Aggro Trigger Logic` to pass `Y = dY`, so the chase
      closes depth as well.

      **9 Nov 2026: the level was fixed in place, but not to `Y = 0`.** The saved
      `L_Level_01` has `BP_Ghost` at **`Y = -70`**, and the gate now reads
      `4 PASS / 0 FAIL` (`BP_Ghost Y=-70 dY=70 boxY±75 tol=80`) — the ghost is
      back on the player's plane and kills on contact (owner-confirmed "works").
      That is only **5 uu** of `ContactBox` depth inside the 75 uu half-extent, so
      it is one drag away from silently going dead again. `_check_enemy_plane.py`
      now prints a `WARN <label>: only N uu of ContactBox depth left ... set its Y
      to <plane>` line whenever a PASS has under `SAFE_OVERLAP = 10` uu to spare;
      it fires for this ghost today. Recommend setting it to `Y = 0` (what the fix
      above asks for); leaving `-70` works but is the fragile configuration.


**Done when:** `_verify_enemy_base.py` = 52 PASS / 0 FAIL; tests 1–9 closed
(1–7 and 8 pass — 8 via the spawn variant — and 9 is N/A in `L_Level_01`);
compile clean; committed; `M1 GREEN` posted.

---

### A2b — `BP_SpikeTurtle` (Owner A2 — **DONE**, transferred from B)

**Read:** `EnemyAI.md` §8.1; `Enemies.md` §6.1; `EnemyPlacement.md` §4.1.
**Depends:** base health/contact only. **No base AI.**

**Status: DONE** — test 10 PASS (§10 status log, 25 Oct 2026), including the
contact kill after the base `ContactBox` fix. Two open rulings were inherited
from B's last resave and are **still pending A1**: the turtle capsule ended at
`Pawn=Block`, and the `ToggleIdle` timer in the card below was removed from the
graph. Neither breaks test 10, so do not "fix" them silently — A1 rules, then
this card is synced to the asset. Do not re-derive the graph.

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

### A2c — `BP_Ghost` (Owner A2 — **DONE**, transferred from B)

**Read:** `EnemyAI.md` §8.4; `Enemies.md` §6.4; `EnemyPlacement.md` §4.4.
**Depends:** base health/contact only. **No base AI.**

**Status: DONE** — tests 12–13 PASS (§10, 26 Oct 2026): 550-sphere trigger,
through-wall chase, visible/hidden loop, 2 hits, no de-aggro. **Open item, A2:**
Ghost was built before M1, so it declares TEMP-M1 locals `bAggro`,
`AggroRadius` and `ChaseSpeed` in the child. The base now owns all three, so
those are shadow variables — delete them, inherit, and retest 12–13. Also keep
the native-left art fix: the Ghost sprite faces left, so the `SetFacing` input is
negated inside the chase.

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

### A2d — `BP_Bat` (Owner A2 — **DONE**, transferred from B)

**Read:** `EnemyAI.md` §8.8; `Enemies.md` §6.8; `EnemyPlacement.md` §4.8.
**Depends:** base health/contact only. **No base AI.**

**Status: DONE (5 Nov 2026 — regression fixed).** Test 14 passed on 27 Oct.
All three playtest bugs are verified fixed in PIE: the live
`RefreshStateFlipbook` has the 13-node hit branch from
`Scripts/_bp_bat_hit_aggro_only.txt` plus the
`Set MaxFlySpeed = ChaseSpeed` write, and the EventGraph `HangIdle` custom event
is gated on `bTriggered`. The staged 17-node
`Scripts/_bp_bat_refresh_modified_v2.txt` remains available for a clean
re-paste (it also contains the hit-path `K2_ClearTimer("HangIdle")`). Live CDO
otherwise unchanged: `TriggerRadius=1000`, `ChaseSpeed=1000`,
`KnockbackForce=0`, `MaxAcceleration=8192`.

**Follow-up (7 Nov 2026):** the remaining "slow / invisible after a hit"
playtest report was not a graph bug — the saved asset was re-verified by a
headless T3D export and CDO readback (hit branch, `HangIdle` gate and
`MaxFlySpeed` write all intact). The **Level 1 instance** was placed at
`Y=-100` while the terrain plane (`TM_Background`, `collision_thickness=200`,
BlockAll) is at `Y=0`; its sprite rendered behind the terrain and its capsule
was embedded in the collision slab. The instance now sits at `Y=0`. Keep
flyers on the terrain plane (`EnemyPlacement.md` §2).

**Root cause of the remaining slowdown (7 Nov 2026, second pass):** the `Y` fix
removed the *invisible* sprite, but the Bat still crawled after a hit. The shared
`AnyDamage` knockback called `LaunchCharacter(..., bZOverride=false)`, and that
flag makes the launch vector inherit the Bat's own Z velocity, so
`KnockbackForce=0` still triggers `HandlePendingLaunch() ->
SetMovementMode(Falling)`. In `Falling` the cap is
`MaxWalkSpeed = MoveSpeed = 100` (written by the same handler) and only
`AirControl`-scaled X/Y input applies, so `MaxFlySpeed=1000` never matters.
`bZOverride=false` is fine for grounded walkers; `BP_Bat` is the only CDO with
`KnockbackForce=0` (every other enemy is `200`). Fix (either one):
`BP_EnemyBase.LaunchCharacter → Z Override` ✓ (root cause, A1) or a `BP_Bat`
Tick node `SetMovementMode(Flying)` before `Bat Tick Logic` (bat only, pre-wired
in `Scripts/_bp_bat_flying_guard_paste.txt`). **Applied 7 Nov 2026 (A1):** the
base pin is `true` and saved; `Scripts/_check_bat_hit_knockback.py` →
`RESULT: PASS (A: bZOverride=true)`; `_verify_enemy_base.py`
45 PASS / 0 FAIL. The Option-B guard is not in the asset and is not needed.
PIE 7/8 (walker knockback + landing/adoption) and 14 (Bat) still to re-run.

**Tasks**

- [ ] Add only the unique variables: `bTriggered`, `bChasing`,
      `TriggerRadius`, `CeilingInFlipbook`, `CeilingOutFlipbook`,
      `FlyingFlipbook`, `HangingFlipbook`. **Do not** declare `ChaseSpeed`;
      inherit it and set it to `1000` in Class Defaults.
- [ ] Class Defaults: `bCanMove=false`, `ChaseSpeed=1000`, `TriggerRadius=1000`,
      `MaxHealth=2`, `ContactDamage=1`, bat flipbooks.
- [ ] `BeginPlay`: `InitEnemy`; `bDealContactDamage=false`; play
      `CeilingInFlipbook`; start `HangIdle` (`0.6`; the callback is gated on
      `bTriggered`, or use `0.3` with the timer-clear alternative).
- [ ] `HangIdle` → Branch `bTriggered` (preferred: false → loop
      `HangingFlipbook`, true → return); or keep unconditional play with the
      `0.3 s` timer plus `K2_ClearTimer("HangIdle")` on the hit chain.
- [ ] Own `Event Tick`: trigger only when the player is valid and within the
      `1000` sphere; set `bTriggered=true`, contact on, play `CeilingOutFlipbook`,
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

### A2e — `BP_FloatingSkull` (Owner A2 — **BUILT 5 Nov; 9 Nov flyer-mode defect FIXED; stuck-bounce fallback open**, transferred from B)

**Read:** `EnemyAI.md` §8.7; `Enemies.md` §6.7; `EnemyPlacement.md` §4.7.
**Depends:** base health/contact only. **No base AI.**

**Status: BUILT 5 Nov 2026 (Owner B), PIE UNVERIFIED (8 Nov 2026 audit).** The
old "NOT STARTED / zero own variables / every base default" text below is
superseded: `bb3627d` (*"fix(enemy): skull facing, ghost contact and turtle
fixes"*, Lee Chung Hei, 5 Nov) already landed the whole build.
`Scripts/_run_probe_skull.py` (read-only, 8 Nov) reads the seven variables back
with the documented defaults (`BounceSpeed=300`, `bPoweredOn=true`,
`bUseWallAlternate=false`, `OnIdleFlipbook=FLB_Skull_Idle01`,
`OffIdleFlipbook=FLB_Skull_Idle02`, `HitWallFlipbookA=FLB_Skull_HitWall01`,
`HitWallFlipbookB=FLB_Skull_HitWall02`) and the Class Defaults as
`bCanMove=false`, `ChaseSpeed=0`, `MaxHealth=2`, `ContactDamage=1`,
`MoveSpeed=300`, `IdleFlipbook=FLB_Skull_Idle01`, `HitFlipbook`/`DeathFlipbook`
`=FLB_Skull_Hit` — 0 of 22 probed properties missing. A fresh export the same day
shows the `RefreshStateFlipbook` override traced node by node (`Parent:
RefreshStateFlipbook` → Branch on `bPoweredOn` → `PlayStateFlipbook(OnIdleFlipbook)`
else `OffIdleFlipbook`) plus a capsule-bound `ComponentHitSignature` event,
`TogglePower` and `BackToSkullIdle` sub-graphs, `BreakHitResult`/`Normal`/`Abs`
and `LaunchCharacter` — i.e. B's "sub-graph collapse" style with the bodies in
`ExecuteUbergraph_BP_FloatingSkull`. **The §10 rows of 8 Nov 2026 carry this
audit; the PIE gate is still open** (see the defect block below).

**Defects seen in PIE 8 Nov 2026** (recording of `L_Level_Testing`, 21:29). In
code the skull is not a hover enemy: it is launched **once** in `BeginPlay`
(`LaunchCharacter((Facing*BounceSpeed, 0, BounceSpeed))`, XY override on, Z
override off, so the Z term is *added* to gravity) and is only re-launched by its
own hit event.

> **Correction (pin-level re-read, same day).** An earlier note in this card said
> the reflect pushes `Abs(normal)` into the velocity and therefore always throws
> the skull up-right. That is **wrong**: `Abs` feeds only the `>= 0.5` gate — the
> `Select` values are `Nx*BounceSpeed` / `Nz*BounceSpeed` off the *raw signed*
> `BreakHitResult.Normal`, i.e. a correct axis-wise bounce. The bounce math is
> not the problem; the five items below are.

1. `ReceiveTick` runs `SetFacing(NegateFloat(Normal(GetVelocity()).X))` — the
   sprite is asked to face **opposite** to its motion, and while the skull is
   falling/rising `X ≈ 0`, `Normal()` returns `(0,0,0)`, `SetFacing(0)` resolves
   to "right", so the facing snaps and flips on every bounce. Fix:
   `SetFacing(BreakVector(Normal(GetVelocity())).X)` and only when
   `Abs(Vx) > 10`.
2. The hit event never inspects `OtherActor`, so contact with the **player** (or a
   projectile) also reflects the skull, plays a wall-hit flipbook and runs
   `TogglePower` — the skull powers itself off by touching the player. Fix: gate
   the reflect/toggle chain on `OtherActor` not being a `Pawn`.
3. The wall-hit flipbook `Select` (A vs B) is indexed by **`bPoweredOn`**, and
   `bUseWallAlternate` is referenced **nowhere** in the asset. It happens to
   alternate today only because the card's `TogglePower`-per-hit flips
   `bPoweredOn` — i.e. the two features are coupled. Fix: index with
   `bUseWallAlternate` and flip it after `PlayStateFlipbook`.
4. There is **no re-hit cooldown**: `LaunchCharacter` starts from the contact
   point, so a corner contact can re-trigger `Hit` on consecutive frames and
   re-reset the velocity — the "vibrating/pinned in the corner" look. Fix: a
   `HitCooldown` float (`0.08`) checked at the top of the hit event.
5. The hit event's **else** pin is unconnected, so a contact whose normal has
   both `|Nx|` and `|Nz|` below `0.5` (Y-facing or strongly oblique geometry)
   does nothing at all — the skull keeps pushing into that surface. Fix: wire
   the else to a plain `LaunchCharacter(Normal * BounceSpeed, XY, Z)` fallback.

`TogglePower` **on every wall/floor hit is the card's design** ("a wall/floor hit
toggles the power state"), so it stays — but it is why the skull alternates
between lethal and harmless every bounce; check that against the recording before
changing it.

`BeginPlay` also sets `bInvulnerable=true` / `bDealContactDamage=true` at
runtime, which overrides the `bInvulnerable=false` class default the probe reads.
`RefreshStateFlipbook` (ON/OFF idle by `bPoweredOn`) is reached only from
`TogglePower` and the `0.35 s` `BackToSkullIdle` timer, never per tick — the same
base-timing gap as `A2a` defect 3, so its idle never updates during a bounce.

**Tasks** (all six are in the asset; the boxes record *structure*, not proof)

- [x] Add only the unique variables: `bPoweredOn`, `OnIdleFlipbook`,
      `OffIdleFlipbook`, `HitWallFlipbookA`, `HitWallFlipbookB`,
      `bUseWallAlternate`, `BounceSpeed`. **8 Nov 2026:** all seven read back
      with the documented defaults.
- [x] Class Defaults: `bCanMove=false`, `ChaseSpeed=0`, `MaxHealth=2`,
      `ContactDamage=1`, `MoveSpeed=300`, skull flipbooks. **8 Nov 2026:** live
      probe matches, including `IdleFlipbook=FLB_Skull_Idle01`.
- [x] `BeginPlay`: `InitEnemy`; `bPoweredOn=true`; `bInvulnerable=true`;
      `bDealContactDamage=true`; play `OnIdleFlipbook`; launch
      `(Facing * BounceSpeed, 0, 1.0 * BounceSpeed)` with XY override on and Z
      override **off**.
      **8 Nov 2026 (traced node by node):** `Multiply_IntFloat(Facing,
      BounceSpeed)` → `MakeVector.X`, `Multiply_FloatFloat(1.0, BounceSpeed)` →
      `MakeVector.Z`, then `LaunchCharacter`; `MoveSpeed=300` is unused by the
      launch. The card's earlier `BounceSpeed * 0.5` was wrong.
- [x] Own `Event Hit`: ignore non-wall/floor normals; play alternating
      `HitWallFlipbookA/B`; `TogglePower`; `BackToSkullIdle` (`0.35`);
      reflect the X/Z velocity through `LaunchCharacter`. **8 Nov 2026:** the hit
      is a capsule-bound `ComponentHitSignature` event that forwards `Hit` =
      `BreakHitResult` to the ubergraph; `Normal`, `Abs`,
      `GreaterEqual_FloatFloat`, `K2_SetTimer("BackToSkullIdle", 0.35)` and
      `LaunchCharacter` are present. **Not a reflect, though:** the normal is
      fed through `Abs()` before it is scaled by `BounceSpeed`, and the else pin
      is unwired (defects 1–2 in the block above).
- [x] `TogglePower`: flip `bPoweredOn`; `bInvulnerable=bPoweredOn`;
      `bDealContactDamage=bPoweredOn`; `RefreshStateFlipbook`. **8 Nov 2026:**
      `TogglePower` is a collapsed sub-graph whose body sits in
      `ExecuteUbergraph_BP_FloatingSkull`; `bPoweredOn` is read/written 12 times,
      `bInvulnerable` and `bDealContactDamage` 4 times each.
- [x] Override `RefreshStateFlipbook`: ON idle vs OFF idle. **8 Nov 2026:**
      traced — `Parent: RefreshStateFlipbook` → Branch(`bPoweredOn`) →
      `PlayStateFlipbook(OnIdleFlipbook, true)` / `OffIdleFlipbook`.
- [ ] **PIE gate** (nothing in §10 yet): the **Done when** list below, i.e. ON
      ignores bullets and kills on contact, OFF is harmless and shootable, a
      wall/floor hit toggles the power state, no gravity, and the pit
      `KillVolume` destroys it. Also confirm the launch direction after a bounce
      and that the sprite faces the bounce direction (`bb3627d` claims the facing
      fix).
- [ ] **Decide the `ReceiveTick` sub-graph.** The asset runs an enabled
      `ReceiveTick` (collapsed, body in the ubergraph, no `PatrolStep` /
      `ChaseStep` in it). `EnemyAI.md` §8.7 says the `LaunchCharacter` bounce and
      `Event Hit` are the Skull's *only* movement, so either the Tick is B's
      bounce maintenance and §8.7 should say so, or it is dead code and should be
      disconnected.

**Defect reported in PIE 9 Nov 2026 — "the skull teleports into the spawn point
the player is standing in, then freezes".** Not the terrain: the skull stops
being a *flyer* at runtime, so `BP_EnemyBase` runs its walker-only rescue on it.
`LaunchCharacter` ends in `UCharacterMovementComponent::Launch`, which does
`SetMovementMode(MOVE_Falling)` whenever the mode is not already `MOVE_Falling`;
the Class Defaults `MOVE_Flying` / `gravity 0` / `MaxFlySpeed 350` therefore hold
only up to `BeginPlay`, and every `Hit` reflect re-enters `Falling` the same way.
Measured live (Simulate, `Scripts/_run_sie_skull.py`, nothing saved):
`mode=MOVE_Falling isFlying=False` at every sample from `t = 1 s` to `t = 5 s`
while the skull bounces at `+-300` uu/s on each axis.

That makes both 7 Nov flyer guards dead code for this enemy (`TryRescue`,
`FindHomePlatform`), and the chain then runs like this.

1. A bounce that ends with `Velocity.Z == 0` is a *landing*: `OnLanded` ->
   `ResolveKnockback` -> `FindHomePlatform` (guard dead) answers with a real zone
   when the skull's XZ happens to sit inside one — `HomePlatform =
   BP_EnemyPlatform_Auto_04_10` was observed at `t = 4 s`.
2. When the landing is outside every zone the function returns nothing and the
   stranded chain runs (`PlayStateFlipbook(IdleFlipbook, true)` plus
   `SetTimer("TryRescue", 0.5)`), i.e. the branch documented in `EnemyAI.md`
   under the 7 Nov rescue rules.
3. `TryRescue` (guard dead) teleports to `Candidate.Location + (0, 0, 120)` with
   `bTeleport = true`, then calls `SetMovementMode(MOVE_Falling)`. `Candidate` is
   the nearest `bEnabled` platform whose pivot is at most `50` above the skull.
   The placed skull reads `RescueRadius = 2000` and all six platforms read
   `bEnabled = true` (`Scripts/_probe_level_platforms.py`); beside the spawn that
   is `BP_EnemyPlatform_Auto_01` at `(-1600, 0, 500)`, so the snap lands on
   **`(-1600, 0, 620)` — ~104 uu from `PlayerStart` `(-1500, 0, 592)`**, which is
   exactly "the spawn point the player is standing in".
   (The compiled `TryRescue` also exposes its scratch locals as UFunction
   parameters — `candidate`, `best_distance`, `temp_int_loop_counter_variable`, …
   — so the timer calls it with all-zero arguments. Harmless, but it is why the
   function reads as if it took inputs.)
4. `gravity 0` means the snapped skull has no velocity and never lands again, so
   `IsFlying()` stays false and `HomePlatform` stays invalid: every later rescue
   attempt re-teleports it to the same point. That is the "it went there and then
   does nothing". `BeginPlay -> InitEnemy -> SetTimer("TryRescue", 0.5, looping)`
   is unconditional, so that timer is the thing that keeps firing.
5. The frozen sprite is the `bLoop = false` hit book: `Event Hit` plays
   `HitWallFlipbookA/B` once and the live read is
   `FLB_Skull_HitWall02 pos=0.583 playing=False` (stopped on its last frame).
   Pinned against geometry the hit event re-fires each frame and restarts that
   one-shot, so it reads as "stuck mid-transition".

**Fix (hand work; Python cannot author K2 nodes in this build).** Test a
design-time flag, not the physics result:

- [x] `BP_EnemyBase`: add `bIsFlyer` (Boolean, `false`, instance editable).
      **9 Nov 2026:** on the CDO; `Scripts/_probe_flyer_flags.py` reads `true` for
      `BP_FloatingSkull` / `BP_Bat` / `BP_Ghost`, `false` for `BP_RockBase` /
      `BP_SpikeTurtle`.
- [x] `TryRescue`: swap its `Branch[Is Flying]` condition for
      `OR(bIsFlyer, CharacterMovement Is Flying)`; keep `true -> Return`.
- [x] `FindHomePlatform`: the same swap on its `Is Flying` guard
      (`true -> Return`).
- [x] `ResolveKnockback`: add `Branch[bIsFlyer]` between `Set UnreachableTime = 0`
      and `Find Home Platform`, `true -> Return`, `false -> Find Home Platform`.
      Do **not** fold the flag into the existing `bIs Dead` entry branch: that
      would skip `bWasKnockedBack = false` above it, and `Aggro Update` returns
      early while `bWasKnockedBack` is true. The `true` leg must skip everything
      below, because the other leg sets `bCanMove = false` and `bStranded = true`
      before `SetTimer("TryRescue")` — those two flags are what actually freeze
      the skull's AI.
- [x] `bIsFlyer = true` on `BP_FloatingSkull`, `BP_Bat` and `BP_Ghost`.
- [x] Re-point the two verifier rules in `Scripts/_verify_enemy_base.py`
      (`TryRescue` / `FindHomePlatform` "Is Flying returns before ...") at the
      new condition and keep `52 PASS | 0 FAIL`.
- [x] Re-run `Scripts/_run_sie_skull.py`: the skull must keep bouncing with
      `HomePlatform=None` and must **not** jump to `(-1600, 0, 620)`.

**Applied 9 Nov 2026 (~02:30), re-read from a fresh export — all six landed.**

- `FindHomePlatform`: `OR(bIsFlyer, Is Flying)` → `IfThenElse_3.Condition`
  (`true` → `Return`).
- `TryRescue`: the same OR feeds its guard `Branch` (`true` → `Return`).
- `ResolveKnockback`: `IfThenElse_2[Condition = bIsFlyer]` sits between
  `Set UnreachableTime = 0` and `Find Home Platform`, `true` → `Return`, `false` →
  `Find Home Platform`, so `bWasKnockedBack = false` is still reached.
- Verifier re-pointed (`is_or()` + `flyer_gate_source()`); the labels now read
  `... Is Flying/bIsFlyer ...` and the suite is **`52 PASS | 0 FAIL | 0 PENDING`**
  (it read `50 PASS | 2 FAIL` between the BP edit and the verifier edit).
- Simulate (`Scripts/_run_sie_skull.py`, nothing saved): `mode=MOVE_Falling`,
  `isFlying=False`, `HomePlatform=None`, `bStranded=False`, `bCanMove=False`, and
  the skull travels `Z 780 → 1180.7 → 1581.1` with **no** jump to
  `(-1600, 0, 620)`. PIE with a live player the same night: the snap is gone.

**Stuck-bounce fallback (9 Nov 2026 — new, hand work).** Independent of the
rescue bug: a skull wedged in a corner, a platform seam or a terrain crevice
never moves again, and its `bLoop=false` hit book freezes on its last frame. The
level-placed skull reproduces it with nobody playing — Simulate reads it at its
own spawn `(-1758.8, 13.0, 610.0)` as `vel=(0,0,-0)`,
`FLB_Skull_HitWall01 pos=0.583 playing=False`, power ON. Full recipe in
`Enemies.md` §6.7 (`Stuck-bounce fallback`); the tasks are:

- [x] `BP_FloatingSkull` variables: `LastMoveLocation` (Vector), `StuckTime`
      (Float `0`), `StuckCount` (Integer `0`), `HomeLocation` (Vector) — exported
      9 Nov 2026, `NewVariables(7)`..`(10)`.
- [x] `BeginPlay`: `Set HomeLocation = Get Actor Location`, then
      `Set LastMoveLocation = HomeLocation` (no `Facing` change needed — the base
      defaults it to `1` and `InitEnemy` calls `SetFacing(1)`). Both sit at the
      end of the chain that `InitEnemy` starts, so the EventGraph reads
      `InitEnemy -> bPoweredOn -> bInvulnerable -> bDealContactDamage ->
      PlayStateFlipbook -> LaunchCharacter -> Set HomeLocation ->
      Set LastMoveLocation`.
- [x] Append the tick watchdog after the existing `SetFacing` call: 16 nodes
      (`Branch`, `NOT Boolean`, `VSize2D`, `Vector - Vector`, `Float < Float`,
      `Float + Float`, `Float >= Float`, three `Set StuckTime`,
      two `Set LastMoveLocation`, `Set StuckCount`, three `Branch`, plus the
      `UnstuckBounce` call) — node-by-node table with exact pin names in
      `Docs/Enemies.md` section 6.7. **Wired and verified 9 Nov**
      (`14 PASS | 0 FAIL | 0 PENDING`). Graph order, walked backwards from
      `UnstuckBounce`:
      `UnstuckBounce <- Set LastMoveLocation <- Set StuckTime = 0 <- Branch
      (Condition = Float >= Float, B = 1.0) <- Set StuckTime (StuckTime +
      DeltaSeconds) <- Branch (Condition = Vector Length 2D < 20) <- Branch
      (Condition = NOT bIsDead) <- SetFacing <- ReceiveTick`; the moving leg is
      `Branch.False (True/False = the < 20 branch) -> Set LastMoveLocation ->
      Set StuckTime = 0 -> Set StuckCount = 0` and stops there. The four wires
      that had to be re-cut during wiring were the `< 20` polarity, the counting
      `Set StuckTime` -> gate link (a `Set StuckCount` wire had to be removed
      from the gate's exec input), the gate's `Condition`, and both
      `Set LastMoveLocation` value pins.
- [x] New function `UnstuckBounce` (20 nodes, same table): `StuckCount += 1`;
      `SetActorLocation(Select(Conv_BoolToInt(StuckCount >= 3), HomeLocation,
      Get Actor Location), bSweep=false, bTeleport=true)`; `Facing *= -1` (via
      `SetFacing`); `LaunchCharacter((Facing * BounceSpeed, 0, BounceSpeed),
      true, true)` (both overrides on: the escape must not inherit the downward
      velocity that pinned it); `BackToSkullIdle`. No `StuckCount` reset inside —
      the tick's moving leg owns it, otherwise `>= 3` can never fire.
- [x] PIE 9 Nov 2026: the watchdog itself is fine, but the level-placed skull
      could never move at all. `Scripts/_watch_pie_skull.py` +
      `Scripts/_sample_skull_stuck.py` read it at `(-1758.8, 13, 610)` for
      minutes as `mode=MOVE_Flying`, `vel=(0,0,0)`, location frozen to 0.1 uu
      while `StuckTime` ramped `0 -> 1` and `StuckCount` climbed `1..49` — the
      escape fired every second and produced **zero** displacement.
      Cause, measured rather than guessed: the skull **spawns inside
      `TM_Background`**, the level's `PaperTileMapActor`.
      `Scripts/_probe_level_clearance.py` reads only `90` uu of free space above
      its centre and `120` below, while its capsule is `150` up / `150` down,
      and `Scripts/_probe_hit_owner2.py` frees all four traces the moment that
      actor's collision is switched off. A capsule that starts the frame
      penetrating performs no swept move at all, so the escape queues
      `PendingLaunchVelocity`, `HandlePendingLaunch` sets `MOVE_Falling`,
      `PhysFalling` slides 0 uu, `SetPostLandedPhysics` drops it back to
      `MOVE_Flying` (its `DefaultLandMovementMode`) and `PhysFlying` brakes the
      300 uu/s away. UE 4.27 `CharacterMovementComponent.cpp` agrees line for
      line: `Launch()` only stores the pending vector, `HandlePendingLaunch()`
      applies it and switches to `MOVE_Falling`, `PhysFlying` applies fluid
      friction before `SafeMoveUpdatedComponent`. The `>= 3` reset was equally
      dead, because `HomeLocation` is that same embedded point.
- [x] Level fix (in-memory; the level is **not** saved):
      `py -3 Scripts/_run_py.py Scripts/_apply_skull_respawn_fix.py` moves the
      instance to `(-1258.8, 13, 730)` — the nearest point
      (`Scripts/_probe_skull_respawn_scan.py`) with `>= 500` uu free up and down
      and `>= 350` uu on every horizontal axis, 278 uu from `PlayerStart`.
      Re-verified in Simulate: the skull flies at `+-300 uu/s`, `StuckCount`
      stays `0`, `HomeLocation` reads the new point.
- [x] Escape chain verified against a real wedge 9 Nov 2026
      (`Scripts/_pie_skull_wedge_test.py` teleports the live skull back into the
      tile block): `StuckCount 1` while the launches are swallowed, then the
      third escape at `StuckCount 3` **resets to its own `HomeLocation`
      `(-1258.8, 13, 730)`** — never `PlayerStart` — and the skull travels again
      with `StuckCount 0` on the next sample. `BackToSkullIdle` restores
      `FLB_Skull_Idle01/02`.
- [ ] Reconcile the skull capsule: the live CDO carries `r=150 / halfZ=150`
      while `Scripts/_make_enemies.py` ships `capsule=(85.0, 168.75)`, so the
      capsule rule in `Scripts/_verify_enemies.py` no longer describes the
      asset. Whichever number wins, **neither fits the old 210 uu slot** — that
      is why the spawn moved instead of the capsule shrinking.
- [x] `py -3 Scripts/_verify_skull_fallback.py` → `14 PASS | 0 FAIL | 0 PENDING`
      (14 rules since 9 Nov; it re-exports the asset and reads `EventGraph` plus
      the T3D variable table, including branch polarity, single-exec-source and
      unlinked-pin checks that the old 8-rule version could not see).

Stop-gap only (kills the snap, not the walker logic):
`BP_FloatingSkull -> RescueRadius = 0`, because `BestDistance` then rejects
every platform.

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
**Status (5 Nov 2026):** `bAggroOnHit=true` is live and verified; the rest of C4
(health/speeds/flipbooks/`TryFire` verification) is still open.

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

### A1b — `BP_Snail` (Owner A1)

**Read:** `EnemyAI.md` §8.3; `Enemies.md` §6.3; `EnemyPlacement.md` §4.3.
**Depends:** M1 — **green 8 Nov 2026** (`EnemyWorkPlan.md` §10), so the graph
tasks below are unblocked. No detection.

**Parallel prep:** the unique variables, Class Defaults and art were prepped
before `M1 GREEN`; the graph tasks are unblocked as of 8 Nov 2026. The `A1b` card
owns `BP_Snail` the way `A1` owns `BP_EnemyBase`: base work is ticked in `A1`, and
nothing here counts as `A1` work just because one person holds both cards.

**Status (8 Nov 2026): PARTIAL — the aggro defaults are done; the seven open tasks
below are the shell graph, the remaining Class Defaults and the art.** The live
CDO still carries the base `MoveSpeed=100`, `MaxHealth=3` and `ContactDamage=1`,
the asset declares zero own variables, and the instance sits at `(-451, 9, 225)`
off every auto marker. **The aggro part is fixed (5 Nov, retuned 7 Nov):** the
Snail overrides `ChaseSpeed=250` (was `80`), `AggroHalfWidth=0`,
`AggroHalfHeight=0` and
`bAggroOnHit=true` — hit-only aggro, patrol otherwise. No proximity aggro is
wanted: a player standing in front of a snail is ignored until it is shot. The
remaining health, movement and flipbook defaults are still base values and are
tracked below. The CDO flip shipped in the same commit as the base change.

**Live probe 8 Nov 2026** (`Scripts/_run_probe_snail.py`, read-only):
`ChaseSpeed=250`, `AggroHalfWidth=0`, `AggroHalfHeight=0`, `bAggroOnHit=true`,
`ContactDamage=1`, `DeAggroTime=2`; still base `MoveSpeed=100` and `MaxHealth=3`;
`IdleFlipbook`/`HitFlipbook`/`DeathFlipbook` unset; all eight shell variables
report `MISSING` — 9 of the 22 probed properties do not exist on the class. The
asset owns no function or event graph (4 Nov export: only
`UserConstructionScript`), so `Die`, `Event Hit` and `RefreshStateFlipbook` are
all still to be added.

**Tasks**

- [ ] Add only the unique variables: `bShellPhase`, `ShellSpeed`,
      `ShellContactDamage`, `ShellLifetime`, `ShellIdleFlipbook`,
      `ShellWallHitFlipbook`, `ShellTopHitFlipbook`, `WithoutShellFlipbook`.
      Live probe 8 Nov 2026: all eight are `MISSING` on the generated class.
- [x] **DONE 5 Nov 2026, retuned 7 Nov — Class Defaults (aggro only).**
      `ChaseSpeed` `80` → `250` (§10), `AggroHalfWidth=0`, `AggroHalfHeight=0`,
      `bAggroOnHit=true` (§13, locked 4 Nov). Saved on `BP_Snail` and re-read from
      the live CDO/spawned instance. This is Snail work, so it is ticked here and
      not in the `A1` card, which owns only the `bAggroOnHit` variable and the hit
      term in `UpdateAggro`.
- [ ] Class Defaults (remaining A1b): `MaxHealth=2`, `MoveSpeed=50`, snail
      flipbooks (`IdleFlipbook=FLB_Snail_Idle`, `HitFlipbook=FLB_Snail_Hit`,
      `DeathFlipbook=FLB_Snail_Hit`). Live probe 8 Nov 2026: still `MaxHealth=3`,
      `MoveSpeed=100`, all three flipbooks unset; `ContactDamage=1` is already
      correct. Until these land the Snail is not yet the full §6.3 asset.
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

### A2a — `BP_RockBase` + `BP_Rock1/2/3` (Owner A2)

**Read:** `EnemyAI.md` §8.2; `Enemies.md` §6.2; `EnemyPlacement.md` §4.2.
**Depends:** M1.

**Status: BUILT 8 Nov 2026 (Jones); split defects 1–3 fixed and re-verified
9 Nov 2026 (static export + Simulate kill), PIE test 11 still open.**
Commits `f37473b` (*"rock tiers split on death with an 8-piece global cap"*) on
`branch/Jones`, merged into `branch/Dennis` as **`320f0de`**. The Class Defaults
and the graph were then read for real on 8 Nov 2026 with a **headless
`UE4Editor-Cmd.exe -run=pythonscript` commandlet** (`Scripts/_dump_rocks_assets.py`
for the CDOs, `Scripts/_dump_graph.py` on the `.T3D` export): `RockTier`
`1/2/3`, `MaxHealth` `3/2/1`, `MoveSpeed` `100/140/180`, `ChaseSpeed`
`120/160/200`, `AggroHalfWidth=700`/`AggroHalfHeight=500`/`DeAggroTime=2`,
`SplitOffset=30`, `SplitImpulse=250`, `MaxPieces=8`, `bCanSplit`
`true/true/false`, `ChildRockClass` `BP_Rock2_C`/`BP_Rock3_C`/`None`,
`IdleFlipbook`/`RunFlipbook`/`HitFlipbook` = `FLB_Rock<n>_Idle/_Run/_Hit`
(`Hit` is also `DeathFlipbook`), `bAggroOnHit=true` — every number in the card
below matches.

The tier chain is wired child-to-child: `BP_Rock1` (38×34, tag
`Enemy.Rock.Tier1`, child `BP_Rock2_C`) → `BP_Rock2` (32×28, `Tier2`, child
`BP_Rock3_C`) → `BP_Rock3` (22×18, `Tier3`, no child). The three children are
**bare**: only `UserConstructionScript` + three `Disabled` template events, no
graphs of their own — all logic is in `BP_RockBase`.

`Die` override (13 of 42 nodes are the split; the live body is the graph named
`Die`, **not** the base `AnyDamage`): `GetAllActorsOfClass(BP_RockBase_C)` →
`Array_Length <= MaxPieces - 1` **and** `bCanSplit` **and**
`IsValidClass(ChildRockClass)` → spawn piece A at `Loc + (+SplitOffset,0,0)`,
cast to `Character`, `LaunchCharacter((+SplitImpulse, 0, SplitImpulse*0.5))` →
spawn piece B at `Loc + (-SplitOffset,0,0)` (both offset and impulse negated),
cast, `LaunchCharacter((-SplitImpulse, 0, SplitImpulse*0.5))` → `Parent: Die`;
the
else branch goes straight to `Parent: Die`. Both spawns use
`SpawnActorFromClass` with `CollisionHandlingOverride=AdjustIfPossibleButAlwaysSpawn`.
**Correction to the earlier static read:** `BeginDeferredActorSpawnFromClass` /
`FinishSpawningActor` exist only in the orphaned `EdGraph_2` leftover (50
nodes, not referenced by `FunctionGraphs`), i.e. an earlier iteration of the
same code — the compiled path does not use them. Pin-level check: piece A takes
`VariableGet_9 = SplitOffset` for its offset and `VariableGet_10 = SplitImpulse`
for its launch, piece B negates both — so the impulses are **outward and
correct**, the split does not fire the pieces into each other.

**Geometry note (8 Nov, second pass).** `SplitOffset=30` while the tier sprites
are `38×34` / `32×28` / `22×18`, so unless the capsule is far smaller than the
sprite, the tier‑1 and tier‑2 siblings are **overlapping at spawn** (≈8 cm and
≈2 cm) and only tier‑3 pieces (`22` wide, `30` apart) come out clear. That
overlap is what `AdjustIfPossibleButAlwaysSpawn` was silently resolving by
nudging a piece to the nearest free spot, and it is also the first frame of the
sibling shoving — so fix-plan step 3 is not optional polish. Raising
`SplitOffset` would be a card change (the card says `30`), not a fix.

**Defects from the 8 Nov 21:29 PIE recording of `L_Level_Testing` — all three
fixed and re-verified 9 Nov 2026 (see the 9 Nov block below).**
The one placed rock (`BP_Rock1` at `(600, 0, 106.2)`, actor rotation all zero —
so this is *not* a placement problem) was split in PIE and three things broke:

1. **Split pieces spawn rotated.** Both `MakeTransform` nodes feed
   `Rotation = Conv_VectorToRotator(GetActorLocation())` — the rock's *world
   position vector* becomes its rotator, so a piece inherits
   `Pitch = atan2(Z, X)` (≈10° for the level's own rock) and `Yaw = 180` for
   any `X < 0`. Fix: use `GetActorRotation()` (pitch/roll zeroed) in both
   `MakeTransform` nodes.
2. **Pieces shove each other.** Not the impulses (they are outward, see above):
   both pieces are Pawn-blocking `Character` capsules that aggro the same player
   and converge on the same `X`, and nothing makes rock-versus-rock ignore, so
   `AddMovementInput` drives them into each other every frame. The spawn also
   still uses `AdjustIfPossibleButAlwaysSpawn`, so a piece whose capsule clips
   the dying parent (or the tilted capsule from defect 1) gets displaced out of
   its intended offset. Fix: spawn with `AlwaysSpawn`, and make the pieces
   ignore each other (`IgnoreActorWhenMoving` between the pair, or a
   `BP_RockBase`-wide ignore loop in `BeginPlay`).
3. **`RefreshStateFlipbook` never runs while the rock walks.** The rock's own
   override is correct (`Parent:` → Branch `|Velocity.X| > 10` → `Run` else
   `Idle`), but `BP_EnemyBase.UpdateAggro` only reaches
   `RefreshStateFlipbook` on the *give-up* branch, and `ChaseStep` /
   `PatrolStep` return through their own `FunctionResult` **without**
   refreshing. Result: the pieces keep `Idle` while they
   chase, and pick up `Run` at the moment the chase is abandoned — the exact
   inversion heard in the recording. Fix belongs in the base, and the four
   insertion points are `ChaseStep` (after `AddMovementInput` and after
   `StopMovementImmediately`) and `PatrolStep` (after `AddMovementInput` and
   after the final `SetFacing`) — every exit of `UpdateAggro` then passes one
   refresh. `PlayStateFlipbook` already no-ops when the flipbook is unchanged.

**Still unverified:** the whole PIE list below (test 11).

**Fix plan (apply in this order, compile + PIE-check after each step).**

| # | Asset | Change | Kills defect |
| - | ----- | ------ | ------------ |
| 1 | `BP_RockBase.Die` | both `MakeTransform.Rotation` ← new `Get Actor Rotation` (pitch/roll zeroed) instead of `Conv_VectorToRotator(GetActorLocation())`; delete the two converters | A2a 1 |
| 2 | `BP_RockBase.Die` | both `SpawnActorFromClass` → `CollisionHandlingOverride = AlwaysSpawn` | A2a 2 (displacement) |
| 3 | `BP_RockBase` | pieces ignore each other: `IgnoreActorWhenMoving(pieceA, pieceB)` / `(pieceB, pieceA)` right after the two casts (or a `BP_RockBase`-wide ignore loop in `BeginPlay` for the 4× Rock3 case) | A2a 2 (shoving) |
| 4 | `BP_EnemyBase` `ChaseStep` + `PatrolStep` | 4 × `RefreshStateFlipbook` insertions (see the insertion points in defect 3) | A2a 3 (and every walker) |
| 5 | `BP_EnemyBase.SetFacing` | verify the else branch: the T3D carries `NewRotation` default `Pitch 180` while its split pins read `Roll/Pitch/Yaw 0,0,0`, so one of the two is stale. Target per `Docs/Enemies.md`: `Direction >= 0` → `Sprite0` relative **Yaw 180**; else → **Yaw 0 / Pitch 0 / Roll 0**. If the details panel really shows `Pitch 180`, every left-facing walker is upside-down | face/orientation on all walkers |
| 6 | `BP_FloatingSkull.ReceiveTick` | `SetFacing` ← `BreakVector(Normal(GetVelocity())).X` (no `NegateFloat`), gated by `Abs(Vx) > 10` | A2e 1 |
| 7 | `BP_FloatingSkull` hit event | gate on `OtherActor` not being a `Pawn`; `Select` index ← `bUseWallAlternate` and flip it after `PlayStateFlipbook`; add the `HitCooldown` guard; wire the else pin to `LaunchCharacter(Normal * BounceSpeed, XY, Z)` | A2e 2–5 |

Steps 1–3 are the rock batch and need only `L_Level_Testing`; step 4 and 5 touch
the shared base, so they need a walker run in `L_Level_01` (tests 1–7) as well as
test 11.

**Status 8 Nov 2026 (after the PIE recording):** steps **1–3 applied and step 3
verified** — the reroute node was deleted, the live export is 14 nodes and
`Scripts/_check_step3_live.py` prints `7 PASS / 0 FAIL`, and the `L_Level_01` PIE
run after the delete logs no runaway loop (owner-confirmed). **Step 4 applied**
(18 / 30 nodes, `Scripts/_check_step4_live.py --self-test` = `10 PASS / 0 FAIL`)
and it immediately exposed **step 4b**: the four per-frame refreshes call
`RefreshStateFlipbook`, whose child overrides each begin with
`Parent: Refresh State Flipbook`, so every frame runs `SetFlipbook(Idle)` ->
`SetFlipbook(Run)` and `SetFlipbook` resets `AccumulatedTime` — every enemy
stopped animating and slid across the floor ("stands still and glides"). Fix: drop
the `Parent: Refresh State Flipbook` node from `BP_RockBase`,
`BP_SpikeTurtle` and `BP_FloatingSkull` (see `A1`, step 4b; `BP_Ghost` needs its
branch finished first, `BP_Bat` is clean), gate
`py -3 Scripts/_check_refresh_reset.py --self-test`. **Steps 5–7 not applied**;
they are the last of the list.

**9 Nov 2026 re-read + live re-test (defects 1–3 closed, step 5 closed, test 11
open).** A fresh `Scripts/_export_rock_check.py` export of the live graph
(`Scripts/_rock_after_step3.txt`) shows both `MakeTransform.Rotation` pins as a
literal `0,0,0` (the two `Conv_VectorToRotator` nodes are gone), both
`SpawnActorFromClass` nodes at `CollisionHandlingOverride = AlwaysSpawn`, and
both `IgnoreActorWhenMoving` calls present — steps 1–3 really are in the asset.
Gates: `_check_step3_live.py` `7 PASS / 0 FAIL`, `_check_step4_live.py`
`10 PASS / 0 FAIL`, `_check_idle_gap.py` `2 PASS / 0 FAIL` (step 4c), and
`_check_refresh_reset.py` no longer fails on `BP_RockBase` (step 4b; only
`BP_Ghost` remains).

The split was then triggered for real without PIE, in Simulate
(`Scripts/_run_sie_rock_split.py` → `_sie_rock_damage.py` +
`_sie_rock_sample.py`): `ApplyDamage(99)` on the placed `BP_Rock1`
(`MaxHealth 3`) spawned **two `BP_Rock2_C`** pieces, both with
`actorRot = (0,0,0)`, both at `Y = 10` (the parent's plane) and both at the same
`Z = 89.6` — defect 1 is gone, and the pieces inherit the parent's plane.
Sibling collision is off in the graph (`IgnoreActorWhenMoving` both ways) and
the separation seen in the samples matches the outward `SplitImpulse`, not a
shove.

**Step 5 is closed: no bug.** The left-facing `SetRelativeRotation` carries a
stale *summary* string (`DefaultValue="0,180.000000, 0"`) while its split pins
are all `0.0`; the right-facing node reads `"180.000000, 0, 0"` with
`NewRotation_Yaw = 180`. Live samples settle which one compiles — `Facing = 1`
→ sprite `(r0, p0, y-180)`, `Facing = -1` → sprite `(r0, p0, y0)`, i.e. right =
**Yaw 180**, left = **Yaw 0 / Pitch 0 / Roll 0**, exactly `Enemies.md`
§`SetFacing`. No walker is upside down; do not "fix" the struct text — UE writes
it as a summary and the split pins win. Evidence:
`Scripts/_run_sie_facing.py`, `_sie_rock_force_left.py`,
`_run_sie_left_branch.py` (the placed rock's `PatrolMinX/-MaxX` are `-799 /
1810`, so the left branch was reached by teleporting it past `PatrolMaxX`;
`PatrolMaxX` is not editable on an instance).

**Still open on this card:** PIE test 11 with a live player — the chase sheet
(`FLB_Rock<n>_Run` while it moves) and the split under the player's feet. Steps
6–7 (skull) are untouched.

**8 Nov 2026, step-3 corrections (two, and the second one is why PIE hung).**
First: the earlier wire list named `CharacterMovement.Ignore Actor When Moving`,
which does not exist in UE 4.27 — `IgnoreActorWhenMoving` is a
`UPrimitiveComponent` function, i.e. it is called on the **Capsule Component**.
That is why the node could not be found/connected and why `For Each Loop.Array
Element` had nowhere sensible to go. Second: the first generated paste wired the
loop body **back into `For Each Loop`'s `Exec` pin** (three wires:
`Ignore.then`, `Branch.else`, `Cast.CastFailed`). A ForEach macro advances by
itself as soon as a body chain simply *ends*; re-entering `Exec` restarts the
macro from index 0, so the first element was processed for ever. The engine log
proves it (`Saved/Logs/DontTrustTheLevels.log`):

    LogScript: Warning: Runaway loop detected (over 1,000,000 iterations)
    	BP_Rock1_C .../UEDPIE_0_L_Level_01.L_Level_01:PersistentLevel.BP_Rock1_2
    	Function .../BP_RockBase.BP_RockBase_C:ExecuteUbergraph_BP_RockBase:0047
    PIE: Error: Infinite loop detected. Blueprint: BP_RockBase
    	Function: Get All Actors Of Class

**Rule for every loop in this plan: never wire a ForEach body back into `Exec`.**
Body chains just stop — `then`, `CastFailed` and `else` may all be left open; the
macro steps to the next element on its own and `Completed` fires when the array
runs out. (The project's own working loops, e.g. `BP_EnemyBase.TryRescue`, have
exactly one wire into `Exec`.) `Scripts/_gen_step3.js` now rejects any graph
whose exec path forms a cycle at all, so this cannot come back unnoticed.

**8 Nov 2026, step-3 second pass: the loopback survived as a reroute node.**
After the four edits, PIE was replayed and hung again — no longer at level start
but *when the first rock died*:

    LogScript: Warning: Runaway loop detected (over 1,000,000 iterations)
    	BP_Rock2_C ...PersistentLevel.BP_Rock2_C_0
    	Function ...BP_RockBase.BP_RockBase_C:ExecuteUbergraph_BP_RockBase:0198
    PIE: Error: Infinite loop detected. Blueprint: BP_RockBase Function: Branch
    	BP_Rock2_C ...PersistentLevel.BP_Rock2_C_1
    PIE: Error: Infinite loop detected. Blueprint: BP_RockBase Function: Outputs

Why it only bites *after* the kill: edits 2–3 left `Branch.else` and `CastFailed`
open, so a rock that sees **no brother** ends the body at `else` and the macro
advances on its own — with one rock in the level, `BeginPlay` looked healthy for
13 s. As soon as `Die` spawns the two `BP_Rock2` pieces, each piece's `BeginPlay`
sees two elements: element 0 is not itself → `then` → the two ignore calls →
**back into `Exec`** → index 0 again, for ever. Two instances, two runaway loops
0.7 s apart: exactly the two log lines above.

Where the wire hid (`Scripts/_export_rock_check.py` →
`Scripts/_rock_after_step3.txt`): edit 1 did not cut, it **spliced**. Dropping a
wire end onto an existing wire makes UE insert a **reroute node**
(`K2Node_Knot`), it does not break the old link, so `For Each Loop.Exec` ended up
with two inputs — `Get All Actors Of Class.then` *and* `K2Node_Knot_7`, whose
input is the right-hand `Ignore Actor When Moving.then`. Pin-level reasoning does
not call that a cycle; the knot is a plain pass-through.

Fix — one action, no re-paste: select the **reroute node** between the right-hand
`Ignore Actor When Moving` and `For Each Loop` and press `Delete`. Deleting a
reroute removes both of its segments, which leaves `Exec` with the single
`Get All Actors Of Class.then` input. Equivalent alternative: `Alt+click` on
`For Each Loop.Exec` (breaks *every* link into it) and drag
`Get All Actors Of Class.then` → `Exec` again.

Verify before PIE:

    py -3 Scripts/_export_rock_check.py      # live T3D -> Scripts/_rock_after_step3.txt
    py -3 Scripts/_check_step3_live.py       # needs 7 PASS / 0 FAIL
    py -3 Scripts/_selftest_step3_live.py    # checker sanity, must end "selftest OK"

`Scripts/_check_step3_live.py` reads that export and enforces: exactly one input
into `For Each Loop.Exec`; **no exec cycle anywhere** (node level — a macro's
`Exec -> LoopBody` edge is implicit, which is why this defect slipped through
twice); `else`/`CastFailed` end the body; `Actor` = `Self` on the left call and
`Array Element` on the right, each with the *opposite* capsule in `self`; and
**no reroute nodes left** in the graph. On the asset as it stands it prints:

    [FAIL] 1  For Each Loop.Exec has 2 inputs: ...GetAllActorsOfClass, ...K2Node_Knot_7
    [FAIL] 2  exec cycle: MacroInstance_0 -> IfThenElse_0 -> DynamicCast_0 ->
              CallFunction_2 -> CallFunction_3 -> Knot_7 -> MacroInstance_0
    [FAIL] 5  reroute node K2Node_Knot_7 still in the graph (...) - delete it

and after the delete it prints `7 PASS / 0 FAIL`. `Scripts/_selftest_step3_live.py`
proves the checker is not a rubber stamp: it strips the reroute from a copy of
the same export (what the delete does) and requires `0 FAIL` on that copy. Those
commands are the gate before PIE — but note that a **stale** export passes just
as happily as a fixed graph, so re-export after every edit.

**Practical rule: after any wire drag in this graph, re-export and run the
checker — a spliced wire looks connected and is not.**

**How to implement step 3 (node level).** `Docs/step3_rock_ignore.txt` is the
corrected clipboard graph: 11 nodes, **16** wires, every input already fed. A
fresh install: paste it into `BP_RockBase`'s `EventGraph`, then drag the one
missing wire, the (still disabled) `ReceiveBeginPlay` stub's `then` →
`Parent: ReceiveBeginPlay.execute`; that drag also enables the stub. `Ctrl+Z`
undoes a paste in one go.

**If the old 19-wire paste is already in the graph, repair it in place** — four
edits, no node moves, no re-paste:

1. **Cut** the wire from the **right-hand** `Ignore Actor When Moving.then` →
   `For Each Loop.Exec` (the left one's `then` feeds the right one's `execute`
   and must stay). Do **not** drag that wire's end onto the existing
   `Get All Actors Of Class.then → Exec` wire: UE *splices* it into a reroute
   node and the loopback survives while looking connected (this is exactly what
   happened on 8 Nov). Delete the wire, or delete the reroute node afterwards.
2. **Cut** `Branch.else` → `For Each Loop.Exec`.
3. **Cut** `Cast To BP_RockBase.CastFailed` → `For Each Loop.Exec`.
4. Drag `Self` → the **left** `Ignore Actor When Moving`'s `Actor` pin (replaces
   `Array Element`), and drag `For Each Loop.Array Element` → the **right**
   `Ignore Actor When Moving`'s `Actor` pin (replaces `Self`). The old pins made
   each capsule ignore *its own* actor, i.e. a no-op, so the graph did nothing
   useful even before it hung.

After that the graph must read exactly like the file; compile + save, then PIE.

Flow: `ReceiveBeginPlay.then` → **`Parent: ReceiveBeginPlay`** → `Get All Actors
Of Class (BP Rock Base)` → `For Each Loop` → `Branch (Array Element != Self)` →
`Cast To BP_RockBase (Array Element)` → **`Get Capsule Component(other)`.
`Ignore Actor When Moving (Actor = Self, true)`** and **`Get Capsule
Component(self).Ignore Actor When Moving (Actor = Array Element, true)`**;
`i2.then`, `Branch.else` and `Cast.CastFailed` **end the body** — nothing goes
back into `For Each Loop.Exec`.

**The call lives on the capsule, not on the movement component.** In 4.27
`IgnoreActorWhenMoving(AActor*, bool)` is declared on `UPrimitiveComponent`
(`Engine/Source/Runtime/Engine/Classes/Components/PrimitiveComponent.h:763`), so
the node is `Capsule Component → Ignore Actor When Moving`; there is no
`CharacterMovement.Ignore Actor When Moving` and that is why the original wire
list could not be built. Each of the two calls therefore takes its own
`Capsule Component` getter into `self` (`self` has no usable default — left empty
the compiler says *This function requires a target*), and `Actor` is `Self` on
the first call (the brother ignores me), `Array Element` on the second (I ignore
the brother). Both directions are
mandatory: the ignore list is `MoveIgnoreActors` on one component, so a one-way
registration leaves the other rock still sweeping against it — the engine's own
comment on that array says *"Components on the other Actor may also need to be
told to do the same when they move."*

Other traps the paste already handles: `Array Element` is an untyped wildcard
until `Out Actors` is in `For Each Loop.Array` (the pasted text carries the type,
so do not re-create the loop by hand), and `Cast.Object` ← `Array Element`.
`CastFailed` is left **unconnected on purpose** — the cast can only fail for a
non-rock actor, and that path simply ends the iteration.

`Parent: ReceiveBeginPlay` must stay first, otherwise `InitEnemy`/`TryRescue`
never run for any rock (the base's `BeginPlay` is `InitEnemy` plus a looping
`SetTimer(TryRescue, 0.5)`). The later sibling registers both directions with its
already-spawned brother, so the 4× `Rock3` crowd from two different `Rock2`
parents ends up mutually ignored.
**Do not** "fix" this by setting the capsule's `Pawn` response to `Ignore`: that
also lets the player walk through the rock and kills the `ContactBox` push-out.
Related nit in `Die`: `CastFailed` is unwired on both `Cast To Character` nodes,
so a failed cast dead-ends the chain and the parent is never `Die`d.

> The wired graph is `Docs/step3_rock_ignore.txt` (16 wires; it *is* the graph)
> and the picture of the same 11 nodes is `Docs/rock_graph.html`. Both are
> regenerated from `Scripts/_gen_step3.js`, which refuses any exec cycle.
> `Scripts/_check_step3_live.py` checks the **live** asset against the same rules
> (one input into `Exec`, no exec cycle, `else`/`CastFailed` open, both `Actor`
> pins, no reroute); it must print `7 PASS / 0 FAIL` before any PIE run.


**Tasks**

- [x] `BP_RockBase`: add `RockTier`, `ChildRockClass`, `bCanSplit`,
      `SplitImpulse`, `SplitOffset`, `MaxPieces`. **8 Nov 2026:** all six read
      back off the CDO.
- [x] Child Class Defaults: health `3/2/1`, `MoveSpeed` `100/140/180`, tier
      `1/2/3`, `ChildRockClass` `Rock2/Rock3/None`, `bCanSplit` `true/true/false`,
      rock flipbooks, positive `ChaseSpeed` per tier (start `120/160/200`).
      **8 Nov 2026:** exactly those values; aggro box `700×500`,
      `DeAggroTime=2`.
- [x] Use base `PatrolStep` / `ChaseStep` / `UpdateAggro`; no child movement
      Tick. **8 Nov 2026:** the children carry no graphs at all.
- [ ] `Die` override: if `bCanSplit` and `ChildRockClass` is valid and the live
      `BP_RockBase` count is `<= MaxPieces - 1`, spawn two children at
      `±SplitOffset`, launch them with `SplitImpulse`; then `Parent: Die`.
      **Wired as specified 8 Nov 2026, but defects 1–2 above (rotation,
      sibling collision) must be fixed before the box can be ticked.**
- [ ] Split pieces rely on `Landed` / `ResolveKnockback` to adopt the landing
      platform; do not copy the parent's `HomePlatform`. **Still PIE-only:**
      the pieces inherit the base's `BeginPlay` `TryRescue` path, which is what
      should place them.
- [x] Override `RefreshStateFlipbook`: run when `Abs(Velocity.X) > 10`, else idle.
      **8 Nov 2026:** the branch is exactly that — but defect 3 means the base
      never calls it while the rock walks.

**Done when:** test 11 passes; kill tier 1 → 2× tier 2; kill tier 2 → 4× tier 3;
tier 3 does not split; live count stays ≤ 8; pieces adopt their landing platform.
**8 Nov 2026:** split + launch + cap verified statically; the pieces come out
rotated and shoving each other, so test 11 fails on presentation.

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
Replace `<SLOT>` with `A1`, `A2` or `C` and `<ASSET>` with the first asset.
There is **no `B` slot any more**: B's assets are A2's.

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
the status-log lines the plan allows. Do not edit a shared base or another
owner's asset, or a level map unless the plan explicitly lists it for your slot.
BP_EnemyBase, BP_EnemyPlatform and BP_Snail are A1-only; BP_RockBase, the Rock
children, BP_SpikeTurtle, BP_Ghost, BP_Bat, BP_FloatingSkull and both level maps
are A2-only; BP_ShooterEnemyBase, BP_EnemyProjectile* and BP_ToxicPuddle are
C-only.

Hard rules:
- Lock the asset with Git LFS / UE Source Control before editing. Never co-edit.
- This build cannot create K2 nodes from Python. Do not attempt graph authoring
  with Python. Build nodes, wires, variables and functions manually in the editor.
- One movement authority per asset. Walkers use the base Event Tick; stationary/
  flyers set bCanMove=false and use their own Tick/Launch. ChaseSpeed=0 for
  Turtle/Ghost/Skull; Bat keeps ChaseSpeed=1000 for MaxFlySpeed.
- Do not add a variable that already exists in a parent. Use inherited
  bAggro, AggroRadius, ChaseSpeed, MoveSpeed, KnockbackForce, Facing and the
  base health/contact/flipbook variables. Do not add MaxWalkSpeed.
- Do not add KnowbackForce. Keep KnockbackForce.
- Contact damage goes through ContactBox, not the capsule.
- Compile and save after every function or graph. Never leave a red error.
- Run `py -3 Scripts\_verify_enemy_base.py` after any base-adjacent change;
  the accepted result is 52 PASS / 0 FAIL.
- A1/A2 may prepare unique child variables/defaults, art and static
  map/platform placement, but may not wire walker graphs or run walker PIE
  before A1 posts M1 GREEN.
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

Owner A1 should also add: `M1 is the gate; post M1 GREEN with verifier output
before wiring Snail. Prepare Snail defaults now, but do not run walker PIE until
M1 GREEN.` Owner A2 should add: `Prepare Rock and Skull defaults and map
placement now; do not wire Rock graphs or run Rock PIE until A1 posts M1 GREEN.
You also own the three finished specials (SpikeTurtle, Ghost, Bat): regression
only, never rebuild them. The first open item is deleting the Ghost's TEMP-M1
bAggro/AggroRadius/ChaseSpeed locals so it inherits them from the base.`
Owner C should add: `Support first; Wood Log patrol/aggro waits for M1; Rhino
before Slime.`

---

## 9. Definition of done (per asset)

An asset is **DONE** only when all are true:

- [ ] Compile is clean and the asset is saved.
- [ ] Every variable in the card exists once, with the exact name, type and
      default; inherited names are not duplicated.
- [ ] Every function/event in the card is wired; no orphan or disabled node that
      the card requires.
- [ ] `BP_EnemyBase` still reports **52 PASS / 0 FAIL / 0 PENDING** with no new
      FAIL (7 Nov 2026: the two `Is Flying` guards of `EnemyAI.md` §7.2 items 4
      and 6 are in and PASS. The `InitEnemy` / `AnyDamage` / `Die` FAILs quoted
      here until 7 Nov 2026 were a bug in the checker, not in the asset:
      `exec_edges()` looked collapsed graphs up by their raw name while
      `parse_nodes()` keys them space-stripped, so every `K2Node_Composite` body
      was invisible — and those three chains keep `Set CurrentHealth`,
      `PlayStateFlipbook` and `SetLifeSpan` inside collapsed nodes. A third
      instance of the same trap hid `FindHomePlatform` itself: `verify()` tested
      the T3D display name `"Find Home Platform"` against the space-free
      `"FindHomePlatform"`, so a guard that had just been built still read as
      PENDING. Both are fixed in `Scripts/_verify_enemy_base.py`; the audit tool
      `Scripts/_audit_enemy_base.py` now expands the same bodies).
- [ ] The card's PIE acceptance test passes; record what you actually observed.
- [ ] No regression in an already-done enemy (contact, health, death, split).
- [ ] The asset is committed and pushed, and the LFS lock is released.
- [ ] The status log has the asset line and any doc deviation.
- [ ] Any changed contract was updated in `EnemyAI.md` / `Enemies.md` by A1 in
      the same commit.

A graph that compiles but has no PIE evidence is **not done**.

---

## 10. Status log

Append one line per asset; do not rewrite another owner's line. Keep the table
sorted by date. Use `PASS`, `FAIL`, `BLOCKED` or `DONE` explicitly.

| Date | Owner | Asset | State | Verifier | PIE test | Commit / note |
|---|---|---|---|---|---|---|
| 24 Oct 2026 | A | plan created | DONE | — | — | `Docs/EnemyWorkPlan.md` |
| 24 Oct 2026 | A | `BP_EnemyPlatform` | PASS | `_verify_enemies.py` 201 PASS / 0 FAIL / 0 WARN | — | `bEnabled=true`, Zone NoCollision/hidden; commit pending |
| 25 Oct 2026 | B | M0 done | DONE | — | — | read-in complete (WorkPlan §3-6, EnemyAI §1-2/§4/§8/§10-11, Enemies §3-4/§6/§7.3, LfsLocking, EnemyPlacement §4.1/4.4/4.7/4.8); merged origin/branch/Dennis into branch/Jones; first asset BP_SpikeTurtle |
| 25 Oct 2026 | B | BP_SpikeTurtle | DONE | n/a | test 10: spike cycle/timers/idle PASS (PrintString evidence); contact kill PASS after Dennis's 744f845 ContactBox fix (fresh side-touch kills in spikes-out window) | ea78feb + merge 0b232e9; B's diagnostic child box deleted; remaining gap (kill-on-already-overlap during phase change) reported to A as base-contract proposal |
| 26 Oct 2026 | A | `BP_EnemyBase` | IN PROGRESS | contact `4 PASS`; kill guard `1 PASS`; base `44 PASS` | drop/contact kills once, one reload | 6/13 AI functions; next aggro set |
| 26 Oct 2026 | B | BP_Ghost | DONE | n/a | tests 12-13 PASS: hidden start (no collision/contact/chase), 550-sphere trigger, through-wall chase (WorldStatic=Ignore), visible/hidden loop forever, 2 hits kill, contact kill while visible, no de-aggro | Ghost art faces left natively: SetFacing input negated in chase; TEMP-M1 locals (bAggro/AggroRadius/ChaseSpeed) declared in child because base M1 has not added them yet - migrate to inherited when A posts M1 GREEN; first-appear GoIdle refresh added (RefreshStateFlipbook 0.5 s after StartAggro) |
| 27 Oct 2026 | A1/A2 | Owner A split | DONE | — | — | A1: `BP_EnemyBase`, `BP_EnemyPlatform`, `BP_Snail`, contract docs; A2: Rocks, `L_Level_01`; §4.2 boundary; walker graphs/PIE wait for M1 |
| 27 Oct 2026 | B | BP_Bat | DONE | n/a | test 14 PASS: hang (CeilingIn -> Hanging loop, no drift), 600-sphere trigger, contact ON during 0.5 s wind-up, direct chase colliding with walls/floors (no WorldStatic=Ignore), 2 hits kill, no de-aggro | DEVIATION: TriggerRadius=600 (card says 300) - deliberate playtest tuning, needs A1's blessing + doc sync; Ghost/Turtle editor resaves ride along (Ghost = byte-noise from f8e6cef adoption; Turtle = capsule Pawn=Block + ToggleIdle removed, both pending A1 ruling) |
| 4 Nov 2026 | A/B | BP_Bat hit retune | DONE | live CDO `KnockbackForce=0`, `TriggerRadius=800`; `RefreshStateFlipbook` 8 nodes | hit no longer slides the Bat along the ceiling or pushes it out of its trigger; it can now enter `CeilingOut` and chase | `BP_Bat.uasset`; docs synced to 800 |
| 4 Nov 2026 | A/B | BP_Bat chase follow-up | DONE | live CDO `KnockbackForce=0`, `TriggerRadius=1000`, `MaxAcceleration=8192`; `ChaseSpeed=1000` | widened the distance trigger so the approach from the playable floor is covered, and made acceleration immediate after the zero-vector hit; damage still does not set `bTriggered`, so a shot from outside `1000` remains idle | `BP_Bat.uasset`; docs synced to 1000/8192 |
| 4 Nov 2026 | A1 | Owner split re-issued | DONE | `_check_enemy_ai_vars.py` **24 PASS / 0 FAIL**; 21 function graphs; 13/13 AI functions | — | `Docs/EnemyWorkPlan.md`; **Owner B retired** — slots are A1/A2/C, B's assets (`BP_SpikeTurtle`, `BP_Ghost`, `BP_Bat`, `BP_FloatingSkull`), `L_Level_Testing` and milestone M2 moved to A2; §0/§3/§4/§4.1/§4.2/§5/§6/§7/§8 updated; A1's next task is the aggro-on-hit base change (`bAggroOnHit`; `HitAggroDuration` was dropped on 4 Nov in favour of reusing `DeAggroTime`) |
| 4 Nov 2026 | A2 | M2 handover | DONE | export + live CDO: zero own variables on `BP_Rock1/2/3`, `BP_Snail`, `BP_WoodLog`, `BP_Rhino`, `BP_ToxicSlime`, `BP_FloatingSkull` | — | A2 inherits three DONE specials (tests 10/12/13/14); open = build `BP_FloatingSkull`, delete the Ghost's TEMP-M1 locals so it inherits `bAggro`/`AggroRadius`/`ChaseSpeed`, and get A1's ruling on the Turtle capsule `Pawn=Block` + removed `ToggleIdle` |
| 5 Nov 2026 | A1 | `BP_EnemyBase` aggro-on-hit | DONE | `UpdateAggro` 54 nodes (46 + 8); fresh export + verifier: 45 PASS / 0 FAIL / 0 PENDING; `_check_enemy_ai_vars.py` 25 PASS / 0 FAIL; `BP_Snail` CDO `ChaseSpeed=80`, `AggroHalfWidth=0`, `AggroHalfHeight=0`, `bAggroOnHit=true` saved and re-read | — | design page `Scripts/_aggro_full_graph.html`; 1 variable (`bAggroOnHit`, `DeAggroTime` reused) + 8 nodes, no new function/local; `_verify_enemy_base.py` now asserts the 3 new links and the 3 old links; Snail health/movement/flipbooks remain open; PIE 1–9 still not logged |
| 5 Nov 2026 | A1/A2 | Gun-aggro consistency | PARTIAL | live CDOs: `BP_Rock1/2/3` and `BP_WoodLog` now `bAggroOnHit=true`; `BP_Snail` already true. Saved and read back; dirty content empty | — | walkers use the base cross-platform hit term and `ChaseStep` walks to the ledge (closest safe X). `BP_Bat` is the one flying gun-aggroable enemy; its 13-node `RefreshStateFlipbook` hit branch is staged in `Scripts/_bp_bat_refresh_modified.txt` but the Function Entry → branch wire is still open, so a hit from outside `TriggerRadius=1000` still hangs. `Rhino`/`Ghost`/`SpikeTurtle`/`FloatingSkull` are not gun-aggroable; `ToxicSlime` cannot be aggroed at all | `BP_Rock1/2/3.uasset`, `BP_WoodLog.uasset`, `Enemies.md`, `EnemyAI.md` |
| 5 Nov 2026 | A2 | `BP_Bat` three-bug follow-up | DONE | issues 1–3 verified in PIE; live `RefreshStateFlipbook` has the 13-node hit branch + `MaxFlySpeed=ChaseSpeed`; EventGraph `HangIdle` gated on `bTriggered` | — | live CDO `TriggerRadius=1000`, `ChaseSpeed=1000`, `MaxFlySpeed=400`, `MaxAcceleration=8192`; staged 17-node patch remains available for a clean re-paste | `Enemies.md` §6.8, `EnemyAI.md` §8.8 |
| 7 Nov 2026 | A2 | `BP_Bat` Level 1 instance | DONE | headless export + CDO readback: hit branch, `HangIdle` gate and `MaxFlySpeed` write all intact (17-node `RefreshStateFlipbook`); `L_Level_01` instance was at `Y=-100` vs terrain `Y=0` (`TM_Background`, 200 uu BlockAll slab; `ortho_width=3000`) | — | the Y offset put the sprite behind the terrain plane (invisible under tiles) and the capsule ~70 uu inside the collision slab (slow / ejected behind walls); moved the instance to `Y=0` | `L_Level_01.umap`, `Enemies.md` §6.8, `EnemyPlacement.md` §2 |
| 7 Nov 2026 | A2 | `BP_Bat` slow after a hit (2nd pass) | DONE (A1 row below) | live T3D export: `BP_EnemyBase.K2Node_CallFunction_28.bZOverride = false`; `BP_Bat` has no `SetMovementMode`; `Scripts/_check_bat_hit_knockback.py` → FAIL. Live CDOs: `BP_Bat` is the only `KnockbackForce=0` (`MoveSpeed=100`, `MaxWalkSpeed=0`, `MaxFlySpeed=400`) | — | `bZOverride=false` makes the launch inherit the Bat's own Z velocity, so `HandlePendingLaunch()` forces `MOVE_Falling`; the cap becomes `MaxWalkSpeed = MoveSpeed = 100` and only `AirControl` (0.05) X/Y input applies, so `MaxFlySpeed=1000` never matters → the Bat crawls until it lands. Fix = base `bZOverride=true` (root cause; grounded walkers unchanged) or the pre-wired Bat Tick guard `Scripts/_bp_bat_flying_guard_paste.txt`; PIE pending | `Enemies.md` §4.2/§6.8, `EnemyAI.md` §7.1/§8.8, `Scripts/_check_bat_hit_knockback.py`, `Scripts/_bp_bat_flying_guard_paste.txt` |
| 7 Nov 2026 | A1 | `BP_EnemyBase` knockback Z override | DONE | live T3D export: `K2Node_CallFunction_28.bZOverride = true`; `Scripts/_check_bat_hit_knockback.py` → `RESULT: PASS (A: bZOverride=true)`; `_verify_enemy_base.py` 45 PASS / 0 FAIL / 0 PENDING | — | the shared `AnyDamage` launch no longer inherits the victim's Z velocity, so a flying enemy with `KnockbackForce=0` keeps `MOVE_Flying` and `MaxFlySpeed`; grounded walkers are unchanged (`Vz ≈ 0`); the Option-B Bat Tick guard is not in the asset and is not needed; closes the A2 row above. Commit `BP_EnemyBase.uasset` + docs, push, then re-run PIE 7/8/14 | `BP_EnemyBase.uasset`, `Enemies.md` §4.2/§6.8, `EnemyAI.md` §7.1/§8.8, `EnemyWorkPlan.md` |
| 7 Nov 2026 | A1 | Knockback retune (shared `AnyDamage`) | DONE | `Scripts/_run_enemy_tuning.py` → live CDO `BP_EnemyBase.KnockbackForce` 200 → 1200, saved and re-read; `Scripts/_run_knockback_lift_check.py` → `RESULT: PASS` (`MakeVector.Z ← Multiply(KnockbackForce, 0.4)`, `lift=480 uu air=0.327 s shove=392 uu`) | PIE pending | a horizontal-only launch is worth ~15 uu at *any* force (`ApplyVelocityBraking` caps the victim at `MaxWalkSpeed` with `GroundFriction^2 * BrakingDecelerationWalking` = `131072` uu/s², then `GroundFriction` 8 kills the rest), so the shove now carries an authored arc: `MakeVector.Z = KnockbackForce * 0.4` via `Scripts/_bp_enemy_base_knockback_lift_paste.txt` → `Lift 480`, `t_air 0.327 s`, ~392 uu at `GravityScale=3`. `BP_Bat` (`KnockbackForce=0`) still sends a zero vector, so the `bZOverride=true` fix above is untouched. Gotcha: every `Content/**` file is read-only on disk after a git operation — `save_loaded_asset` returns `False` until the flag is cleared | `BP_EnemyBase.uasset`, `Enemies.md` §4.2, `EnemyAI.md` §7.1, `Scripts/_set_enemy_tuning.py`, `Scripts/_check_knockback_lift.py`, `Scripts/_bp_enemy_base_knockback_lift_paste.txt` |
| 7 Nov 2026 | A1 | `BP_Snail` chase speed | DONE | `Scripts/_run_enemy_tuning.py` → live CDO `BP_Snail.ChaseSpeed` 80 → 250, saved and re-read; aggro box still `0/0`, `bAggroOnHit=true` | PIE pending | `UpdateAggro`'s chase branch writes `MaxWalkSpeed = ChaseSpeed` (patrol writes `MoveSpeed`), so the old `80` uu/s against the player's `1000` uu/s was indistinguishable from standing still. No proximity aggro was added: the zero aggro box plus `bAggroOnHit` is the locked §13 design (a snail ignores a player until it is shot) | `BP_Snail.uasset`, `Enemies.md` §6.3, `EnemyAI.md` §8.3/§10, `EnemyWorkPlan.md` |
| 7 Nov 2026 | A1 | `BP_EnemyBase` acquire/keep split | DONE (8 Nov row below) | whole-graph paste applied: live T3D `Update Aggro` is 61 nodes, **1 piece**, 10 of 11 checks PASS — the six new→old links landed. The editor renamed the pasted `FunctionEntry` (`K2Node_FunctionEntry_0` → `_4`), so the importer dropped **five** entry wires, not the three that were first noticed: `FunctionEntry.Player` → `IsPlayerInAggroBox.Player` `(592,-640)`, → `IsPlayerOnHomePlatform.Player` `(880,-640)`, → `K2_GetActorLocation.self` `(592,-288)` (the *player* location; the second `K2_GetActorLocation` at `(592,-432)` is the enemy's own and must stay unwired), → `ChaseStep.Player` `(4208,-960)`, and `FunctionEntry.Delta Seconds` → `Add.A` `(3440,-480)` (without it `UnreachableTime += dt` becomes `+= 0`, so a walker would never de-aggro). The `then` wire survived. The regenerated paste writes all five on both pins and `Scripts/_test_full_paste.py` PASSes 11/11 both as-is and with the entry renamed on purpose | drag those five wires (entry `(96,-752)`) or re-paste `Scripts/_bp_enemy_base_updateaggro_full_paste.txt` → compile → save → `_run_aggro_keep_check.py` = PASS → PIE | the box term is acquire-only now: `Chase = Detect OR (bAggro AND Keep)` where `Keep = OnHome AND |ΔZ| ≤ MaxChaseStepZ (+ hit window + AggroRadius > 0)`. A walker used to de-aggro after `DeAggroTime` whenever the player ran past `AggroHalfWidth` on the *same* platform, because acquire and keep shared one 600–1400 uu rectangle. Flyers are unaffected (they never call `UpdateAggro`) and the `AggroRadius > 0` term keeps that guarantee inside the shared rule | `Scripts/_bp_enemy_base_updateaggro_full_paste.txt`, `Scripts/_make_full_aggro_paste.py`, `Scripts/_test_full_paste.py`, `Scripts/_make_aggro_paste_graph.py`, `Scripts/_check_aggro_keep.py`, `Scripts/_run_aggro_keep_check.py`, `Scripts/_verify_enemy_base.py`, `EnemyAI.md` §1/§4/§6.2/§6.3/§6.4, `Enemies.md` §5.1/§7.3 |
| 7 Nov 2026 | A1 | `BP_EnemyBase` flyer guards | DONE | `_verify_enemy_base.py` **52 PASS / 0 FAIL / 0 PENDING** — both `Is Flying` guards present; `_audit_enemy_base.py` 50 graphs / 23 composites / **11 unwired (0 suspicious)** / 0 orphans; walker rescue PIE-confirmed (9a) | 9a PASS (walker); 9b PASS (flyers — no flyer sent back to a zone) | `TryRescue` and `FindHomePlatform` now return immediately for `MOVE_Flying`, so a flyer is never snapped to a zone and never adopts one. Three checker bugs fixed in the same session, all the same `gnorm()` trap: `exec_edges()` looked a composite's `BoundGraph` up by raw name (3 false FAILs, 23 composite bodies invisible), `verify()` tested the T3D display name `"Find Home Platform"` (a built guard still read PENDING), and the audit counted `K2Node_ComponentBoundEvent` as an orphan. `_probe_rescue.py` no longer hard-codes `guard PENDING`: it reads `_verify_enemy_base_out.txt` (`guards_built()`), covered by `Scripts/_test_probe_guards.py` |
| 8 Nov 2026 | A1 | **M1 gate — walker PIE tests 1–9** | **M1 GREEN** | `_check_aggro_keep.py` re-run 8 Nov 2026 on the post-guard export: 11/11 PASS — the five `FunctionEntry` wires of the row above are present (`FunctionEntry drives Tick, both player pins and the clock — 6 wires present`); `_verify_enemy_base.py` 52 PASS / 0 FAIL / 0 PENDING | 1–4, 6, 7 PASS with no deviation; 5 PASS — the walker halts where it is and faces the player instead of walking to the ledge, then patrols again after `DeAggroTime` (the `False → bAggro` branch); 8 PASS through the spawn variant — a walker placed on a zone-less surface is taken by the 0.5 s `BeginPlay` `TryRescue` timer to the nearest zone, the same function the knockback path calls (no stair step exists in `L_Level_01` to knock one into); 9 N/A there: `RescueRadius=2000` on a ~4000 uu level leaves every step with an eligible zone at or below it, so "stays stranded" cannot be produced — 9a covers the candidate path | closes the acquire/keep row above; `EnemyAI.md` §11 rows 1–9, §6.3, §12 |
| 8 Nov 2026 | A2 (B's asset) | `BP_FloatingSkull` | **BUILT, PIE open** | `Scripts/_run_probe_skull.py` (read-only) on the live CDO: **0 of 22** probed properties missing — seven own variables (`BounceSpeed=300`, `bPoweredOn=true`, `bUseWallAlternate=false`, `OnIdleFlipbook=FLB_Skull_Idle01`, `OffIdleFlipbook=FLB_Skull_Idle02`, `HitWallFlipbookA/B`) and Class Defaults `bCanMove=false`, `ChaseSpeed=0`, `MaxHealth=2`, `ContactDamage=1`, `MoveSpeed=300`, `IdleFlipbook=FLB_Skull_Idle01`, `HitFlipbook`/`DeathFlipbook=FLB_Skull_Hit`; fresh `_check_child_overrides.py` export: own `RefreshStateFlipbook` traced (`Parent:` → Branch(`bPoweredOn`) → ON/OFF idle), capsule-bound `ComponentHitSignature`, `TogglePower` + `BackToSkullIdle` sub-graphs, `BreakHitResult`/`Normal`/`Abs` and `LaunchCharacter` reflect | not run | build came in `bb3627d` (**Lee Chung Hei**, 5 Nov 2026) with no doc update, which is why `A2e` still read NOT STARTED; `A2a` (Rocks) is now the only untouched A2 card; the asset also runs an enabled `ReceiveTick` sub-graph that `EnemyAI.md` §8.7 does not mention — decide keep or remove |
| 8 Nov 2026 | A2 (Jones) | `BP_RockBase` + `BP_Rock1/2/3` | **BUILT, unverified** | merged `branch/Jones` `f37473b` into `branch/Dennis` as `320f0de`; static `.uasset` string read (editor closed, no live probe): `BP_RockBase` declares `RockTier`/`ChildRockClass`/`bCanSplit`/`SplitImpulse`/`SplitOffset` + a `BP_RockBase` array, with `BeginDeferredActorSpawnFromClass`/`FinishSpawningActor` in the graph; `Rock1` (38×34, `Enemy.Rock.Tier1`, child `BP_Rock2_C`) → `Rock2` (32×28, `Tier2`, child `BP_Rock3_C`) → `Rock3` (22×18, `Tier3`, no child); `FLB_Rock<n>_Idle/Run/Hit` referenced per tier | not run | same failure mode as `A2e`: the asset shipped without a card update. **Open:** live CDO probe of the defaults (`MaxHealth` `3/2/1`, `MoveSpeed` `100/140/180`, `ChaseSpeed` `120/160/200`, `MaxPieces=8`), where the split hangs off `Die` vs base `AnyDamage`, and PIE test 11 |
| 8 Nov 2026 | A2 (Jones' rocks, B's skull) | `BP_RockBase`+`BP_Rock1/2/3`+`BP_FloatingSkull` in PIE | **PIE FAIL — 8 defects** | read without the editor via `UE4Editor-Cmd.exe -run=pythonscript` (`Scripts/_dump_rocks_assets.py`, `_dump_rocks_flipbooks.py`, `_dump_level_rocks.py`) + `Scripts/_dump_graph.py`: rock CDOs are exactly the card's `3/2/1`, `100/140/180`, `120/160/200`, `MaxPieces=8`, `bCanSplit` `true/true/false`; `L_Level_Testing` holds a single `BP_Rock1` at `(600,0,106.2)` with rotation `0,0,0`; flipbooks `Rock1` 14/14/1, `Rock2` 13/14/1, `Rock3` 11/14/5 frames at 10/14/12 fps | 21:29 recording: (a) split pieces spawn rotated — `MakeTransform` rotation is `Conv_VectorToRotator(GetActorLocation())`; (b) pieces shove each other — both pieces are Pawn-blocking Characters chasing one player and nothing makes rock-vs-rock ignore, and `AdjustIfPossibleButAlwaysSpawn` displaces the spawns (the impulses themselves are outward/correct); (c) rocks play `Idle` while chasing and `Run` once the chase is dropped — `ChaseStep`/`PatrolStep` never call `RefreshStateFlipbook`, only `UpdateAggro`'s give-up branch does; skull: (d) hit flipbook A/B selected by `bPoweredOn` (`bUseWallAlternate` is dead), (e) no `OtherActor` filter so it reflects and power-toggles off the player, no re-hit cooldown → corner jitter, else pin unwired, (f) `ReceiveTick` sets facing to `NegateFloat(Normal(Velocity).X)` and snaps to "right" when `Vx≈0`. The bounce math is a correct signed per-axis reflect; `TogglePower` per hit is the card's design | `Docs/EnemyWorkPlan.md` `A2a`/`A2e`; scratch: `Scripts/_rock_base_graph_dump.txt`, `_skull_graph_dump2.txt`, `_enemy_base_graph_dump.txt` |

| 8 Nov 2026 | A1 | `BP_Ghost` contact + `UpdateAggro` idle gap | **DIAGNOSED, fix spec'd** | `_verify_enemy_base.py` = 52 PASS / 0 FAIL, so the base contact chain ("ContactBox overlap kills the player after the player-only gate") is intact; live CDO/component probe (`Scripts/_run_probe_ghost_contact.py`) shows the Ghost `ContactBox` itself is correct (`Custom`, QueryOnly, `Pawn=Overlap`, overlap events on) while its `CollisionCylinder` is the only enemy capsule left at `NoCollision`; `Scripts/_check_ghost_phases.py` = 11 PASS / 5 FAIL (no capsule enable in `StartAggro`/`StartAppear`, no `ContactBox` off in `BecomeInvisible`, `bInvulnerable` inverted in `Init` and `StartAppear`); `Scripts/_check_idle_gap.py` = 1 PASS / 1 FAIL (`UpdateAggro` `StopMovementImmediately -> SetFacing` wait branch has no `RefreshStateFlipbook`, so the rock holds `Run` for `DeAggroTime`) | 8 Nov PIE reports: "the rock keeps playing walk while it stands still after de-aggro" and "the ghost chases me but never kills me". Fixes: base `SetFacing.then -> Refresh State Flipbook` (step 4c) and five Ghost edits (step 4d) | `Docs/EnemyWorkPlan.md` step 4c/4d; `Scripts/_check_idle_gap.py`, `Scripts/_check_ghost_phases.py`, `Scripts/_dump_varsets.py`, `Scripts/_find_member.py`, `Scripts/_grep_members.py`, `Scripts/_probe_ghost_contact.py` |
| 8 Nov 2026 | A1 | `BP_Ghost` contact — **root cause: Y plane** | **ROOT-CAUSED, level fix pending save** | re-export after the 4d edits: `_check_ghost_phases.py` **16 PASS / 0 FAIL**, every phase node on the **exec** chain (`Sprite.SetVisibility` → `ContactBox.QueryOnly` → `Capsule.QueryOnly` → `bInvulnerable=false` → `bDealContactDamage=true`); live PIE capture (`Scripts/_watch_pie_ghost.py` → `_snapshot_pie_ghost.py`) shows the visible phase correct (`bInvisible=false`, `bDealContactDamage=true`, `ContactBox=QueryOnly`) but `overlaps=[]`, `dist=292`, ghost pinned at **Y=280**; `Scripts/_check_enemy_plane.py` = **3 PASS | 1 FAIL** (`BP_Ghost Y=280 dY=280 boxY±75 tol=80`) | moving the live ghost to `Y=0` mid-chase gave `overlaps=['BP_Player_C_0']` and an immediate level reload (`Kill` → `OpenLevel`) — contact damage works once the planes match | `Aggro Trigger Logic` drops Y on purpose (`MakeVector(X = dX, Y = 0, Z = dZ)` → `Normal` → `AddMovementInput`), so a Ghost placed off the player's plane can never overlap it although it looks adjacent in the orthographic side view; the 4d "capsule gate" theory was wrong for this symptom (child primitives update their own overlaps). Fix = `BP_Ghost` `Location Y = 0` in `L_Level_01`, save; optional hardening = pass `Y = dY` in `Aggro Trigger Logic`. Also: `AggroRadius` lives in a variable named `AggroRadius` + **trailing tab** (`550.0`); plain `AggroRadius` reads `0.0`, so probes must use the tab name. Step 4e | `Docs/EnemyWorkPlan.md` step 4e; `Scripts/_check_enemy_plane.py`, `Scripts/_apply_ghost_plane_fix.py`, `Scripts/_watch_pie_ghost.py`, `Scripts/_snapshot_pie_ghost.py`, `Scripts/_pie_ghost_y_fix.py`, `Scripts/_probe_ghost_tuning.py`, `Scripts/_probe_ghost_aggro.py`, `Scripts/_probe_player_geom.py`, `Scripts/_probe_player_collision.py`, `Scripts/_probe_mobility.py` |
| 9 Nov 2026 | A2 | `BP_RockBase` split + `SetFacing` (A2a fix plan 1–5) | **DONE (PIE test 11 still open)** | fresh `_export_rock_check.py` export: both `MakeTransform.Rotation` literal `0,0,0` (no `Conv_VectorToRotator`), both spawns `AlwaysSpawn`, both `IgnoreActorWhenMoving` present; gates `_check_step3_live.py` `7 PASS / 0 FAIL`, `_check_step4_live.py` `10 PASS / 0 FAIL`, `_check_idle_gap.py` `2 PASS / 0 FAIL` (step 4c applied), `_check_refresh_reset.py` `16 PASS / 2 FAIL` with **both fails on `BP_Ghost`** (rocks/turtle/skull clean); Simulate kill (`_run_sie_rock_split.py`): `ApplyDamage(99)` on the placed `BP_Rock1` (`MaxHealth 3`) spawned two `BP_Rock2_C`, `actorRot=(0,0,0)`, both `Y=10`, same `Z=89.6`; facing samples: `Facing=1` → sprite `(0,0,y-180)`, `Facing=-1` → `(0,0,0)` | PIE test 11 with a player (chase sheet + split underfoot); `BP_Ghost` rules 1+2 of step 4b | defects 1–3 are gone from the asset — pieces spawn unrotated, inherit the rock's plane (`Y=10`, dY 10 vs player `Y=0`, box ±75) and the shove seen in the samples is the outward `SplitImpulse`; **step 5 needed no edit**: the "Pitch 180" worry was a stale T3D *summary* string (`DefaultValue="0,180.000000, 0"`) on the left branch while its split pins are `0.0` — the split pins are what compile, and the live sprite is Yaw 180 / Yaw 0 exactly as `Enemies.md` §`SetFacing` says; `PatrolMinX/-MaxX` are `-799/1810` and `PatrolMaxX` cannot be set on an instance, so the left branch was reached by teleporting the rock past the bound | `BP_RockBase.uasset`, `Docs/EnemyWorkPlan.md` `A2a`; scratch: `Scripts/_rock_after_step3.txt`, `_enemy_after_step5.txt`, `_run_sie_rock_split.py`, `_run_sie_facing.py`, `_run_sie_left_branch.py`, `_probe_setfacing_rot.py`, `_probe_level_rocks.py` |



**`M1 GREEN` — 8 Nov 2026.** Walker PIE tests 1–7 passed in `L_Level_01` on the
staged `BP_Rock1`; verifier output: `_verify_enemy_base.py` **52 PASS | 0 FAIL |
0 PENDING** and `_check_aggro_keep.py` **11/11**. Test 8 passed through the spawn
variant of the rescue, test 9 is N/A in that level (see the row above and
`EnemyAI.md` §11). Walker graphs and walker PIE are unblocked: `A1b`
(`BP_Snail`), `A2` (`BP_Rock1/2/3`) and C may start; tests 10–16 are unaffected.

**Defect report (B → A1, 25 Oct 2026) — `BP_EnemyBase` contact chain cannot fire.**
Binary inspection of the committed `BP_EnemyBase.uasset` (458 KB, commit
`8505b35`) shows only three SCS components (`CollisionCylinder`, `Sprite0`,
`CharMoveComp`). **No `ContactBox` component exists**, and the contact chain
("Is Overlapped Actor a Player?" → "Is Player Killable" → Kill/ApplyDamage) is
bound to `ReceiveActorBeginOverlap`. Both `BP_EnemyBase` and `BP_Player` use the
`Pawn` preset with `Pawn = Block`, so per `EnemyAI.md` §9 the overlap event never
fires and no enemy can kill the player on contact. PIE evidence (Owner B,
`L_Level_Testing`): `BP_SpikeTurtle` spike cycle/timers work; fresh side-touch
during the spikes-out window does not kill the player; stomping the turtle
kills the turtle via the player's `Event Hit`/Kill path (turtle `bInvulnerable`
was reset by `InitEnemy`; B re-asserts it in the child BeginPlay). The docs'
"ContactBox done 24 Oct / 44 PASS" claim does not match the committed asset,
and `Scripts/_verify_enemy_base.py`, `_make_enemies.py`, `_verify_enemies.py`
are not in any branch's history. Requested from A1: add `ContactBox`
(`BoxComponent`, QueryOnly, Generate Overlap Events, `Pawn=Overlap`, all other
channels Ignore, extents ~`(50,50,90)`), rebind the existing contact chain to
`On Component Begin Overlap (ContactBox)`, re-run the base verifier, commit
`BP_EnemyBase.uasset` + the verifier scripts. B's four assets need no changes
once the base fix lands; B will re-run test 10 and flip the status line.

**Resolved.** `ContactBox` exists on `BP_EnemyBase` and the turtle's contact kill
passed in PIE after the 744f845 fix (see the 25 Oct `BP_SpikeTurtle` row). No
further action; the report is kept for history.

**Current gate:** `M1` **is green since 8 Nov 2026** (§10). `BP_EnemyPlatform` is
PASS, and `BP_EnemyBase` has **13/13** AI functions, **25/25** §4 variables
(24 verified on 4 Nov; `bAggroOnHit` is in the asset and `EXPECTED` grew to 25
rows with it — re-run `_check_enemy_ai_vars.py`) and a wired `Event Tick`. Tests
1–7 passed in `L_Level_01`, 8 through the spawn variant of the rescue, 9 is N/A
there (`RescueRadius=2000`). Walker graphs and walker PIE are unblocked; the
Snail's remaining Class Defaults are the next A1 work.

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
7. Append the status line and tell A1 if a contract changed.

Never commit `Saved/`, `Intermediate/`, `DerivedDataCache/`, `__pycache__/`,
probe dumps, or a `.umap` you do not own.

---

## 12. Priority and scope if time slips

The full target remains all nine mechanics. If the schedule slips, keep this
order:

1. **Must-have V1:** M1 base gate (A1), `BP_Snail` (A1), `BP_Rock1/2/3` (A2),
   `BP_WoodLog` (C), `BP_Rhino` (C). `BP_Ghost` (A2) and `BP_Bat` (A2) are
   already DONE, so they cost no remaining time.
2. **Cheap and worth keeping:** `BP_SpikeTurtle` (A2 — already DONE; timers
   only, no movement).
3. **Defer last:** `BP_FloatingSkull` (A2), `BP_ToxicSlime` (C).

Do not “save time” by skipping M1, duplicating movement into a child, or letting
a walker ignore a ledge. Those shortcuts create the exact bugs the AI design
exists to prevent.

---

## 13. Open decisions locked by this plan

These are deliberate, and the technical docs must agree with them:

- `bCanMove` is the shared walker-AI gate. Stationary/flyers set it false; their
  own movement still works.
- `ChaseSpeed <= 0` means “no detection”: Toxic Slime patrols only. Snail is the
  exception introduced by the hit-window decision below (`ChaseSpeed=250` with a
  zero-size aggro box).
- Snail's shell uses base `PatrolStep`; there is no second shell Tick.
- Wood Log stops by setting `bCanShoot=false` and `bCanMove=false` in
  `TryFire`; `EndAttack` restores both. It overrides `ChaseStep` to stand.
- Ghost inherits `bAggro` and `AggroRadius`; Bat inherits `ChaseSpeed`; Rhino
  inherits `MoveSpeed`.
- `BP_PeaPlant` and `BP_EnemyProjectile_Pea` remain unused shells.
- The first PIE gate is a temporary `BP_Rock1` on P_02 or `BP_Snail` on P_00,
  not the current Snail placement at `(-451, 9, 225)`. A2 stages/removes it;
  A1 runs the PIE check without saving the map.
- **Locked 4 Nov 2026 (A1-owned), contracts updated, PIE pending:** aggro on a
  bullet hit. `bAggroOnHit` (bool, `false`) in the base; the post-hit window is
  the existing `DeAggroTime` (`2.0`), deliberately shared with the box de-aggro
  so there is one grace knob and not two. Enabled only on `BP_Rock1/2/3`,
  `BP_WoodLog` and `BP_Snail`.
  The Snail rule above is therefore replaced by `ChaseSpeed=250` with
  `AggroHalfWidth=0` / `AggroHalfHeight=0` and `bAggroOnHit=true`;
  `EnemyAI.md` §4/§6.2/§6.3/§8.2/§8.3/§8.9 and `Enemies.md`
  §4.2/§5.3/§6.2/§6.3 now describe it. Ghost and Rhino stay detection-only and
  bullet-immune. The 8 new nodes and the `BooleanOR` re-wire are in
  `BP_EnemyBase` in the same commit; the acceptance is 54 nodes in a fresh
  `UpdateAggro` export (46 + 8), **45 PASS / 0 FAIL** from
  `_verify_enemy_base.py` (including the 3 new / 3 old link audit) and
  **25 PASS / 0 FAIL** from `_check_enemy_ai_vars.py`. `BP_Snail` carries the
  aggro CDO flip in that same commit.

If implementation proves a decision wrong, A1 updates this list and the matching
contract in the same commit. A2 and C do not fork the design silently.
