# Enemies — base class, nine mechanics, and build sheets

**Status (19 Oct 2026):** the Enemy pillar has **19 Blueprint shells** under
`Content/DontTrustTheLevels/Enemies/Blueprints/`, created by
`Scripts/_make_enemies.py`. All 19 were new (the folder contained only
`.gitkeep`); the generator skips existing assets unless `--update-defaults` is
passed. Their inherited Paper2D, capsule, movement, tag and lifespan defaults
pass **196 / 0 / 0** in `Scripts/_verify_enemies.py`.

This build's Python **cannot create event graphs, variables, functions, SCS
components or implemented interfaces** (probed in
`Scripts/_probe_graph_api.py` / `_probe_blueprint_vars.py`). The shells are
real and configured; the behaviour below is the **hand work** left in the
editor. The same boundary is documented in `ProjectileShooting.md` §“Limits”
and `Structure.md` §11.

> **⚠ 21 Oct 2026 AI revision.** Movement, patrol, detection, platform
> ownership, stairs and contact-damage collision are redefined in
> **`Docs/EnemyAI.md`**. Where the two files disagree, `EnemyAI.md` wins.
> Key changes: Spike Turtle is stationary/invulnerable; walkers use
> `BP_EnemyPlatform` zones and never walk off ledges; walkers use a rectangular
> aggro box + de-aggro; Ghost/Bat use a sphere + no de-aggro; Rhino has 4
> wall-health; Wood Log uses a finite rectangle; every contact is `1.0` and
> needs the collision fix in `EnemyAI.md` §9. Level-placement rules are in
> **`Docs/EnemyPlacement.md`**.

---

## 1. What exists

| Asset | Parent | Role | Default art |
|---|---|---|---|
| `BP_EnemyBase` | `PaperCharacter` | shared health / damage / death / contact / facing | — |
| `BP_ShooterEnemyBase` | `BP_EnemyBase` | shared ranged logic (fire interval, muzzle, projectile) | — |
| `BP_RockBase` | `BP_EnemyBase` | shared split logic / piece cap | — |
| `BP_SpikeTurtle` | `BP_EnemyBase` | spikes-out invulnerability | `FLB_Turtle_Idle01` |
| `BP_PeaPlant` | `BP_ShooterEnemyBase` | **unused** — Wood Log is the only shooter | `FLB_Plant_Idle` |
| `BP_WoodLog` | `BP_ShooterEnemyBase` | moving wood shooter | `FLB_Trunk_Idle` |
| `BP_Snail` | `BP_EnemyBase` | shell sweep after death | `FLB_Snail_Idle` |
| `BP_Ghost` | `BP_EnemyBase` | visible/invisible cycle | `FLB_Ghost_Idle` |
| `BP_Rock1` | `BP_RockBase` | tier 1, splits ×2 | `FLB_Rock1_Idle` |
| `BP_Rock2` | `BP_RockBase` | tier 2, splits ×2 | `FLB_Rock2_Idle` |
| `BP_Rock3` | `BP_RockBase` | tier 3, final | `FLB_Rock3_Idle` |
| `BP_ToxicSlime` | `BP_EnemyBase` | leaves toxic tracks | `FLB_Slime_IdleRun` |
| `BP_Rhino` | `BP_EnemyBase` | wall-only death | `FLB_Rino_Idle` |
| `BP_FloatingSkull` | `BP_EnemyBase` | ON/OFF wall toggle | `FLB_Skull_Idle01` |
| `BP_Bat` | `BP_EnemyBase` | ceiling trigger → chase | `FLB_Bat_CeilingIn` |
| `BP_EnemyProjectile` | `PaperSpriteActor` | enemy bullet base | — (5 s lifespan) |
| `BP_EnemyProjectile_Pea` | `BP_EnemyProjectile` | pea bullet | `SPR_Plant_Bullet` |
| `BP_EnemyProjectile_Wood` | `BP_EnemyProjectile` | wood bullet | `SPR_Trunk_Bullet` |
| `BP_ToxicPuddle` | `PaperSpriteActor` | slime trail hazard | `SPR_Slime_Particles` (3 s lifespan) |

**Tags already set on the CDOs**

- every enemy: `Enemy` + `Enemy.<Type>` (e.g. `Enemy.Turtle`)
- bases: `Enemy.Base`, `Enemy.Shooter`, `Enemy.Rock`
- flying: `Enemy.Flying`; special: `Enemy.Invulnerable`, `Enemy.Charger`,
  `Enemy.Phase`, `Enemy.Toggle`, `Enemy.Toxic`, `Enemy.Shell`
- projectiles: `EnemyProjectile` + `EnemyProjectile.Pea` / `.Wood`
- puddle: `Enemy.Hazard`, `ToxicPuddle`

Tags are identifiers, not collision filters. `BP_Projectile` does **not** read
them today.

---

## 2. Architecture decisions

| Decision | Why |
|---|---|
| `BP_EnemyBase` is a `PaperCharacter`, not `Actor` | inherited `Sprite0` (PaperFlipbookComponent), `CollisionCylinder` (capsule) and `CharacterMovement` mean a shell already renders and collides; no SCS components needed. |
| One `BP_EnemyBase` + data/overrides | shared damage/death/facing/animation; each enemy only owns its state machine. |
| `BP_ShooterEnemyBase` | Wood Log and Pea Plant share the same function; Wood Log is the only shooter used. |
| `BP_RockBase` + three children | split tier is data; art and health differ per child. |
| Actor tags on CDO | lets later systems find enemies without a hard cast; also documents intent in the Content Browser. |
| Contact damage checks `Get Player Character(0)` | enemies do not damage each other; no player-class cast and no new interface. |
| `BPI_Killable` on the base | the player projectile and `BP_KillVolume` speak it. Ordinary traps do **not**: they are player-only so enemies never trigger them (see 2.3). |

### 2.1 The projectile contract (important)

`BP_Projectile`'s hit graph currently does:

```text
On Component Hit → gates → Does Implement Interface(OtherActor, BPI_Killable)
  → True → Apply Point Damage → Kill (Message) on OtherActor
```

So an enemy that implements `BPI_Killable` receives **point damage and then a
Kill message in the same frame**. If `Kill` always died, every bullet would be
a one-hit kill and `MaxHealth` would be meaningless.

`BP_EnemyBase` therefore uses a **damage-frame guard**:

```text
Event AnyDamage:
    set LastDamageTime = now
    ... subtract health ...

Event Kill:
    if bIsDead            -> return
    if bInvulnerable      -> return
    if bUseHealth AND (now - LastDamageTime < 0.05)
        -> return          # this is the projectile's immediate Kill, not a trap
    Die
```

Consequences:

- A surviving bullet hit does **not** kill; health works.
- A second bullet in the same 0.05 s window also just damages (its Kill is ignored).
- `BP_KillVolume` destroys `Enemy`-tagged actors at the pit bottom; it does not rely on `Kill`, which would be ignored while `bInvulnerable`. Ordinary traps never call `Kill` or `Destroy Actor` on an enemy (see 2.3).
- Rhino now has 4 wall health (`MaxHealth=4`, `bInvulnerable=true` so bullets
  are no-ops). Each wall `Event Hit` subtracts 1 and turns it; the 4th calls
  `Die`. See `EnemyAI.md` §8.6.
- If you would rather make this explicit, add one `Actor Has Tag(OtherActor,
  "Enemy")` gate before `Kill` in `BP_Projectile` (Weapons pillar) and remove
  the time guard. That is a one-node change; it is **not** applied here.

### 2.2 Player damage

The player has no health variable today; `BP_Player` implements `Kill` and
reloads the level. Enemy contact damage therefore calls the **Kill message** on
the player, after confirming `OtherActor == Get Player Character(0)` and
`Does Implement Interface(OtherActor, BPI_Killable)`. If the target is not
killable, the overlap falls back to `Apply Damage` with `ContactDamage` (see
§4.4). If `BP_Player` gains health later, replace that Kill with `Apply Damage`
first.

### 2.3 Trap interaction contract (enemy-neutral)

**Enemies never trigger traps and traps never damage enemies. The only
trap-related death is falling into a player-triggered hole.**

