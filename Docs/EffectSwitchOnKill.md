# EffectSwitchOnKill.md — a kill re-rolls the gun's effect

**Status: card, nothing built yet.** Python in this build cannot author
Blueprint nodes or variables (`unreal.BlueprintEditorLibrary` and
`KismetEditorUtilities` are absent — `Structure.md` §11), so §1-§4 are editor
work; §6 is the scripted half.

**Before editing:** `git lfs lock` the three assets you are about to touch —
`Content/DontTrustTheLevels/Core/Interfaces/BPI_EffectUser.uasset`,
`.../Player/Blueprints/BP_Player.uasset`,
`.../Enemies/Blueprints/BP_EnemyBase.uasset` (`EnemyWorkPlan.md` §11). None of
them is locked today; `BP_EnemyProjectile_Wood.uasset` is (wing-del007) and is
not part of this card.

**Concept.** Killing an enemy switches the player's gun to a *different*,
randomly picked effect class from the pool — through the port every other switch
already uses (`BP_Player::Set Effect Class`, `ProjectileShooting.md` Part 7).
It is that doc's "any trigger" caller, with a random class instead of a fixed
one:

```text
BP_EnemyBase::Die                          BP_Player
  Sprite -> Play                             Event Randomize Effect Class   (BPI_EffectUser)
  Clear Timer ("RecoverFromHit")             pick an index that is NOT the current one
  Get Player Character (0)   ------------->  Set Effect Class(Effect Classes[i])   <- the port
  Randomize Effect Class (Message) -------->
  [Destory Actor after delay] -> Set Life Span (DestroyDelay)
```

One kill = one roll: `Die` opens with the `bIsDead` gate (`Enemies.md` §4.5), so
a corpse cannot re-roll twice. Nothing else in the shooting chain changes — a
bullet copies `Effect Class` when it spawns (`ProjectileShooting.md` 5.3) and
the fire gate reads `Can Fire` off the live effect (6.3) — so the switch is
visible on the next LMB, `Jammed` included (that shot then does nothing, §7).

| | |
|---|---|
| Trigger | `BP_EnemyBase::Die`, between `Clear Timer ("RecoverFromHit")` and the `Destory Actor after delay` box |
| Pool | `BP_Effect_Basic` · `BP_Effect_Ricochet` · `BP_Effect_Heavy` · `BP_Effect_Jammed` |
| Port | `BP_Player::Set Effect Class` — still the only writer of `Effect Class` |
| Transport | new `BPI_EffectUser` interface (`Structure.md` §9: no cross-pillar casts) |
| Roll | uniform over the pool, **minus** the effect that is live right now |

Coverage: every enemy that lets the base `Die` run. `BP_RockBase` (§6.2) and
`BP_Snail` (§6.3) override `Die` and call **Parent: Die**, so rock and snail
kills roll too. The Snail's *shell* phase is not a death and does not call `Die`
— it correctly does not roll.

Owner split (`Structure.md` §4): §2-§3 are pillar 3 (the gun decides what the
pool is), §1 and §4 are pillar 4 (the enemy only says "you killed me").

---

## 1. `Core/Interfaces/BPI_EffectUser`

| Step | Action |
|---|---|
| 1 | Content Browser → `Core/Interfaces/` → **right-click → Blueprint Interface** → name it `BPI_EffectUser` |
| 2 | **My Blueprint → Functions → +** → rename it to `Randomize Effect Class` — **no inputs, no outputs** |
| 3 | **Compile + Save** |

**No outputs = void = it is implemented as an Event** (`Structure.md` §9).
Build the function **before** adding the interface to any class: a class that
adds an interface while it is still function-less never picks later functions
up (`Structure.md` §9, "Creating an interface").

Press **`+` once**. A second click leaves an empty `NewFunction_0` in the asset
(the verifier reports it as `WARN … extra function graph`); it surfaces as a
bogus "New Function 0" event on every class that implements the interface.

The export strips spaces (`On Wall Hit` → `OnWallHit`), so the verifier looks
for `RandomizeEffectClass`.

---

## 2. `BP_Player` — the pool variable

