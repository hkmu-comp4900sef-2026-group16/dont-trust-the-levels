# Modular UI — Title / Settings / Levels · build guide

**Concept:** three screens behind one router widget. Every page is its own
Widget Blueprint that knows **nothing** about the others — it only *raises
Event Dispatchers*. A single `WBP_RootUI` owns a `WidgetSwitcher`, binds every
dispatcher, and routes. Adding a page = one new widget + one slot + one bind.

**Style rule (from BP_Player's Event Graph):** every page's logic lives in
**Collapsed Graphs / Functions** — the top-level graph reads as a wiring
diagram only (`Play → OnPlay`, `Back → OnBack`), one node per concern.

```
WBP_RootUI  (the ONLY widget anything else knows about)
├── RootCanvas (Canvas Panel)
│   └── Pages (WidgetSwitcher)
│       ├── 0: WBP_Page_Title     ── raises: OnPlay, OnSettings, OnQuit
│       ├── 1: WBP_Page_Settings  ── raises: OnBack
│       └── 2: WBP_Page_Levels    ── raises: OnLevelSelected(Index)
├── Switch Page (Collapsed Function)        ← one node routes all pages
└── Bind Page Events (Collapsed Function)   ← wires every dispatcher in Construct
```

**Flow:** Title **Play** → Levels page → level button → `Open Level`.
Title **Settings** → Settings page → **Back** → Title.

**Persistence:** settings live in `SG_Settings` (SaveGame) via
`BP_GameInstance` — GameInstance survives `Open Level`, so volume/fullscreen
choices survive both level reloads (death respawn) and level switches.

---

## Part 0 — Assets (script does this)

```bat
:: with the editor open, PIE stopped:
py -3 Scripts\create_ui_assets.py
```

Creates (idempotent): `UI/WBP_Page_Title`, `UI/WBP_Page_Settings`,
`UI/WBP_Page_Levels`, `UI/WBP_RootUI`, `Core/Blueprints/BP_GameInstance`
(parent `GameInstance`), `Core/Data/SG_Settings` (parent `SaveGame`).

**Hand step (Python cannot):** Project Settings → Maps & Modes →
**Game Instance Class = BP_GameInstance**. (World-settings are not exposed to
Python — Structure.md §11.)

---

## Part 1 — WBP_RootUI (the router)

### Designer layout

1. Root → **Canvas Panel** (`RootCanvas`).
2. Canvas → **Widget Switcher** (`Pages`), anchor full-rectangle.
3. Drag the three page widgets from the Content Browser into `Pages`
   (order: 0 Title, 1 Settings, 2 Levels).

### Variables

| Name | Type | Notes |
|---|---|---|
| `PageIndex` | Integer | internal — current page |

### Function `Switch Page` (inputs: `NewIndex` int)

```
SET PageIndex = NewIndex
→ Set Active Widget (Target = Pages, Widget = Pages.GetWidgetAtIndex(NewIndex))
```
Collapsed after building. All routing goes through this one node.

### Function `Bind Page Events` (called from Event Construct)

```
Get Widget From Class (WBP_Page_Title)  → Bind Event to OnPlay      → Switch Page(2)
                                        → Bind Event to OnSettings  → Switch Page(1)
                                        → Bind Event to OnQuit      → Quit Game
Get Widget From Class (WBP_Page_Settings) → Bind Event to OnBack    → Switch Page(0)
Get Widget From Class (WBP_Page_Levels)   → Bind Event to OnLevelSelected
        → custom event "Open Selected Level"
```

> `Get Widget From Class` here returns the same instances the switcher
> already holds (same class + same outer) — binding works because the
> dispatcher belongs to the widget object the switcher displays. If a bind
> ever doesn't fire, the fix is: cast the switcher's child instead
> (`Pages.GetWidgetAtIndex(0) → Cast To WBP_Page_Title → Bind Event`).

### Event Construct

```
Event Construct → Bind Page Events (collapsed) → Switch Page(0)
```

### Custom event `Open Selected Level` (input: `Index` int)

```
Open Selected Level(Index)
  → Get Level Names array element (clamp Index)   ← see Variables below
  → Open Level (by name)
```

| Variable | Type | Default |
|---|---|---|
| `LevelNames` | **String Array** | `["L_Level_00"]` — append `L_Level_01`… as they ship |

Open Level **by name** is fine for the router (names come from one array in
one file); the death-respawn doc's by-reference advice applies to
`BP_Player`, which shouldn't know the level list.

---

## Part 2 — WBP_Page_Title

### Designer layout
Vertical Box (`MenuBox`), centered: **Title text** (`Don't Trust The Levels`),
then buttons: `Btn_Play`, `Btn_Settings`, `Btn_Quit`.

### Event Dispatchers (My Blueprint → Event Dispatchers → +)

| Dispatcher | Payload |
|---|---|
| `OnPlay` | — |
| `OnSettings` | — |
| `OnQuit` | — |

### Event graph (one collapsed function `Handle Buttons`)

```
Btn_Play.OnClicked     → OnPlay.Broadcast
Btn_Settings.OnClicked → OnSettings.Broadcast
Btn_Quit.OnClicked     → OnQuit.Broadcast
```
The page never opens a level, never switches the switcher — it only broadcasts.

---

## Part 3 — WBP_Page_Settings

### Designer layout
`MenuBox` (Vertical Box): **Settings** title, `Sld_Music` (Slider, 0–1),
`Sld_SFX` (Slider), `Chk_Fullscreen` (Check Box), `Btn_Back`.

### Dispatchers / variables

| Name | Type |
|---|---|
| Dispatcher `OnBack` | — |
| `MusicVolume`, `SFXVolume` | Float (0–1) |
| `bFullscreen` | Boolean |

### Collapsed functions

**`Load Settings`** (from Event Construct):
```
Get Game Instance → Cast To BP_GameInstance → Load Settings (its function)
  → SET MusicVolume / SFXVolume / bFullscreen
  → push values into Sld_Music.Value / Sld_SFX.Value / Chk_Fullscreen.IsChecked
```

**`Save Settings`** (from each control's OnValueChanged):
```
SET MusicVolume/SFXVolume/bFullscreen ← widget value
→ Get Game Instance → Cast To BP_GameInstance → Save Settings (its function)
```

**`Handle Back`:** `Btn_Back.OnClicked → OnBack.Broadcast`.

### BP_GameInstance (the persistence owner — 2 collapsed functions)

Variables: `MusicVolume`, `SFXVolume` (Float), `bFullscreen` (Bool).

```
Load Settings:  Does Save Game Exist ("SG_Settings")? → False: defaults, return
                → Load Game from Slot → Cast To SG_Settings
                → copy the three values into self
Save Settings:  Create Save Game Object (SG_Settings)
                → copy the three values in → Save Game to Slot ("SG_Settings", 0)
                → GameUserSettings: Set Full Screen Mode + Apply (only when bFullscreen changed)
```
GameInstance survives level reloads — settings persist through death respawns
without any extra work.

---

## Part 4 — WBP_Page_Levels

### Designer layout
`MenuBox` (Vertical Box): **Levels** title, `LevelButtons` (Vertical Box —
one `Btn_Level_N` per level), `Btn_Back`.

### Dispatcher / variables

| Name | Type |
|---|---|
| Dispatcher `OnLevelSelected` | **Byte** `Index` |
| `LevelCount` | Integer | — matches RootUI's `LevelNames` length |

### Collapsed function `Handle Buttons` (per button)

```
Btn_Level_0.OnClicked → OnLevelSelected.Broadcast(0)
Btn_Level_1.OnClicked → OnLevelSelected.Broadcast(1)   (when L_Level_01 exists)
Btn_Back.OnClicked    → (no dispatcher — see wiring note)
```
> **Wiring note:** Levels' Back goes through RootUI like the others — add a
> `OnBack` dispatcher here too and bind it in `Bind Page Events`
> (`→ Switch Page(0)`), keeping the pages-never-route rule.

Buttons are **locked** (IsEnabled = false) for levels that don't exist yet —
the UI never hard-codes which levels ship.

---

## Part 5 — Showing the UI (BP_PlayerController — 1 collapsed function)

`Core/Blueprints/BP_PlayerController`:

```
Event BeginPlay → Create WBP_RootUI Widget → Add to Viewport (Z=100)
                → Set Show Mouse Cursor (true)
                → Set Input Mode Game and UI (so keyboard play keeps working)
```

Collapsed as `Create Root UI`. (Death-respawn's level reload re-runs
BeginPlay → UI rebuilds itself automatically. Nothing else spawns UI.)

---

## Part 6 — Verify

1. `py -3 Scripts\create_ui_assets.py` → all six assets `OK`.
2. PIE from the **title map**: Title shows → Play → Levels → click
   `L_Level_00` → level opens, UI hidden behind gameplay is fine (or set
   `Pages` collapsed on level open later).
3. Settings: drag Music slider → **quit PIE → relaunch** → value restored.
4. Die to the fake floor → level reloads → UI still present (GameInstance
   persisted, RootUI re-created by BeginPlay).
5. Back from Settings/Levels → Title. Quit → editor PIE session ends.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Button click does nothing | Dispatcher not bound in `Bind Page Events`, or the widget instance bound ≠ the one displayed (see the cast note in Part 1) |
| Switcher shows wrong page | `GetWidgetAtIndex` index ≠ slot order (0 Title, 1 Settings, 2 Levels) |
| Settings lost after relaunch | Game Instance Class not set in Project Settings, or slot name mismatch ("SG_Settings") |
| Settings lost after death reload | Save happening in the *widget* not the *GameInstance* — reload destroys widgets, keeps GameInstance |
| Can't click buttons in PIE | Mouse cursor not shown / Input Mode not `Game and UI` |
| Killed → reload → two RootUIs | Create-UI ran twice (check BeginPlay only, not Possessed-by-both) |

## Ownership

- `UI/` is pillar 6's home (UI, audio & progression) — coordinate if that
  pillar's owner is someone else; this guide is the contract.
- `BP_GameInstance`/`SG_Settings` live in `Core/` (shared — per Structure.md
  §4 rule 4, agree changes with pillar 1).
- Commit with the **editor closed** on `branch/Jones`.
- Suggested message — `feat: modular UI (title/settings/levels) + settings persistence`