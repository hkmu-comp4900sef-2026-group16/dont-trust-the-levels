"""The floor's luminance forms a symmetric hump peaking at the viewport centre:

  left edge ~90  ->  centre ~128  ->  right edge ~90

That is a radial falloff centred on the screen = a VIGNETTE. UE4 applies a
default vignette (intensity 0.4) when there is no PostProcessVolume.

Test: disable it via console command, re-screenshot, re-measure. If the hump
flattens, the vignette is confirmed.
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

    p("=== try console commands to kill the vignette ===")
    for cmd in ("r.Vignette 0",
                "r.DefaultFeature.Vignette 0",
                "r.Tonemapper.Quality 0",
                "r.Tonemapper.Sharpen 0"):
        try:
            unreal.SystemLibrary.execute_console_command(world, cmd)
            p("  issued: %s" % cmd)
        except Exception as ex:
            p("  %-32s FAILED: %s" % (cmd, repr(ex)[:70]))

    p("")
    p("=== try a PostProcessVolume with vignette 0 ===")
    p("  hasattr PostProcessVolume: %s" % hasattr(unreal, "PostProcessVolume"))
    for a in list(ell.get_all_level_actors()):
        if "PostProcess" in a.get_class().get_name():
            ell.destroy_actor(a)
    try:
        ppv = ell.spawn_actor_from_class(unreal.PostProcessVolume,
                                         unreal.Vector(0, 0, 0),
                                         unreal.Rotator(0, 0, 0))
        p("  spawn -> %s" % ppv)
        if ppv:
            ppv.set_actor_label("DTL_PostProcess")
            try:
                ppv.set_editor_property("unbound", True)
                p("  unbound = True")
            except Exception as ex:
                p("  unbound FAILED: %s" % repr(ex)[:90])
            try:
                s = ppv.get_editor_property("settings")
                p("  settings: %s" % type(s))
                for prop in ("vignette_intensity", "auto_exposure_method",
                             "auto_exposure_bias", "bloom_intensity"):
                    try:
                        p("     %-24s = %s" % (prop, s.get_editor_property(prop)))
                    except Exception:
                        p("     %-24s <none>" % prop)
                try:
                    s.set_editor_property("vignette_intensity", 0.0)
                    p("     set vignette_intensity = 0")
                except Exception as ex:
                    p("     set vignette FAILED: %s" % repr(ex)[:90])
                ppv.set_editor_property("settings", s)
            except Exception as ex:
                p("  settings FAILED: %s" % repr(ex)[:110])
    except Exception as ex:
        p("  SPAWN FAILED: %s" % repr(ex)[:140])

    p("")
    try:
        ell.set_level_viewport_camera_info(unreal.Vector(0.0, 1000.0, -200.0),
                                           unreal.Rotator(0.0, 0.0, -90.0))
        ell.editor_invalidate_viewports()
    except Exception:
        pass
    try:
        unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, "dtl_novig.png")
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
    h = glob.glob(r"C:\dtl\Saved\Screenshots\Windows\dtl_novig.png")
    if h:
        print("LANDED:", h)
        break
    time.sleep(1)
else:
    print("no screenshot")
