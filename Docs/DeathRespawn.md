# Death & Respawn — pit death via BP_KillVolume · build guide

**Concept (Level Devil rule):** falling into a pit = death. The fake floor drops
the player into the pit; a **`BP_KillVolume`** at the pit bottom kills them
(`BPI_Killable → Kill`), and `BP_Player`'s Kill event reloads the level.
Everything resets — the fallen floor comes back, the run restarts clean.

**Why level reload (not teleport):** teleporting back leaves the fake floor
fallen/destroyed — the level becomes unbeatable. A reload resets *everything*
for free. A soft-respawn (`BPI_Resettable` on traps) is a later feature.

**Why overlap (not tick):** overlap events are engine-native physics callbacks —
zero per-frame Blueprint cost. The player-side KillZ tick check was rejected
for exactly that reason (polling every frame vs. waking only on contact).

---

## Part 0 — What already exists (verified 18 Oct 2026)

| Asset | State |
|---|---|
| `BPI_Killable` | ✅ exists — `Kill` has **no outputs**, so it is implemented as an **event** (Structure.md §9) |
| `BP_Player` | ✅ exists, **already implements `BPI_Killable`** — the Kill message will reach it |
| `BP_KillVolume` | ✅ **created** (empty Actor BP at `Traps/Blueprints/`) — needs its component + graph |
| Trap overlap chain | ✅ `BP_Trap_FakeFloor` correctly wired (screenshot verified) |

**Verified via remote Python** (`Scripts/_killrespawn_state.py`):
`BPI iface class: BPI_Killable_C`, `implements BPI_Killable: True`,
`walk speed: 1000.0`.

---

## Part 1 — BP_KillVolume: component (hand work)

Open `Content/DontTrustTheLevels/Traps/Blueprints/BP_KillVolume`.

Components panel → **+ Add → Box Collision** → rename **`KillBox`**:

| Setting | Value |
|---|---|
| Collision Presets | **OverlapAllDynamic** |
| Collision Enabled | **Query Only** |
| Generate Overlap Events | ✓ |

Leave the box extent at the default (100 uu half-extent) — you size it
**per placed instance** in the level.

**Compile + Save.**

---

## Part 2 — BP_KillVolume: event graph (4 nodes, hand work)

Same chain as every trap (FakeFloorTrap.md Chain A):

```
OnComponentBeginOverlap (Target = KillBox)
  → Does Implement Interface (Test Object = Other Actor, Interface = BPI_Killable)
  → Branch (True →)
  → Kill (Message)   Target ← Other Actor
```

1. Click **KillBox** in the Components panel → Details → Events →
   **+ On Component Begin Overlap**.
2. Drag off **Other Actor** → search **Does Implement Interface** →
   set **Interface = BPI_Killable**.
3. Drag off **Return Value** → **Branch**.
4. **True** → drag off **Other Actor** again → search **Kill** → pick the
   **(Message)** variant (the plain `Kill` node fails to compile) →
   the Target pin auto-wires from Other Actor.

### ⚠️ THE RULE (broke earlier attempts — FakeFloorTrap.md)

**Never drag a wire onto a node's non-exec pin area / a function's start
node.** Stray parameters get created silently, are fed zeros at runtime, and
the logic dies while compiling clean. After building: click the start node →
**Details → Inputs must be empty**.

**Compile + Save.**

---

## Part 3 — BP_Player: Kill event → level reload (hand work)

Open `Content/DontTrustTheLevels/Player/Blueprints/BP_Player`.

The interface event already exists as a hook (the class implements
`BPI_Killable`); if you don't see it: right-click → search **Event Kill**
→ it should appear under **Interfaces** (add via Class Settings →
Interfaces → BPI_Killable if missing).

```
Event Kill
  → Branch (bRespawning? → True: return / False: continue)     ← re-entry guard
  → SET bRespawning = true
  → Print String ("YOU DIED - respawning")                     ← visible until UI exists
  → Delay (0.5)
  → Open Level (by name: Get Current Level Name)               ← reload resets all
```

### Variables (My Blueprint → Variables → +)

| # | Name | Type | Default | Notes |
|---|---|---|---|---|
| 1 | `bRespawning` | Boolean | `false` | internal — re-entry guard |