| Rule | Implementation |
|---|---|
| No spike/fake-floor/saw trigger | Ordinary trap overlaps gate on `Equal(OtherActor, Get Player Character(0))`, not `BPI_Killable` |
| No trap damage | Spikes are player-only and their `Sprite` is `NoCollision`; an enemy can stand in active spikes and walk through unharmed |
| No enemy-caused collapse | `BP_Trap_FakeFloor.TriggerBox` drops the floor only for the player |
| Enemies can fall | Gravity/collision still apply; an enemy on a floor when the **player** drops it falls with it |
| Only the pit kills | `BP_KillVolume` keeps `BPI_Killable`; a tagged enemy that physically enters the `KillBox` is destroyed, bypassing `bInvulnerable` |
| Projectile still damages | `BP_Projectile` still uses `BPI_Killable` + `ApplyPointDamage`; this is not trap damage |
| Invulnerable still falls | A spikes-out turtle or Rhino dies in a pit because the volume destroys `Enemy`-tagged actors instead of relying on `Kill` |

Why not reuse `BPI_Killable` for traps? Because `BP_EnemyBase` implements the
same interface for bullets and pit death. The old trap gate would then make
enemies pop spikes and take trap damage for free. `Docs/TrapTriggers.md` §2.1
and §4.5 have the exact graph edits; `Scripts/_verify_traps.py` enforces them.

**Do not** add a "trap immunity" collision channel to enemies. Keep the default
`Pawn` capsule: collision is shared with terrain, bullets and the pit volume.
The separation is the player-equality gate in the trap graph, which is also why
an active spike can be walked through without a special enemy state.

> **Contact damage is a separate problem.** Both `BP_EnemyBase` and `BP_Player`
> use the `Pawn` preset with `Pawn = Block`. Unreal only fires overlap events
> when one side is `Overlap`, so the current actor-level `ActorBeginOverlap`
> contact chain never runs against the player. Add a `ContactBox` overlap
> component (recommended: keeps the capsule solid) or set the capsule's
> `Pawn` response to `Overlap`. Full options: `EnemyAI.md` §9.

---
## 3. `BP_EnemyBase` — variables, functions, components

### 3.1 Components (inherited; do not add duplicates)

| Component | Class | Use |
|---|---|---|
| `CollisionCylinder` | `CapsuleComponent` | root, terrain/bullet collision, `Event Hit` |
| `ContactBox` (add by hand) | `BoxComponent` | player contact overlap; `Pawn=Overlap`, everything else `Ignore` |
| `Sprite0` | `PaperFlipbookComponent` | all animation; rename variable only if you prefer `Sprite` |
| `CharMoveComp` | `CharacterMovementComponent` | walking / flying / disabling movement |

No SCS components are added by the generator. The **`ContactBox` is the one
required hand-added component** (see `EnemyAI.md` §9); the inherited capsule
stays solid for terrain/bullets and cannot generate player overlaps while both
capsules are `Pawn=Block`. Do not use the capsule for contact events.

`BP_EnemyBase` also has **Auto Possess AI = Placed In World Or Spawned** and the
default `AIController` class. That is what makes `Add Movement Input` work for a
placed enemy (and for rocks spawned at runtime) without a custom AI controller;
it does not add a Behavior Tree or any AI logic.

### 3.2 Variables (add in **My Blueprint → Variables**)

| Name | Type | Default | Purpose |
|---|---|---|---|
| `MaxHealth` | Float | `3.0` | full health; children override |
| `CurrentHealth` | Float | `3.0` | runtime |
| `bUseHealth` | Boolean | `true` | false = ignore health (Spike Turtle); Rhino keeps health but is `bInvulnerable` |
| `bInvulnerable` | Boolean | `false` | spikes-out / skull-on / rhino / i-frame gate |
| `bIFrameActive` | Boolean | `false` | short post-hit immunity |
| `IFrameDuration` | Float | `0.30` | i-frame length |
| `LastDamageTime` | Float | `-1000.0` | damage-frame guard |
| `bIsDead` | Boolean | `false` | hard stop |
| `ContactDamage` | Float | `1.0` | used only for non-player damage fallback |
| `bDealContactDamage` | Boolean | `true` | contact hazards on/off |
| `ContactDamageCooldown` | Float | `0.50` | prevents overlap spam |
| `LastContactDamageTime` | Float | `-1000.0` | cooldown stamp |
| `KnockbackForce` | Float | `200.0` | hit reaction |
| `HitRecoveryTime` | Float | `0.20` | hit flipbook return |
| `IdleFlipbook` | Paper Flipbook | child | base state |
| `HitFlipbook` | Paper Flipbook | child | damage reaction |
| `DeathFlipbook` | Paper Flipbook | child | death pose |
| `Facing` | Integer | `1` | `1` right, `-1` left |
| `DestroyDelay` | Float | `1.0` | seconds before `Destroy Actor` |
| `ScoreValue` | Integer | `10` | optional score hook |
| `MoveSpeed` | Float | `100.0` | child movement |
| `bCanMove` | Boolean | `true` | attack/state pause |

Set `MaxHealth`/`CurrentHealth` defaults per child (see §5–§7). The generator
sets capsule/movement per child; these variables are **not** set by Python.

### 3.3 Functions (all in `BP_EnemyBase`)

| Function | Inputs | Outputs | Job |
|---|---|---|---|
| `InitEnemy` | — | — | set health/flags/facing, play idle |
| `PlayStateFlipbook` | `NewFlipbook` (Paper Flipbook), `bLoop` (Boolean) | — | set + loop + play only when changed |
| `SetFacing` | `Direction` (Float) | — | `Facing = sign(Direction)`; yaw 0/180 on `Sprite0` |
| `RefreshStateFlipbook` | — | — | base plays `IdleFlipbook`; children override |
| `ClearIFrames` | — | — | `bIFrameActive = false` |
| `RecoverFromHit` | — | — | white sprite color + `RefreshStateFlipbook` |
| `Die` | — | — | shared death; children override for shell/split |
| `Kill` | interface event | — | forced death, with damage-frame guard |

`Die` and `RefreshStateFlipbook` must be **functions**, not custom events, so a
child can right-click → **Override**. Do not implement `Kill` as a function; it
is the `BPI_Killable` **event** (the interface function has no outputs, and
`Structure.md` §9 requires the event form).

### 3.4 Class Settings

1. **Class Settings → Interfaces → Add → `BPI_Killable`.**
2. Compile. The **Event Kill** node should now appear under *Interfaces*.
3. If it does not: remove and re-add `BPI_Killable` (the interface existed
   before the class picked it up; documented in `Structure.md` §9).

---

## 4. `BP_EnemyBase` — event graph (build order)

### 4.1 `Event BeginPlay` → `InitEnemy`

```text
Event BeginPlay
  → InitEnemy
```

`InitEnemy` body:

```text
Set CurrentHealth   = MaxHealth
Set bIsDead         = false
Set bInvulnerable   = false
Set bIFrameActive   = false
Set LastDamageTime  = -1000.0
Set LastContactDamageTime = -1000.0
Set Facing          = 1
PlayStateFlipbook (IdleFlipbook, true)
```

Children that add their own `Event BeginPlay` must call **`InitEnemy` first**
then start their own timers/state. If a child does not add BeginPlay, the
inherited base BeginPlay runs normally.

### 4.2 `Event AnyDamage` (health + hit reaction)

```text
Event AnyDamage (Damage, DamageType, InstigatedBy, DamageCauser)
  → Branch: bIsDead OR bInvulnerable OR bIFrameActive OR NOT bUseHealth
      True  → (return)
      False →
        Set LastDamageTime = Get Game Time in Seconds
        Set bIFrameActive  = true
        Set Timer by Function Name ("ClearIFrames", IFrameDuration, false)
        Set CurrentHealth  = CurrentHealth - Damage
        Set Sprite0 Sprite Color = Red
        PlayStateFlipbook (HitFlipbook, false)
        Set Timer by Function Name ("RecoverFromHit", HitRecoveryTime, false)
        Branch: CurrentHealth <= 0
          True  → Die
          False → optional LaunchCharacter knockback
```

Knockback (optional, but it sells the hit):

```text
Get Actor Location (DamageCauser) → Break Vector
Get Actor Location (Self)         → Break Vector
Sign(Self.X - Causer.X) → Multiply(KnockbackForce) → LaunchCharacter(X, 0, 0,
                                                        bXYOverride = true,
                                                        bZOverride = false)
```

If `DamageCauser` is not valid, use `-Facing * KnockbackForce`.

> `ApplyPointDamage` from `BP_Projectile` raises **both** `AnyDamage` and
> `PointDamage`. Bind only **AnyDamage** here; binding both would subtract twice.

### 4.3 `Event Kill` (forced death)

