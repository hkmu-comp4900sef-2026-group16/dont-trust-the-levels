# Traps — react to the player, not the bullets · build guide

**Status: the spike trap is unfixed (19 Oct PIE: "the traps is reacting to the
bullets too, I want it only show when player walk pass").** Everything else in
the Traps pillar already obeys the rule; one graph does not.

---

## 1. Symptom

Shooting across the room pops the **spike traps** up. They are supposed to stay
retracted until the **player** walks into them. Three `BP_Trap_Spikes` instances
are placed in `L_Level_00`:

| Actor | Location | Should erupt for | Reacted to a bullet |
|---|---|---|---|
| `BP_Trap_Spikes` | (600, 0, 100) | the player | **yes** |
| `BP_Trap_Spikes2` | (1500, 0, 100) | the player | **yes** |
| `BP_Trap_Spikes3` | (1000, 0, 700) | the player | no (out of the bullet's line) |

Evidence (PIE, 19 Oct): a `BP_Projectile` placed at `(400, 0, 100)` flew along
`+X`; after 2 s the sprites at x=600 and x=1500 were at their **up** offset
`(0, −50, 0)` while the one at z=700 was still retracted at `(0, −50, −100)`.
The third trap never saw the bullet, so the cause is the bullet passing through
the first two — not the level starting in the up state.

---

## 2. The rule

**A trap may only react to an actor that can be killed.**

```
Overlap  ->  Does Implement Interface (Other Actor, BPI_Killable)  ->  Branch
                                                                 True -> react
```

`BPI_Killable` is the project's "can die" question (`Docs/Structure.md` §9), not
a class check. Today only `BP_Player` implements it, so the gate means "the
player" without a `Cast To BP_Player` that would break the next time the player
class is renamed. When enemies exist they implement the same interface and
traps start working on them for free — bullets never do.

`BP_Projectile` is an **Actor with a `BlockAllDynamic` box**; it does not
implement `BPI_Killable` (checked live with
`unreal.SystemLibrary.does_implement_interface`: `BP_Projectile` **False**,
`BP_Player` **True**). A trap that skips the interface check therefore treats a
bullet exactly like a player.

---

## 3. Why the spikes tripped on bullets

`BP_Trap_Spikes`'s `Event ReceiveActorBeginOverlap` chain (current graph):

```
ReceiveActorBeginOverlap
  └─ then ──> Branch   (Condition <- GET bEruptOnTrigger)          ← no filter
                └─ True ──> Set Relative Location  (Target = Sprite,
                                          New Location <- SpriteStartOffset)
                              └─ then ──> Branch  (Condition <-
                                  Does Implement Interface)         ← Test Object EMPTY
                                            └─ True ──> Kill (Other Actor)
```

Two separate faults:

1. **The eruption branch has no actor filter.** `bEruptOnTrigger` only says
   *whether* this trap erupts at all, not *for whom*. Every overlapping actor
   moves the sprite back to `SpriteStartOffset` — a bullet included.
2. **The kill gate is dead.** `Does Implement Interface` has no `Test Object`
   wired (the same empty-pin failure as `ProjectileShooting.md` 5.5), so it is
   false for every actor and `Kill` has **never** fired from this graph. The
   player has always been killed by `BP_TrapBase`'s own `Trigger` overlap, which
   is correctly gated — proved in PIE by moving a `BP_Player` into the x=600
   `Trigger`: its `bIsDead` flipped to `True` with the spike graph untouched.

---

## 4. Fix — `BP_Trap_Spikes` EventGraph

Four edits, no new event node. Open `BP_Trap_Spikes` → **EventGraph**.

| Step | Node | Pins |
|---|---|---|
| 1 | **`Does Implement Interface`** (the one already feeding the second Branch) | **Test Object** ← `ReceiveActorBeginOverlap.OtherActor` — **it is empty today**; the pin is one word, `OtherActor`, not `Other Actor` |
| 2 | **`AND`** (right-click → search `AND`, the boolean one) | **A** ← `GET bEruptOnTrigger` (move the wire that currently feeds the first Branch's `Condition`), **B** ← `Does Implement Interface.Return Value` |
| 3 | **first `Branch`** (the one whose True goes to `Set Relative Location`) | **Condition** ← `AND.Return Value` |
| 4 | **second `Branch` + its `Kill` message** | **Delete both** — this copy has never run (Test Object was empty) and `BP_TrapBase` already kills the player through the inherited `Trigger`, so keeping it only risks a second `Kill` (two `OpenLevel` waits) once step 1 makes it live |

### Where the `Other Actor` pin is

The event node in this graph is easy to lose: the two `Branch`es and `Kill`
sit at the far **right** (`x ≈ 650 … 1840`) while the event itself is parked at
the far **left** (`≈ (0, 208)`). If you are zoomed into the right-hand side you
are looking at `Branch` / `Kill`, not the event.

- It is the **red** node titled `Event Receive Actor Begin Overlap`, not the
  grey `Call to Parent Function Receive Actor Begin Overlap` stub at
  `(304, 112)` (that one is disabled and its `OtherActor` is an **input**, so it
  cannot feed anything).
- In 4.27 its output pin is labelled **`OtherActor`** (one word; there is no
  space, the tooltip is what reads `Other Actor / Actor Object Reference`). It is
  the blue **object** pin below `then` (white exec) and `Output Delegate` (grey).
- Fastest way there: **Ctrl+Shift+F** (Find in Blueprints) → `ReceiveActorBeginOverlap`
  → double-click the result, or select the node and press **F** to frame it.
- **Fallback that always works:** the same reference is already wired into the
  `Kill` message's **`Target`** pin (`OtherActor → Kill.Target`). Drag from
  **`Kill.Target`** to **`Test Object`** instead — identical value, no need to
  find the event. Do it **before** deleting `Kill` in step 4.

Result:

```
ReceiveActorBeginOverlap
  Other Actor ──> Does Implement Interface (BPI_Killable)
                            │ Return Value
  GET bEruptOnTrigger ──> AND ──> Branch.Condition
                                    └─ True ──> Set Relative Location (Sprite)
```

Then **Compile** and **Ctrl+S**. Click the `ReceiveActorBeginOverlap` node →
**Details → Inputs must be empty** (the Traps rule: a stray dragged parameter
silently feeds zeros).

> **Why an `AND` and not a second Branch.** An exec input pin takes exactly one
> wire, so two Branches in series cannot merge back before
> `Set Relative Location`; the two conditions have to become one boolean. This
> is the same shape `ProjectileShooting.md` 5.5 uses for
> `(Other == Shooter) AND NOT Can Hit Shooter`.

> **Why delete the Kill copy instead of just wiring it.** With `Test Object`
> wired, both this graph and `BP_TrapBase` would call `Kill` on the player in
> the same frame. `Kill` sets `bIsDead`, swaps to `FLB_Player_Hit`, waits 0.58 s
> and calls `OpenLevel`; running it twice queues the reload twice. The base
> already owns that job for every trap child, so the spike does not need it.

---

## 5. The other three traps (already correct)

| Blueprint | Overlap source | Reaction | Gate |
|---|---|---|---|
| `BP_TrapBase` | `Trigger` (component) | `Kill` (message) on `Other Actor` | `Does Implement Interface (Other Actor, BPI_Killable)` |
| `BP_Trap_FakeFloor` | `TriggerBox` (component) | `FloorBox.SetCollisionEnabled(NoCollision)` → `SET bFalling = true` | same interface check |
| `BP_Trap_FallPlat` | inherits `BP_TrapBase` | none of its own (its overlap event only calls the parent) | inherited from the base |

All three stay quiet for a bullet because the bullet is not killable. They are
not changed by this fix; the verifier keeps them honest.

---

## 6. Verify (Python)

With the editor open and PIE stopped:

```bat
py -3 Scripts\_verify_traps.py
```

It exports all four trap blueprints to T3D, then **exec-traces** from every
overlap event and requires each state-changing call (`Set Relative Location`,
`Kill`, `Set Collision Enabled`) to sit behind a Branch whose `Condition` comes
from `Does Implement Interface (…, BPI_Killable)` — directly or through an
`AND` — with a non-empty `Test Object` and a real `Interface` pin. It also
checks the premise live: `BP_Projectile` must **not** implement `BPI_Killable`,
`BP_Player` must.

Expected on the fixed graph:

```
SUMMARY  9 PASS | 0 FAIL | 0 WARN | 0 PENDING
```

Before the fix it reports exactly one FAIL:

```
FAIL  BP_Trap_Spikes: overlap pops the spikes / kills only for killable actors
      [unguarded: K2Node_CallFunction_7, K2Node_Message_1;
       K2Node_CallFunction_8: Test Object is empty (the gate can never pass)]
```

`Scripts/_trap_export.py` is the export-only helper; the verifier runs the same
export itself. Neither script writes to any asset.

---

## 7. PIE checklist (L_Level_00)

1. Walk into `BP_Trap_Spikes` at x=600 → spikes pop up, player dies/reloads.
2. Fire past it (key 1, any effect) → **spikes stay retracted**.
3. Stand next to a spike trap and fire the other way → still no erupt.
4. Fire at `BP_Trap_FakeFloor` (x=−1000) → floor does **not** collapse.
5. Walk onto `BP_Trap_FakeFloor` → it drops and the player falls.
6. Ricochet bullet passing a spike trap → no erupt on either pass.

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Spikes still pop on bullets | `AND.Return Value` is not feeding the first Branch's `Condition` — the branch still reads only `bEruptOnTrigger` |
| Spikes never pop for the player | `Does Implement Interface.Test Object` is still empty, or `Interface` is not set to `BPI_Killable` (an empty pin is false for **every** actor) |
| Player no longer dies on spikes | the base's `Trigger` overlap was damaged; this fix does not touch `BP_TrapBase` — check its `Kill` target is `Other Actor` |
| Player dies twice / level reloads twice | the old second Branch + `Kill` were kept instead of deleted (step 4) |
| Verifier says `T3D export missing` | the editor is closed; it must be open to export |
| Verifier says `unguarded: K2Node_CallFunction_…` | the gate sits *after* the call in the exec chain; move the Branch before it (or wire the `AND` into the branch that feeds it) |

