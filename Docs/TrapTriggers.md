# Traps - react to the player, not bullets or enemies - build guide

**Status (19 Oct 2026): the trap gate is now PLAYER-ONLY.** The 19 Oct PIE bug
("the traps is reacting to the bullets too") is one failure; the enemy rule adds a
second: an enemy must never trigger a trap and must never take trap damage.
`BP_KillVolume` is the single deliberate exception - it must kill an enemy that
falls into a pit.

**Step 0 audit (19 Oct 2026, live T3D): COMPLETE - 14 PASS.**
`BP_TrapBase`, `BP_Trap_Spikes`, `BP_Trap_FakeFloor` and `BP_Trap_FallPlat`
are **PASS** - ordinary traps are player-only. `BP_KillVolume` passes both
branches: player `Kill` behind `BPI_Killable`, and `Enemy`-tagged fallers
destroyed through `Destroy Actor` with **Target = `OtherActor`**.
`BP_EnemyBase` now implements `BPI_Killable`. Current verifier:

`14 PASS | 0 FAIL | 0 WARN | 0 PENDING`.

There is no remaining Step 0 hand work. Enemy behaviour graphs (health, `Kill`,
`AnyDamage`, contact damage) are the separate next block in
`Docs/Enemies.md` §7.1 step 1.

---

## 1. Symptom

Shooting across the room pops the **spike traps** up. They are supposed to stay
retracted until the **player** walks into them. Three `BP_Trap_Spikes` instances
are placed in `L_Level_00`:

| Actor | Location | Should erupt for | Reacted to a bullet |
|---|---|---|---|
| `BP_Trap_Spikes` | (600, 0, 100) | the player | **yes** |
| `BP_Trap_Spikes2` | (1500, 0, 100) | the player | **yes** |
| `BP_Trap_Spikes3` | (1000, 0, 700) | the player | no (out of the bullet line) |

Evidence (PIE, 19 Oct): a `BP_Projectile` placed at `(400, 0, 100)` flew along
`+X`; after 2 s the sprites at x=600 and x=1500 were at their **up** offset
`(0, -50, 0)` while the one at z=700 was still retracted at `(0, -50, -100)`.
The third trap never saw the bullet, so the cause is the bullet passing through
the first two - not the level starting in the up state.

---

## 2. The rule

**A trap may only react to the player. Enemies are trap-neutral; bullets are
trap-neutral.**

```
Overlap  ->  Equal (Other Actor, Get Player Character(0))  ->  Branch
                                                          True -> react
```

`Get Player Character(0)` is not a `Cast To BP_Player`. It asks the engine for
the locally controlled player, so renaming the player class cannot break it.
`BPI_Killable` is still the project "can die" question, but it is **not** the
trap-trigger question any more: enemies implement `BPI_Killable` so bullets and
the pit volume can kill them.

`BP_Projectile` is an **Actor with a `BlockAllDynamic` box** and does **not**
implement `BPI_Killable`. Enemies are `Pawn`s with the `Enemy` tag and **do**
implement `BPI_Killable` once `BP_EnemyBase` is built. That is exactly why the
old killable gate is wrong for ordinary traps.

### 2.1 The enemy contract

| Rule | Meaning |
|---|---|
| Enemies never trigger traps | Enemy overlap does not pop spikes, drop a fake floor, or start a saw |
| Enemies take no trap damage | An enemy can stand in active spikes and walk through them unharmed |
| Enemies may fall | A player-triggered hole can drop an enemy, and gravity still applies |
| Only the pit kills by trap | `BP_KillVolume` at the pit bottom destroys `Enemy`-tagged actors (even `bInvulnerable` ones) |
| No class casts | Gate with player equality, not `Cast To BP_Player` |

The `Enemy` tag on every enemy CDO is defense in depth for future trap logic,
but the current gate is the equality above - tags are identifiers, not collision
filters (`Docs/Enemies.md` §1).

---

## 3. Why the spikes tripped on bullets

`BP_Trap_Spikes`'s `Event ReceiveActorBeginOverlap` chain (current graph):

```
ReceiveActorBeginOverlap
  -> then -> Branch   (Condition <- GET bEruptOnTrigger)          <- no filter
                -> True -> Set Relative Location  (Target = Sprite,
                                          New Location <- SpriteStartOffset)
                             -> then -> Branch  (Condition <-
                                 Does Implement Interface)         <- Test Object EMPTY
                                           -> True -> Kill (Other Actor)
```

Two separate faults:

1. **The eruption branch has no actor filter.** `bEruptOnTrigger` only says
   *whether* this trap erupts at all, not *for whom*. Every overlapping actor
   moves the sprite back to `SpriteStartOffset` - a bullet or enemy included.