```text
Event Kill
  → Branch: bIsDead            → True: return
  → Branch: bInvulnerable      → True: return
  → Branch: bUseHealth AND (Get Game Time in Seconds - LastDamageTime < 0.05)
      True  → return           # projectile's immediate Kill
      False → Die
```

This is the whole reason a 3-health turtle is not a one-shot.

### 4.4 Contact damage (`Event ActorBeginOverlap` / component overlap)

> **21 Oct 2026:** this event is bound to the inherited capsule, but the capsule
> is `Pawn = Block` on both sides, so it does **not** fire against the player.
> Bind the same chain to a `ContactBox` overlap component instead (or change the
> capsule's `Pawn` response to `Overlap`). See `EnemyAI.md` §9.

```text
Event ActorBeginOverlap (OtherActor)
  → Branch: OtherActor == Get Player Character (Player Index 0)
      False → (return)
      True  →
        Branch: bIsDead OR NOT bDealContactDamage → True: return
        Branch: (Get Game Time - LastContactDamageTime) < ContactDamageCooldown
          True  → return
          False →
            Set LastContactDamageTime = Get Game Time in Seconds
            Does Implement Interface (OtherActor, BPI_Killable)
              True  → Kill (Message)   Target = OtherActor
              False → Apply Damage (OtherActor, ContactDamage, ...)
```

Keep the player-equality gate. Without it every enemy would kill every other
enemy that also implements `BPI_Killable`.

---

### 4.5 `Function Die` (shared death)

```text
Branch: bIsDead → True: return
Set bIsDead            = true
Set bInvulnerable      = true
Set bDealContactDamage = false
CharMoveComp → Disable Movement
CollisionCylinder → Set Collision Enabled (No Collision)
Sprite → Set Flipbook (DeathFlipbook)
Sprite → Set Looping (false)
Sprite → Play
Clear Timer by Function Name ("RecoverFromHit")
[optional: score / sound / spawn effect]
Set Life Span (DestroyDelay)
```

`DestroyDelay` must be wired into `Set Life Span`'s **In Lifespan** pin. A
literal `0.0` clears the lifespan timer, so the corpse never auto-destroys.

`Clear Timer ("RecoverFromHit")` is **required**. `AnyDamage` schedules that
timer just before calling `Die` on a lethal hit; if it is left pending it fires
0.2 s later, `RefreshStateFlipbook` plays `IdleFlipbook`, and the death art
snaps back to idle for the rest of `DestroyDelay`. Clearing `"ClearIFrames"` is
optional (it only resets a flag that no longer matters while dead).

Overrides:

- **Snail**: do not call `Die`; transition to the shell (see §6.3).
- **Rocks**: spawn children, then call `Parent: Die` (see §6.2).
- **Rhino**: call `Die` only from the wall-hit event (see §7.1).

### 4.6 Helper functions — exact pins

```text
PlayStateFlipbook(NewFlipbook, bLoop)
  Branch: NewFlipbook == None → return
  Branch: Sprite0 → Get Flipbook == NewFlipbook
    (if your graph has no Get Flipbook node, read Source Flipbook instead)
    True  → Sprite0 → Set Looping(bLoop) → Play
    False → Sprite0 → Set Flipbook(NewFlipbook)
            → Set Looping(bLoop) → Play
```

`SetFacing(Direction)`:

```text
Branch: Direction >= 0
  True  → Set Facing = 1   → Sprite Set Relative Rotation  (X 0, Y 0, Z 0)
  False → Set Facing = -1  → Sprite Set Relative Rotation  (X 0, Y 0, Z 180)
```

The pin boxes are **X (Roll)**, **Y (Pitch)**, **Z (Yaw)**, so the flip goes
in the **Z** box. The saved `DefaultValue` is ordered Pitch, Yaw, Roll, so a
correct false branch serialises as `0, 180, 0`; typing `0, 0, 180` into a
compact triple puts the 180 on Roll instead. Drag the `Sprite` component into
the graph and pick **Set Relative Rotation** — plain "Set Actor Relative
Rotation" targets the actor, not the flipbook.

`ClearIFrames` → `Set bIFrameActive = false`.

`RecoverFromHit` → `Set Sprite0 Sprite Color (White)` →
`RefreshStateFlipbook`.

`RefreshStateFlipbook` (base) → `PlayStateFlipbook(IdleFlipbook, true)`.

---

## 5. `BP_ShooterEnemyBase` + projectiles + puddle

### 5.1 `BP_ShooterEnemyBase` variables

| Name | Type | Default | Purpose |
|---|---|---|---|
| `ProjectileClass` | Class (Actor) | child | `BP_EnemyProjectile_Wood` (`_Pea` unused) |
| `FireInterval` | Float | `2.0` | seconds between shots |
| `NextFireTime` | Float | `0.0` | runtime |
| `MuzzleOffset` | Vector | `(60, 0, 20)` | local X is forward; multiply X by `Facing` |
| `ProjectileSpeed` | Float | `900.0` | passed to bullet |
| `ProjectileDamage` | Float | `1.0` | passed to bullet |
| `AttackFlipbook` | Paper Flipbook | child | attack state |
| `bCanShoot` | Boolean | `true` | state gate |
| `bRequireLineOfSight` | Boolean | `false` | optional trace |

`Event BeginPlay` (shooter base) → `InitShooter`.

`InitShooter`: call `InitEnemy`; `Set NextFireTime = Get Game Time in Seconds +
FireInterval`; `Set Timer by Function Name ("TryFire", 0.2, true)`.

Do **not** add a BeginPlay to `BP_WoodLog` unless it calls `InitShooter`; the
shooter base BeginPlay is what starts the fire timer. `BP_PeaPlant` is unused
and does not need this work.

`TryFire`:

```text
Branch: bIsDead OR NOT bCanShoot → return
Branch: Get Game Time in Seconds < NextFireTime → return
Get Player Character (0) → Is Valid? → false: return
SetFacing (Player.X - Self.X)
PlayStateFlipbook (AttackFlipbook, false)
Spawn Actor from Class:
  Class = ProjectileClass
  Spawn Transform = Self.ActorTransform
      + MakeVector(MuzzleOffset.X * Facing, 0, MuzzleOffset.Z)
  Collision Handling Override = Always Spawn
  → Return Value → Cast to BP_EnemyProjectile → Init Projectile
       Direction = (Facing, 0, 0)
       Speed     = ProjectileSpeed
       Damage    = ProjectileDamage
       Shooter   = Self
Set NextFireTime = Get Game Time in Seconds + FireInterval
Set Timer by Function Name ("EndAttack", 0.5, false)
```

`EndAttack` → `bCanShoot = true`, `bCanMove = true`,
`RefreshStateFlipbook`.

### 5.2 `BP_EnemyProjectile` (hand-add components + graph)

Add to the shell:

| Component | Class | Settings |
|---|---|---|
| `SphereCollision` | `SphereComponent` | radius 8; **BlockAllDynamic**; generate hit events |
| `ProjectileMovement` | `ProjectileMovementComponent` | Initial Speed 0; Max Speed 0; Gravity 0; Should Bounce false |

Variables: `Speed` Float `900`, `Damage` Float `1`, `Direction` Vector `(1,0,0)`,
`Shooter` Actor.

`Function InitProjectile(Direction, Speed, Damage, Shooter)`:
set the four variables; `ProjectileMovement → Set Velocity = Direction * Speed`.

`Event BeginPlay` → `Set Life Span(5.0)`; if `Speed` is already set, set
velocity (children may spawn with defaults).

`On Component Hit (SphereCollision)`:

```text
Branch: OtherActor == Shooter → return
Branch: OtherActor == Get Player Character(0)
  True  → Does Implement Interface(BPI_Killable) → Kill (Message) on OtherActor
          → Destroy Actor
  False → Destroy Actor          # wall / floor / other blocking actor
```

For hit VFX, spawn `SPR_Plant_BulletPieces` or `SPR_Trunk_BulletPieces` at
`Hit.ImpactPoint` before `Destroy Actor`. Do **not** use `ApplyPointDamage` on
the player unless the player gains health; today `Kill` is the player contract.

---

### 5.3 Wood Log defaults (Pea Plant reference)

The current build uses **Wood Log only**. The `BP_PeaPlant` column below is
kept for reference and is not part of the build order.

| Setting | `BP_PeaPlant` | `BP_WoodLog` |
|---|---|---|
| `ProjectileClass` | `BP_EnemyProjectile_Pea` | `BP_EnemyProjectile_Wood` |
| `FireInterval` | `2.2` | `2.5` |
| `MuzzleOffset` | `(60, 0, 20)` | `(90, 0, 10)` |
| `AttackFlipbook` | `FLB_Plant_Attack` | `FLB_Trunk_Attack` |
| `IdleFlipbook` | `FLB_Plant_Idle` | `FLB_Trunk_Idle` |
| `HitFlipbook` | `FLB_Plant_Hit` | `FLB_Trunk_Hit` |
| `DeathFlipbook` | `FLB_Plant_Hit` | `FLB_Trunk_Hit` |
| `MaxHealth` | `2.0` | `3.0` |
| `MoveSpeed` | `0` | `90` |
| movement | `MOVE_None`, gravity 0 (already set) | ground walk (already set) |

**Detection (superseded 21 Oct 2026):** Wood Log uses a **finite horizontal
rectangle** and de-aggro, not unlimited range. Start with
`AggroHalfWidth=1400`, `AggroHalfHeight=500`, `DeAggroTime=2.0`, plus the
same-platform check. It stops to shoot, fires only horizontally
(`Direction=(Facing,0,0)`, fixed muzzle Z), and resumes patrol when the player
leaves or becomes unreachable. `TryFire` is gated by `bAggro`. See
`EnemyAI.md` §6 and §8.9. A jumping player can dodge the shot by design.

`BP_PeaPlant`: no patrol; `bCanMove=false`; `RefreshStateFlipbook` always
`FLB_Plant_Idle`. It is unused in the current build.

`BP_WoodLog`: patrol left/right with `Add Movement Input`; on wall/edge,
`SetFacing(-Facing)`; use `FLB_Trunk_Run` while moving, `FLB_Trunk_Idle` while
the attack pauses movement. `AttackFlipbook` is one-shot; `EndAttack` resumes.

### 5.4 `BP_ToxicPuddle` (hand-add collision + graph)

Add a `BoxCollision` named `ToxicBox`:

- Box Extent `(100, 50, 20)` (scale the inherited sprite separately if needed)
- Collision Preset **OverlapAllDynamic**
- Generate Overlap Events ✓

`InitialLifeSpan` is already **3.0** on the shell, so it self-destroys.

`Event ActorBeginOverlap` → `OtherActor == Get Player Character(0)` →
`Does Implement Interface(BPI_Killable)` → `Kill` message. Optional: start a
0.5 s timer that applies damage while the player stands in it; clear it on
`ActorEndOverlap`.

The shell's default art is `SPR_Slime_Particles` (64×16 strip). Treat it as a
placeholder: create a dedicated puddle sprite later if the strip reads wrong.

---

## 6. The nine mechanics

All children inherit §3–§4. Only the child-specific additions are listed here.
Set each child's **Class Defaults** for the variables in the tables; the
generator already set the capsule, movement mode/speeds and idle flipbook.

### 6.1 Spike Turtle — `BP_SpikeTurtle`

**Goal:** cannot be damaged while thorns are out.

**Extra variables**

| Name | Type | Default |
|---|---|---|
| `bSpikesOut` | Boolean | `false` |
| `SpikeInterval` | Float | `1.8` |
| `SpikeChangeTime` | Float | `0.7` |
| `SpikesOutFlipbook` | Paper Flipbook | `FLB_Turtle_SpikesOut` |
| `SpikesInFlipbook` | Paper Flipbook | `FLB_Turtle_SpikesIn` |
| `IdleFlipbookA` | Paper Flipbook | `FLB_Turtle_Idle01` |
| `IdleFlipbookB` | Paper Flipbook | `FLB_Turtle_Idle02` |
| `bIdleAlt` | Boolean | `false` |

**Defaults (21 Oct 2026 revision):** `bCanMove=false`, `bUseHealth=false`,
`bInvulnerable=true`, `ContactDamage=1`, `MaxHealth=3`,
`HitFlipbook=FLB_Turtle_Hit`, `DeathFlipbook=FLB_Turtle_Hit`.

**BeginPlay:** call `InitEnemy`; `Set Timer by Function Name("SpikeCycle",
SpikeInterval, true)`; `Set Timer by Function Name("ToggleIdle", 1.4, true)`.

**`SpikeCycle`**

```text
Set bSpikesOut = NOT bSpikesOut
Branch bSpikesOut
  True  → PlayStateFlipbook(SpikesOutFlipbook, false)
          Set Timer by Function Name("FinishSpikeChange", SpikeChangeTime, false)
  False → PlayStateFlipbook(SpikesInFlipbook, false)
          Set Timer by Function Name("FinishSpikeChange", SpikeChangeTime, false)
```

**`FinishSpikeChange`**

```text
Set bDealContactDamage = bSpikesOut
Set ContactDamage      = 1.0
RefreshStateFlipbook
```

`RefreshStateFlipbook` (override): if `bSpikesOut`, play `IdleFlipbookB`;
otherwise play `bIdleAlt ? IdleFlipbookB : IdleFlipbookA`; loop true.
`ToggleIdle` → `Set bIdleAlt = NOT bIdleAlt` → `RefreshStateFlipbook`.

**Movement/detection:** none. Do not add a patrol Tick, wall reversal or aggro
box. The turtle is stationary scenery. It cannot be damaged by the player:
`bInvulnerable=true` permanently, so `AnyDamage` and `Kill` are no-ops. Only a
`BP_KillVolume` at the bottom of a pit destroys it (by `Enemy` tag). It is
harmful only while `bSpikesOut`; contact damage is always `1.0`.

**Why the timer, not `AnimFinished`:** `FLB_Turtle_SpikesOut/In` are 8 frames at
12 fps (~0.67 s); a timer is deterministic and does not depend on the flipbook
component broadcasting a finish delegate.

---

### 6.2 Rocks — `BP_Rock1` → `BP_Rock2` → `BP_Rock3`

**Goal:** each rock splits into two; total live pieces capped at **8**.

**`BP_RockBase` variables**

| Name | Type | Default | Purpose |
|---|---|---|---|
| `RockTier` | Integer | `1` | 1 / 2 / 3 |
| `ChildRockClass` | Class (Actor) | `BP_Rock2` on tier 1 | next tier |
| `bCanSplit` | Boolean | `true` | tier 3 false |
| `SplitImpulse` | Float | `250.0` | outward launch |
| `SplitOffset` | Float | `30.0` | spawn X offset |
| `MaxPieces` | Integer | `8` | global live cap |

**Child defaults**

| | `BP_Rock1` | `BP_Rock2` | `BP_Rock3` |
|---|---|---|---|
| `MaxHealth` | `3.0` | `2.0` | `1.0` |
| `MoveSpeed` | `100` | `140` | `180` |
| `RockTier` | `1` | `2` | `3` |
| `ChildRockClass` | `BP_Rock2` | `BP_Rock3` | `None` |
| `bCanSplit` | `true` | `true` | `false` |
| `IdleFlipbook` | `FLB_Rock1_Idle` | `FLB_Rock2_Idle` | `FLB_Rock3_Idle` |
| `HitFlipbook` | `FLB_Rock1_Hit` | `FLB_Rock2_Hit` | `FLB_Rock3_Hit` |
| `DeathFlipbook` | `FLB_Rock1_Hit` | `FLB_Rock2_Hit` | `FLB_Rock3_Hit` |

**Movement (21 Oct 2026 revision):** patrol with the platform/ledge guard
(`EnemyAI.md` §5); do **not** copy the turtle — it is now stationary. Rocks have
**detection**: a horizontal rectangle (`AggroHalfWidth=700`,
`AggroHalfHeight=500`), same-platform/reachability gate, and `DeAggroTime=2.0`.
They chase horizontally on their own platform, stop at ledges, and return to
patrol when the player leaves or becomes unreachable. Each tier keeps its own
`MoveSpeed`/`ChaseSpeed`. `RefreshStateFlipbook` chooses `FLB_RockN_Run` when
`Abs(GetVelocity.X) > 10`, else `FLB_RockN_Idle`. Split pieces run the same
`Landed`/platform adoption as the parent.

**`Die` override**

```text
Branch: bCanSplit AND ChildRockClass != None
  False → Parent: Die
  True  →
    Get All Actors of Class (BP_RockBase) → Length
    Branch: Length <= MaxPieces - 1        # self will disappear
      False → Parent: Die
      True  →
        For each side in (-1, +1):
          Spawn Actor from Class:
            Class = ChildRockClass
            Location = GetActorLocation + (side * SplitOffset, 0, 0)
            Collision Handling Override = Always Spawn
            → Return Value → Cast to BP_RockBase
              → LaunchCharacter(side * SplitImpulse, 0, SplitImpulse * 0.5,
                                bXYOverride = true, bZOverride = true)
        Parent: Die
```

The `Length <= MaxPieces - 1` check reserves the slot the dying rock will free.
If you want a hard cap even when a burst of rocks dies in one frame, replace it
with a tiny `BP_RockManager` (global counter) later; the 7-piece natural tree
(1 + 2 + 4) already stays under 8.

**Art:** tier 1 38×34, tier 2 32×28, tier 3 22×18. The capsule sizes were set
from those frame sizes.

---

### 6.3 Snail — `BP_Snail` → unkillable shell

**Goal:** after death the body becomes a shell that sweeps the platform and
cannot be killed.

**Extra variables**

| Name | Type | Default |
|---|---|---|
| `bShellPhase` | Boolean | `false` |
| `ShellSpeed` | Float | `600.0` |
| `ShellContactDamage` | Float | `1.0` |
| `ShellLifetime` | Float | `8.0` |
| `ShellIdleFlipbook` | Paper Flipbook | `FLB_Snail_ShellIdle` |
| `ShellWallHitFlipbook` | Paper Flipbook | `FLB_Snail_ShellWallHit` |
| `ShellTopHitFlipbook` | Paper Flipbook | `FLB_Snail_ShellTopHit` |
| `WithoutShellFlipbook` | Paper Flipbook | `FLB_Snail_WithoutShell` |

**Defaults:** `MaxHealth=2`, `MoveSpeed=50`, `ContactDamage=1`,
`IdleFlipbook=FLB_Snail_Idle`, `HitFlipbook=FLB_Snail_Hit`,
`DeathFlipbook=FLB_Snail_Hit`.

**Normal state (21 Oct 2026 revision):** patrol left/right with
`Add Movement Input` and the platform/ledge guard (`EnemyAI.md` §5). No
detection and no chase. `Event Hit` on a wall reverses `Facing`;
`RefreshStateFlipbook` uses `FLB_Snail_Walk` when moving, otherwise
`FLB_Snail_Idle`. The shell also uses the ledge guard: it sweeps its platform
and never walks off an edge.

**`Die` override**

```text
Branch: bShellPhase → True: return
Set bShellPhase          = true
Set bIsDead              = false       # keep overlap/contact alive
Set bInvulnerable        = true        # unkillable shell
Set bDealContactDamage   = true
Set ContactDamage        = ShellContactDamage
Set MoveSpeed            = ShellSpeed
Set MaxWalkSpeed         = ShellSpeed
Set bCanMove             = true
PlayStateFlipbook (ShellIdleFlipbook, true)
Set Life Span (ShellLifetime)
```

Do **not** call `Parent: Die`: it would disable collision and destroy the actor.
`bInvulnerable=true` makes base `AnyDamage` and `Kill` no-ops; `bIsDead=false`
keeps the contact overlap working (bind it to `ContactBox`, not the blocking
capsule). The shell remains a hazard.

**Shell movement / wall reaction**

```text
Event Tick → Add Movement Input((Facing,0,0), 1)
Event Hit  → Break Hit Result
  Branch: Abs(Normal.X) > 0.7 AND OtherActor != Get Player Character(0)
    True → SetFacing(-Facing)
           PlayStateFlipbook(ShellWallHitFlipbook, false)
           Set Timer by Function Name("BackToShellIdle", 0.25, false)
```

`BackToShellIdle` → `PlayStateFlipbook(ShellIdleFlipbook, true)`.
`ShellTopHitFlipbook` is optional: play it when the player lands on the shell
(player Z above shell Z and falling), but the shell still kills on contact.

`RefreshStateFlipbook` override: if `bShellPhase`, play `ShellIdleFlipbook`
(loop); otherwise the normal walk/idle choice.

---

### 6.4 Ghost — `BP_Ghost` (rewritten 21 Oct 2026)

**Goal:** starts **invisible and harmless**, becomes visible and starts chasing
only when the player enters its sphere, then loops visible/hidden forever. It
chases directly through walls.

**Extra variables**

| Name | Type | Default |
|---|---|---|
| `bInvisible` | Boolean | `true` |
| `bAggro` | Boolean | `false` |
| `AggroRadius` | Float | `550.0` |
| `VisibleTime` | Float | `2.5` |
| `InvisibleTime` | Float | `2.0` |
| `FadeTime` | Float | `0.5` |
| `AppearFlipbook` | Paper Flipbook | `FLB_Ghost_Appear` |
| `DisappearFlipbook` | Paper Flipbook | `FLB_Ghost_Disappear` |

**Defaults:** `MaxHealth=2`, `MoveSpeed=80`, `ContactDamage=1`,
`IdleFlipbook=FLB_Ghost_Idle`, `HitFlipbook=FLB_Ghost_Hit`,
`DeathFlipbook=FLB_Ghost_Hit`.

**BeginPlay:** `InitEnemy`; start fully hidden and harmless:
`bInvisible=true`, `Sprite0` visibility false, `CollisionCylinder` NoCollision,
`bInvulnerable=true`, `bDealContactDamage=false`, `bAggro=false`. No appear/
disappear timer yet.

**Trigger:** `Event Tick` → if `NOT bAggro` and player is valid and
`VSize(Player - Self) <= AggroRadius` → `StartAggro`. This is a **sphere** and
there is **no de-aggro** branch.

```text
StartAggro:
  Set bAggro = true
  Set bInvisible = false
  Sprite0 -> Set Visibility (true)
  CollisionCylinder -> Set Collision Enabled (Query and Physics)
  SetCollisionResponseToChannel(WorldStatic, Ignore)   # phase through walls
  Set bInvulnerable = false
  Set bDealContactDamage = true
  PlayStateFlipbook(AppearFlipbook, false)
  Set Timer by Function Name("StartDisappear", VisibleTime, false)
```

The visible/hidden loop is the old cycle, but it only starts after
`StartAggro`:

```text
StartDisappear:
  Set bDealContactDamage = false
  PlayStateFlipbook(DisappearFlipbook, false)
  Set Timer by Function Name("BecomeInvisible", FadeTime, false)

BecomeInvisible:
  Set bInvisible = true
  Sprite0 -> Set Visibility (false)
  CollisionCylinder -> Set Collision Enabled (No Collision)
  Set bInvulnerable = true
  Set Timer by Function Name("StartAppear", InvisibleTime, false)

StartAppear:
  Set bInvisible = false
  Sprite0 -> Set Visibility (true)
  CollisionCylinder -> Set Collision Enabled (Query and Physics)
  SetCollisionResponseToChannel(WorldStatic, Ignore)
  Set bInvulnerable = false
  PlayStateFlipbook(AppearFlipbook, false)
  Set Timer by Function Name("BecomeVisible", FadeTime, false)

BecomeVisible:
  Set bDealContactDamage = true
  RefreshStateFlipbook
  Set Timer by Function Name("StartDisappear", VisibleTime, false)
```

**Movement:** after `bAggro`, `Event Tick` gets the player, sets facing from
`Player.X - Self.X`, and moves directly in X/Z:
`Direction = Normalize(Player.Location - Self.Location)`, Y=0,
`Add Movement Input(Direction, 1)`. It does **not** path around walls; it flies
through them (`WorldStatic = Ignore`). The shell is `MOVE_Flying`, gravity 0.

**Damage/contact:** hidden = no collision, no contact, no damage, and player
bullets pass through. Disable **both** the capsule and the base `ContactBox`
while hidden; re-enable the `ContactBox` (`QueryOnly`, `Pawn=Overlap`) in the
visible phase. Visible = vulnerable, contact `1`. There is no
`bInvulnerableWhileInvisible` toggle any more; hidden is always untouchable.

`RefreshStateFlipbook` override: if `bInvisible`, do nothing; otherwise play
`FLB_Ghost_Idle` loop. Optional VFX: `SPR_Ghost_Particles` on a second
`PaperSpriteComponent`, toggled with the same state.

---

### 6.5 Toxic Slime — `BP_ToxicSlime`

**Goal:** leaves toxic tracks that exist for 3 seconds.

**Extra variables**

| Name | Type | Default |
|---|---|---|
| `PuddleClass` | Class (Actor) | `BP_ToxicPuddle` |
| `PuddleInterval` | Float | `0.75` |
| `NextPuddleTime` | Float | `0.0` |
| `PuddleOffset` | Vector | `(0, 0, -60)` |
| `bLeaveTracks` | Boolean | `true` |

**Defaults:** `MaxHealth=3`, `MoveSpeed=70`, `ContactDamage=1`,
`IdleFlipbook=FLB_Slime_IdleRun`, `HitFlipbook=FLB_Slime_Hit`,
`DeathFlipbook=FLB_Slime_Hit`.

**BeginPlay:** `InitEnemy`; `Set NextPuddleTime = Get Game Time in Seconds`.

**Movement (21 Oct 2026 revision):** patrol left/right with the platform/ledge
guard (`EnemyAI.md` §5). No detection and no chase. `RefreshStateFlipbook`
plays `FLB_Slime_IdleRun` (the only locomotion art) while alive.

**`Event Tick` — drop a track**

```text
Branch: bIsDead OR NOT bLeaveTracks → return
Branch: Abs(GetVelocity.X) < 10 → return
Branch: Get Game Time in Seconds < NextPuddleTime → return
Spawn Actor from Class:
  Class = PuddleClass
  Location = GetActorLocation + PuddleOffset
  Rotation = 0
  Collision Handling Override = Always Spawn
Set NextPuddleTime = Get Game Time in Seconds + PuddleInterval
```

`BP_ToxicPuddle` already has `InitialLifeSpan=3.0`, so the track disappears
after three seconds without any graph in the slime. If the puddle reads too
large/small, set `Spawn Transform → Scale` to `(0.75, 0.75, 0.75)`.

`BP_ToxicPuddle` itself needs the `ToxicBox` overlap from §5.4; that is where
the player is killed. Slime contact damage is the normal base `ContactBox`
overlap (not the blocking capsule; see `EnemyAI.md` §9).

---

### 6.6 Rhino — `BP_Rhino` (rewritten 21 Oct 2026)

**Goal:** a heavy charger with **4 wall health**. Player bullets do nothing;
each wall impact removes 1 health and turns it around. It dies on the 4th wall
hit or in a `BP_KillVolume`.

**Extra variables**

| Name | Type | Default |
|---|---|---|
| `bCharging` | Boolean | `false` |
| `MoveSpeed` | Float | `120.0` |
| `ChargeSpeed` | Float | `600.0` |
| `ChargeDirection` | Float | `1.0` |
| `WallHitCooldown` | Float | `0.5` |
| `LastWallHitTime` | Float | `-1000.0` |
| `RunFlipbook` | Paper Flipbook | `FLB_Rino_Run` |
| `HitWallFlipbook` | Paper Flipbook | `FLB_Rino_HitWall` |

**Defaults:** `MaxHealth=4`, `CurrentHealth=4`, `bUseHealth=true`,
`bInvulnerable=true` (bullets/Kill no-op), `ContactDamage=1`,
`IdleFlipbook=FLB_Rino_Idle`, `HitFlipbook=FLB_Rino_Hit`,
`DeathFlipbook=FLB_Rino_HitWall`.

**BeginPlay:** `InitEnemy`; `Set bInvulnerable=true`;
`Set bDealContactDamage=true`; `SetFacing(ChargeDirection)`;
`Set MaxWalkSpeed=MoveSpeed`; `PlayStateFlipbook(IdleFlipbook, true)`.
The rectangle detection is the long one: `AggroHalfWidth=1200`,
`AggroHalfHeight=500`, `DeAggroTime=2.0`. On aggro, `bCharging=true`,
`MaxWalkSpeed=ChargeSpeed`, face the player horizontally. On de-aggro,
`bCharging=false`, resume patrol. No vertical movement.

**`Event Hit` — the only damage path**

```text
Break Hit Result
Branch: OtherActor == Get Player Character(0) -> return   # contact kills player
Branch: Abs(Normal.X) > 0.7
  False -> return
  True  ->
    Branch: now - LastWallHitTime < WallHitCooldown -> return
    Set LastWallHitTime = now
    Set CurrentHealth = CurrentHealth - 1
    SetFacing(-Facing)                       # turn around after wall
    PlayStateFlipbook(HitWallFlipbook, false)
    Branch: CurrentHealth <= 0
      True  -> Set bInvulnerable = false
               Die
      False -> Set Timer by Function Name("EndWallHit", 0.3, false)
```

`EndWallHit` -> `bCharging=true` if the player is still aggro/reachable,
otherwise `bCharging=false` and patrol; `RefreshStateFlipbook`.

`RefreshStateFlipbook` override: `FLB_Rino_Run` while `bCharging`, otherwise
`FLB_Rino_Idle`. Because `bInvulnerable=true`, player bullets and `Kill` never
reduce health; the wall event is the only path. Falling into a `BP_KillVolume`
still destroys it by `Enemy` tag.

---

### 6.7 Floating Skull — `BP_FloatingSkull`

**Goal (21 Oct 2026 revision):** bounces like a slow bullet. It toggles ON/OFF
when it hits a wall or floor; ON = cannot take damage, OFF = cannot deal damage.
It has no detection and no chase; it just bounces until killed or it falls into
a `BP_KillVolume`.

**Extra variables**

| Name | Type | Default |
|---|---|---|
| `bPoweredOn` | Boolean | `true` |
| `OnIdleFlipbook` | Paper Flipbook | `FLB_Skull_Idle01` |
| `OffIdleFlipbook` | Paper Flipbook | `FLB_Skull_Idle02` |
| `HitWallFlipbookA` | Paper Flipbook | `FLB_Skull_HitWall01` |
| `HitWallFlipbookB` | Paper Flipbook | `FLB_Skull_HitWall02` |
| `bUseWallAlternate` | Boolean | `false` |
| `BounceSpeed` | Float | `300.0` |

**Defaults:** `MaxHealth=2`, `ContactDamage=1`, `MoveSpeed=300`,
`HitFlipbook=FLB_Skull_Hit`, `DeathFlipbook=FLB_Skull_Hit`.

**BeginPlay:** `InitEnemy`; `Set bPoweredOn=true`;
`Set bInvulnerable=true`; `Set bDealContactDamage=true`;
`PlayStateFlipbook(OnIdleFlipbook,true)`;
`LaunchCharacter((Facing * BounceSpeed, 0, BounceSpeed * 0.5), true, true)`.
The shell is already `MOVE_Flying`, gravity 0, `MaxFlySpeed=350`.

**`Event Hit` — toggle + reflect**

```text
Break Hit Result
Branch: Abs(Normal.X) > 0.5 OR Abs(Normal.Z) > 0.5
  False → return
  True  →
    PlayStateFlipbook(bUseWallAlternate ? HitWallFlipbookA : HitWallFlipbookB,
                      false)
    Set bUseWallAlternate = NOT bUseWallAlternate
    TogglePower
    Set Timer by Function Name("BackToSkullIdle", 0.35, false)
    Reflect velocity:
      Break Vector (GetVelocity)
      X' = Abs(Normal.X) > 0.5 ? -X : X
      Z' = Abs(Normal.Z) > 0.5 ? -Z : Z
      LaunchCharacter(MakeVector(X', 0, Z'), true, true)
```

**`TogglePower`**

```text
Set bPoweredOn          = NOT bPoweredOn
Set bInvulnerable       = bPoweredOn
Set bDealContactDamage  = bPoweredOn
Set Sprite0 Sprite Color = bPoweredOn ? Orange : Red   (optional)
RefreshStateFlipbook
```

`RefreshStateFlipbook` override: play `OnIdleFlipbook` when powered, otherwise
`OffIdleFlipbook`; loop true.

Base `AnyDamage` and `Kill` both check `bInvulnerable`, so ON ignores bullets;
OFF is vulnerable and harmless. Ordinary traps never call `Kill` on it. A
`BP_KillVolume` at a pit bottom destroys `Enemy`-tagged actors directly, so even
an ON skull dies if it falls out of the world. The projectile's damage-frame
guard still applies on OFF, so it takes multiple hits.

Optional particles: `SPR_Skull_OrangeParticle` / `SPR_Skull_RedParticle`
(16×16) can be a second `PaperSpriteComponent` toggled with the state. That
component is hand-added; Python cannot add SCS components.

---

### 6.8 Bat — `BP_Bat`

**Goal (21 Oct 2026 revision):** hangs until the player enters a **smaller
sphere** (300), then chases directly like the Ghost but **collides with walls
and floors**. No de-aggro once triggered.

**Extra variables**

| Name | Type | Default |
|---|---|---|
| `bTriggered` | Boolean | `false` |
| `bChasing` | Boolean | `false` |
| `TriggerRadius` | Float | `300.0` |
| `ChaseSpeed` | Float | `300.0` |
| `CeilingInFlipbook` | Paper Flipbook | `FLB_Bat_CeilingIn` |
| `CeilingOutFlipbook` | Paper Flipbook | `FLB_Bat_CeilingOut` |
| `FlyingFlipbook` | Paper Flipbook | `FLB_Bat_Flying` |
| `HangingFlipbook` | Paper Flipbook | `FLB_Bat_Idle` |

**Defaults:** `MaxHealth=2`, `ContactDamage=1`, `HitFlipbook=FLB_Bat_Hit`,
`DeathFlipbook=FLB_Bat_Hit`.

**BeginPlay:** `InitEnemy`; `Set bDealContactDamage=false`;
`PlayStateFlipbook(CeilingInFlipbook,false)`;
`Set Timer by Function Name("HangIdle", 0.6, false)`.

`HangIdle` → `PlayStateFlipbook(HangingFlipbook,true)`.

**`Event Tick` — trigger**

```text
Branch: bTriggered OR bIsDead
  True  → if bChasing and player valid: Chase step (below); return
  False →
    Get Player Character(0) → Is Valid? → false: return
    Distance(Self, Player) <= TriggerRadius
      False → return
      True  →
        Set bTriggered = true
        Set bDealContactDamage = true
        PlayStateFlipbook(CeilingOutFlipbook, false)
        Set Timer by Function Name("StartChase", 0.5, false)
```

`StartChase` → `Set bChasing=true`;
`Set MaxFlySpeed = ChaseSpeed`;
`PlayStateFlipbook(FlyingFlipbook,true)`.

**Chase step** (inside Tick or a 0.1 s timer):

```text
Get Player Character(0) → Is Valid? → false: return
Direction = Normalize(Player.Location - Self.Location)  (X/Z plane; set Y=0)
SetFacing(Direction.X)
Add Movement Input(Direction, 1)
```

The shell is already `MOVE_Flying`, gravity 0, `MaxFlySpeed=400`; `StartChase`
lowers it to `ChaseSpeed` (300) so the bat is dodgeable. `FLB_Bat_Flying` loops.

`RefreshStateFlipbook` override: `FlyingFlipbook` while `bChasing`, otherwise
`HangingFlipbook`.

The bat is a normal health enemy: `AnyDamage` / `Kill` from the base. Contact
damage is enabled only after the trigger, so a hanging bat is safe to touch.

---

## 7. Build order, verification, test matrix

### 7.1 Build order (do not skip ahead)

0. **Trap contract first (DONE - 14 PASS).** `Docs/TrapTriggers.md` §4.0
   audits the live graphs: `BP_TrapBase`, `BP_Trap_Spikes`, `BP_Trap_FakeFloor`
   and `BP_Trap_FallPlat` are player-only and **PASS**. `BP_KillVolume` passes
   both branches (`BPI_Killable` player `Kill`; `Enemy`-tagged `Destroy Actor`
   with `Target = OtherActor`). `BP_EnemyBase` implements `BPI_Killable`. Run
   `py -3 Scripts\_verify_traps.py` to confirm 14 PASS before enemy behaviour
   work.
0a. **Contact fix (do this first).** Add `ContactBox` to `BP_EnemyBase`
    (`Pawn=Overlap`, all else `Ignore`, generate overlaps) and bind its
    `On Component Begin Overlap` to the contact chain; or set the capsule's
    `Pawn` response to `Overlap`. The current actor `ActorBeginOverlap` cannot
    fire while both capsules are `Pawn=Block`. PIE-test one enemy touching the
    player before building child AI. See `EnemyAI.md` §9.
0b. **`BP_EnemyPlatform`** — box marker (no collision, hidden in game) and
    place one on each intended enemy platform. See `EnemyPlacement.md` for the
    per-enemy minimum widths and placement rules. Then `BP_EnemyBase` gets the
    platform/aggro state from `EnemyAI.md` §4–7. Compile + save.
1. **`BP_EnemyBase`** — Class Settings → `BPI_Killable`; add variables; build
   `InitEnemy`, `AnyDamage`, `Kill`, contact overlap, `Die`,
   `PlayStateFlipbook`, `SetFacing`, `ClearIFrames`, `RecoverFromHit`,
   `RefreshStateFlipbook`, plus the `EnemyAI.md` §4–7 helpers. Compile + save.

   **Harness ready (19 Oct, base complete 21 Oct):**
   `py -3 Scripts\_verify_enemy_base.py` checks this whole block from a fresh
   T3D + live CDO. It now reports **43 PASS / 0 FAIL / 0 PENDING** against the
   finished base graph. Re-run it after the contact/platform additions.
2. **`BP_EnemyProjectile`** — add `SphereCollision` + `ProjectileMovement`;
   add `InitProjectile`, `BeginPlay`, `On Component Hit`. Compile + save the
   `_Wood` child. `_Pea` is unused and can remain a shell.
3. **`BP_ToxicPuddle`** — add `ToxicBox` (OverlapAllDynamic) and the overlap
   kill. Compile + save.
4. **`BP_ShooterEnemyBase`** — fire timer, `TryFire`, `EndAttack`; compile.
   Then `BP_WoodLog` only (Class Defaults + rectangular detection/de-aggro +
   horizontal attack); `BP_PeaPlant` is not used.
5. **`BP_SpikeTurtle`** — spike cycle and idle alternation only. **No patrol**
   and no detection; `bInvulnerable=true`, `bUseHealth=false`.
6. **`BP_Rock1/2/3`** — patrol + rectangular detection/chase + `Die` split
   override; set `ChildRockClass`. Pieces adopt their landing platform.
7. **`BP_Snail`** — normal ledge-bound patrol, `Die` shell override, shell
   ledge-bound wall reaction. No detection.
8. **`BP_Ghost`** — invisible start, sphere aggro, visible/hidden loop, direct
   through-wall chase, no de-aggro. Hidden = no collision/contact/hits.
9. **`BP_ToxicSlime`** — ledge-bound patrol + puddle timer. No detection.
10. **`BP_Rhino`** — long rectangle detection, charge, **4 wall health**,
    turn after each wall, bullets no-op.
11. **`BP_FloatingSkull`** — slow bullet-like bounce + `Event Hit` toggle.
12. **`BP_Bat`** — hang → smaller-sphere trigger → direct chase with collision;
    no de-aggro.

After each asset: **Compile + Save** (Ctrl+S). A red compile error in a child is
usually a missing variable/function in the parent — fix the parent first.

### 7.2 Automated verification (already run)

```bat
py -3 Scripts\_make_enemies.py                    :: create missing shells
py -3 Scripts\_make_enemies.py --update-defaults  :: re-assert CDO defaults
py -3 Scripts\_verify_enemies.py                  :: fresh-load verification
py -3 Scripts\_verify_enemy_base.py               :: step 1 graph/interface audit
```

Current result: **196 PASS / 0 FAIL / 0 WARN / 19 assets**. The shell verifier
checks asset existence, T3D `ParentClass`, inherited idle flipbook or sprite,
capsule radius/half-height, movement defaults, tags, `InitialLifeSpan`, and the
base `AutoPossessAI`. It does **not** test event graphs.

`_verify_enemy_base.py` is the step-1 graph audit. It re-exports
`BP_EnemyBase`, reads the live CDO + `BPI_Killable`, and checks every §3.2
variable (type/default), §3.3 function signature, `Kill` event binding, and the
§4 event/helper graphs. `PENDING` means not built yet; `FAIL` means present but
mis-wired. Current baseline: **43 PASS / 0 FAIL / 0 PENDING**.

---


### 7.3 PIE test matrix

| Enemy | Test | Expected |
|---|---|---|
| Any enemy | Touch the player | player dies once; `ContactBox`/`Pawn=Overlap` fires; no enemy-vs-enemy kill |
| Any walker | Patrol on a floating platform | turns before the edge; never steps down |
| Any walker | Player on platform above/below | no aggro; no chase |
| Any walker | Player jumps over it on the same platform | walker turns, does not jump or step off |
| Any walker | Player drops to a lower platform | walker stops at the edge; after `DeAggroTime` resumes patrol |
| Any walker | Player returns to its platform | walker re-aggros and chases |
| Any walker | Shoot it off the platform | lands on the lower broad platform and adopts it as home |
| Any walker | Knock it into a stair step | `Stranded` idle; drops to nearest lower `BP_EnemyPlatform` if one exists; otherwise stays put |
| Spike Turtle | Shoot while spikes are out or in | no damage ever; `Kill`/point damage ignored |
| Spike Turtle | Walk through an active spike trap | no damage, no retrigger; enemy is trap-neutral |
| Spike Turtle | Let it fall into `BP_KillVolume` | destroyed by `Enemy` tag |
| Any enemy | Stand on `BP_Trap_FakeFloor` | floor does **not** drop for an enemy |
| Any enemy | Player drops the floor under it | enemy falls; if it reaches `BP_KillVolume`, it dies |
| Any enemy | Touch a spike trap before the player | spikes do **not** pop; player-only gate |
| Pea Plant (optional, unused) | Stand in range | `FLB_Plant_Attack`, pea spawns, travels, kills player |
| Wood Log | Watch patrol + range | patrols platform, stops inside `1400×500`, fires only horizontally, de-aggros and resumes |
| Snail | Kill it | body → shell, no destruction; shell sweeps its platform |
| Snail | Shoot the shell | no damage; contact `1` still kills player |
| Snail | Shell hits wall/edge | reverses at wall/edge, `ShellWallHit`; destroys after 8 s |
| Ghost | Before trigger | invisible, no collision, no contact, no chase |
| Ghost | Enter the 550 sphere | visible → chase through walls; visible/hidden loop starts; no de-aggro |
| Ghost | Shoot while hidden | no hit; collision is off |
| Rocks | Kill Rock1 | 2× Rock2; kill both → 4× Rock3; cap ≤ 8 live |
| Rocks | Kill Rock3 | no split; normal death |
| Rocks | Player enters 700×500 on same platform | chases; stops at ledge; de-aggros after 2 s unreachable |
| Toxic Slime | Walk around | puddles spawn; each disappears after 3 s; no detection |
| Toxic Slime | Step in puddle | player killed by `BP_ToxicPuddle` |
| Rhino | Shoot repeatedly | no damage (`bInvulnerable=true`) |
| Rhino | Lead it into a wall | `-1` health, turn around, `FLB_Rino_HitWall`; 4th wall hit dies |
| Rhino | Touch it | player dies; rhino continues |
| Floating Skull | Shoot while ON | no damage |
| Floating Skull | Let it hit wall/floor | toggles OFF; `HitWall01/02`; bounces slower (~300) |
| Floating Skull | Touch while OFF | no damage; shoot it to kill |
| Bat | Stand outside 300 sphere | hangs in `CeilingIn`/`Idle`; safe |
| Bat | Enter 300 sphere | `CeilingOut` → `Flying` → direct chase with collision; contact kills; no de-aggro |
| Bat | Shoot twice | 2 hits kills; `FLB_Bat_Hit` |
| Enemy projectile | Fire near a wall | destroys on wall, no self-hit, 5 s lifespan |
| Toxic puddle | Spawn and wait | destroyed at 3 s via `InitialLifeSpan` |

---


### 7.4 Known limits and deliberate decisions

- **No graph authoring from Python.** Event graphs, functions, variables,
  interfaces and SCS components are hand work in this UE 4.27.2 build. The
  generator only creates/configured the shells.
- **`BP_EnemyBase` behaviour graph is complete (43 PASS, 21 Oct).** `Kill`,
  `AnyDamage`/health, `ActorBeginOverlap` contact damage, `Die` and the helper
  bodies are in place, so bullets damage enemies and `BP_KillVolume` can still
  identify and destroy them. Ordinary traps must **never** damage enemies.
- **Wood Log is the only shooter; Pea Plant is intentionally unused.** The
  `BP_PeaPlant` and `BP_EnemyProjectile_Pea` assets remain in the project but
  are not part of the build order or required PIE tests. Wood Log now uses a
  **finite horizontal rectangle** (`1400×500`), same-platform/de-aggro and
  horizontal-only fire; it no longer shoots from anywhere in the level. See
  `EnemyAI.md` §8.9.
- **`BP_EnemyProjectile` and `BP_ToxicPuddle` have no collision/movement**
  until the hand-added components in §5.2/§5.4.
- **Contact damage is currently dead.** The inherited capsule is
  `Pawn=Block` on both enemy and player, so actor-level `ActorBeginOverlap`
  never fires. Add a `ContactBox` overlap component (recommended) or set the
  capsule's `Pawn` response to `Overlap`. See `EnemyAI.md` §9.
- **Player has no health.** Contact and projectiles call `Kill`; add health to
  `BP_Player` later if you want multi-hit damage. `ContactDamage` is `1.0`
  everywhere; the old `2.0` turtle/shell values are removed.
- **`Kill` time guard is 0.05 s.** It exists because `BP_Projectile` sends
  `ApplyPointDamage` then `Kill` in the same frame. If you add the one-node
  `Actor Has Tag("Enemy")` gate to `BP_Projectile`, remove the guard.
- **Capsule sizes are art-derived, not gameplay-tuned.** They fit the frame
  sizes but are narrower than the widest art (a capsule cannot be flat/wide);
  tune per enemy after the first PIE pass.
- **Toxic puddle art is a placeholder.** `SPR_Slime_Particles` is a 64×16
  particle strip, not a purpose-made puddle. Replace it when the art exists.
- **Rock cap is best-effort.** `Get All Actors of Class` is not atomic across
  simultaneous deaths; the natural 1 → 2 → 4 tree stays at 7 live pieces.
- **Rhino uses 4 wall health, not player damage.** `bInvulnerable=true` makes
  `AnyDamage`/`Kill` no-ops; each wall `Event Hit` subtracts 1, turns it around,
  and the 4th hit calls `Die`. `BP_KillVolume` can still remove it by tag.
- **Snail shell is invulnerable, not `bIsDead`.** It keeps `bIsDead=false` so
  contact overlap still runs; `bInvulnerable=true` blocks `AnyDamage` and
  `Kill`. Its `Die` override returns immediately while `bShellPhase`. Shell
  contact is `1.0`.
- **Ghost hidden phase is fully intangible.** Hidden = sprite off, collision
  off, `bInvulnerable=true`, contact off. Visible = vulnerable and contact `1`;
  it phases through `WorldStatic` walls. There is no optional invisibility
  toggle and no de-aggro after the sphere trigger.
- **Skull ON is fully invulnerable** because base `AnyDamage` and `Kill` both
  read `bInvulnerable`; OFF is vulnerable and harmless. Bounce speed is ~300,
  slower than the 900 bullet.
- **Spike Turtle is stationary scenery.** No patrol, no detection; it is
  permanently invulnerable to the player and dies only via `BP_KillVolume`.
  Contact is harmful only while spikes are out.
- **Walkers use authored `BP_EnemyPlatform` zones.** If a platform has no zone,
  enemies will not patrol there. Stairs are deliberately not zones; a knockback
  into a stair step makes the enemy `Stranded`, and it drops to the nearest
  lower zone only if one is authored. If none exists it **stays put** instead
  of jumping into a pit. See `EnemyAI.md` §3 and §7.
- **No navmesh/pathfinding.** Walkers turn at walls; Bat can stick on a wall.
  This is accepted for the current scope.
- **No enemy is placed in a level yet.** The shells exist in
  `Enemies/Blueprints/`; drag instances into `L_Level_00` (or a test map) and
  set their Class Defaults.
- **Auto Possess AI is enabled** (`Placed In World Or Spawned`) so
  `Add Movement Input` works without a custom AI controller. There is still no
  Behavior Tree, perception, or navmesh logic.
- **No C++.** This remains a Blueprint-only project.

### 7.5 Files touched by this work

| Path | What |
|---|---|
| `Content/DontTrustTheLevels/Enemies/Blueprints/BP_*.uasset` | 19 new shells |
| `Docs/Enemies.md` | this build sheet |
| `Docs/EnemyAI.md` | 21 Oct movement/detection/platform/stairs revision |
| `Docs/EnemyPlacement.md` | shared level-placement guide for all enemy types |
| `Docs/Structure.md` | enemy tree/ownership now points here |
| `README.md` | enemy status + guide link |
| `Scripts/_make_enemies.py` | local-only generator (gitignored) |
| `Scripts/_verify_enemies.py` | local-only verifier (gitignored) |
| `Scripts/_make_enemies_out.json`, `_verify_enemies_out.json` | local audit output |
| `Scripts/_verify_enemies_t3d/` | local T3D export used for parent checks |

---