Open `/Game/DontTrustTheLevels/Player/Blueprints/BP_Player`.

| Variable | Type | Instance Editable | Default |
|---|---|---|---|
| `Effect Classes` | **Array** of **Class Reference** → `BP_EffectBase` | ✓ | Basic, Ricochet, Heavy, Jammed |

| Step | Action |
|---|---|
| 1 | **My Blueprint → Variables → +** → `Effect Classes` |
| 2 | Variable type dropdown → **Class Reference** → parent class `BP_EffectBase` |
| 3 | Next to the type, tick the **array** grid icon (a `TArray<Class>` — the icon stays on) |
| 4 | Details → tick **Instance Editable** |
| 5 | **Compile**, then **Class Defaults** → Details → `Effect Classes` → `+` four times, pick `BP_Effect_Basic`, `BP_Effect_Ricochet`, `BP_Effect_Heavy`, `BP_Effect_Jammed` |
| 6 | **Compile + Save** |

The pool is data: drop `BP_Effect_Jammed` from the list if a kill should never
take the gun away, add a fifth effect later and §3 picks it up with no rewiring.
Do **not** leave the array empty (§7).

---

## 3. `BP_Player` — `Event Randomize Effect Class`

`Class Settings → Interfaces → Add → BPI_EffectUser` (the function must already
exist, §1). The void message shows up in **My Blueprint → Interfaces**; drag
**Event Randomize Effect Class** into the Event Graph.

| # | Node | Pins |
|---|---|---|
| 1 | **Event Randomize Effect Class** | — |
| 2 | **Get `Effect Classes`** | one get node, three array consumers (steps 3, 6, 11) |
| 3 | **Length** *(array)* | Array ← step 2 → int `N` |
| 4 | **Subtract** *(int)* | A ← step 3 · B = `1` → `N-1` |
| 5 | **Random Integer in Range** | Min = `0` · Max ← step 4 → `r` (**inclusive**: `0..N-1`) |
| 6 | **Find Item** *(array)* | Array ← step 2 · Item To Find ← **Get `Effect Class`** → `cur` (`-1` when the live effect is not in the pool) |
| 7 | **Equal (int)** | A ← step 5 · B ← step 6 → "rolled the one that is live" |
| 8 | **Add (int)** | A ← step 5 · B = `1` → `r+1` |
| 9 | **Percent (int)** | A ← step 8 · B ← step 3 → wraps `N` back to `0` |
| 10 | **Select** | **Condition** ← step 7 · **True** ← step 9 · **False** ← step 5 → index `i` |
| 11 | **Get (a copy)** | Array ← step 2 · **Index** ← step 10 → the class |
| 12 | **Set Effect Class** — the **function**, the one whose pin is `New Effect Class` (not the variable setter of the same name, `ProjectileShooting.md` 6.4) | **New Effect Class** ← step 11 |

Exec: `Event then → step 12 execute`. **Compile + Save.**

**Why this arithmetic.** `r` is uniform on `0..N-1`. If it lands on the effect
that is live right now, `+1` with a wrap (`Percent`) moves to the next one;
otherwise it is used as-is. Every effect other than the current one is reachable
exactly once, so the switch is uniform *and* always visible — no "kill did
nothing" 1-in-4. Two degenerate cases are safe: a one-entry pool keeps that one
entry (`(0+1) % 1 = 0`), and a live effect that is not in the pool (`cur = -1`)
just rolls normally.

`Random Integer in Range` includes **Max**, so Max is `N-1` (step 4), never
`N`: with `N` the wrap would be a no-op and `Get` could read past the array
(§7).

---

## 4. `BP_EnemyBase::Die` — the trigger

Open `/Game/DontTrustTheLevels/Enemies/Blueprints/BP_EnemyBase` → function
`Die` (`Enemies.md` §4.5). The end of it is:

```text
... Sprite -> Play ─then→ Clear Timer ("RecoverFromHit") ─then→ [Destory Actor after delay]
                                                                  Set Life Span (DestroyDelay)
```

