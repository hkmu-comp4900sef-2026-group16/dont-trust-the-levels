"""Prepare BP_Player for movement: tune the CharacterMovementComponent and
report the sprite setup.

Movement TUNING is scriptable (CDO properties). Movement BINDING (input graph)
is not - that is human work in the editor.
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
    eal = unreal.EditorAssetLibrary
    BP = "/Game/DontTrustTheLevels/Player/Blueprints/BP_Player"

    cls = eal.load_blueprint_class(BP)
    if cls is None:
        p("could not load BP_Player_C")
    else:
        cdo = unreal.get_default_object(cls)

        # ---- 1. report the sprite ----
        p("=== sprite component ===")
        sprites = cdo.get_components_by_class(unreal.PaperFlipbookComponent)
        for s in sprites:
            p("  name = %s" % s.get_name())
            for prop in ("source_flipbook", "relative_rotation",
                         "relative_location", "relative_scale3d"):
                try:
                    p("     %-20s = %s" % (prop, s.get_editor_property(prop)))
                except Exception:
                    p("     %-20s <none>" % prop)

        # ---- 2. report the capsule ----
        p("")
        p("=== capsule ===")
        for c in cdo.get_components_by_class(unreal.CapsuleComponent):
            for prop in ("capsule_half_height", "capsule_radius"):
                try:
                    p("  %-22s = %s" % (prop, c.get_editor_property(prop)))
                except Exception:
                    pass

        # ---- 3. tune the movement component ----
        p("")
        p("=== movement tuning ===")
        movs = cdo.get_components_by_class(unreal.CharacterMovementComponent)
        if not movs:
            p("  NO CharacterMovementComponent found")
        else:
            mc = movs[0]
            p("  before:")
            for prop in ("max_walk_speed", "jump_z_velocity", "air_control",
                         "gravity_scale", "max_fall_speed"):
                try:
                    p("     %-22s = %s" % (prop, mc.get_editor_property(prop)))
                except Exception:
                    p("     %-22s <none>" % prop)

            # sensible side-scroller values
            settings = [
                ("max_walk_speed", 500.0),      # 5 tiles/sec
                ("jump_z_velocity", 650.0),     # clears ~2 tiles
                ("air_control", 0.35),          # default 0.05 is too stiff
                ("gravity_scale", 1.6),         # snappier arcs
                ("max_fall_speed", 1200.0),
            ]
            p("  setting:")
            for prop, val in settings:
                try:
                    mc.set_editor_property(prop, val)
                    p("     %-22s = %s" % (prop, val))
                except Exception as ex:
                    p("     %-22s FAILED: %s" % (prop, repr(ex)[:80]))

            p("  after:")
            for prop, _ in settings:
                try:
                    p("     %-22s = %s" % (prop, mc.get_editor_property(prop)))
                except Exception:
                    pass

        # ---- 4. character rotation settings ----
        p("")
        p("=== character rotation ===")
        for prop in ("orient_rotation_to_movement", "b_orient_rotation_to_movement",
                     "use_controller_rotation_yaw", "use_controller_rotation_pitch"):
            try:
                p("  %-34s = %s" % (prop, cdo.get_editor_property(prop)))
            except Exception:
                p("  %-34s <none>" % prop)

        # ---- save ----
        bp = eal.load_asset(BP)
        if bp:
            eal.save_loaded_asset(bp)
            p("")
            p("saved BP_Player")

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=180)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
