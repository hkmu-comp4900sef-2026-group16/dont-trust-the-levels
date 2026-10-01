"""Get the exact set_flipbook signature - the bReset parameter is critical
(without it, the animation restarts every frame and looks frozen)."""
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
    p("=== set_flipbook signature ===")
    try:
        p(unreal.PaperFlipbookComponent.set_flipbook.__doc__)
    except Exception as ex:
        p("  no doc: %s" % repr(ex)[:100])

    p("")
    p("=== play / play_from_start / stop signatures ===")
    for m in ("play", "play_from_start", "stop", "is_playing"):
        try:
            p("  %s: %s" % (m, getattr(unreal.PaperFlipbookComponent, m).__doc__))
        except Exception as ex:
            p("  %s: <err>" % m)

    p("")
    p("=== character movement: what can we query? ===")
    cls = unreal.EditorAssetLibrary.load_blueprint_class(
        "/Game/DontTrustTheLevels/Player/Blueprints/BP_Player")
    cdo = unreal.get_default_object(cls)
    for c in cdo.get_components_by_class(unreal.CharacterMovementComponent):
        ms = [m for m in dir(c) if not m.startswith("_") and
              any(k in m.lower() for k in ("fall", "air", "velocity", "moving",
                                           "walk", "jump"))]
        p("  CharacterMovement methods: %s" % sorted(ms))
        for prop in ("is_falling", "movement_mode"):
            try:
                p("  %-18s = %s" % (prop, c.get_editor_property(prop)))
            except Exception:
                p("  %-18s <none>" % prop)

    p("")
    p("=== MovementMode enum ===")
    try:
        for n in dir(unreal.MovementMode):
            if not n.startswith("_"):
                try:
                    p("  %-14s = %s" % (n, getattr(unreal.MovementMode, n)))
                except Exception:
                    pass
    except Exception as ex:
        p("  <err %s>" % repr(ex)[:80])

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=180)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