`Clear Timer` sits in the `Die` graph itself (`fn K2_ClearTimer`), the box is the
collapsed `Destory Actor after delay` graph. That one wire is the insertion
point — it is exactly where `Enemies.md` §4.5 lists `[optional: score / sound /
spawn effect]`.

| Step | Action |
|---|---|
| 1 | **Delete only the wire** `Clear Timer ("RecoverFromHit").then -> Destory Actor after delay` (keep both nodes) |
| 2 | Add **Get Player Character** (Gameplay Statics) — **Player Index** = `0` |
| 3 | Drag off its return pin → search `Randomize Effect Class` → pick the **(Message)** node; **Target** auto-wires to the player character (a message node with a blank Target fails to compile, `Structure.md` §9) |
| 4 | Wire `Clear Timer.then → Randomize Effect Class.execute` and `Randomize Effect Class.then → Destory Actor after delay` |
| 5 | **Compile + Save** |

`Clear Timer ("RecoverFromHit")` must stay **before** the new chain: it kills the
0.2 s hit-recovery timer that would otherwise snap the death art back to idle
mid-`DestroyDelay` (`Enemies.md` §4.5).

**No `Does Implement Interface` gate on the enemy side.** The Message node
compiles to an internal *Cast To Interface* whose **cast-failed** pin is wired to
the node's `then` (`Engine/Source/Editor/BlueprintGraph/Private/K2Node_Message.cpp`,
4.27), so a pawn that does not implement `BPI_EffectUser` skips the call and
carries on to the corpse clean-up — no crash, no switch. The guard that matters
is on the player side: if `BP_Player` never implements the interface, nothing
ever switches, and §6 says so in one line.

**Why `Die` and not the `Kill` event.** `Kill` is the interface entry with the
0.05 s damage-frame guard (`Enemies.md` §4.3): it is deliberately ignored for
bullets that did not kill. `Die` is the single "this enemy is now dead" funnel
that every real death reaches — bullets, wall hits (Rhino), rock splits, snail
shell pops — and it is already `bIsDead`-gated.

---

## 5. PIE checklist

| # | Do | Expect |
|---|---|---|
| 1 | Kill a Slime/Bat with bullets | the gun's behaviour changes on the next LMB (see table below) |
| 2 | Press `2` (Ricochet), kill one enemy | the result is never Ricochet — the roll excludes the live effect |
| 3 | Kill eight enemies | all four effects turn up; no kill leaves the gun on the same class |
| 4 | Shoot a Snail | first hit pops the shell — **no switch** (`Die` is not called, `Enemies.md` §6.3); the next lethal hit switches |
| 5 | Kill a `BP_Rock1`/`BP_Rock2` | the split spawns children, then `Parent: Die` switches — once, not once per rock |
| 6 | Two bullets, one kill | one switch (the `bIsDead` gate at the top of `Die`) |
| 7 | Let an enemy fall in the pit | **no** switch — `BP_KillVolume` destroys the actor without `Kill`/`Die` (`Enemies.md` §2.3) |
| 8 | Trim the pool to two entries | the switch still alternates |

What each effect looks like (from `ProjectileShooting.md` Part 3):

| Class | Tell |
|---|---|
| `BP_Effect_Basic` | fast, straight, no bounce, 1 damage |
| `BP_Effect_Ricochet` | bounces up to 3 times and can kill the shooter on the return |
| `BP_Effect_Heavy` | slow, drops (gravity 1.0), 5 damage |
| `BP_Effect_Jammed` | LMB does **nothing** — the fire gate reads `Can Fire` off the live effect |

If a kill takes the gun away and nothing brings it back, that is `Jammed`
doing its job; debug keys `1`-`4` restore a class by hand.

---

## 6. Verify

```text
py -3 Scripts/_verify_effect_on_kill.py        # editor open, PIE stopped
py -3 Scripts/_verify_effect_on_kill.py --self-test   # parser only, offline
```

Live half: the interface asset exists, and `BP_Player`'s CDO carries the
`EffectClasses` array (count + the class in each slot). Offline half, from fresh
T3D exports in `Scripts/_kill_effect_export/`:

