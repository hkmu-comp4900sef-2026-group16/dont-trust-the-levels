# Projectile shooting · build guide (BP_Projectile + effect port)

**Concept:** LMB fires a small bullet (`PistolAmmoSmall`, `SPR_PistolAmmoSmall`)
from the M92's muzzle, along the barrel — the gun already aims at the cursor
(GunAiming.md Part 5), so the bullet inherits `Gun`'s world rotation. The
bullet's **behavior is a swappable port**: the player holds one *effect class*
variable, every shot spawns a tiny effect actor from it, and the effect
answers two questions — *"can the gun fire?"* and *"what happens when the
bullet hits a wall?"* — through **data defaults** (`Can Fire`, `Damage`,
`Speed`, `Bounces`, `Gravity Scale`, `Can Hit Shooter`) plus **one interface
message** (`BPI_ProjectileEffect → On Wall Hit`). Switching between Basic /
Ricochet / Heavy / Jammed is a runtime class swap — **no graph rewiring,
ever**.

```text
BP_Player (gun side)                      BP_Projectile (bullet side)
  Effect Class  ── class var ─────────────→ Effect Class  (exposed on spawn)
  Gun Effect    ── ref ─┐                 Shooter        (exposed on spawn)
  Set Effect Class()  ←─ THE PORT          Effect         ── spawned from Effect Class
       ▲                                  BeginPlay:  velocity = forward x Effect.Speed
       │                                              IgnoreActorWhenMoving(Shooter, true)
       │                                              gravity scale = Effect.Gravity Scale
  any trigger: keys 1-4, traps,           OnComponentHit (Box):
  pickups, volumes → call this                  OtherActor == Shooter  → ignore ‡
  one function                                  implements BPI_Killable → Apply Point
       │                                        Damage(Effect.Damage) + Kill + Destroy
  Can Fire ← Gun Effect.Can Fire                else → Effect: "On Wall Hit" message
```

`‡` the shooter is skipped *while the bullet still ignores it*. `Bounce` lifts
that ignore when `Effect.Can Hit Shooter` is true (Ricochet), so a returning
ricochet is a legit kill — Part 5.4 / Part 8 item 8.

**Two kinds of work:**

