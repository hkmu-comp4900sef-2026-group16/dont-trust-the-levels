# UI backlog — v2 items parked during v1 build (branch/Jones)

Decided 18 Oct 2026 while building the modular UI (Docs/UI.md).

## 1. Title backdrop = level capture ("middle path")
- v1 ships flat `T_UI_Background_Blue_D` (static menu, no world sim).
- v2: replace `WBP_Page_Title.Img_Background` brush with a captured image of
  `L_Level_00` (editor screenshot or terrain art composite). Layout unchanged;
  only the brush swaps. Owner: UI pillar.

## 2. Levels page = per-level preview thumbnails
- v1 uses the numbered Pixel Adventure tiles (`T_UI_Level_01_D`...).
- v2: capture a screenshot per level, import as `T_UI_Level_NN_Preview_D`,
  feed the same buttons. The tile grid and dispatcher design do not change.
- Needs: a repeatable PIE/screenshot capture step per level (Scripts tooling).

## 3. Menu-over-level mode (stretch)
- Alternative flow: menu shows over the *live* level (RootUI spawned in
  `L_Level_00`, gameplay gated behind Play). Parked - v1 uses a dedicated
  title map. Revisit after the full flow works.

## 4. Soft respawn (`BPI_Resettable`) — from DeathRespawn.md
- Level-reload respawn ships in v1 (resets everything for free).
- v2: implement `BPI_Resettable` on traps + a soft teleport respawn for
  faster retries. Unblocks: speedrunning feel, no map reload flash.

## 5. Pixel-font text (optional polish)
- `Assets/PixelAdventure/Free/Menu/Text/Text (White|Black) (8x10).png`
  atlases exist. v1 uses the default font; v2 can slice + bitmap-font them
  for the full pixel look.

## 8. Slider art (v1 uses engine-drawn sliders)
- The pack has a volume ICON but no slider track/handle art.
- v1 ships default-engine sliders; v2 can slice a pixel track/handle (or
  draw one) and set Brush on the Slider widget for the full pixel look.

## 6. Quit button (removed from title v1)
- Decision 18 Oct 2026: not needed on the title screen.
- `T_UI_Btn_Quit_D` stays imported; natural future home is a pause menu
  (ESC in-game) rather than the title.

## 9. KNOWN ISSUE — buttons dead after closing the Settings popup (parked 19 Oct)

**Repro:** PIE → title → Settings → close with the X → all page buttons
dead (no hover, no click) for the rest of the session. Cursor still moves.

**State when parked (all verified via live-editor measurement):**
- Popup widget itself: `Collapsed` ✓, Overlay slot Fill/Fill ✓ (centering fix
  in place), **exactly one** RootUI instance ✓, crosshair
  `SelfHitTestInvisible` (harmless) ✓ — the widget tree is CLEAN.
- Close chain (WBP_SettingsPopup): `OnClicked(Btn_Close) → Set Visibility
  (self, Collapsed) → Set Input Mode Game and UI (Do Not Lock, no hide) →
  Set Show Mouse Cursor(true)` — the two 19-Oct rules are APPLIED and did
  NOT fix it.
- Frozen-PIE fingerprint: PlayerController
  `bEnableClickEvents=False`, `bEnableMouseOverEvents=False`
  (`bShowMouseCursor=True`). NOTE: flipping these two properties live did
  nothing (they gate 3D-world click events, not Slate) — red herring.
- The same dead-clicks symptom also appears on the Levels page flow, which
  points at **Switch Page / input-mode re-assertion** as the shared suspect,
  not the popup alone.

**Next step (do NOT re-debug from scratch):**
1. Reproduce + FREEZE PIE in the broken state, keep PIE running.
2. Run `Scripts/_decisive_fix_scan.py` (live input-mode re-assert via
   `WidgetLibrary.set_input_mode_game_and_ui` + full widget census +
   SlateBlueprintLibrary probe). If clicks revive → mechanism proven; make
   the re-assert permanent in `Switch Page` (and popup close).
3. If not → the census names any remaining hit-test shield; else suspect
   Slate-level stuck pointer capture (slider drag before close) — try
   focus/capture reset in the close chain.
4. Also candidate: RootUI Construct's `Hide Settings` + popup self-Collapse
   fighting (two visibility owners) — unify to ONE owner (the popup).

## 7. Fullscreen setting (dropped from v1)
- Decision 18 Oct 2026: only Music + SFX sliders ship in v1.
- `bFullscreen` remains in BP_GameInstance/SG_Settings (already built,
  harmless); v2 adds the Check Box + GameUserSettings apply logic.