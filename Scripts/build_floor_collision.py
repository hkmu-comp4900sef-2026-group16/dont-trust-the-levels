"""Build the floor collision for L_Level_00.

The tilemap provides the VISUAL (grass tiles). It has no working collision, so
we add a BlockingVolume spanning the same footprint.

Tilemap:  X -800..800,  Z -400..0   (4 rows tall, only row 0 has collision geom)
Floor:    X -800..800,  Z -100..0   (matches the grass row exactly)

BlockingVolume default size is 200x200x200 uu, so scale accordingly.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

ue = UERemote()
ue.connect(timeout=15, expected_project="DontTrustTheLevels")

CODE = r'''
import unreal, traceback
out = []
def p(s):
    out.append(str(s))

try:
    ell = unreal.EditorLevelLibrary

    # ---- find the tilemap and its footprint ----
    tm = None
    for a in ell.get_all_level_actors():
        if a.get_components_by_class(unreal.PaperTileMapComponent):
            tm = a
    if tm is None:
        p("no tilemap actor found - aborting")
    else:
        o, e = tm.get_actor_bounds(only_colliding_components=False)
        x0, x1 = o.x - e.x, o.x + e.x
        z_top = o.z + e.z
        p("tilemap X %.0f..%.0f  Z %.0f..%.0f" % (x0, x1, o.z - e.z, z_top))

        # ---- remove any previous collision floor ----
        for a in list(ell.get_all_level_actors()):
            if a.get_actor_label().startswith("DTL_FloorCollision"):
                ell.destroy_actor(a)
                p("removed old DTL_FloorCollision")

        # ---- create the BlockingVolume ----
        width = x1 - x0            # 1600
        cx = (x0 + x1) / 2.0       # 0
        thickness = 100.0          # one tile tall
        cz = z_top - thickness / 2.0   # -50

        # default BlockingVolume = 200 x 200 x 200 uu
        sx = width / 200.0
        sz = thickness / 200.0

        vol = ell.spawn_actor_from_class(
            unreal.BlockingVolume,
            unreal.Vector(cx, 0.0, cz),
            unreal.Rotator(0.0, 0.0, 0.0))
        if vol is None:
            p("SPAWN FAILED")
        else:
            vol.set_actor_label("DTL_FloorCollision")
            vol.set_actor_scale3d(unreal.Vector(sx, 1.0, sz))
            p("")
            p("created DTL_FloorCollision")
            p("  location = (%.1f, %.1f, %.1f)" % (cx, 0.0, cz))
            p("  scale    = (%.3f, %.3f, %.3f)" % (sx, 1.0, sz))
            o2, e2 = vol.get_actor_bounds(only_colliding_components=False)
            p("  X %.1f..%.1f   Y %.1f..%.1f   Z %.1f..%.1f" % (
                o2.x - e2.x, o2.x + e2.x,
                o2.y - e2.y, o2.y + e2.y,
                o2.z - e2.z, o2.z + e2.z))
            p("  X edge mod 100 = %.2f" % ((o2.x - e2.x) % 100))
            p("  Z edge mod 100 = %.2f" % ((o2.z - e2.z) % 100))
            for c in vol.get_components_by_class(unreal.PrimitiveComponent):
                p("  collision_enabled       = %s" % c.is_collision_enabled())
                p("  query_collision_enabled = %s" % c.is_query_collision_enabled())

    # ---- save the level ----
    p("")
    try:
        world = ell.get_editor_world()
        ok = unreal.EditorLoadingAndSavingUtils.save_map(
            world, "/Game/DontTrustTheLevels/Levels/L_Level_00")
        p("level saved: %s" % ok)
    except Exception as ex:
        p("save FAILED: %s" % repr(ex)[:120])

    p("")
    p("=== final actors ===")
    for a in ell.get_all_level_actors():
        loc = a.get_actor_location()
        p("  %-24s %-22s (%.0f, %.0f, %.0f)" % (
            a.get_actor_label()[:24], a.get_class().get_name()[:22],
            loc.x, loc.y, loc.z))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=150)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