| Work | Done by | Status (18 Oct 2026) |
|---|---|---|
| Import ammo art, create `T_PistolAmmoSmall_D` + `SPR_PistolAmmoSmall` | `Scripts/_make_shooting.py` (live editor) | ✅ done, idempotent — re-run any time |
| Create `BPI_ProjectileEffect`, `BP_EffectBase` + 4 children, `BP_Projectile` (empty shells) | `Scripts/_make_shooting.py` | ✅ done |
| Add `Fire` / `Effect_*` action mappings to `DefaultInput.ini` | `Scripts/_make_shooting.py` | ✅ done — **live in the running editor** |
| Add the `On Wall Hit` function to `BPI_ProjectileEffect` | **human**, editor UI | ✅ done (Part 2) |
| `BP_EffectBase` variables (`Can Fire`, `Damage`, `Speed`, `Bounces`, `My Projectile`) | **human**, editor UI | ✅ done (Part 3.1) |
| `BP_EffectBase` per-effect knobs (`Gravity Scale`, `Can Hit Shooter`) | **human**, editor UI | ✅ done (Part 3.1 — both variables added 18 Oct; the two base reads and all 8 child values PASS) |
| `BP_EffectBase` implements `BPI_ProjectileEffect` | **human**, editor UI | ✅ done (Part 3.2 — *Class Settings*, not Class Defaults) |
| `BP_EffectBase` `On Wall Hit` logic (Bounces decrement + `Bounce` call) | **human**, editor UI | ✅ done (Part 3.3 — 13 nodes / 24 wires, all three markers PASS) |
| Per-child default values | `Scripts/_make_shooting.py` re-run | ✅ 24/24 PASS — 6 per child (the 18 Oct re-run wrote the two new fields: Ricochet `CanHitShooter=true`, Heavy `GravityScale=1.0`) |
| `BP_Projectile` components + Details | **human**, editor UI | ✅ done (Part 5.1 — Box is the root, Extent `(20,50,20)`, presets `BlockAllDynamic` / `NoCollision`, Source Sprite `SPR_PistolAmmoSmall`, gravity 0.0, **Should Bounce ✓ / Bounciness 1.0 / Friction 0.0**; the two eyeball-only WARNs stay) |
| `BP_Projectile` variables (`Effect Class`, `Shooter`, `Effect`) | **human**, editor UI | ✅ done (Part 5.2) |
| `BP_Projectile` `Bounce` function | **human**, editor UI | ✅ done (Part 5.4 — 27 nodes with step 16's second `Ignore Actor When Moving`; read back from the 19 Oct 00:03 export) |
| `BP_Projectile` BeginPlay chain | **human**, editor UI | ✅ done (Part 5.3 — 17 nodes; step 7's `Set Projectile Gravity Scale` writes the component's own `ProjectileGravityScale` from the effect) |
| `BP_Projectile` `On Component Hit` graph | **human**, editor UI | ✅ done (Part 5.5 — 17 nodes / 26 wires; step 2b's `==` AND NOT gate feeds the shooter Branch's `Condition`) |
| `BP_Player` port + fire chain | **human**, editor UI | ✅ 6.1–6.4 built (saved 18 Oct 02:09; the verifier reads all four `Effect_*` keys PASS). Two nits left, both in Part 6 below |

**Resume here.** With the editor open, `py -3 Scripts/_verify_shooting.py` is
the ground truth for the scripted half *and* presence-checks the manual half
(effect CDO defaults, `BP_EffectBase` variables + graph markers, BP_Projectile
component *details* and variables + graph markers, BP_Player variables + graph
markers, and — since the 18 Oct PIE pass — the four `Effect_*` key chains and
the movement's bounce settings). The 19 Oct 00:03 run read **97 PASS · 0 FAIL ·
2 WARN · 0 PENDING**; the PIE fixes below took it to **104 PASS · 0 FAIL · 2
WARN · 0 PENDING**. The **19 Oct 00:41 run** (after the Projectile Movement fix
and a first attempt at the key fix) read **101 PASS · 1 FAIL · 2 WARN**:
`Should Bounce` / `Bounciness` / `Friction` PASS, but the four `Effect_*`
**event nodes were deleted along with the setters**, so no key fired at all (see
bug 3 below). After the key events were rebuilt the run read **102 PASS · 1
FAIL · 2 WARN** — the four key chains PASS again, the FAIL being the kill gate
(bug 4). **The 27 Oct run reads 105 PASS · 0 FAIL · 2 WARN · 0 PENDING**: the
`Interface` pin is set to `BPI_Killable`, 5.6's `Destroyed` hook is present as
the `Effect Clean Up` collapsed graph, and the verifier now expands collapsed
graphs and normalizes the `SetEffectClass` graph name. The extra PASS is the
5.6 chain (`ReceiveDestroyed` → `Effect Clean Up` → `Is Valid(Effect)` →
`Destroy Actor(Effect)`); PIE confirms the per-shot effect count stays flat.
The last four PASSes are the counted graph markers of the per-effect wiring:
the BeginPlay
gravity setter, the second `Ignore Actor When Moving` in `Bounce`, `NOT` on
`Can Hit Shooter`, and `Can Hit Shooter` read in both graphs.

**PIE pass (18 Oct) — two build bugs, both regression-checked now (plus one
self-inflicted regression from the first fix attempt):**

1. **`4` still fires.** The four `Effect_*` keys only *set the `Effect Class`
   variable*; they never call the `Set Effect Class` **function**, so `Gun
   Effect` keeps pointing at the Basic instance and the fire gate reads its
   stale `Can Fire = true`. The bullets still pick up the new class (the player
   passes `Effect Class` to the spawn), which is why `2`/`3` changed the bullet
   but `4` did not jam the gun. Fix: **Part 6.4** — each key's `Pressed` pin
   goes to the **call** node (`New Effect Class` pin), not the variable setter.
2. **Ricochet bullets freeze at the wall.** `Projectile Movement → Should
   Bounce` is **off**; on the first blocking hit `HandleImpact()` calls
   `StopSimulating()` (velocity 0, updated component detached) *after* the
   ComponentHit delegate, so `Bounce`'s `Set Velocity` is wiped a few lines
   later. The bullet never moves or hits again, so `Bounces` never reaches 0
   and the effect never destroys it. Fix: **Part 5.1** — **Should Bounce ✓**,
   **Bounciness 1.0**, **Friction 0.0**.
3. **`2`/`3`/`4` stopped switching** (19 Oct 00:41 — the first attempt at the
   fix above). Deleting the four setters took the four `InputAction` key events
   with them: EventGraph's `Nodes()` list no longer contains
   `K2Node_InputAction_3..6`, so `Pressed` never fires, `Effect Class` stays
   `BP_Effect_Basic`, `Gun Effect` is never replaced and every bullet keeps
   `Gravity Scale 0.0` — pressing `3` no longer drops. Fix: **Part 6.4** —
   right-click → `Effect_Heavy` (under *Action Events*) to get the event back,
   then `Pressed` → the `Set Effect Class` **call**. The verifier names it:
   `Effect_Heavy (event node deleted - it is only left in the transaction
   buffer)`.

4. **A ricochet bounces off the player instead of killing them** (same PIE
   run, after the keys worked — **fixed 19 Oct**). Gate 3 of the hit graph is
   built — `Does Implement Interface` → True → `Apply Point Damage` → `Kill` →
   `Destroy Actor` — but its **`Interface` pin was empty**. The stock pin
   defaults to *None*, and `Does Implement Interface(Other, None)` is **false
   for every actor**, so every hit took the False branch: the effect was told it
   hit a wall and `Bounces > 0` turned the return shot into one more bounce.
   Fix: **Part 5.5 step 3** — pick `BPI_Killable` in the pin's dropdown. The
   pin is set now (the export carries
   `DefaultObject=…BPI_Killable.BPI_Killable_C`), so the verifier's
   `Does Implement Interface has no Interface set ...` FAIL is gone.

5. **One effect actor was left behind per shot** (19 Oct PIE: "even when the
   bullets are gone there is an effect actor left"). `BeginPlay` spawns a fresh
   `BP_Effect_*` actor for every bullet (5.3 steps 2–3) and **nothing destroyed
   it** — the hit graph kills the bullet, and `BP_EffectBase` is component-less,
   so the leftovers were invisible in the viewport but piled up in the World
   Outliner, each still holding a hard `MyProjectile` reference to the dead
   projectile. Fix: **Part 5.6** — `Event Destroyed` → `Branch` (`Is Valid`,
   Input ← `Get Effect`) → True → `Destroy Actor` (Target ← `Get Effect`). The
   current graph implements this as the `Effect Clean Up` collapsed graph; the
   27 Oct verifier run reaches it through the composite and PASSes, and PIE shows
   no actor increase after shooting.

The build half is therefore **closed** — the Part 8 PIE checklist, not more
nodes.
**Part 6 is finished** once the four key events exist again and each `Pressed`
chain ends on the `Set Effect Class` **call** — the verifier follows each chain
and FAILs a missing or variable-only one (`PASS  the four debug keys call Set
Effect Class (the function)` is the gate). The built half is re-read node by node
in panel **6.0b** of `Scripts/player_graph.html` (the boards for every step are
in the same page).
Both WARNs are values this Python build cannot read
at all — the sprite *asset*'s baked collision (Part 1) and the Box's
*Simulation Generates Hit Events* flag (Part 5.1) — so they are eyeball-only and
can never PASS. The Part 8 PIE checklist
needs no restart — the verifier already reads the five mappings as **LIVE** in
the running session (see *Input mappings* below).
With the editor **closed** the live half cannot run at all — the T3D re-export
happens inside the editor, so the offline half would only re-check whatever the
last live run left on disk. A shorter run is not a better run: the first line of
the output must read `success: True`, and `T3D exports: 8/8 written` proves the
markers were read from a fresh export.
`Scripts/_check_markers.py` re-checks the T3D markers offline, with controls on
`BP_Player`'s hand-wired events, whenever a marker looks wrong.
`Scripts/_check_pin_links.py` flags input pins that the export says carry **two**
wires (an undo/duplicate leftover: the extra source is an orphan node or a
mirror of the same value, and the graph still compiles) — BP_Projectile showed
2, BP_Player 2 older ones. The two findings are drawn on their own graphs in
`Scripts/cleanup_graphs.html` (red dashes = delete, nothing else marked).
`Scripts/_dump_graph.py <t3d> <out> <name>` reads a finished graph out of an
export node by node, pins and links included — that is how Part 5.5's 22 wires
were verified, since a marker only proves that a node exists.
`Scripts/_inspect_projectile.py` dumps every Part 5.1 value (root, mobility,
extent, presets, source sprite, gravity scale) off a throwaway spawn whenever a
verifier line needs explaining.

Per Structure.md §11: Python handles *assets and properties*; humans handle
*graphs and components*. `unreal.BlueprintEditorLibrary` is not exposed in
this project's Python (verified live), so Parts 2–6 are manual by design.
Python *also cannot construct `unreal.Key` values* in this build (verified
live — opaque struct), which is why the script writes `DefaultInput.ini`
directly instead of calling `add_action_mapping`.

**Ownership:** `Weapons/` is pillar 3's folder (Structure.md §4) — the effect
and projectile assets live there. `BPI_ProjectileEffect` lives in
`Core/Interfaces/` with `BPI_Killable` (shared). `BP_Player` is pillar 1's
asset: one owner at a time, commit with the editor closed.

---

## Part 1 — Assets (scripted, done)

`Assets/PixelBullets/PistolAmmoSmall.png` — 16×16 px cell, the bullet art
(~6×4 px) sits roughly at cell center, art default points **right** (same
convention as the M92 and the character frames).

Facts, read back live from the editor (`Scripts/_make_shooting.py`
re-asserts them on every run):

| Asset | Path | Settings |
|---|---|---|
| `T_PistolAmmoSmall_D` | `/Game/DontTrustTheLevels/Weapons/Textures/` | Nearest / TC_EditorIcon / No mipmaps / sRGB — Structure.md §10.2 pixel-art rules |
| `SPR_PistolAmmoSmall` | `/Game/DontTrustTheLevels/Weapons/Sprites/` | source `T_PistolAmmoSmall_D`, source 16×16, PPU **0.16**, pivot **center (8,8)** |
| `BPI_ProjectileEffect` | `/Game/DontTrustTheLevels/Core/Interfaces/` | ✅ `OnWallHit(HitResult Hit)` added (Part 2) — present in its T3D export |
| `BP_EffectBase` | `/Game/DontTrustTheLevels/Weapons/Blueprints/` | Actor, empty shell — Part 3 |
| `BP_Effect_Basic` / `_Ricochet` / `_Heavy` / `_Jammed` | `.../Weapons/Blueprints/` | children of `BP_EffectBase` — Part 4 sets their defaults |
| `BP_Projectile` | `.../Weapons/Blueprints/` | Actor, empty shell — Part 5 |

- **PPU 0.16** matches every player frame and the M92 (16 px art = 100uu), so
  the bullet keeps the project's pixel scale.
- **Pivot is center** — the sprite's rotation origin is the bullet's middle,
  which is what the ricochet re-orientation expects.
- ⚠️ Python could not disable the sprite's baked collision — the
  `collision_source` property is not exposed on `PaperSprite` in this
  Python build (live probe: `Failed to find property 'collision_source'`).
  The projectile's **Box component** does all collision, so Part 5 sets
  the Sprite *component* to `NoCollision` — that override is required, not
  optional. `Scripts/_verify_shooting.py` reports a standing **WARN** for
  this on every run; it can never PASS in this build. The *component's*
  preset **is** readable (`get_collision_profile_name()`, see Part 5.1), so
  the assertion that matters ("Sprite preset = `NoCollision`") is machine
  checked — this WARN is cosmetic.

### Input mappings (scripted into `Config/DefaultInput.ini`)

| Action | Key | Consumed by |
|---|---|---|
| `Fire` | Left Mouse Button | `BP_Player` — Part 6 |
| `Effect_Basic` | 1 | `BP_Player` — Part 6 debug keys |
| `Effect_Ricochet` | 2 | ″ |
| `Effect_Heavy` | 3 | ″ |
| `Effect_Jammed` | 4 | ″ |

⚠️ **The running editor does not re-read `DefaultInput.ini`** (input settings
live in memory, and `load_key_mappings` is not exposed) — the actions appear in
**Project Settings → Input** and in a Blueprint's *Action Events* list from the
**next editor start** after the file changes. That has already happened: the
ini was written 12 Oct 21:05 and the current session started 17 Oct 22:28, so
`Scripts/_verify_shooting.py` reads all five as **LIVE** —

```text
live input actions: Jump, Dash, Fire, Effect_Basic, Effect_Ricochet,
                    Effect_Heavy, Effect_Jammed
input action Fire: LIVE      (…each of the four Effect_* keys: LIVE)
```

— so **Part 6 can be built in this session** (`Fire` and the four
`Effect_*` entries are in the *Action Events* submenu right now) and the Part 8
PIE checklist needs no restart. Restart only if the ini is edited again.

---

## Part 2 — BPI_ProjectileEffect: the message (human, ~2 minutes)

1. Open `/Game/DontTrustTheLevels/Core/Interfaces/BPI_ProjectileEffect`.
2. In **My Blueprint → Functions**, click the **+** (**New Function**).
3. Rename it to `OnWallHit` (details: **Display Name** should show
   `On Wall Hit` — friendly spacing only; the member name is `OnWallHit`).
4. With the function entry node selected, in the function's graph Details
   panel find **Inputs** and add one parameter:
   - Name: `Hit` — Type: **HitResult** (struct).
5. **Compile + Save** (the check icon, then the save icon).

This is a *message*, not an implementation: like `BPI_Killable`'s single
`Kill` function, this interface declares the contract and nothing else. The
bullet will *send* `On Wall Hit` to its effect whenever it hits something
that is neither the shooter nor a killable actor; the effect instance
decides what to do about it (bounce, die, spawn debris, later: poison,
teleport, …).

> Convention check (matches BPI_Killable in the same folder): one function,
> no return values, structs passed by value, no side effects in the
> interface itself.

---

## Part 3 — BP_EffectBase: the port's brain (human, ~10 minutes)

`BP_EffectBase` is a plain **Actor** with **no components** (it never
renders, never collides; it is a per-shot data holder that owns hit
policy). Per-shot instances are spawned by `BP_Projectile`'s BeginPlay.

**Status:** ✅ 3.1 + 3.2 + 3.3 all done. All seven variables are live — the
verifier reads `MyProjectile`, `GravityScale` and `CanHitShooter` on the base
plus all 24 child values; 3.2 the export carries `ImplementedInterfaces` and the
verifier reads `PASS implements BPI_ProjectileEffect`; 3.3 the `On Wall Hit`
event node, the `Bounces` decrement and the `Bounce` call are all in the
EventGraph's 13 nodes / 24 wires, and the verifier's three graph markers PASS.
The two per-effect rows were data-only — nothing else in this file changed —
and Parts 4–5 now read them.

### 3.1 Variables (My Blueprint → Variables → +)

| Variable | Type | Instance Editable | Default | Why |
|---|---|---|---|---|
| `Can Fire` | Boolean | ✓ | `true` | the trigger gate — `BP_Player` reads this before spawning a bullet |
| `Damage` | Float | ✓ | `1.0` | fed to **Apply Point Damage** on killable hits |
| `Speed` | Float | ✓ | `3000.0` | bullet velocity magnitude (uu/s; player walk ≈ 600, dash ≈ 1400) |
| `Bounces` | Integer | ✓ | `0` | remaining ricochets, decremented per wall hit |
| `Gravity Scale` | Float | ✓ | `0.0` | how hard gravity pulls *this* effect's bullet: `0.0` = dead straight (Basic / Ricochet / Jammed), `1.0` = world gravity, so **Heavy visibly arcs**. BeginPlay copies it into the bullet's `Projectile Movement → Projectile Gravity Scale` (Part 5.3 step 7) |
| `Can Hit Shooter` | Boolean | ✓ | `false` | may this effect's *bounced* bullet stop ignoring the player who fired it? `false` = never (Basic / Heavy / Jammed), `true` = **Ricochet**, so a return shot is a legit kill. Read twice: in `Bounce` (Part 5.4 step 16) and in the hit graph's second gate (Part 5.5 step 2b) |
| `My Projectile` | Object → `BP_Projectile` | ✗ | — | runtime back-reference the projectile sets in its BeginPlay, used to command the bullet (bounce / destroy) |

Both new rows are plain **data** — no new interface message and no per-effect
graph. The bullet already holds the effect reference, so the values reach it
through the same `Effect` get it uses for `Speed` and `Damage`; a brand-new
child inherits `0.0` / `false` and behaves exactly like Basic until you type a
number or tick the box (Part 4).

### 3.2 Implement the interface

**Status: ✅ done (17 Oct 2026).** The live export contains
`ImplementedInterfaces(0)=(Interface=BlueprintGeneratedClass'…/BPI_ProjectileEffect.BPI_ProjectileEffect_C')`
and `Scripts/_verify_shooting.py` reports `PASS implements BPI_ProjectileEffect`.
**Compile** is what the verifier sees (it exports in memory); **Ctrl+S** is
still what puts it on disk — save it before moving on.

> **The button is `Class Settings`, NOT `Class Defaults`.** The two sit next to
> each other in the 4.27 toolbar and only one has the category. Verified in the
> engine source — `SBlueprintEditorToolbar.cpp` registers
> `EditGlobalOptions` labeled **"Class Settings — Edit Class Settings
> (Previously known as Blueprint Props)"** alongside `EditClassDefaults`
> labeled **"Class Defaults — Edit the initial values of your class"**, and the
> `Interfaces` category is added in
> `FBlueprintGlobalOptionsDetails::CustomizeDetails` (i.e. the Class
> **Settings** panel, `BlueprintDetailsCustomization.cpp`). `Class Defaults`
> only shows the CDO's variable values; **no Interfaces category exists
> there**. The `Defaults` mode button (tooltip *"Switches to Class Defaults
> Mode"*) is the same dead end.

1. **Open `BP_EffectBase` in the Blueprint editor** — double-click the asset
   in the Content Browser — or let the script open it for you:
   `py -3 Scripts/_open_asset.py BP_EffectBase` (also opens
   `BPI_ProjectileEffect`; graph editing is *not* scriptable in this build —
   probed in `Scripts/_probe_graph_api.py` — so this only puts the window on
   screen).
2. In that tab's toolbar, click **`Class Settings`** — the button immediately
   **left of** `Class Defaults` (hover both: *"Edit Class Settings (Previously
   known as Blueprint Props)"* is the right one, *"Edit the initial values of
   your class"* is the trap).
3. The **Details** panel on the right now shows the blueprint's Class
   Settings: **Class Options** (parent class) first, then the **Interfaces**
   category. Its row is titled **Implemented Interfaces** — reading **"No
   Interfaces"** while empty — with an **`Add`** dropdown below the list.
4. **`Add`** → pick **`BPI_ProjectileEffect`**.
5. **Compile**. `My Blueprint` gains an `Interfaces` section listing
   **On Wall Hit** — drag it into the EventGraph when you wire 3.3 below.

A mis-pick is one click to undo: each entry in that list carries a clear
(`x`) button (`MakeClearButton` → `OnRemoveInterface`).

### 3.3 Event graph: `Event On Wall Hit`

Drag **On Wall Hit** from My Blueprint into the **EventGraph** — this
creates the interface event node (entry point) with the `Hit` parameter.

> **What implementing the interface already did — and what it did *not*.** It
> made the editor generate an `OnWallHit` **stub graph** in `BP_EffectBase`
> (`EdGraph "OnWallHit"`: `K2Node_FunctionEntry(OnWallHit, Hit)` →
> `K2Node_SetVariableOnPersistentFrame` → `K2Node_CallFunction
> (ExecuteUbergraph_BP_EffectBase)`). That is compiler plumbing that forwards
> into the ubergraph: it holds **no logic**, and it is *not* the event node.
> The EventGraph still contains only the three disabled creation-time
> placeholders (BeginPlay / ActorBeginOverlap / Tick), so `On Wall Hit` really
> does still have to be dragged in. The verifier tells the two apart by the
> member reference — stub graphs carry `FunctionReference=` +
> `CustomGeneratedFunctionName=`, a placed event node carries `EventReference=`
> (checked against `BP_Player`'s wired `OnLanded` / `ReceiveTick`, which have
> both). Re-run `Scripts/_check_markers.py` to see that split offline.

Wire it:

> **One ordering trap: the `Bounce` call node needs Part 5.4 first.** A call
> node can only target a function that already exists, and `Bounce` is a
> function you add to `BP_Projectile` in Part 5.4. So either build the Branch /
> `Bounces − 1` / `Destroy Actor` half now and drop the `Bounce` call in after
> 5.4, or work in the order **5.1 → 5.2 → 5.4 → back here → 5.3 → 5.5 → 6**
> (Part 5's own order already puts 5.4 before 5.3). Everything else on this
> table needs nothing from Part 5.

| Node | Pins |
|---|---|
| `Event On Wall Hit` | `Hit` (HitResult) |
| `>` **Integer** | A ← `Bounces` (variable get) · B = `0` → **Condition** of Branch |
| **Branch** | **True** = bullet bounces · **False** = bullet dies |
| **True path:** `Integer − Integer` | A ← `Bounces` · B = `1` |
| `Set Bounces` | value ← the subtract · (self = the effect) |
| `Get My Projectile` | → **Target** of `Bounce` call |
| **`Bounce`** *(function message call on BP_Projectile — built in Part 5.4)* | **Wall Normal** ← `Break Hit Result` (input `Hit`) → **Normal** output |
| **False path:** `Get My Projectile` | → **Target** of `Destroy Actor` |

So: `Event On Wall Hit` → Branch(`Bounces > 0`) — True: decrement `Bounces`,
then tell the projectile to `Bounce` with the wall normal; False: `Destroy
Actor` on the projectile.

Note that the effect commands the *bullet*, never the level: single
direction of authority (projectile → effect → projectile), which keeps every
future effect a copy-paste of this file.

---

## Part 4 — The four effects (defaults, mostly scripted)

Each child is **only a row in Class Defaults** — that is the entire
"strategy". **Status: ✅ 24/24 (18 Oct) — 6 values × 4 children. The original
four were scripted on 17 Oct; once Part 3.1 compiled the two new variables onto
`BP_EffectBase`, a plain re-run wrote `GravityScale` / `CanHitShooter` too and
all 24 values read back from the CDOs. (While the variables were still missing
the verifier said `PENDING BP_Effect_Basic.GravityScale: variable not added yet
(doc Part 3)` — the expected state then, not a failure.)**
Re-run any time (idempotent):

```
py -3 Scripts/_make_shooting.py
```

(the script is idempotent; it finds the new variables and sets all 24 values —
6 per child). Target values — verify by opening each child's **Class Defaults**,
or in the editor with `py -3 Scripts/_verify_shooting.py`:

| Blueprint | Can Fire | Damage | Speed | Bounces | Gravity Scale | Can Hit Shooter | Reads as |
|---|---|---|---|---|---|---|---|
| `BP_Effect_Basic` | true | 1.0 | 3000 | 0 | 0.0 | false | the starting pistol |
| `BP_Effect_Ricochet` | true | 1.0 | 3000 | **3** | 0.0 | **true** | pinball rounds — and they can come back at you |
| `BP_Effect_Heavy` | true | **5.0** | **2200** | 0 | **1.0** | false | slow, lethal, drops while it flies |
| `BP_Effect_Jammed` | **false** | 1.0 | 3000 | 0 | 0.0 | false | click — nothing |

If you prefer by hand: open each child, **Class Defaults**, type the six
values (four numbers, one number, one tick), Compile + Save — identical
result.

---

## Part 5 — BP_Projectile: the bullet (human, ~25 minutes)

**Status: ✅ built (19 Oct 2026; 5.6 verified 27 Oct)** — 5.1 the component
Details, 5.2 the three variables, 5.3 the BeginPlay chain, 5.4 the `Bounce`
function, 5.5 the hit and 5.6 the `Destroyed` cleanup are all in the export
(the kill gate's `Interface` pin is set to `BPI_Killable`), and
`_verify_shooting.py` reports **105 PASS · 0 FAIL · 2 WARN**. The 5.6 hook is
the `Effect Clean Up` collapsed graph on `Event Destroyed`; the verifier expands
it and PASSes `ReceiveDestroyed` → `Is Valid(Effect)` → `Destroy Actor(Effect)`
(97 PASS before the 18 Oct fixes, the PIE pass found Should Bounce off, which is
why ricochet bullets froze at the wall) with all four per-effect markers among
them. The three additions this port
needed are in: **step 7** of 5.3 (`Set Projectile Gravity Scale`, read from the
effect), **step 16** of 5.4 (lift the shooter ignore in `Bounce`) and **step 2b**
of 5.5 (the `Can Hit Shooter` gate) — the boards number them 17 / 21, 27 / 35
and 17 / 26 nodes / wires, and the wires read back from the 19 Oct 00:03 export
match.
`Scripts/edit_graphs.html` has exactly those three boards for a rebuild;
`Scripts/shooting_graph.html` and `Scripts/hit_graph.html` keep the older,
fuller versions.

Two cosmetic leftovers, both from the same export via
`Scripts/_check_pin_links.py`: BeginPlay's `Ignore Actor When Moving` had a
second `execute` wire from a stray, exec-less `Set Projectile Gravity Scale`
(at ~1088,64 — it never runs, but it sits in the chain), and `Bounce`'s
`Ignore Actor When Moving` target had two wires (`Box` and `Get Updated
Primitive`, the same component). `Scripts/cleanup_graphs.html` draws both on
the real boards — the node and the wire to delete in red dashes, nothing else
marked. **The 19 Oct re-export reads `0 duplicate input link(s)`** — the
in-editor cleanup is done in memory, so the page can be ignored; just make
sure the asset is saved (`Ctrl+S`) before closing.

Open `/Game/DontTrustTheLevels/Weapons/Blueprints/BP_Projectile`.

### 5.1 Components (Components panel → Add)

**Full names.** Column 1 is the exact **Add ▾** entry — `Box Collision` (that
is one entry; there is no "Collision Box"), `Paper Sprite`, `Projectile
Movement`. Column 2 is the **node name** in the tree, which is what Parts
5.3–5.5 refer to. Adding a component already names the node after its class
with the `Component` suffix stripped
(`FComponentEditorUtils::GenerateValidVariableName`), so `Box` and
`ProjectileMovement` normally need no rename — only the sprite's automatic
`PaperSprite` → `Sprite`.

| # | Add ▾ entry (full name) | Node name | Details |
|---|---|---|---|
| 1 | **Box Collision** (search "Box") | `Box` | becomes the root. **Mobility: Movable**. **Box Extent (20, 50, 20)**. **Collision Presets: BlockAllDynamic**. **Simulation Generates Hit Events: ✓** (needed for the hit event). |
| 2 | **Paper Sprite** | `Sprite` | child of `Box`. **Source Sprite: `SPR_PistolAmmoSmall`**. **Collision Presets: `NoCollision`** ← required, the Box does collision (python could not fix this at asset level — see Part 1). Location (0,0,0), Rotation (0,0,0). Mobility: Movable. |
| 3 | **Projectile Movement** (search "Projectile") | `ProjectileMovement` | not attached to anything (it is a plain actor component, not a scene one) — it drives the actor's **root**. **Projectile Gravity Scale: 0.0** ← the component stays at zero; the *effect* decides per shot and BeginPlay copies `Effect.Gravity Scale` in (5.3 step 7). If you type anything else here, every effect inherits it as a baseline. **Should Bounce: ✓ on**, **Bounciness: 1.0**, **Friction: 0.0** ← **required**: with Should Bounce off, the first blocking hit calls `StopSimulating()` (`Velocity = 0`, the updated component is detached) *after* the hit delegate has run, so `Bounce`'s `Set Velocity` is wiped and the bullet freezes at the wall forever (the 18 Oct PIE pass: "ricochet bullets stick and never disappear"). The custom `Bounce` (5.4) already computed the reflection; `Bounciness 1.0` / `Friction 0.0` keep the engine's own fallback bounce a pure reflection instead of the 0.6 / 0.2 defaults. **Initial Speed / Max Speed** stay 0 (BeginPlay sets **Velocity** directly, step 5 of 5.3). |

The Should Bounce / Bounciness / Friction fix above is drawn, with the three
values highlighted, in `Scripts/fix_pie_bugs.html` (board *5.1*).

Expected tree once 5.1 is finished (the Components panel shows it parent →
child):

```
Box                   <- Box Collision, root, Movable, Box Extent (20, 50, 20)
└── Sprite            <- Paper Sprite, NoCollision, Source Sprite set
ProjectileMovement    <- not attached; drives the ROOT (see the root trap below)
```

`Default Scene Root` and the `Billboard` under it are gone by then — both are
explained below.

Why the tall Box (`Y extent 50`): gameplay is a 2D plane, but collision
volumes are 3D. The gun sits at `Y ≈ +20` in front of the level geometry
(GunAiming.md Part 5 offsets); a 100uu-deep box guarantees overlap with any
wall/floor collision depth so hits register on the first frame. It blocks
*along* the shot the same as a small box — `X/Z extents 20` ≈ the art.

**Root trap — silent, nothing logged.** `Box` must end up as the **root**
component: drag it onto `Default Scene Root` in the Components tree so that
`Default Scene Root` disappears and `Box` is promoted. Why it matters:
`Projectile Movement` never moves itself — `UMovementComponent` registers its
owner's **root** as `Updated Component` (`MovementComponent.cpp:117-124`,
`bAutoRegisterUpdatedComponent` defaults true) and the projectile then sweeps
*that* component on every step (`bSweepCollision` default true —
`ProjectileMovementComponent.cpp:23, 213/219/369`). A `Default Scene Root` has no
collision shape, so while `Box` is merely a child the bullet flies straight
through walls without stopping (and `Box`'s **On Component Hit**, Part 5.3,
never fires). The verifier names this case:
`PENDING … Box Collision is the ROOT component`.

**The extra `Billboard` in the tree is engine furniture, not a stray
component.** A `Default Scene Root` is created with `bVisualizeComponent =
true`, and `USceneComponent::OnRegister` (`SceneComponent.cpp:696`) then adds a
transient `Billboard` child carrying the `/Engine/EditorResources/EmptyActor`
texture — but only when `!GetWorld()->IsGameWorld()`, i.e. **editor only**
(`Hidden in Game` = true, `RF_Transient`). It vanishes by itself as soon as
`Default Scene Root` is gone, which is the same edit as the root trap above.
Control experiment: the untouched `BP_Effect_Basic` has one too
(`Scripts/_probe_billboard.py`).

**Mobility warning:** leaving the root **Static** makes `Projectile
Movement` unable to move it, with no obvious log. Set **Box** and
**Sprite** (the two primitive components) Movable before wiring anything.

**Read-back:** `py -3 Scripts/_inspect_projectile.py` (read-only, editor open)
spawns `BP_Projectile` far from the level, prints each component with its
parent, mobility, extent, collision preset, source sprite and gravity scale,
then destroys it. The same values are asserted by `Scripts/_verify_shooting.py`.
Collision presets are read with `get_collision_profile_name()` — the
`collision_profile_name` *editor property* raises "Failed to find property" in
this build, so that call is the only route. **Simulation Generates Hit Events**
has no readable route at all → that one stays an eyeball-only WARN.

### 5.2 Variables (My Blueprint → Variables → +)

| Variable | Type | Instance Editable | Expose on Spawn | Default | Why |
|---|---|---|---|---|---|
| `Effect Class` | **Class Reference** → Parent `BP_EffectBase` | ✓ | ✓ | `BP_Effect_Basic` | the effect the bullet uses — the player passes it per shot |
| `Effect` | Object → `BP_EffectBase` | ✗ | ✗ | — | runtime instance spawned in BeginPlay |
| `Shooter` | Object → **Actor** | ✓ | ✓ | — | who fired — used to ignore self-collision |

**Type picker for `Effect Class`:** click the type dropdown in the variable
Details, choose **Class Reference**, then pick the **Parent Class**
`BP_EffectBase`. Do **not** pick Actor as the parent — the point of the port
is type safety: the bullet can only ever hold a `BP_EffectBase`-derived
class.

### 5.3 Event graph — BeginPlay chain

One straight exec chain, no branches:

| Step | Node | Pins |
|---|---|---|
| 1 | `Event BeginPlay` | → exec → 2 |
| 2 | **Spawn Actor from Class** | **Class** ← `Get Effect Class` (variable) · **Spawn Transform** ← `Get Actor Transform` (self) · **Collision Handling Override** = `Always Spawn, Ignore Collisions` · **Return Value** → New Effect pin of 3 |
| 3 | **Set Effect** (variable set) | New Effect ← spawn's Return Value |
| 4 | **Set My Projectile** *(function on the effect, not on self)* | **Target** ← `Get Effect` (variable) · **My Projectile** ← **Get a reference to self** |
| 5 | **Set Velocity** *(property setter on the ProjectileMovement component)* | **Target** ← `ProjectileMovement` (component get) · **New Velocity** ← node 5b |
| 5b | **Multiply** *(Vector × Float)* | A ← `Get Actor Forward Vector` (self) · B ← node 5c |
| 5c | **Get Speed** *(property get on the effect)* | **Target** ← `Get Effect` (variable) |
| 6 | **Ignore Actor When Moving** | **Target** ← **Get Updated Primitive** dragged off `ProjectileMovement` (the pin is a *Primitive* pin, so the component itself will not connect — the component's `UpdatedPrimitive` is the Box) · **Actor** ← `Get Shooter` · **bShouldIgnore** = `true` (hard-coded here: the bullet must always survive its own muzzle) |
| 7 | **`Set Projectile Gravity Scale`** *(property setter on the ProjectileMovement component — the pin really is `ProjectileGravityScale`)* | **Target** ← **`Get ProjectileMovement`** (component get on self) · **Projectile Gravity Scale** ← **`Get Gravity Scale`** *(variable get on the effect, Target ← **`Get Effect`**)*. **Append after step 6** (its `then` pin is free). This is the only gravity writer: `0.0` = straight (Basic / Ricochet / Jammed), `1.0` = world gravity (Heavy). There is **no** plain "Set Gravity Scale" to pick: 4.27's `UMovementComponent` has no `GravityScale`, and the projectile only applies gravity when `ProjectileGravityScale != 0` (`ShouldApplyGravity()` gates `GetGravityZ()`, which then multiplies by it). |

So: BeginPlay → spawn effect → remember it → tell it who I am → velocity =
forward × effect's Speed → ignore the shooter → copy the effect's gravity.

> **Which gravity node? `Set Projectile Gravity Scale`.** The component's
> property is `ProjectileGravityScale` (Details: **Projectile Gravity Scale** —
> the one Part 5.1 leaves at `0.0`), so the setter is titled **Set Projectile
> Gravity Scale** and its value pin is labelled **Projectile Gravity Scale**,
> *not* "Gravity Scale". The number itself comes from **Get Gravity Scale** on
> the *effect* (`BP_EffectBase`), whose Target is the `Effect` variable — that
> node keeps the shorter title because the effect's variable is called
> `GravityScale`. Rule of thumb: the node whose **Target** is `ProjectileMovement`
> must say **Projectile**; the node whose **Target** is the effect must not.
> Dragging the effect variable and picking "Get Gravity Scale" gives the value
> node; if the context menu on the component offers only "Get Projectile Gravity
> Scale", you are on the component and need the **Set** variant.

Why a fresh instance per shot (not a shared one): every ricochet bullet
must count **its own** `Bounces` down from its effect's default. Two
ricochet bullets sharing one effect would steal each other's bounces. The
cost is one tiny actor per shot — negligible at pistol fire rates, and it
keeps the design stateless anywhere else.

### 5.4 Function — `Bounce` (My Blueprint → Functions → + → `Bounce`)

Input: `Wall Normal` (Vector). This runs when the effect says "bounce", and
it is also where the **owner policy** is applied (step 16) — the only moment
the bullet knows it has left the muzzle and is at a wall:

| Step | Node | Pins |
|---|---|---|
| 1 | **Get Velocity** *(property get on ProjectileMovement — read the component's `Velocity`, **not** `Get Owner → Get Velocity` on the actor)* | Return Value → **Vector** of 2 |
| 2 | **Break Vector** | X, Y, Z of current velocity |
| 3 | **Break Vector** *(of the `Wall Normal` input)* | X and Z of the input parameter |
| 4 | **>** (float) | A ← **Absolute** (Wall Normal X) · B ← **Absolute** (Wall Normal Z) → **Condition** of Branch |
| 5 | **Branch** | on node 4 |
| 6 | **True — vertical wall, flip X:** **Multiply** (float) | A ← velocity X · B = `-1` |
| 7 | **False — floor/ceiling, flip Z:** **Multiply** (float) | A ← velocity Z · B = `-1` |
| 8 | **Make Vector** | True: (flipped X, `0`, original Z) · False: (original X, `0`, flipped Z) |
| 9 | **Set Velocity** (property setter) | Target ← `ProjectileMovement` · New Velocity ← node 8 |
| 10 | **Multiply** (float) | A ← node 8's Z · B = `-1` ("negative Vz") |
| 11 | **Atan2 (degrees)** | **Y** ← node 10 · **X** ← **Absolute** (node 8's X) → **Pitch** |
| 12 | **<** (float) | A ← node 8's X · B = `0` → condition of Select |
| 13 | **Select** (Integer) | condition ← node 12 · **Pick A** = `180` · **Pick B** = `0` → **Yaw** (left-facing when X is negative) |
| 14 | **Make Rotator** | Pitch ← node 11 · Yaw ← node 13 · Roll = `0` |
| 15 | **`SetActorRotation`** (self — the node title really is one word in 4.27: `K2_SetActorRotation` ships `meta=(DisplayName="SetActorRotation")`; typing "Set Actor Rotation" in the palette still finds it) | `execute` ← `Set Velocity` · **New Rotation** ← node 14 · `bTeleportPhysics` left `false` · **`then` unconnected** |
| 16 | **`Ignore Actor When Moving`** (no DisplayName meta, so the camel-case split gives the spaced title you see) | **Target** ← **`Get Updated Primitive`** off **`Get ProjectileMovement`** · **Actor** ← **`Get Shooter`** · **bShouldIgnore** ← **`NOT Boolean`** of **`Get Can Hit Shooter`** (Target ← **`Get Effect`**) · **append after node 15** — `SetActorRotation`'s `then` pin is free, so nothing already built gets rewired |

> **First-tick trap — never read the actor's velocity.** `Get Owner → Get
> Velocity` calls `AActor::GetVelocity()`, which returns the root
> component's `ComponentVelocity`. BeginPlay writes `ProjectileMovement`'s
> `Velocity` directly, and `ComponentVelocity` is only synchronised at the
> **end** of the movement component's first tick. A point-blank downward
> shot hits the floor *inside that first tick*, so `Bounce` reflects
> `(0,0,0)`, `Set Velocity` writes zero, and `HandleImpact` calls
> `StopSimulating()`: the bullet freezes on the floor. Drag **Get Velocity**
> off `ProjectileMovement` (the `Velocity` property get) and feed the
> velocity `Break Vector`'s `InVec` with it — that is the 26 Oct
> "bouncing bullet sticks on the ground" fix. The verifier FAILs the actor
> shape with `Bounce reads Actor GetVelocity`.

Step 16 is the **owner policy**, and this is the only safe place for it.
BeginPlay's ignore (5.3 step 6) is hard-coded `true` because the Box extends
50uu *behind* the spawn point: the bullet starts inside the player's capsule,
so lifting the ignore at spawn would kill the shooter on frame 1. By the time
`Bounce` runs the bullet is at a wall, far from the muzzle — so
`bShouldIgnore = NOT Can Hit Shooter` costs nothing and means: `true` for
Basic / Heavy / Jammed (keeps ignoring, a harmless repeat) and `false` for
Ricochet, which is what lets the return shot connect (5.5 step 2b then stops
filtering it). Without step 16 the flag does nothing at all: `Ignore Actor
When Moving` filters the projectile's *sweeps*, so no hit event is ever
generated for the shooter no matter what the hit graph says.

Wiring notes for step 16, read off the 18 Oct export: `Bounce` holds just two
variable gets (`ProjectileMovement`, for nodes 1 and 9), so the step drops
**6 new nodes** — `Ignore Actor When Moving`, **Get Updated Primitive** (its
`self` ← `ProjectileMovement`; the Target pin is a *Primitive* pin), `Get
Shooter`, `Get Effect`, **Get Can Hit Shooter** (`self` ← the `Effect` get) and
**NOT Boolean** — taking the graph from 24 to 30. Node 15's title in the
editor is `SetActorRotation` (one word — that is 4.27's `meta=(DisplayName=...)`
for `K2_SetActorRotation`; the palette search "Set Actor Rotation" still finds
it) and its `then` is unconnected, so the exec wire is
`15.then → Ignore Actor When Moving.execute`; the other six wires are
`Target` and `Actor`, the `bShouldIgnore` boolean, plus the three internal feeds
(`Get ProjectileMovement` → `Get Updated Primitive` self · `Get Effect` →
`Get Can Hit Shooter` self · `Get Can Hit Shooter` → `NOT Boolean` A). All of
them are fresh: nothing already built gets rewired.

The ricochet is exactly two cases in 2D — a horizontal surface flips Z, a
vertical surface flips X — and the bigger component of the wall normal
tells which plane blocked. (The input's `Wall Normal` gets its own Break
Vector, separate from the velocity's — two Breaks total.)

The re-orientation (nodes 10–15) exists because the art mirrors instead of
rotating: pointing left is yaw 180 + mirrored tilt, not pitch 180. Pitch =
`Atan2(−Vz, |Vx|)` in degrees — negative pitch = up, the same convention
the gun aim chain ends with (`DegAtan2` in BP_Player's direction-flipping
graphs). After a floor bounce the sprite visibly tilts up and travels up —
the two tell the same story, which is the whole test of Part 8.

### 5.5 Event graph — the hit

**Status: ✅ done, step 2b included** (saved 19 Oct 00:00, export read back
00:03). 17 nodes / 26 wires; every wire matched pin by pin against
`Scripts/_shooting_out/Game/DontTrustTheLevels/Weapons/Blueprints/BP_Projectile.T3D`
with `py -3 Scripts/_dump_graph.py <t3d> <out> BP_Projectile`. The built gate is
the one drawn in `Scripts/edit_graphs.html`: **3 nodes** (`Get Can Hit Shooter`,
**NOT Boolean**, **AND Boolean**) and 4 wires (`==` → AND.A · Can Hit Shooter →
NOT → AND.B · AND → the shooter Branch's Condition). The export shows exactly
that — `K2Node_IfThenElse_0.Condition ← BooleanAND.ReturnValue`, `A ←` the `==`
call, `B ← Not_PreBool`, whose `A ←` the `CanHitShooter` get off `Effect`. It is
an **AND in the Branch's condition**, not a second Branch — see the note under
the table.

Select the **Box** component in the Components panel → Details → Events →
click **On Component Hit** (+). That drops `Event On Component Hit (Box)`
in the EventGraph, with **Hit Component**, **Other Actor**, **Other
Component**, **Normal Impulse**, **Hit** outputs.

| Step | Node | Pins |
|---|---|---|
| 1 | `Event On Component Hit (Box)` | Other Actor + Hit feed everything |
| 2 | **Branch** — "is it my shooter?" | Condition ← 2b · **True** → wire nothing · **False** → 3 |
| 2b | **AND Boolean** + **NOT Boolean** — "is it my shooter *and* may I not hit it?" | Rewires the shooter Branch's **Condition** only: **AND** A ← `==` (Object) · B ← **NOT Boolean** (A ← **Get Can Hit Shooter**, Target ← `Get Effect`) · AND → **Condition**. `True` = shooter this effect may not hit → wire nothing, ignored; `False` = everything else (including a shooter the effect *may* hit) → still step 3. **No exec wire is touched.** |
| 3 | **Branch** — "is the target killable?" | Condition ← **Does Implement Interface** · **Target** ← Other Actor · **Interface** ← **`BPI_Killable`** (pick it in the pin's dropdown: the stock pin is *None*, and the check then returns false for **every** actor — bug 4, the 19 Oct "ricochet bounces off me" report) |
| 4 | **True — damage:** **Apply Point Damage** | **Target** ← Other Actor · **Base Damage** ← **Get Damage** (Target ← `Get Effect`) · **Hit From Direction** ← `Break Hit Result` (Hit) → **Normal** · **Hit** ← event Hit · **Damage Causer** ← **Get a reference to self** · **Event Instigator** — leave unwired |
| 5 | → **Kill** *(BPI_Killable message)* | **Target** ← Other Actor |
| 6 | → **Destroy Actor** | Target ← self (the bullet dies with the target) |
| 7 | **False — plain geometry:** **On Wall Hit** *(BPI_ProjectileEffect message)* | **Target** ← `Get Effect` · **Hit** ← event Hit |

Three cases in order: shooter the effect may not hit → ignore; killable → point
damage + `Kill` + self-destruct; anything else → hand the hit to the effect,
which either bounces the bullet or destroys it.

> **The `Interface` pin is the whole gate.** `Does Implement Interface` with an
> empty `Interface` pin still compiles and still runs — and returns `false` for
> **every** actor, with no warning. If a ricochet comes back at you and bounces
> off, this pin is why: the hit takes the False branch (treat it as a wall)
> instead of True (damage → `Kill` → self-destruct). Only the T3D pin line
> carries the chosen class, so the verifier reads it and FAILs with `Does
> Implement Interface has no Interface set`.

> **Why 2b is an AND and not a second Branch.** An **exec input pin takes
> exactly one wire**. The killable Branch's `execute` already holds the shooter
> Branch's `False`, so a second Branch's `True` cannot land on it too — the
> editor would *replace* that link and every non-shooter hit would fall into
> nothing. Two exec paths can only merge through one condition, so the policy
> folds into the shooter Branch's own condition: `(Other == Shooter) AND NOT
> Can Hit Shooter`. It is also strictly less work — 3 pure nodes and 4 wires, no
> existing wire moved. The verifier counts the same two reads either way
> (`CanHitShooter` in `Bounce` + in this graph).

> **Order matters:** test the shooter first, killable second, wall last.
> `BP_Player` implements `BPI_Killable` itself — without the shooter check,
> the first shot kills the player. Gate 2b is the deliberate exception and it
> is opt-in per effect: `Bounce` has already lifted the movement ignore
> (5.4 step 16) for Ricochet, so a return shot really is a hit — while a
> shooter whose effect leaves `Can Hit Shooter` at `false` makes the AND true
> and stays harmless, exactly as before the extension.
>
> Note on `Kill`: BPI_Killable is binary (no params), so death is not
> damage-scaled. Point damage runs alongside it so future health systems
> see the event; today both fire together and both are cheap.

---

### 5.6 Event graph — the bullet takes its effect with it

**Status: ✅ implemented (27 Oct readback: `ReceiveDestroyed` → `Effect Clean
Up` collapsed graph → `Is Valid(Effect)` → `Destroy Actor(Effect)`; PIE actor
count stays flat after shooting).** The 19 Oct PIE report ("every time I shoot,
even when the bullets are gone, there is an effect actor left") was real before
the hook: every shot ran 5.3 steps 2–3, which **spawn a fresh `BP_Effect_*`
instance into the world**, and nothing destroyed it — the hit graph killed the
*bullet*, `BP_EffectBase` has no components (so the leftovers were invisible —
you saw them in the World Outliner, not in the viewport), and each one kept a
hard `MyProjectile` reference to the destroyed projectile, so that actor could
not be collected either. Fifty shots leaked fifty actors and fifty dead
projectiles. This is the effect-side twin of the `Gun Effect` swap in 6.2:
whoever spawns an instance owns its lifetime.

The built hook (recreate it this way if rebuilding) is a collapsed graph on
`BP_Projectile`'s **EventGraph**:

| Step | Node | Pins |
|---|---|---|
| 1 | **Event Destroyed** (right-click the graph → **Add Event** → *Actor* → **Destroyed**, or search `Destroyed` in the palette) | no input pins; its `then` fires on **every** path that kills the bullet — the hit graph's `Destroy Actor` (5.5 step 6), the effect's `On Wall Hit` false branch (3.3), and PIE shutdown |
| 2 | **Branch** | **Condition** ← **Is Valid** (*Input* ← `Get Effect`) |
| 3 | **True → Destroy Actor** | **Target** ← `Get Effect` |

So: the bullet dies → if its effect instance is still alive, it dies too. The
`Is Valid` guard matters: `Destroy Actor` on an unset Target logs *Accessed
None* every time a bullet dies, and the effect can legitimately be gone already
(PIE shutdown destroys in arbitrary order).

> **Why `Event Destroyed` and not a `Lifespan`.** `Set Life Span` on the effect
> would need one number that fits every effect — a Basic bullet lives ~0.3 s, a
> ricochet up to 3 bounces, a Heavy arc for seconds. The bullet already knows
> the exact moment it is done; hook that.

> **Why not `Destroy Actor` on self in `BP_EffectBase`'s `On Wall Hit`.** That
> only covers the wall-death path. A bullet that kills the player (5.5 step 6)
> or dies inside the wall it spawned in never reaches the effect's graph, so it
> would still leak. The `Destroyed` hook covers all three, and it keeps 3.3's
> authority rule intact (the effect still commands the bullet, never itself).

The verifier reads the **exec chain**, not the node's presence: `Destroy Actor`
must be reachable from `ReceiveDestroyed` **and** its Target pin must come from
the `Effect` variable. It follows `K2Node_Composite` nodes through their
`BoundGraph` and starts at the collapsed graph's `K2Node_Tunnel` entry, so the
current `ReceiveDestroyed` → `Effect Clean Up` chain PASSes. (Before the 27 Oct
fix it stopped at the composite and falsely reported
`nothing destroys the per-shot effect …`; `_key_wiring` had the same kind of
false failure because the exported function graph is named `SetEffectClass`, not
`Set Effect Class`.)

---

## Part 6 — BP_Player: the port + the trigger (human, ~20 minutes)

**Status (re-checked 19 Oct, PIE pass 18 Oct): 6.1–6.4 are built.** `BP_Player`
was saved **18 Oct 02:09** and rewired **19 Oct** (the four key events were
recreated and each `Pressed` goes to the `Set Effect Class` **call**);
`_verify_shooting.py` reads **105 PASS / 0 FAIL / 2 WARN / 0 PENDING** (the 5.6
`Destroyed` hook is present as the `Effect Clean Up` collapsed graph; before the
27 Oct verifier fix the composite was not expanded and the `SetEffectClass`
graph-name comparison was not normalized, which produced a false 103 PASS /
2 FAIL). The graph dump shows both variables, an 11-node
`Set Effect Class` function, the BeginPlay hook (collapsed as a box named
`Update Effect Class` at 976,−480) and the whole Fire chain. **The step-1 bug
is fixed**, verified in the dump: step 1 is now `K2Node_VariableSet_2`
(`var EffectClass`), its `execute` fed by `ExecutionSequence.then_0`, its
**Effect Class** input by the entry's `NewEffectClass`, its `then` by the
Branch — the self-call is gone. For the record, the old symptom was: step 1
was a *call* of `Set Effect Class` — the function calling itself — so `Effect
Class` was never written and the call recursed into itself. The pin is the
tell: `Effect Class` = the variable, `New Effect Class` = the function.

**The 6.4 keys repeat that mistake** — found in PIE on 18 Oct: each key's
`Pressed` pin feeds a `K2Node_VariableSet` on `EffectClass`
(`EventGraph/K2Node_VariableSet_0..3`, at x≈912, y≈−1376 … −912), so the
palette's *variable* entry was picked instead of the function. Consequence:
`Gun Effect` is never replaced, the fire gate keeps the Basic instance's
`Can Fire = true`, and **press 4 → LMB still fires** (the bullet itself does
use the new class — that is why 2 and 3 changed the bullet). Delete the four
variable-set nodes and put one **call** of `Set Effect Class` in their place
(6.4 below); `_verify_shooting.py` now follows each key's exec chain and
FAILs a variable-only chain.

**One detail is still wrong:**
* **both** Spawn Actor nodes — 6.1's (inside the function) and 6.3's — still
  have **Collision Handling Override = `Undefined`** instead of *Always Spawn,
  Ignore Collisions*.

The `Instance Editable` ticks are *not* a problem: `Effect Class` carries the
same flag bit (5) as `BP_EffectBase.Can Fire` ✓ and `Gun Effect` the same as
`My Projectile` ✗, and `Effect Class`'s default *is* `BP_Effect_Basic` (the
verifier prints the value). Drawing:
`Scripts/player_graph.html` — board **6.0** is the file *before* the 01:56 save
and where each piece attaches (`ReceiveBeginPlay` → the collapsed **Add
Crosshair** box, whose `then` pin was wired to nothing), 6.1 the port function,
**6.2 the BeginPlay hook (the board this doc never drew)**, 6.3 the trigger,
6.4 the debug keys; panel **6.0b** is the same check run over what is built
right now. **Every box carries an origin chip** (green *NEW* = you
build it, grey *EXISTS* = already in the file, purple = it lives in another
asset, gold = an ini mapping) and panel **6.0a** answers the two questions a
build sheet has to: *every name &rarr; what it is, which asset it lives in, who
made it, is it in the file yet* and *every box &rarr; the exact clicks to place
it*. Regenerate and re-check with
`py -3 Scripts/_player_graph_html.py` then
`py -3 Scripts/_check_wires_html.py Scripts/player_graph.html` (currently
**PASS**, 4 boards / 34 nodes / 32 wires).

Open `/Game/DontTrustTheLevels/Player/Blueprints/BP_Player`. One owner at a
time on this asset — build Parts 2–5 first, then come here in one sitting.

### 6.1 Variables + function

**Board 6.1** in `Scripts/player_graph.html` (11 nodes / 13 wires).

| Variable | Type | Instance Editable | Default |
|---|---|---|---|
| `Effect Class` | **Class Reference** → `BP_EffectBase` | ✓ | `BP_Effect_Basic` (set in Class Defaults) |
| `Gun Effect` | Object → `BP_EffectBase` | ✗ | — (runtime ref to the live effect instance) |

New function, **My Blueprint → Functions → + → `Set Effect Class`** —
this function **is** the port; every effect switch in the game funnels
through it:

| Step | Node | Pins |
|---|---|---|
| — | Input: `New Effect Class` (Class Reference → `BP_EffectBase`) | |
| 1 | **Set Effect Class** — the *variable set* of `Effect Class`, **not** the function of the same name (the search lists both; the pin is the tell: `Effect Class` = variable, `New Effect Class` = function) | ← `New Effect Class` |
| 2 | **Branch** — "do I already have a live effect?" | Condition ← **Is Valid** (Object) Input ← `Get Gun Effect` |
| 3 | **True path:** **Destroy Actor** | Target ← `Get Gun Effect` · then → step 4 |
| 4 | **Spawn Actor from Class** | **Class** ← `Get Effect Class` (the variable, *after* step 1) · **Spawn Transform** ← `Get Actor Transform` (self) · **Collision Handling Override** = `Always Spawn, Ignore Collisions` (spawns inside the capsule — required) |
| 5 | **Set Gun Effect** (variable set) | ← spawn's Return Value |

The old instance is destroyed first so two effects never coexist; the fresh
instance gets default `Bounces`/`Can Fire` from the child's CDO. The
player's `Effect Class` variable stays the source of truth — `Gun Effect`
is just the live instance of it.

### 6.2 BeginPlay: hand out the first effect

**Board 6.2** in `Scripts/player_graph.html` — the one board this doc never had
as a drawing (4 nodes / 3 wires).

Find `Event BeginPlay` in the EventGraph (it runs the collapsed **Add
Crosshair** box — GunAiming.md Part 4). In the export that box is
`K2Node_Composite_3` at (800,−480) and its `then` pin is wired to **nothing**:

```text
K2Node_Event_0 (ReceiveBeginPlay, 592,−464)  →  K2Node_Composite_3 (Add Crosshair)
                                                    └─ then: empty  ← 6.2 starts here
```

Inside the box: `CreateWidget(WBP_Crosshair)` → `Set CrosshairWidget` →
`AddToViewport`. Wire the exec out of **Add Crosshair** into a call to
**`Set Effect Class`** with **New Effect Class** ← `Get Effect Class` (the
variable's default, `BP_Effect_Basic`).

Routing the initial spawn through the same function means one code path:
no "first effect" special case exists anywhere.

### 6.3 The fire chain

**Board 6.3** in `Scripts/player_graph.html` (13 nodes / 14 wires).

Right-click in the EventGraph → **Input → Action Events → Fire → Pressed**.

| Step | Node | Pins |
|---|---|---|
| 1 | `Fire` (Pressed) | |
| 2 | **Branch** — "may I?" | Condition ← **Get Can Fire** (property get) · **Target** ← `Get Gun Effect` |
| 3 | **True:** **Get World Location** *(of Gun component)* | component variable `Gun` → output **Location** |
| 4 | **Get World Rotation** *(of Gun component)* | same `Gun` → output **Rotation** |
| 5 | **Get Forward Vector** *(Kismet Math — input is a rotator)* | ← node 4's rotation |
| 6 | **Multiply** *(Vector × Float)* | A ← node 5 · B = `60.0` (muzzle clearance: half the 100uu art + a hair) |
| 7 | **Add** *(Vector + Vector)* | A ← node 3 · B ← node 6 → muzzle world location |
| 8 | **Spawn Actor from Class** (Class pin = `BP_Projectile`) | **Class** = `BP_Projectile` · right-click the **Spawn Transform** pin → **Split Struct Pin** → **Location** ← node 7 · **Rotation** ← node 4 · Scale (1,1,1) · **Collision Handling Override** = `Always Spawn, Ignore Collisions` · exposed pins: **Effect Class** ← `Get Effect Class` · **Shooter** ← **Get a reference to self** |
| 9 | **False (can't fire):** | wire nothing — a jammed effect makes the LMB do exactly nothing |

The bullet spawns at the muzzle with the barrel's world rotation — the gun
already aims at the crosshair (GunAiming.md Part 5), so no aim math is
duplicated here. Everything past the spawn (velocity, hit policy, damage)
is the bullet's own BeginPlay and hit event from Part 5.

**Why read `Can Fire` from `Gun Effect`, not from the class:** the gate
must consult the *live instance*. If a future effect lowers `Can Fire`
mid-flight (an overheat, say), the gate obeys instantly — reading the CDO
default would ignore live state.

### 6.4 Debug keys: switch effects in PIE

Four one-node chains, placed near the **Dash** input event:

| Input event (Pressed) | Call | New Effect Class pin |
|---|---|---|
| `Effect_Basic` | `Set Effect Class` | `BP_Effect_Basic` (pick in the pin's class dropdown) |
| `Effect_Ricochet` | `Set Effect Class` | `BP_Effect_Ricochet` |
| `Effect_Heavy` | `Set Effect Class` | `BP_Effect_Heavy` |
| `Effect_Jammed` | `Set Effect Class` | `BP_Effect_Jammed` |

The input pin is a Class Reference — leave it **unwired** and pick the
class from the pin's dropdown. **Compile + Save.**

> **The pin is the tell — the 18 Oct build got it wrong here.** The palette
> lists two nodes called `Set Effect Class`: the **variable setter**
> (`Effect Class` pin, `Target` = self) and the **function call**
> (`New Effect Class` pin, `Target` hidden). The built keys use the setter
> (`K2Node_VariableSet_0..3` at x≈912, y≈−1376/−1232/−1072/−928), which only
> changes what the *next bullet* will spawn — `Gun Effect` is never replaced,
> so the fire gate keeps the old instance's `Can Fire` and **`4` still
> fires**. Fix per key: delete the `Set Effect Class` *variable* node (the one
> whose body shows `Effect Class`), drop the **call** node in its place and
> pick the class in `New Effect Class`. The resulting chain is exactly one
> wire: `Pressed` → call's `execute`. Compile + Save.
>
> **Delete only that node — keep the key event.** The 19 Oct attempt
> box-selected the row and deleted the four `InputAction` events
> (`K2Node_InputAction_3..6`) along with it. The export then has no key event at
> all: `Pressed` never fires, `Effect Class` stays `BP_Effect_Basic`, every
> bullet keeps `Gravity Scale 0.0` (pressing `3` stops dropping) and `4` stops
> jamming. Recreate the event with right-click → `Effect_Heavy` under
> **Action Events**, then wire it as above.
>
> Regression check: `py -3 Scripts/_verify_shooting.py` follows each key's
> `Pressed` chain and prints
> `FAIL  debug keys must CALL Set Effect Class (the function) … [Effect_Jammed
> -> K2Node_VariableSet_3]` while a setter is in the chain, plus
> `FAIL  EffectClass variable set outside Set Effect Class: EventGraph/…` for
> each leftover. A deleted key event reads
> `[Effect_Heavy (event node deleted - it is only left in the transaction
> buffer)]`, which distinguishes "never built" from "deleted by mistake".
> Both fixes are drawn side by side (before / after) in
> `Scripts/fix_pie_bugs.html`.

---

## Part 7 — Switching effects from anywhere (the payoff)

The debug keys are just *callers* of `Set Effect Class`. The same call works
from traps, pickups, volumes, cutscenes:

```text
(any trigger)  →  Get Player Pawn  →  Set Effect Class(New Effect Class = <class>)
```

- The caller holds no reference to the bullet, the effect, or the muzzle —
  one function call, and the port state flips.
- **Anti-cast check (Structure.md §9):** inside pillar 1 (the player and
  its own HUD/UI), a direct cast is fine — it is the owner. Cross-pillar
  callers (an Environment trap changing the gun's ammo, say) should not
  reach into BP_Player. When the first such trap exists, add a
  one-function interface — `BPI_EffectUser` with message
  `Set Effect Class` — implement it on `BP_Player` (the implementation
  body is this same function). Five minutes of work, done lazily, not now.

**Why a class variable and not an instance:** instances are runtime
artifacts (spawned per player, per shot); the *port state* must survive the
instance dying and be trivially serializable for save games. The class is
the truth; instances are derived from it on demand — the "effect port"
pattern Structure.md §4 sketches for the weapons pillar.

---

## Part 8 — Verify + play test

Scripted half (editor running): `py -3 Scripts/_verify_shooting.py` —
asset presence, import settings, live input actions, ini mappings (parsed
offline), and — after Parts 2–6 — effect defaults, BP_EffectBase
variables/graph, BP_Projectile components/variables, BP_Player
variables, plus offline T3D graph-node markers (parentage, fire chain,
interface messages — presence only, never topology).

Two facts about reading live state out of this build, both learned the hard
way (probes in `Scripts/_probe_cdo.py`, `Scripts/_probe_parent.py`):

* **Reading** an actor's defaults: `load_class(path).get_default_object()`
  returns the *class's* metaclass object, not the actor CDO. The verifier
  therefore spawns a throwaway actor far from the level
  (`100000,100000,100000`) and destroys it (`finally`-guarded); nothing is
  saved. `None` from such a read is ambiguous — `get_editor_property()`
  *raises* for a property that does not exist but *returns* `None` for an
  existing object reference that is simply unset. The verifier uses
  `prop_exists()` for object-typed variables (`My Projectile`, `Shooter`,
  `Effect`, …) so a legitimately-null default is not mistaken for a missing
  variable.
* **Writing** a CDO: `get_default_object()` accepts `set_editor_property()`
  as a *silent no-op*. The real actor CDO is only reachable as the package
  subobject `<AssetPath>.Default__<AssetName>_C` via
  `unreal.load_object(None, ...)` — `Scripts/_make_shooting.py`'s `cdo_of()`
  does exactly that, and its Part 4 writes land (verified 16/16).
* **Graphs and components are not scriptable at all in this build** (probed in
  `Scripts/_probe_graph_api.py`): `unreal` exposes no `BlueprintEditorLibrary`,
  `EdGraph`, `EdGraphSchema_K2`, `K2Node_*` or `SubobjectDataSubsystem`. So
  Parts 3.2–3.3, 5 and 6 are hand work *by construction*, not by choice —
  `Scripts/_open_asset.py <asset name>` can only put the editor tab on screen
  for you (it uses `AssetEditorSubsystem.open_editor_for_assets`).

The verifier reports PENDING for anything not built yet (naming the doc part
that fixes it) and standing WARNs for the sprite `collision_source` and the Box's
`Simulation Generates Hit Events` (Part 5.1 — this Python build cannot read
either, so both stay eyeball checks). The four per-effect markers are
**counted, not presence-checked**, because the export already contained one
`IgnoreActorWhenMoving` (BeginPlay) and one `Bounces` read (in `Bounce`) — a
plain "does this node exist?" test would have PASSed before step 16 / 2b were
built. `marker_min()` demands the next occurrence, so they could only flip on
the run after the hand work landed — they all did on 19 Oct (4/4). The gravity marker is doubly narrow: it wants a
`K2Node_VariableSet` whose `VariableReference` carries a `…MovementComponent`
parent **and** `MemberName="ProjectileGravityScale"`, so neither the effect's
`Get Gravity Scale` nor a `Get Projectile Gravity Scale` dragged off the
component can stand in for the setter (step 7 writes
`ProjectileGravityScale`; the base `GravityScale` does not exist on 4.27's
`UMovementComponent`).

Live half — re-run `py -3 Scripts/_make_shooting.py` any time (it is
idempotent): it re-asserts the child CDO defaults against the now-existing
variables and prints their live status. Its writes are the only ones the
project can script, so if a part is still open, anything it reports as
`FAIL`/stale for the *manual* parts still has to be rebuilt by hand per the
part above; the verify script's spawned reads are the ground truth that
catches a silent no-op.

PIE checklist (editor **restarted** first so the five mappings are live).

One mechanical pass before the checklist, in this order: `py -3
Scripts/_verify_shooting.py` (it re-exports the 8 T3D files — expect **105
PASS · 0 FAIL · 2 WARN · 0 PENDING**; the verifier expands the 5.6 `Effect
Clean Up` composite, and before the 18 Oct fixes the run was 97 PASS + 3 FAIL +
4 WARN — every FAIL line names its own fix, and the
edits are drawn in `Scripts/fix_pie_bugs.html`), then `py -3
Scripts/_check_pin_links.py` (expect **no output**, exit
0; anything else is drawn in `Scripts/cleanup_graphs.html`), then `py -3
Scripts/_make_shooting.py` if an effect value below looks wrong.

| # | Expect | Tests |
|---|---|---|
| 1 | LMB fires a bullet from the muzzle toward the crosshair, both facings | spawn, rotation inheritance, velocity |
| 2 | Bullet dies on walls/floors; no error spam | hit event → effect → destroy |
| 3 | Press 2 → bullets bounce up to 3 times, sprite re-tilts after each bounce, **and the next contact destroys them** (nothing may sit at the wall) | ricochet + re-orientation + `Should Bounce` on the movement |
| 4 | Press 3 → visibly slower bullets that **drop** as they fly (an arc, not a straight line) | speed default + `Gravity Scale` 1.0 copied in BeginPlay |
| 5 | Press 4 → LMB does nothing, no bullet spawned | Can Fire gate |
| 6 | Press 1 → back to normal | port reset |
| 7 | Walking while shooting never kills the player | shooter ignore on spawn (5.3 step 6) |
| 8 | Switch to 2, bounce a shot off a nearby wall and stand in its return path → **you die** | `Can Hit Shooter` true → `Bounce` lifts the ignore (5.4 step 16) → gate 2b lets it through (5.5) |
| 9 | The same return shot with 1 / 3 / 4 selected passes harmlessly through you | `Can Hit Shooter` false → gate 2b returns False |
| 10 | Aim/crosshair behavior unchanged | BP_Player untouched except Part 6 |
| 11 | Fire ~20 shots at walls and stop → the World Outliner holds **exactly one** `BP_Effect_*` actor (the player's `Gun Effect`), not one per shot | 5.6 `Destroyed` hook destroys each bullet's effect instance with it |

Item 8 is the design, not a bug: a returning ricochet is a legit kill, and it is
now **data** — one tick on `BP_Effect_Ricochet`. If playtests hate it, untick
`Can Hit Shooter` on that child (or leave 5.4 step 16 out) and the behaviour
returns to "bullets never hurt their owner"; no architecture change.

---

## Troubleshooting

| Symptom | Cause → fix |
|---|---|
| `Fire` not in the Action Events list | Editor started before the ini write → restart the editor |
| LMB does nothing at all | Same restart reason; or the `Can Fire` branch's Target is not `Get Gun Effect` |
| Bullet spawns but sits still | BeginPlay exec chain broken (steps 2→3→4→5, then 6→7, are one chain); or `Effect Class` default is None → the effect spawn fails, `Get Speed` returns 0. Set default `BP_Effect_Basic` in Class Defaults |
| Bullet falls downward | If **every** effect drops, `Projectile Movement → Projectile Gravity Scale` was typed on the *component* — reset it to **0.0**; the effect owns gravity (5.3 step 7). If only Heavy drops, that is correct |
| Bullet passes through floors | Box preset not `BlockAllDynamic`, or `Simulation Generates Hit Events` off, or the sprite still collides (must be `NoCollision`) |
| Bullet dies at the spawn point | Spawned inside a wall (fired while hugging one) — keep `Always Spawn, Ignore Collisions` on the player's SpawnActor; confirm `Ignore Actor When Moving` runs with `Shooter` set |
| First shot kills the player | Hit-event order wrong — the `== Shooter` branch must come **first**; or the effect's `Can Hit Shooter` gate (2b) is missing/shorted so the True path falls straight through |
| Heavy bullets fly dead straight | `Gravity Scale` is 0.0 on `BP_Effect_Heavy` (re-run `_make_shooting.py`), or 5.3 step 7 is missing / wired to the wrong node. The node must be **Set Projectile Gravity Scale** (Target `ProjectileMovement`), fed by **Get Gravity Scale** on the effect — without it the effect value never reaches the component |
| Ricochet never hurts me | **First: 5.5 step 3's `Does Implement Interface` has no `Interface` set** — an empty pin is false for *every* actor, so the hit is treated as a wall and the bullet bounces instead of dying (the verifier FAILs it with `Does Implement Interface has no Interface set`). Then: `Can Hit Shooter` is false on `BP_Effect_Ricochet`, or 5.4 step 16 is missing (the movement ignore then filters the sweep, so no hit event exists), or 2b is not wired to 3 on True |
| Every effect hurts me, even Basic | `bShouldIgnore` is not `NOT Can Hit Shooter` but wired/crossed — Basic must end at `true`; check 5.4 step 16's NOT node sits between the getter and the pin |
| Ricochet bullet points the wrong way after a bounce | Pitch inverted → the `−Vz` Multiply feeds Atan2's **Y**, `|Vx|` feeds **X**; or yaw Select swapped → Pick A = `180` is the *condition-true* case |
| Ricochet bounces forever | `Set Bounces` not wired before `Bounce`, or child default wrong → re-run `py -3 Scripts/_make_shooting.py` |
| Press 4 → LMB still fires (a bullet spawns) | The key is wired to the **variable** setter called `Set Effect Class` instead of the **function**: `Gun Effect` is never replaced, so the fire gate reads the old instance's `Can Fire = true`. Fix per 6.4 — one call node, `Pressed` → `execute`; the verifier names the offending chain (`Effect_Jammed -> K2Node_VariableSet_3`) |
| Ricochet bullet stops dead at the wall and never disappears | `Projectile Movement → Should Bounce` is off: `HandleImpact()` calls `StopSimulating()` (velocity 0, updated component detached) right after the hit delegate, so `Bounce`'s `Set Velocity` is wiped. Tick **Should Bounce**, set **Bounciness 1.0** / **Friction 0.0** (5.1); the verifier FAILs with `Should Bounce is OFF` |
| Ricochet bullet freezes on the floor when fired point-blank | `Bounce` reads `Get Owner → Get Velocity` (the actor), but `AActor::GetVelocity()` returns the root component's `ComponentVelocity`, which is still `(0,0,0)` during the projectile's first tick. A close downward shot hits the floor in that tick → `Bounce` reflects zero and the bullet stops. Replace those two nodes with a **`Velocity` property get on `ProjectileMovement`** feeding the velocity `Break Vector` (5.4 step 1). The verifier FAILs with `Bounce reads Actor GetVelocity` |
| Effects won't switch | `Set Effect Class` — the SpawnActor must read the variable **after** step 1 sets it; and BeginPlay must call `Set Effect Class` (6.2) or `Gun Effect` stays None and the gate blocks |
| None of 2/3/4 changes anything; bullets fly straight like Basic and `4` still fires | The four `InputAction` **key events** were deleted together with the setters (a box-select delete) — `Pressed` fires no more, so `Effect Class` never leaves `BP_Effect_Basic`. Recreate each event (6.4: right-click → `Effect_Heavy` under *Action Events*), then `Pressed` → the `Set Effect Class` **call**. The verifier FAILs with `Effect_Heavy (event node deleted - it is only left in the transaction buffer)` |
| Switching leaves two effects | The `Is Valid` True path must `Destroy Actor` the old one before the SpawnActor (False path goes straight to SpawnActor) |
| An **effect actor** is left in the World Outliner after every shot | 5.6's `Effect Clean Up` hook is missing or broken: `BP_Projectile`'s BeginPlay spawns one `BP_Effect_*` (5.3 steps 2–3) and the hit graph only destroys the bullet. Restore the `Event Destroyed` → `Effect Clean Up` collapsed graph → `Is Valid(Effect)` → `Destroy Actor(Effect)` chain; the verifier expands the composite and FAILs `nothing destroys the per-shot effect …` when it is absent |
| Sprite looks flipped relative to travel | Spawn rotation comes from the gun — check the gun's facing flip chain first (GunAiming.md Part 5); only then suspect `Bounce`'s yaw Select |

---

## Adding a new effect in 60 seconds

The entire point of the port — no graph in this file is touched:

1. Content Browser → right-click **BP_EffectBase** → **Create Child
   Blueprint Class** → name it (say `BP_Effect_Poison`) → save in
   `/Game/DontTrustTheLevels/Weapons/Blueprints/`.
2. **Class Defaults** → type new numbers (Damage 2, Speed 2600, Gravity
   Scale 0.4 if it should lob, Can Hit Shooter if its bounces may hurt you).
3. Wire any trigger — a key, a trap volume, a pickup — to
   `Set Effect Class` with the new class. Done. No new variable, node or
   interface — the two knobs added in this revision are exactly so that
   "gravity" and "owner policy" are *numbers and a tick*, not new graphs.
4. *If the new effect needs new behavior*, not just new numbers: grow the
   message protocol (e.g. `On Killable Hit` on BPI_ProjectileEffect),
   implement it in BP_EffectBase once, default it differently per child.
   The port absorbs the change; the player and the bullet stay untouched.

---

## Commit

Editor closed, then two commits (same split as GunAiming.md):

```
feat: projectile shooting — ammo art, BP_Projectile, effect port assets
feat: BP_Player fire chain + effect-swap keys (manual build per Docs/ProjectileShooting.md)
```

1. Scripted half: the 9 new `.uasset`s under `Weapons/` and
   `Core/Interfaces/`, `Config/DefaultInput.ini`, this file.
   (`Assets/PixelBullets/PistolAmmoSmall.png` is already tracked from the
   earlier art commit, and the whole `Scripts/` folder is gitignored in
   this project — `_make_shooting.py`, `_verify_shooting.py` and
   `_probe_parent.py` stay local, like every previous feature's scripts.
   Their generated artifacts are equally transient; nothing under
   `Scripts/` belongs in a commit.)
2. Manual half (after Parts 2–6 build and the PIE checklist passes): the
   7 edited `.uasset`s — `BPI_ProjectileEffect`, `BP_EffectBase` + its 4
   children, `BP_Projectile`, `BP_Player`. This revision adds two variables to
   `BP_EffectBase` and nodes to `BP_Projectile`, so those two assets change
   again; the children change only in Class Defaults (`Gravity Scale`,
   `Can Hit Shooter`) and are normally *not* re-saved by
   `_make_shooting.py`'s CDO writes unless the values differ.
