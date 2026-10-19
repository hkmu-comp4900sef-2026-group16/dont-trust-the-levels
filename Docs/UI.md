# Modular UI — Title / Settings / Levels · build guide

**Concept:** three screens behind one router widget. Every page is its own
Widget Blueprint that knows **nothing** about the others — it only *raises
Event Dispatchers*. A single `WBP_RootUI` owns a `WidgetSwitcher`, binds every
dispatcher, and routes. Adding a page = one new widget + one slot + one bind.

**Style rule (from BP_Player's Event Graph):** collapse when a chain is
*thick* (5+ nodes, reused, or one concept — `Kill Logic`, `Dash Logic`,
`Load Settings`). **Pages stay flat** — their chains are 2-node
`OnClicked → Call <Dispatcher>` pairs; wrapping them in functions hides
more than it shows. Modularity here is the **dispatcher boundary** (pages
broadcast, RootUI routes), not function indirection.

```
WBP_RootUI  (the ONLY widget anything else knows about)
├── RootCanvas (Canvas Panel)
│   ├── Pages (WidgetSwitcher)
│   │   ├── 0: WBP_Page_Title     ── raises: OnPlay, OnSettings
│   │   └── 1: WBP_Page_Levels    ── raises: OnLevelSelected(Index), OnBack
│   └── SettingsLayer (Overlay, full-anchor, hidden by default)
│       └── WBP_SettingsPopup     ── closes itself (no navigation, no OnBack)
├── Switch Page (Collapsed Function)        ← one node routes all pages
└── Bind Page Events (Collapsed Function)   ← wires every dispatcher in Construct
```

**Flow:** Title **Play** → Levels page → level button → `Open Level`.
Title **Settings** → popup opens **over** the title → Close → exactly where
you were. The popup never navigates — it only shows/hides itself.

**Persistence:** settings live in `SG_Settings` (SaveGame) via
`BP_GameInstance` — GameInstance survives `Open Level`, so volume/fullscreen
choices survive both level reloads (death respawn) and level switches.

**Why popup (decided 18 Oct):** a switcher page owns navigation ("Back →
Title"), which couples it to the menu it came from — the pages-don't-route
rule's one exception. A popup only closes: pure behavior, zero navigation,
and reusable later as the in-game pause menu over gameplay.

---

## Part 0 — Assets (script does this)

```bat
:: with the editor open, PIE stopped:
py -3 Scripts\create_ui_assets.py
py -3 Scripts\import_ui_art.py
```

Two scripts, both idempotent:

**1. `create_ui_assets.py`** — creates `UI/WBP_Page_Title`,
`UI/WBP_Page_Settings`, `UI/WBP_Page_Levels`, `UI/WBP_RootUI`,
`Core/Blueprints/BP_GameInstance` (parent `GameInstance`),
`Core/Data/SG_Settings` (parent `SaveGame`).

**2. `import_ui_art.py`** — imports the Pixel Adventure menu art with the
correct texture settings (Nearest filter, no mips, UserInterface2D
compression — Structure.md §10.2) into `UI/Textures/`:

| Source (`Assets\PixelAdventure\Free\Menu\`) | Imported as | Used on |
|---|---|---|
| `Buttons\Play.png` | `T_UI_Btn_Play_D` | Title — Play |
| `Buttons\Settings.png` | `T_UI_Btn_Settings_D` | Title — Settings |
| `Buttons\Close.png` | `T_UI_Btn_Quit_D` | Title — Quit (the X) |
| `Buttons\Back.png` | `T_UI_Btn_Back_D` | Settings/Levels — Back |
| `Buttons\Volume.png` | `T_UI_Btn_Volume_D` | Settings — slider icon |
| `Background\Blue.png` | `T_UI_Background_Blue_D` | every page — backdrop |
| `Levels\01.png` … `04.png` | `T_UI_Level_01_D` … `_04_D` | Levels grid (import only levels that exist; 50 available) |

Raw PNGs stay in `Assets\` (gitignored) — only the imported
`Content\...\UI\Textures\T_UI_*_D` assets are committed.

**Hand step (Python cannot):** Project Settings → Maps & Modes →
**Game Instance Class = BP_GameInstance**. (World-settings are not exposed to
Python — Structure.md §11.)

---

## Part 1 — WBP_RootUI (the router)

### Designer layout

1. Root → **Canvas Panel** (`RootCanvas`).
2. Canvas → **Widget Switcher** (`Pages`), anchor full-rectangle.
3. Drag **two** page widgets into `Pages` (order: 0 Title, 1 Levels).
4. Canvas → **Overlay** (`SettingsLayer`), anchor full-rectangle — sibling
   **after** `Pages` in the hierarchy (drawn on top), Visibility =
   **Collapsed** by default.
5. Drag `WBP_SettingsPopup` into `SettingsLayer`.
   ⚠️ Its Overlay slot must be set **Horizontal = Fill · Vertical = Fill**
   (19 Oct fix — the runtime `Add Child` path defaulted Left/Top, which
   pinned the popup top-left at desired size and broke centering; the
   designer-authored slot is the fix. If the popup is ever re-created at
   runtime instead, the equivalent is `Add Child to Overlay` + both
   `Set Alignment in Overlay Slot = Fill` nodes — plain `Add Child` is not
   enough, its OverlaySlot defaults Left/Top.)

### Variables

| Name | Type | Notes |
|---|---|---|
| `PageIndex` | Integer | internal — current page |
| `LevelNames` | String Array | level order, e.g. `["L_Level_01", "L_Level_02"]` — append as levels ship |
| `Btn_Levels` | Button | corner button (Designer) — gameplay-only "back to levels" |

### Event Construct (as built 19 Oct)

```
Event Construct
  → Bind Page Events (collapsed)
  → Get Game Instance → Cast To BP_GameInstance
      → Branch (bInGame?)
           True  → Switch Page(PendingPage) → SET PendingPage = 0   (consume)
                   → Btn_Levels.Visibility = Visible
           False → Switch Page(PendingPage) → SET PendingPage = 0   (consume)
                   → Btn_Levels.Visibility = Collapsed
  → Hide Settings (start clean)
```
`PendingPage` (Integer, on BP_GameInstance, default 0) lets gameplay request
"show Levels after the next load": the corner button sets it to 1 and opens
`L_Menu`; the fresh Construct consumes it. Consume-on-read keeps normal boots
on Title.

### Function `Complete Level` (called by BP_ExitDoor)

```
Get Current Level Name (pure, Remove Prefix ✓)
  → Find (LevelNames, Item ← level name) → Index
  → Index + 1 → Next
  → Branch (Next < Length(LevelNames))
       True  → Get (a copy) (LevelNames[Next]) → Open Level (by name)
       False → Open Level (by name) = "L_Menu"      ← no next level → title
```
The bounds branch makes the array access unreachable when there is no next
level — no Blueprint runtime error, by construction. The last level's door
returns to the title over `L_Menu` (map-derived `bInGame=false` shows it).
`BP_ExitDoor` calls this via: Overlap → Print "Level Complete" → Delay →
Get Player Controller(0) → Cast To BP_PlayerController → Get Root UI →
**Complete Level**. (Requires the PC to store its RootUI unconditionally —
see Part 5.)

### Functions `Show Settings` / `Hide Settings` (no I/O)

```
Show:  SET SettingsLayer.Visibility = Visible
Hide:  SET SettingsLayer.Visibility = Collapsed
```
Two one-node functions (or plain chains). The popup itself never touches
the switcher.

### Function `Switch Page` (inputs: `NewIndex` int)

```
SET PageIndex = NewIndex
→ Set Active Widget (Target = Pages, Widget = Pages.GetWidgetAtIndex(NewIndex))
```
All page routing goes through this one node.

### Function `Bind Page Events` (called from Event Construct)

```
Get Widget From Class (WBP_Page_Title)  → Bind Event to OnPlay      → Switch Page(1)
                                        → Bind Event to OnSettings  → Show Settings
Get Widget From Class (WBP_Page_Levels)   → Bind Event to OnLevelSelected
        → custom event "Open Selected Level"
                                          → Bind Event to OnBack    → Switch Page(0)
```

> `Get Widget From Class` here returns the same instances the switcher
> already holds (same class + same outer) — binding works because the
> dispatcher belongs to the widget object the switcher displays. If a bind
> ever doesn't fire, the fix is: cast the switcher's child instead
> (`Pages.GetWidgetAtIndex(0) → Cast To WBP_Page_Title → Bind Event`).

### Event Construct

```
Event Construct → Bind Page Events (collapsed) → Switch Page(0)
                                              → Hide Settings (start clean)
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
**Image** (`Img_Background`, anchor full-rectangle) → Horizontal Box
(`MenuBar`), centered:
**Title text** (`Don't Trust The Levels`, default font is fine to start —
the 8×10 pixel-font atlases in `Menu/Text/` are optional decoration),
then two **Buttons** laid out **horizontally** (the art is square —
21×22 px tiles that upscale to chunky icon-buttons, not wide banners).
**No child Images** — the texture goes directly on each Button's Style:

| Button | Image brush (Style → Normal/Hovered/Pressed = same texture) |
|---|---|
| `Btn_Play` | `T_UI_Btn_Play_D` |
| `Btn_Settings` | `T_UI_Btn_Settings_D` |

*(Quit button removed from v1 — the decision: not needed. `T_UI_Btn_Quit_D`
stays imported for a future pause menu.)*

**How:** select the Button → Details → **Appearance → Style** → expand
**Normal → Brush** → pick the texture; repeat for **Hovered** (same texture,
Tint ~0.85 brightness for feedback) and **Pressed** (same texture). One
widget per button — the button IS the image.

**Title backdrop (decided — "middle path"):** v1 uses the flat
`T_UI_Background_Blue_D` so the menu stays static (no world simulation
behind menus). v2 upgrade, once the flow works: replace the brush with a
**level capture** (screenshot of `L_Level_00` or its terrain art) so the
title reads as "this is the game" — zero simulation cost either way. The
widget layout does not change; only the brush swaps.

Pixel Adventure buttons are single-frame, so all three states share one
texture; tint **Hovered** slightly (e.g. 0.85 brightness) for feedback.
Buttons must be the actual `Button` widget (not raw Images) so they take
clicks.

**Sizing (pixel-perfect):** the art is tiny (21×22 px) — size each **Button
itself** (its Horizontal Box slot → Size → Custom) to a whole-number
multiple of the art: e.g. 8× → 168×176 for Play/Settings, 120×128 for Quit
(15×16 × 8), or a uniform 120×128 for all three (Quit just renders slightly
smaller art inside). Set each brush **Margin 0 / tiling
No-Horizontal-No-Vertical** so the texture is not stretched. At 1080p these
sizes land near whole
px/texel ratios — crisp, per Structure.md §10.5.

### Event Dispatchers (My Blueprint → Event Dispatchers → +)

| Dispatcher | Payload |
|---|---|
| `OnPlay` | — |
| `OnSettings` | — |

### Event graph (flat — no collapse needed)

```
Btn_Play.OnClicked     → Call OnPlay      (right-click → "Call OnPlay" —
                                           this node IS the broadcast)
Btn_Settings.OnClicked → Call OnSettings
```
The page never opens a level, never switches the switcher — it only broadcasts.
Two two-node chains: readable as-is, collapsing them buys nothing.

---

## Part 3 — WBP_SettingsPopup

### Designer layout
Root of the popup = one **Canvas Panel**, three layers:
1. `Img_Dim` — **Image**, anchor full-rectangle, brush = blue background
   **Color = black, Alpha ≈ 0.5** (dim veil; also blocks clicks to the
   page beneath)
2. `Panel` — **Border** (or Image), anchor **center**, ~420×300, opaque
3. In `Panel` → **Vertical Box** (`MenuBox`): **Header row** (Horizontal
   Box: stretch **Space Filler** / Size = Fill, then `Btn_Close` — the X
   hugs the card's top-right), **Settings** title, one
   **Horizontal Box** per slider row:
`Img_Volume` (**Image** widget with brush `T_UI_Btn_Volume_D`, ~84×88 = 4×
art — a plain Image, not a button) + `Sld_Music` (Slider, 0–1, fill
remaining width), then `Sld_SFX` row (same shape).

**No Check Box (decided 18 Oct):** Fullscreen dropped from v1 — only the
two volume sliders ship. `bFullscreen` stays in `BP_GameInstance`/`SG_Settings`
(harmless, already built) but no widget drives it in v1; revisit in v2
(UI_Backlog.md).

### Variables (NO dispatchers — the popup doesn't navigate)

| Name | Type |
|---|---|
| `MusicVolume`, `SFXVolume` | Float (0–1) |
| `bFullscreen` | Boolean |

### Functions (these earn their keep — real multi-node chains)

**`Load Settings`** (from Event Construct):
```
Get Game Instance → Cast To BP_GameInstance → Load Settings (its function)
  → SET MusicVolume / SFXVolume / bFullscreen
  → push values into Sld_Music.Value / Sld_SFX.Value / Chk_Fullscreen.IsChecked
```

**`Save Settings`** (from each slider's OnValueChanged):
```
SET MusicVolume/SFXVolume ← widget value
→ Get Game Instance → Cast To BP_GameInstance → Save Settings (its function)
```

**`Handle Close` (flat):** `Btn_Close.OnClicked → Set Visibility
(Target = **self**, Collapsed) → Get Owning Player Controller →
Set Input Mode Game and UI (Do Not Lock, Hide Cursor During Capture off)
→ Set Show Mouse Cursor (true)`. The popup hides **itself** — no dispatcher,
no navigation — and re-asserts the UI input mode on the way out.

> **⚠️ Two rules learned 19 Oct (both broke in testing):**
> 1. **Never hide a UserWidget by collapsing its root child.** Collapsing the
>    popup's internal root canvas leaves the popup *widget shell* Visible —
>    the shell still occupies the hit-test grid, so every click above the
>    pages underneath is swallowed (an invisible click shield). Collapse
>    **self** so the whole subtree leaves hit-testing.
> 2. **Re-assert the input mode whenever UI hands control back** (popup
>    close, page switch). A stale game-only mode kills Slate clicks globally
>    (`bEnableClickEvents/MouseOver = False` fingerprint) while everything
>    *looks* fine. Same call as BeginPlay's — cheap insurance.
>
> **⚠️ KNOWN ISSUE (parked 19 Oct, see UI_Backlog.md):** even with both
> rules applied, closing the popup can still leave buttons dead. Repro +
> frozen-PIE diagnosis state recorded in UI_Backlog.md §9 — do not
> re-debug from scratch; continue from the recorded measurement.

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
`Img_Background` (`T_UI_Background_Blue_D`) → `MenuBox` (Vertical Box):
**Levels** title, `LevelGrid` (**Uniform Grid Panel**, 4 columns — the art
is a near-square 19×17 tile) — one **Button** per level, texture directly
on its Style (`Btn_Level_1` Normal/Hovered/Pressed = `T_UI_Level_01_D`,
`Btn_Level_2` → `T_UI_Level_02_D`, …), **Disabled** = same texture with a
grey tint → locked tiles dim automatically when `IsEnabled = false`.
`Btn_Back` (`T_UI_Btn_Back_D`, ~120×128).

**Tile sizing:** each Button ~152×136 (8× the 19×17 art) via its grid cell,
cell padding ~12 px. With 4 levels that's one clean row; more levels wrap
to new rows automatically — the grid, not the buttons, owns the layout.

Level tiles are the Level Devil-style grid: the art is a numbered tile, so
the button needs no text. Import only the tiles for levels that exist
(start with 01–04); enable more later by importing the next PNG and adding
one button.

### Dispatcher / variables

| Name | Type |
|---|---|
| Dispatcher `OnLevelSelected` | **Byte** `Index` |
| `LevelCount` | Integer — matches how many level buttons are on the page |

### Event graph (flat — no collapse needed)

```
Btn_Level_1.OnClicked → OnLevelSelected.Broadcast(0)   (payload = 0-based index)
Btn_Level_2.OnClicked → OnLevelSelected.Broadcast(1)   (when L_Level_01 exists)
Btn_Back.OnClicked    → Broadcast OnBack               (RootUI: → Switch Page(0))
```
> **Wiring note (verified 19 Oct):** all three buttons need their OnClicked
> component-bound events (`Details → Events → OnClicked → +`). `Btn_Back` was
> found unwired in testing — the dispatcher + RootUI binding existed but the
> button never broadcast. Search "on back" in the actions menu gives both the
> **Broadcast OnBack** call (correct) and **Bind Event to OnBack** (wrong —
> that's for subscribing).

Buttons are **locked** (IsEnabled = false) for levels that don't exist yet —
the UI never hard-codes which levels ship.

---

## Part 5 — Showing the UI (BP_PlayerController — as built 19 Oct)

`Core/Blueprints/BP_PlayerController`:

```
Event BeginPlay
  → Branch on map: Get Current Level Name (Remove Prefix ✓) == "L_Menu"?
      → Get Game Instance → Cast To BP_GameInstance → SET bInGame = (not L_Menu)
  → Create WBP_RootUI Widget
  → SET RootUI (variable, WBP_RootUI reference)      ← UNCONDITIONAL
  → Add to Viewport (Z=100)
  → Set Show Mouse Cursor (true)
  → Set Input Mode Game and UI
```

> **⚠️ Two rules learned 19 Oct:**
> 1. **Store the RootUI reference before any branch.** The variable must be
>    set on *every* load regardless of `bInGame` — a SET inside a branch left
>    it `None` on gameplay loads and `BP_ExitDoor`'s `Complete Level` call
>    failed with *Accessed None trying to read property RootUI*. Branches
>    decide **behavior**, never **existence**.
> 2. **`bInGame` is derived from the map, not remembered.** PIE from a
>    gameplay level must go straight into gameplay (no title overlay over
>    Level 1/2), and the title background is `L_Menu` by rule. Deriving at
>    every BeginPlay makes both true and removes session-order state.

Death-respawn's level reload re-runs BeginPlay → UI rebuilds + `bInGame`
re-derives automatically. Nothing else spawns UI.

---

## Part 6 — Verify

1. `py -3 Scripts\create_ui_assets.py` → all six assets `OK`;
   `py -3 Scripts\import_ui_art.py` → all `T_UI_*_D` textures imported.
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
| Can't click buttons after closing Settings | Popup collapsed its root child instead of itself (click shield) — see Part 3 Handle Close; then re-assert input mode (Part 3) |
| Settings popup off-center | Popup's Overlay slot not Fill/Fill — see Part 1 step 5 |
| Dying in a later level reloads Level 1 | `BP_Player` Kill used a hardcoded by-reference level — use Get Current Level Name (DeathRespawn.md Part 3) |
| *Accessed None trying to read property RootUI* | PC's `SET RootUI` inside a branch (or unwired) — must run unconditionally before AddToViewport (Part 5 rule 1) |
| Title overlay shows over gameplay levels | `bInGame` not map-derived — see Part 5 rule 2 |
| Back button does nothing | `Btn_Back.OnClicked` never component-bound — Part 4 wiring note |
| Killed → reload → two RootUIs | Create-UI ran twice (check BeginPlay only, not Possessed-by-both) |

## Ownership

- `UI/` is pillar 6's home (UI, audio & progression) — coordinate if that
  pillar's owner is someone else; this guide is the contract.
- `BP_GameInstance`/`SG_Settings` live in `Core/` (shared — per Structure.md
  §4 rule 4, agree changes with pillar 1).
- Commit with the **editor closed** on `branch/Jones`.
- Suggested message — `feat: modular UI (title/settings/levels) + settings persistence`