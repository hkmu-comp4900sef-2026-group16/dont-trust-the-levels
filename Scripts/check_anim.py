"""Prepare for animation state switching.

Verify:
  1. all flipbooks exist with correct frame counts
  2. the sprite component's current state
  3. whether the character has the nodes we need (IsFalling, GetVelocity)
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
    eal = unreal.EditorAssetLibrary
    FLB = "/Game/DontTrustTheLevels/Player/Animations"

    p("=== FLIPBOOKS ===")
    p("%-28s %-8s %-8s %s" % ("NAME", "FRAMES", "FPS", "FIRST SPRITE"))
    p("-" * 70)
    for n in ("Idle", "Run", "Jump", "Fall", "DoubleJump", "Hit", "WallJump"):
        fb = eal.load_asset(FLB + "/FLB_Player_" + n)
        if not fb:
            p("%-28s MISSING" % n)
            continue
        kfs = fb.get_editor_property("key_frames")
        fps = fb.get_editor_property("frames_per_second")
        first = kfs[0].get_editor_property("sprite") if kfs else None
        p("%-28s %-8d %-8.0f %s" % (
            "FLB_Player_" + n, len(kfs), fps,
            first.get_name() if first else None))

    p("")
    p("=== sprite component on BP_Player ===")
    cls = eal.load_blueprint_class(
        "/Game/DontTrustTheLevels/Player/Blueprints/BP_Player")
    cdo = unreal.get_default_object(cls)
    for s in cdo.get_components_by_class(unreal.PaperFlipbookComponent):
        p("  %s" % s.get_name())
        for prop in ("source_flipbook", "play_rate", "looping",
                     "relative_rotation"):
            try:
                p("     %-20s = %s" % (prop, s.get_editor_property(prop)))
            except Exception:
                p("     %-20s <none>" % prop)
        # methods available for animation control
        ms = [m for m in dir(s) if not m.startswith("_") and
              any(k in m.lower() for k in ("flipbook", "play", "stop", "pause",
                                           "anim", "frame"))]
        p("     animation methods: %s" % sorted(ms))

    p("")
    p("=== character nodes we need ===")
    p("  IsFalling:        %s" % hasattr(unreal.Character, "is_falling"))
    p("  GetVelocity:      %s" % hasattr(unreal.Actor, "get_velocity"))
    p("  VectorLength:     %s" % hasattr(unreal.KismetMathLibrary, "v_size"))
    p("  SetFlipbook:      %s" % hasattr(unreal.PaperFlipbookComponent,
                                          "set_flipbook"))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=180)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
