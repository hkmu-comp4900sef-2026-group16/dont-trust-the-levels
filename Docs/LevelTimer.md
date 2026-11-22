# Level timer and records

Current implementation and validation: 2026-11-21, Unreal Engine 4.27.

## Ownership and event flow

- `BP_PlayerController` starts `BP_GameInstance.StartLevelTimer` when gameplay UI and input are initialized. It derives the map name without the PIE prefix. Entering `L_Menu` calls `AbortLevelTimer` and removes gameplay UI through the existing navigation flow.
- `BP_GameInstance` owns runtime state: `ActiveLevelId`, `LevelTimerStartSeconds`, `LevelFinalSeconds`, `bLevelTimerRunning`, and `bLevelNewBest`. `GetLevelElapsedSeconds` uses game time, so pausing excludes elapsed time. Time dilation also affects this clock.
- `WBP_LevelHUD` reads elapsed time and formats it as `MM:SS:hundredths`; widget Tick does not accumulate authoritative time.
- `BP_ExitDoor` requires a key and a living player. It calls `FinishLevelTimer` before the existing completion delay. Duplicate completion calls are ignored once the timer stops.
- Death calls `StopLevelTimer`: freeze the elapsed value without saving a completion. Retry creates a new run. `AbortLevelTimer` clears the active run on menu navigation.
- `WBP_LevelResultPopup` owns result presentation and dispatches Retry / Next / Level Select to the HUD's navigation flow. Clear results show final time, best time, and NEW BEST only after a successful improved-record save.

## Persistent data and UI

`SG_Settings.BestTimes` is a Map<Name, float> in the existing `SG_Settings` slot (user index 0). Keys are stable map names, not list indices or translated labels. Values remain numeric seconds; comparisons happen before display formatting. Only a strictly smaller completed time replaces an existing record. Equal and slower times retain the existing value.

`GetSettingsSave` loads the existing object or creates it for a missing slot. Both record saves and `Save Settings` reuse that object, preserving MusicVolume, SFXVolume, bFullscreen and BestTimes together. Older compatible saves have an empty map until a completion is recorded. A wrong save class is not overwritten.

Title RECORDS opens `WBP_Page_Records`. It builds `WBP_RecordRow` children from `WBP_RootUI.LevelNames`, refreshes on entry, and displays `--:--:--` for missing records. Current switcher indices are 0 Title, 1 Levels, 2 Records; Settings uses its separate overlay layer. These indices supersede the original setup guide in UI.md.

## Adding levels and future Time Attack

Add stable map names to `WBP_RootUI.LevelNames` in progression order and add the corresponding level-select button through the current selection dispatcher. Records and Next use the common list; timer initialization and exit-door completion need no copied Level Blueprint logic. Keep map identifiers stable if existing records must remain associated with a level. Include added maps in packaging.

A future multi-map Time Attack should own separate session state in GameInstance: mode, route, accumulated completed segments and current segment start. Capture each segment before travel, carry the accumulated value across maps, and reset only when starting or abandoning the entire session. Keep its save keys and restart policy separate from normal per-level best times. Full Time Attack is intentionally not implemented.

## Verification

Controlled PIE integration checks passed on L_Level_01, L_Level_02 and L_Level_03:

- HUD timer, level intro and key status reset on new levels and retries.
- Repeated pause/settings/resume cycles exclude paused time and preserve the original run start.
- Retry cancellation continues the run; confirmation starts from zero.
- Death stops timing without writing a best time; an exit without a key does not record a completion.
- Actual key and door overlaps capture final time before the one-second result delay. Next resets the run, and the last level hides Next.
- Result-to-level-select and gameplay-settings-to-title navigation restore clickable menu controls and clear the active gameplay timer.
- Leaving an unfinished level preserves the save bytes.
- Controlled numeric cases 70, 75, 58.5, 58.5 retain bests 70, 70, 58.5, 58.5, with NEW BEST only for the first and third cases. Repeated completion calls do not overwrite the result.
- Changing the Music slider preserves the entire BestTimes map. A fresh PIE session loads the saved audio value and the 58.5-second validation record from disk.

Tests used temporary actor isolation and position changes to exercise actual key/goal overlaps; they are UI integration checks, not complete manual platforming playthroughs. No test actor changes were saved to maps. The original user save was restored byte-for-byte and test callbacks were removed. Blueprint compilation passed. Packaged-build testing remains separate.
