"""Set up the level background:

  1. Rename TM_Background -> TM_Terrain (it is the floor, not a backdrop)
  2. Create TS_Background tileset from T_Background_Blue_D (64x64 tiles)
  3. Create TM_BackgroundLayer tilemap
  4. Place a PaperTileMapActor at Y=-100 (behind the floor), scale 6.25
  5. Paint a grid of background tiles covering the room

Camera sits at Y=+1000 looking along -Y, so smaller Y = further away = behind.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

ue = UERemote()
ue.connect(timeout=20, expected_project="DontTrustTheLevels")
print("connected")

CODE = r'''
import unreal, traceback
out = []
def p(s):
    out.append(str(s))

def recompile(path):
    for _ in range(3):
        try:
            c = unreal.EditorAssetLibrary.load_blueprint_class(path)
            if c:
                return c
        except Exception:
            pass
    return None

try:
    eal = unreal.EditorAssetLibrary
    at = unreal.AssetToolsHelpers.get_asset_tools()
    ell = unreal.EditorLevelLibrary

    TS_DIR = "/Game/DontTrustTheLevels/Environment/TileSets"
    TM_DIR = "/Game/DontTrustTheLevels/Environment/TileMaps"

    # ---------- 1. rename the floor tilemap ----------
    p("=== 1. rename TM_Background -> TM_Terrain ===")
    src = TM_DIR + "/TM_Background"
    dst = TM_DIR + "/TM_Terrain"
    if eal.does_asset_exist(src):
        ok = eal.rename_asset(src, dst)
        p("  rename -> %s" % ("OK" if ok else "FAILED"))
    else:
        p("  TM_Background not found (already renamed?)")
    p("  TM_Terrain exists: %s" % eal.does_asset_exist(dst))

    # ---------- 2. tileset for the background ----------
    p("")
    p("=== 2. create TS_Background ===")
    ts_path = TS_DIR + "/TS_Background"
    if eal.does_asset_exist(ts_path):
        eal.delete_asset(ts_path)
        p("  deleted stale tileset")
    f = unreal.PaperTileSetFactory()
    ts = at.create_asset("TS_Background", TS_DIR, unreal.PaperTileSet, f)
    if ts is None:
        p("  CREATE FAILED")
    else:
        tex = eal.load_asset(
            "/Game/DontTrustTheLevels/Environment/Textures/T_Background_Blue_D")
        ts.set_editor_property("tile_size", unreal.IntPoint(64, 64))
        ts.set_editor_property("tile_sheet", tex)
        eal.save_loaded_asset(ts)
        p("  created; tile_size=%s sheet=%s" % (
            ts.get_editor_property("tile_size"),
            ts.get_editor_property("tile_sheet").get_name() if tex else None))

    # ---------- 3. tilemap for the background ----------
    p("")
    p("=== 3. create TM_BackgroundLayer ===")
    tm_path = TM_DIR + "/TM_BackgroundLayer"
    if eal.does_asset_exist(tm_path):
        eal.delete_asset(tm_path)
        p("  deleted stale tilemap")
    f2 = unreal.PaperTileMapFactory()
    tm = at.create_asset("TM_BackgroundLayer", TM_DIR, unreal.PaperTileMap, f2)
    if tm is None:
        p("  CREATE FAILED")
    else:
        tm.set_editor_property("tile_width", 64)
        tm.set_editor_property("tile_height", 64)
        eal.save_loaded_asset(tm)
        p("  created; tile %dx%d" % (
            tm.get_editor_property("tile_width"),
            tm.get_editor_property("tile_height")))

    # ---------- 4. place the actor ----------
    p("")
    p("=== 4. place the background actor ===")
    for a in list(ell.get_all_level_actors()):
        if a.get_actor_label().startswith("DTL_Background"):
            ell.destroy_actor(a)
            p("  removed old DTL_Background")

    # room: X -1600..1600, Z -400..0 ; visible height ~1800
    # 64px tiles at scale 6.25 -> 400uu each
    # cover X -2000..2000 (10 tiles), Z -1200..800 (5 tiles)
    loc = unreal.Vector(0.0, -100.0, 0.0)
    actor = ell.spawn_actor_from_class(unreal.PaperTileMapActor, loc,
                                       unreal.Rotator(0.0, 0.0, 0.0))
    if actor is None:
        p("  SPAWN FAILED")
    else:
        actor.set_actor_label("DTL_Background")
        actor.set_actor_scale3d(unreal.Vector(6.25, 6.25, 6.25))
        p("  spawned at (%.0f, %.0f, %.0f) scale 6.25" % (loc.x, loc.y, loc.z))

        comp = actor.get_components_by_class(unreal.PaperTileMapComponent)[0]
        comp.create_new_tile_map(10, 5, 64, 64)
        p("  create_new_tile_map(10, 5, 64, 64)")

        # paint
        info = unreal.PaperTileInfo()
        info.set_editor_property("tile_set", ts)
        info.set_editor_property("packed_tile_index", 0)
        n = 0
        for y in range(5):
            for x in range(10):
                try:
                    comp.set_tile(x, y, 0, info)
                    n += 1
                except Exception as ex:
                    p("  set_tile(%d,%d) FAILED: %s" % (x, y, repr(ex)[:70]))
                    break
        p("  painted %d tiles" % n)

        try:
            comp.set_layer_collision(0, False)
            p("  layer collision OFF (background must not collide)")
        except Exception:
            pass
        try:
            comp.rebuild_collision()
        except Exception:
            pass

        o, e = actor.get_actor_bounds(only_colliding_components=False)
        p("  bounds X %.0f..%.0f  Y %.0f..%.0f  Z %.0f..%.0f" % (
            o.x - e.x, o.x + e.x, o.y - e.y, o.y + e.y, o.z - e.z, o.z + e.z))
        p("  per tile = %.0f uu" % ((e.x * 2) / 10))

    # ---------- 5. save ----------
    p("")
    try:
        ok = unreal.EditorLoadingAndSavingUtils.save_map(
            ell.get_editor_world(), "/Game/DontTrustTheLevels/Levels/L_Level_00")
        p("level saved: %s" % ok)
    except Exception as ex:
        p("save FAILED: %s" % repr(ex)[:110])

    p("")
    p("=== final actors ===")
    for a in ell.get_all_level_actors():
        loc2 = a.get_actor_location()
        p("  %-24s %-22s (%.0f, %.0f, %.0f)" % (
            a.get_actor_label()[:24], a.get_class().get_name()[:22],
            loc2.x, loc2.y, loc2.z))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=240)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