2. **The kill gate is dead.** `Does Implement Interface` has no `Test Object`
   wired (the same empty-pin failure as `ProjectileShooting.md` 5.5), so it is
   false for every actor and `Kill` has **never** fired from this graph. The
   player has always been killed by `BP_TrapBase`'s own `Trigger` overlap.

---

## 4. Fixes (hand work - Python cannot create graph nodes)

The trap graphs are **done and verified**, including the `BP_KillVolume` pit
exception in section 4.5.

### 4.0 Step 0 audit

| # | Asset / edit | Live result |
|---|---|---|
| 0.1 | `BP_TrapBase` Trigger overlap -> `Equal(OtherActor, Get Player Character(0))` -> `Kill` | **PASS** |
| 0.2 | `BP_Trap_Spikes` eruption behind `AND(bEruptOnTrigger, player equality)`; old duplicate `Kill` removed; `Sprite` = `NoCollision` | **PASS** |
| 0.3 | `BP_Trap_FakeFloor` TriggerBox gate -> `Set Collision Enabled(FloorBox)` + `bFalling` | **PASS** (gate lives inside the collapsed `Triggerable Actor` graph) |
| 0.4 | `BP_Trap_FallPlat` — no overlap chain of its own; inherits `BP_TrapBase` | **PASS** |
| 0.5 | `BP_KillVolume` player `Kill` behind `BPI_Killable`; enemy `Destroy Actor` behind `Actor Has Tag(Enemy)` | **PASS** — player branch gated; enemy `Destroy Actor.Target = OtherActor` |
| 0.6 | `BP_EnemyBase` implements `BPI_Killable` (pit exception prerequisite) | **PASS** |

The verifier follows collapsed graphs (`K2Node_Composite` -> `K2Node_Tunnel_0`),
so a gate inside `Triggerable Actor` is not reported as missing.


### 4.1 `BP_TrapBase` - Trigger overlap

Current chain in `EventGraph`:

```
ComponentBoundEvent (Trigger)
  -> Branch (Condition <- Does Implement Interface(OtherActor, BPI_Killable))
       -> True -> Kill (Message) Target = Other Actor
```

> **Where is the overlap event?** In `BP_TrapBase` the live event is the
> **`Trigger` component-bound** node titled **`On Component Begin Overlap
> (Trigger)`**, below the three disabled placeholder events. The red
> `Event Receive Actor Begin Overlap` near the top is **disabled** (it shows
> "This node is disabled and will not be called") - do not wire it. The actor
> itself has no overlap collision; the `Trigger` component is what fires.
>
> To jump to it: Components panel -> select **`Trigger`** -> Details -> Events
> -> click the **+** next to **On Component Begin Overlap**. If the event
> already exists, that opens the existing node instead of duplicating it.
> Its pins are `Overlapped Component`, `Other Actor`, `Other Comp`,
> `Other Body Index`, `bFrom Sweep`, `Sweep Result`.

Change only the **Branch condition**:

1. Delete the wire from `Does Implement Interface.Return Value` to the Branch
   `Condition`.
2. Add **`Get Player Character`** (Player Index = `0`).
3. Add **`Equal (Object)`**: **A** = the event's **`OtherActor`**, **B** =
   `Get Player Character.Return Value`.
4. Wire `Equal.Return Value` -> Branch **Condition**.
5. Keep the True pin -> `Kill (Message)` with **Target = Other Actor**.
6. **Compile + Ctrl+S.** Click the component-bound event node -> Details ->
   Inputs must be empty.

### 4.2 `BP_Trap_Spikes` - actor overlap

Open `BP_Trap_Spikes` -> **EventGraph**. The live event is the red
`Event Receive Actor Begin Overlap` at the far left; the old branches sit at the
far right. Do not confuse it with the disabled
`Call to Parent Function Receive Actor Begin Overlap` stub.

1. Before deleting anything, drag **`OtherActor`** from the event into a new
   **`Equal (Object)`** node's **A** pin.
2. Add **`Get Player Character`** (index `0`) -> **B** pin.
3. Add an **`AND`** (boolean) node: **A** = existing `GET bEruptOnTrigger`,
   **B** = `Equal.Return Value`.
4. Wire `AND.Return Value` -> the first Branch's **Condition** (the one whose
   True goes to `Set Relative Location`).
5. **Delete** the old second Branch and its `Kill` message. `BP_TrapBase`
   already kills the player through the inherited `Trigger`; keeping this copy
   would queue a second level reload.
