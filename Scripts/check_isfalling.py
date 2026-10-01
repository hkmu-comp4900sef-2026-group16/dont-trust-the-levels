"""Where does 'Is Falling' live - Character or CharacterMovementComponent?

This decides which node the user must add in the Blueprint graph.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

ue = UERemote()
ue.connect(timeout=20, expected_project="DontTrustTheLevels")

CODE = r'''
import unreal, traceback
out = []
def p(s):
    out.append(str(s))

try:
    p("=== ACharacter: fall / air related ===")
    ms = [m for m in dir(unreal.Character) if not m.startswith("_")
          and any(k in m.lower() for k in ("fall", "air", "jump", "land"))]
    p("  %s" % sorted(ms))

    p("")
    p("=== CharacterMovementComponent: fall / air related ===")
    ms2 = [m for m in dir(unreal.CharacterMovementComponent) if not m.startswith("_")
           and any(k in m.lower() for k in ("fall", "air", "jump", "land",
                                            "moving", "walk"))]
    p("  %s" % sorted(ms2))

    p("")
    p("=== does the BP_Player CDO expose is_falling? ===")
    cls = unreal.EditorAssetLibrary.load_blueprint_class(
        "/Game/DontTrustTheLevels/Player/Blueprints/BP_Player")
    cdo = unreal.get_default_object(cls)
    p("  cdo has is_falling: %s" % hasattr(cdo, "is_falling"))
    mc = cdo.get_components_by_class(unreal.CharacterMovementComponent)
    if mc:
        p("  movement comp has is_falling: %s" % hasattr(mc[0], "is_falling"))
        try:
            p("  current is_falling() = %s" % mc[0].is_falling())
        except Exception as ex:
            p("  call failed: %s" % repr(ex)[:90])

    p("")
    p("=== velocity access ===")
    p("  cdo has get_velocity: %s" % hasattr(cdo, "get_velocity"))
    if mc:
        p("  movement comp velocity prop: %s" % (
            "velocity" in [x for x in dir(mc[0]) if not x.startswith("_")]))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=180)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
