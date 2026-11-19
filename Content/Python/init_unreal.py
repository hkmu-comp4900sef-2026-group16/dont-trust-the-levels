"""Editor startup hook: keep BP_EnemyPlatform markers in sync with the tiles.

UE 4.27 runs this file automatically when the Python plugin starts. It only
watches the editor world; PIE and packaged games never execute it.

Designers paint the Floor layer in TM_Background and save the level. After a
short debounce this watcher rebuilds the auto markers so they are baked into
the .umap before the level is played or packaged. Markers tagged
EnemyPlatform.Auto are owned by this tool; manual markers are left alone.
"""
import os
import sys
import time

import unreal

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import enemy_platforms  # noqa: E402

AUTO_SYNC_ENABLED = True
CHECK_INTERVAL_SECONDS = 2.0
DEBOUNCE_SECONDS = 1.5

_state = {
    "level": "",
    "signature": None,
    "pending_signature": None,
    "pending_since": 0.0,
    "last_check": 0.0,
}
_handle = None


def _apply_if_needed(level_name):
    data = enemy_platforms.build_plan()
    if data.get("error"):
        return
    if enemy_platforms.markers_match_plan(data):
        return
    result = enemy_platforms.apply_plan(data, save=False)
    if result.get("error"):
        unreal.log_warning("EnemyPlatforms: " + result["error"])
        return
    unreal.log(
        "EnemyPlatforms: {} marker(s) rebuilt for {} (deleted {}, skipped {})."
        .format(result.get("spawned", 0), level_name,
                result.get("deleted", 0), result.get("skipped_narrow", 0)))
    for warning in result.get("warnings", [])[:4]:
        unreal.log_warning("EnemyPlatforms: " + warning)


def _tick(delta_seconds):
    if not AUTO_SYNC_ENABLED:
        return
    now = time.time()
    if now - _state["last_check"] < CHECK_INTERVAL_SECONDS:
        return
    _state["last_check"] = now

    try:
        world = unreal.EditorLevelLibrary.get_editor_world()
        if not world:
            return
        if unreal.EditorLevelLibrary.get_game_world():
            return  # PIE/simulate is running; never mutate the source level.
        level_name = world.get_name()
    except Exception:
        return

    signature = enemy_platforms.tile_signature()
    if not signature:
        return

    if level_name != _state["level"]:
        _state["level"] = level_name
        _state["signature"] = signature
        _state["pending_signature"] = signature
        _state["pending_since"] = now
        _apply_if_needed(level_name)
        return

    if signature != _state["signature"]:
        _state["signature"] = signature
        _state["pending_signature"] = signature
        _state["pending_since"] = now
        return

    if (_state["pending_signature"] is not None
            and now - _state["pending_since"] >= DEBOUNCE_SECONDS):
        _state["pending_signature"] = None
        _apply_if_needed(level_name)


def _shutdown():
    global _handle
    if _handle is not None:
        try:
            unreal.unregister_slate_post_tick_callback(_handle)
        except Exception:
            pass
        _handle = None


if _handle is None:
    _handle = unreal.register_slate_post_tick_callback(_tick)
    unreal.register_python_shutdown_callback(_shutdown)
    unreal.log("EnemyPlatforms: editor auto-sync enabled.")
