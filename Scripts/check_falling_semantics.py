"""What does IsFalling() actually mean?

The name suggests "descending", but in UE4 it means "in the air / not grounded",
which is TRUE while rising during a jump. Verify from the API docs and by
comparing against the movement-mode enum.
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
    p("=== is_falling() docstring ===")
    try:
        p(unreal.CharacterMovementComponent.is_falling.__doc__)
    except Exception as ex:
        p("  <no doc>")

    p("")
    p("=== is_walking() / is_moving_on_ground() docstrings ===")
    for m in ("is_walking", "is_moving_on_ground", "is_jumping"):
        cls = (unreal.CharacterMovementComponent
               if hasattr(unreal.CharacterMovementComponent, m) else unreal.Character)
        try:
            p("  %s:" % m)
            p("    %s" % getattr(cls, m).__doc__)
        except Exception as ex:
            p("  %s: <err>" % m)

    p("")
    p("=== MovementMode enum (what IsFalling maps to) ===")
    for n in ("MOVE_WALKING", "MOVE_FALLING", "MOVE_NONE"):
        try:
            p("  %-14s = %s" % (n, getattr(unreal.MovementMode, n)))
        except Exception:
            pass

    p("")
    p("=== Character-level jump state nodes ===")
    for m in ("is_jumping", "was_jumping", "jump_current_count",
              "jump_max_count", "is_jump_providing_force"):
        p("  Character.%-26s %s" % (m, hasattr(unreal.Character, m)))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=180)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
