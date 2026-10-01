"""Check screen percentage and disable the vignette, then re-measure the edge.

r.ScreenPercentage < 100 makes UE render at lower resolution and upscale,
which blurs everything regardless of texture filtering.
"""
import sys, os, glob, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

ue = UERemote()
ue.connect(timeout=20, expected_project="DontTrustTheLevels")

for old in glob.glob(r"C:\dtl\Saved\Screenshots\Windows\dtl_*.png"):
    try:
        os.remove(old)
    except Exception:
        pass

CODE = r'''
import unreal, traceback
out = []
def p(s):
    out.append(str(s))

try:
    ell = unreal.EditorLevelLibrary
    world = ell.get_editor_world()

    p("=== console vars that affect sharpness ===")
    for var in ("r.ScreenPercentage", "r.Vignette", "r.DefaultFeature.Vignette",
                "r.Tonemapper.Sharpen", "r.Tonemapper.Quality",
                "r.DefaultFeature.AntiAliasing", "r.PostProcessAAQuality",
                "r.MotionBlurQuality", "r.DefaultFeature.Bloom"):
        try:
            v = unreal.SystemLibrary.get_console_variable_value(world, var)
            p("  %-32s = %s" % (var, v))
        except Exception as ex:
            p("  %-32s <err %s>" % (var, repr(ex)[:50]))

    p("")
    p("=== force them for this session ===")
    for cmd in ("r.ScreenPercentage 100",
                "r.Vignette 0",
                "r.DefaultFeature.Vignette 0",
                "r.Tonemapper.Sharpen 0",
                "r.DefaultFeature.AntiAliasing 0",
                "r.PostProcessAAQuality 0",
                "r.MotionBlurQuality 0",
                "r.DefaultFeature.Bloom 0"):
        try:
            unreal.SystemLibrary.execute_console_command(world, cmd)
            p("  issued: %s" % cmd)
        except Exception as ex:
            p("  %-34s FAILED" % cmd)

    p("")
    try:
        ell.set_level_viewport_camera_info(unreal.Vector(0.0, 1000.0, -200.0),
                                           unreal.Rotator(0.0, 0.0, -90.0))
        ell.editor_invalidate_viewports()
    except Exception:
        pass

    try:
        unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, "dtl_sharp.png")
        p("screenshot requested")
    except Exception as ex:
        p("screenshot FAILED: %s" % repr(ex)[:100])

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=180)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())

for _ in range(25):
    h = glob.glob(r"C:\dtl\Saved\Screenshots\Windows\dtl_sharp.png")
    if h:
        print("LANDED:", h)
        break
    time.sleep(1)
else:
    print("no screenshot")