### Node-by-node

1. **Event Kill** — the interface event node.
2. **Branch** — Condition ← `GET bRespawning`. **True** → do nothing (a second
   Kill message in the same death is ignored). **False** → continue.
3. **SET bRespawning** — set **true** immediately (first thing after the branch).
4. **Print String** — `"YOU DIED - respawning"` (temporary; UI pillar will own
   the real death screen later).
5. **Delay** — **0.5** seconds (short pause so the death reads on screen).
6. **Open Level (by name)** — search **Get Current Level Name** (pure node;
   click the node's ⌄ expander and tick **Remove Prefix** — otherwise in PIE
   the name reads `UEDPIE-0-..._L_Level_01` and the open fails) → wire its
   Return Value into **Open Level (by name) → Level Name**.
   *(Changed 19 Oct — the original by-object-reference pattern was per-level
   and broke: `BP_Player` is one shared class, its reference default stayed
   `L_Level_00`, so dying in Level 2 reloaded Level 1. "Ask the engine where
   you are" needs no per-level maintenance and cannot desync.)*

**Compile + Save.**

---

## Part 4 — Place it in the level (hand work)

1. Open `L_Level_00`.
2. Drag `BP_KillVolume` into the level, **under the fake-floor pit**
   (below where the floor drops, at/below the pit bottom).
3. Scale the **KillBox** component (not the actor) so it spans the pit:
   generous width/depth, top face just below the lowest walkable surface so
   nothing above can graze it. A tall box (e.g. top at pit bottom, extending
   far down) catches the player at any fall speed.
4. Duplicate for every future pit (each pit = one instance).

⚠️ **Volume placement is a `.umap` edit** — `L_Level_00` is shared with the
team. Per Structure.md §4 rule 3 the map references `BP_KillVolume` **by
class**, so a trap fix never breaks the map; still, coordinate placement with
the level-design pillar (pillar 5) if the pit is theirs.

---

## Part 5 — Verify

### 5.1 Static checks (remote Python, PIE stopped)

```bat
py -3 Scripts\_killrespawn_state.py
:: expect: BP_KillVolume exists: True
```

(Add a KillBox/overlap-presence check to the script after Part 1 is built —
Python cannot read SCS components, so the overlap wiring itself stays a
hand-verifiable step: see Structure.md §11 table.)

### 5.2 PIE walkthrough (the real test)

1. In the editor: PIE.
2. Walk onto the fake floor → it drops → you fall into the pit.
3. **Expect:** the KillBox overlap fires → `YOU DIED - respawning` prints →
   0.5 s pause → level reloads clean (floor restored at the top, traps reset).
4. Walk onto the fake floor again → it must drop again (no stale state).

### 5.3 Regression

- Jumping *over* the pit must **not** trigger the volume (box top below the
  lowest walkable surface).
- Standing on solid floor must not trigger it (KillBox only in the pit).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Fall into pit, nothing happens | KillBox presets ≠ OverlapAllDynamic, or Collision Enabled ≠ Query Only, or Generate Overlap Events unticked |
| Overlap fires, player doesn't die | Kill node is the plain `Kill` not **(Message)**, or Target not wired from Other Actor |
| Compile error "must have valid target" | Message node created from empty space — re-drag off Other Actor |
| "Does Implement Interface" always False | Interface set to wrong asset; must be `BPI_Killable` from `Core/Interfaces/` |
| Player dies, level doesn't reload | Open Level not wired, or level reference pin empty |
| Dying in Level 2 reloads Level 1 | The old by-reference default was still wired — use Get Current Level Name (Remove Prefix ✓) per Part 3 |
| Reloads but floor still gone | You teleported instead of reloading — use Open Level |
| Dies twice / double reload | Missing `bRespawning` guard |
| Level reloads instantly, no pause | Delay not 0.5 or bypassed |

---

## Ownership & commit

- Pillar 1 (you): `BP_Player` Kill event, `BP_KillVolume` build, this doc.
- `L_Level_00` placement: coordinate with pillar 5 (shared map).
- Commit with the **editor closed** (Structure.md §4 rule 5) on `branch/Jones`.
- Suggested message — `feat: pit death + respawn via BP_KillVolume (player Kill → level reload)`