6. **Make the spike sprite non-blocking:** select `Sprite` in Components ->
   Collision Presets = **NoCollision**. It is currently `BlockAllDynamic`, which
   would stop an enemy at the spikes even though the gate prevents damage. The
   inherited `Trigger` remains the only interaction volume. Do **not** do this
   to `BP_Trap_FallPlat` - its Sprite is the platform the player stands on.
7. **Compile + Ctrl+S.** Click the event node -> Details -> Inputs must be empty.

Result:

```
ReceiveActorBeginOverlap
  Other Actor -> Equal (Object) <- Get Player Character(0)
                      | Return Value
  GET bEruptOnTrigger -> AND -> Branch.Condition
                                 True -> Set Relative Location (Sprite)
```

### 4.3 `BP_Trap_FakeFloor` - TriggerBox overlap

Current chain drops `FloorBox` for every `BPI_Killable`. Replace the gate the
same way as `BP_TrapBase`:

> **The gate is inside a collapsed graph.** In the live asset the TriggerBox
> event feeds a `K2Node_Composite` named **`Triggerable Actor`**. Double-click
> that node and edit the `Equal(OtherActor, Get Player Character(0))` inside
> it. The outer `EventGraph` only shows the component event and the composite;
> that is expected, not a missing wire. `Scripts/_verify_traps.py` follows the
> composite's `K2Node_Tunnel_0` and checks the inner gate.

1. Select the `TriggerBox` component-bound event -> `OtherActor`.
   It is the only overlap event in the graph; the old standalone
   `Event Receive Actor Begin Overlap` has been removed.
2. `Equal (Object)`: **A** = the `Triggerable Actor` input **A** (fed by
   `OtherActor`), **B** = `Get Player Character(0)`.
3. `Equal.Return Value` -> the existing Branch **Condition** that feeds
   `Set Collision Enabled (FloorBox)` and `SET bFalling = true`.
4. Remove the old `Does Implement Interface` wire (or delete the unused node).
5. **Compile + Ctrl+S.**

An enemy can stand on the fake floor safely; the floor still supports it until
the **player** steps on it and drops it.

### 4.4 `BP_Trap_FallPlat` - inherited

No child graph change. Its overlap chain forwards to `BP_TrapBase`, so the
player-only Trigger gate in 4.1 covers it.

### 4.5 `BP_KillVolume` - the pit exception

**Status: PASS (19 Oct 2026).** The live graph is player `Kill` behind
`BPI_Killable` and `Enemy`-tagged `Destroy Actor` with `Target = OtherActor`.
The steps below are the rebuild recipe and the reason each wire exists.

**Do not change this to player equality.** The pit volume must kill both the
player and enemies. It already exists at
`Content/DontTrustTheLevels/Traps/Blueprints/BP_KillVolume` with a `KillBox`
(OverlapAllDynamic, generate overlap events).

Keep the existing `Does Implement Interface(OtherActor, BPI_Killable)` gate,
then split inside its True branch:

1. Add **`Actor Has Tag`**: Target = `OtherActor`, Tag = `Enemy`.
   - It lives under **Utilities** (`AActor::ActorHasTag`).
   - The live graph uses the **pure** form (`bIsPureFunc=True`): `Return Value`
     feeds the second Branch's **Condition** and there is no exec pin. That is
     valid - do not convert it just to match a guide.
   - If your node search gives the **impure** form (it has `exec` / `then`),
     put it in the exec chain instead: first Branch **True** -> `Actor Has Tag`
     exec; `Actor Has Tag.then` -> second Branch exec.
   - Easiest creation: drag from the first Branch's **True** exec pin into
     empty space and search `Actor Has Tag`. If it is hidden, right-click
     empty graph space, uncheck **Context Sensitive**, and search
     `Actor Has Tag` or `Has Tag`.
   - It only appears in Actor-derived Blueprints (this one is).
2. Wire the branch: if your `Actor Has Tag` is pure, first Branch **True** ->
   second Branch exec directly. If it is impure, use the exec chain in step 1.
3. Add a second **Branch**:
   - **Condition** = `Actor Has Tag.Return Value`.
   - **True -> `Destroy Actor`** Target = `OtherActor`.
     > **The Target pin is easy to miss.** `Destroy Actor`'s target pin is
     > labelled **Target** internally (`self` in the T3D). Drag `OtherActor`
     > onto it. An empty Target compiles clean but destroys nothing - this was
     > the 19 Oct failure; the live wire now targets `OtherActor`.
   - **False -> existing `Kill (Message)`** Target = `OtherActor` (the player).
4. **Compile + Ctrl+S.**

Why destroy the enemy instead of calling `Kill`? `BP_EnemyBase.Kill` returns
early for `bInvulnerable` enemies (spikes-out turtle, Rhino). A pit fall must
still kill them. Destroying the tagged enemy at the pit bottom is the one
allowed enemy trap death; it is already out of play. The player still runs the
normal `Kill` -> reload path.