* `BPI_EffectUser.T3D` — function graph `RandomizeEffectClass`
* `BP_Player.T3D` — `ImplementedInterfaces` contains `BPI_EffectUser`; the
  `EffectClasses` array variable exists; the `Event RandomizeEffectClass` node
  exists; its exec chain reaches a **`SetEffectClass` call** and passes a
  `RandomIntegerInRange` + an array `Find`/`Get`
* `BP_EnemyBase.T3D` — in `Die`, `Clear Timer ("RecoverFromHit").then` runs into
  the `RandomizeEffectClass` **message** node, that node's `then` still reaches
  the `Destory Actor after delay` box, and the death chain around it is untouched
  (`bIsDead` gate first, `SetFlipbook(DeathFlipbook)`, `SetLifeSpan(DestroyDelay)`)

Regressions it also re-checks: the four `Effect_*` debug keys still call
`SetEffectClass` (the 18 Oct bug, `ProjectileShooting.md` 6.4). Unbuilt parts
report `PENDING`; a broken wire reports `FAIL`. Exit code 1 only on `FAIL`.

---

## 7. Pitfalls

| Symptom | Cause |
|---|---|
| Gun goes silent for good | `Effect Classes` is empty, or the index ran past the end (`Get` → None → `Set Effect Class(None)` → live effect destroyed, nothing spawned, fire gate reads `Can Fire` off None). Keep Max = `N-1` (§3 step 4) and the pool non-empty |
| `Jammed` still fires after a kill | the chain ends on the `Effect Class` **variable setter** instead of the `Set Effect Class` **function** — `Gun Effect` stays the old instance. The pin is the tell: `New Effect Class` = function, `Effect Class` = setter (`ProjectileShooting.md` 6.4) |
| Enemy corpse never disappears | the `Randomize Effect Class.then -> Destory Actor after delay` wire is missing — the box no longer runs |
| Kill does nothing at all | `BP_Player` does not implement `BPI_EffectUser`, or the interface was added before its function existed (remove + re-add it, `Structure.md` §9) |
| Two switches per kill | a second trigger was added (e.g. the same message in `BP_Projectile`'s kill branch). One trigger only |
| Compile error "must have a valid target" | the Message node was created from empty space — drag it off the `Get Player Character` return pin instead |

`Die` and `RefreshStateFlipbook` must stay **functions**, never custom events
(`Enemies.md` §3.3): children override them and call `Parent: Die`.

---

## 8. Why this shape (and the one alternative)

* **The pool lives on `BP_Player`.** `Effect Class` is the source of truth and
  instances are derived from it (`ProjectileShooting.md` Part 7, "why a class
  variable and not an instance"); the caller stays dumb — it says "re-roll",
  it does not need to know which effects exist.
* **Interface, not a cast.** The enemy is pillar 4, the gun is pillar 3;
  `Structure.md` §9 forbids naming `BP_Player` from another pillar. This is the
  first cross-pillar caller, so `BPI_EffectUser` is the five-minute interface
  that doc pre-authorized. Traps and pickups can reuse it with a fixed class
  later.
* **Alternative — bullet kills only.** If trap/contact/fall deaths must not
  switch the gun, skip §4 and call the same message from `BP_Projectile`'s
  killable branch (`ProjectileShooting.md` 5.5), where `Shooter` is already a
  `BP_Player` pin (same pillar — no interface needed at all). The trade: "every
  death" becomes "only my bullets", and the trigger is scattered across the
  weapons pillar instead of sitting in one enemy function.

**Rollback.** The pre-edit anchor is `e90faa3` (the 12 enemy packages) plus
`11cdd6a` (this card), so `git checkout -- Content/.../BP_EnemyBase.uasset` (and
the same for `BP_Player.uasset`) is a clean revert — check `git status` shows
neither file before you start, and commit the built version so the next revert
works too. Manual revert instead: rewire
`Clear Timer.then -> Destory Actor after delay`, delete the message + `Get Player
Character` nodes, delete the event and the `Effect Classes` variable, then remove
`BPI_EffectUser` from Class Settings and delete the interface asset.