This is the only trap-related death an enemy may have: it must physically fall
into the volume. Spikes, saws, fake floor triggers and pre-existing damaging
terrain never call `Kill` or `Destroy Actor` on an enemy.

---

## 5. Verify (Python)

With the editor open and PIE stopped:

```bat
py -3 Scripts\_verify_traps.py
```

It exports all five trap blueprints to T3D, then **exec-traces** from every
overlap event. A state-changing call (`Set Relative Location`, `Kill`,
`Set Collision Enabled`) must sit on the **True** output of a Branch whose
Condition is `Equal(OtherActor, Get Player Character(0))` - directly or through
an `AND`. `BP_KillVolume` is checked separately: its player `Kill` must stay
behind `Does Implement Interface(OtherActor, BPI_Killable)`, and its enemy
`Destroy Actor` must sit on the **True** output of `Actor Has Tag(OtherActor,
Enemy)`. The script also checks that `BP_Projectile` does **not** implement
`BPI_Killable`, that the spike `Sprite` collision preset is `NoCollision`, and
requires `BP_EnemyBase` to implement `BPI_Killable`.

Expected and current result (19 Oct 2026, step 0 complete):

```
SUMMARY  14 PASS | 0 FAIL | 0 WARN | 0 PENDING
```

All trap-side checks and both `BP_KillVolume` branches are green. The
`BPI_Killable` interface is present on `BP_EnemyBase`; its behaviour graphs
remain separate work in `Docs/Enemies.md` §7.1.

`Scripts/_trap_export.py` is the export-only helper; the verifier runs the same
export itself. Neither script writes to any asset.

---

## 6. PIE checklist (`L_Level_00`)

1. Walk into `BP_Trap_Spikes` at x=600 -> spikes pop up, player dies/reloads.
2. Fire past it (key 1, any effect) -> **spikes stay retracted**.
3. Stand next to a spike trap and fire the other way -> still no erupt.
4. Fire at `BP_Trap_FakeFloor` (x=-1000) -> floor does **not** collapse.
5. Walk onto `BP_Trap_FakeFloor` -> it drops and the player falls.
6. Ricochet bullet passing a spike trap -> no erupt on either pass.
7. Place `BP_SpikeTurtle` on a spike trap while it is up -> turtle walks
   through unharmed; spikes do not re-trigger.
8. Place the turtle on `BP_Trap_FakeFloor` -> floor does **not** drop while only
   the turtle stands on it. Step on it as the player -> floor drops; if the
   turtle falls into the pit, `BP_KillVolume` kills it.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| Spikes still pop on bullets or enemies | The Branch still reads `bEruptOnTrigger` alone; wire `AND(bEruptOnTrigger, Equal(OtherActor, Get Player Character(0)))` into its Condition |
| Spikes never pop for the player | `Equal` has no `Get Player Character(0)` input, or `OtherActor` is not wired; also check the player index is 0 |
| Player no longer dies on spikes | `BP_TrapBase`'s Trigger Branch is not gated by player equality, or its `Kill` target is not `Other Actor` |
| Player dies twice / level reloads twice | The old second Branch + `Kill` still exist in `BP_Trap_Spikes`; delete both |
| Enemy triggers the fake floor | The FakeFloor TriggerBox still uses `BPI_Killable`; replace with player equality |
| Enemy dies on spikes | A trap still calls `Kill` on it; check the base Trigger and the spike graph for old interface gates |
| Enemy is blocked by spikes but does not die | `BP_Trap_Spikes.Sprite` is still `BlockAllDynamic`; set its Collision Presets to `NoCollision` |
| Enemy falls in a pit but survives | `BP_KillVolume` is missing the `Actor Has Tag(OtherActor, Enemy)` -> `Destroy Actor` branch, **or `Destroy Actor.Target` is empty** (compiles clean, does nothing), or the volume is not under the pit |
| `Actor Has Tag` is not in the node search | It is `AActor::ActorHasTag` under **Utilities**. The live graph uses the **pure** form (no exec pins); if you create the **impure** form from the True exec pin, insert it into the exec chain (True -> node -> second Branch). To find it, right-click empty graph, uncheck **Context Sensitive**, search `Has Tag` |
| Verifier says `T3D export missing` | The editor is closed; it must be open to export |
| Verifier says `unguarded: K2Node_...` | The gate sits after the call in the exec chain; move the Branch before it or fix the AND feeding its Condition |
 it must be open to export |
| Verifier says `unguarded: K2Node_...` | The gate sits after the call in the exec chain; move the Branch before it or fix the AND feeding its Condition |
