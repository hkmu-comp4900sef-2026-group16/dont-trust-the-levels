"""Rebuild the 2D Side Scroller template flipbooks (IdleAnimation, RunningAnimation)
from the template's OWN sprite frames.

Why: an old-project script (fix_flipbooks.py) had overwritten them with
/Game/DTF/Characters/PinkMan/SP_PinkMan_* references. Those assets do not exist
in this project, so every frame failed to load and the template character
rendered as nothing.

Runs in the LIVE editor via remote execution, guarded to this project only.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

PROJECT = "DontTrustTheLevels"

ue = UERemote()
node, addr = ue.connect(timeout=15, expected_project=PROJECT)   # <-- guard
print("connected:", node["data"].get("project_name"),
      "| engine", node["data"].get("engine_version"))

CODE = r'''
import unreal, traceback

OUT = []
def p(s):
    OUT.append(str(s))

SPR = "/Game/2DSideScroller/Sprites"

try:
    # ---- 1. confirm the factory/class we need exists -------------------
    p("PaperFlipbook: %s" % hasattr(unreal, "PaperFlipbook"))
    p("PaperFlipbookFactory: %s" % hasattr(unreal, "PaperFlipbookFactory"))

    at = unreal.AssetToolsHelpers.get_asset_tools()
    eal = unreal.EditorAssetLibrary

    # ---- 2. collect the template's own frames --------------------------
    idle_paths = ["%s/IdleFrames/IdleCycle%d" % (SPR, i) for i in range(1, 9)]
    run_paths = ["%s/RunFrames/RunCycle_%d" % (SPR, i) for i in range(1, 17)]

    def load_sprites(paths):
        got = []
        for path in paths:
            a = eal.load_asset(path)
            if a is None:
                p("  MISSING FRAME: %s" % path)
            else:
                got.append(a)
        return got

    idle = load_sprites(idle_paths)
    run = load_sprites(run_paths)
    p("idle frames loaded: %d/8" % len(idle))
    p("run  frames loaded: %d/16" % len(run))

    # ---- 3. (re)create the flipbooks -----------------------------------
    def make_flipbook(name, sprites, fps):
        path = "%s/%s" % (SPR, name)
        if eal.does_asset_exist(path):
            eal.delete_asset(path)
            p("deleted stale %s" % path)

        factory = unreal.PaperFlipbookFactory()
        fb = at.create_asset(name, SPR, unreal.PaperFlipbook, factory)
        if fb is None:
            p("CREATE FAILED: %s" % path)
            return False

        frames = []
        for s in sprites:
            k = unreal.PaperFlipbookKeyFrame()
            k.set_editor_property("sprite", s)
            k.set_editor_property("frame_run", 1)
            frames.append(k)

        try:
            fb.set_editor_property("key_frames", frames)
            fb.set_editor_property("frames_per_second", fps)
            eal.save_loaded_asset(fb)
        except Exception as e:
            p("set props FAILED for %s: %s" % (name, repr(e)[:200]))
            return False

        # read back
        kfs = fb.get_editor_property("key_frames")
        first = kfs[0].get_editor_property("sprite") if kfs else None
        p("OK %s -> %d frames @ %sfps, first=%s" % (
            name, len(kfs), fps, first.get_name() if first else None))
        return True

    if idle:
        make_flipbook("IdleAnimation", idle, 10.0)
    if run:
        make_flipbook("RunningAnimation", run, 14.0)

    # ---- 4. verify no foreign refs remain ------------------------------
    for nm in ("IdleAnimation", "RunningAnimation"):
        a = eal.load_asset("%s/%s" % (SPR, nm))
        p("verify %s: %s" % (nm, "LOADED" if a else "MISSING"))

except Exception:
    p("EXC: " + traceback.format_exc())

print("\n".join(OUT))
'''

res = ue.run(CODE)
print("success:", res.get("success"))
for entry in res.get("output", []):
    print("  [%s] %s" % (entry.get("type"), entry.get("output", "").rstrip()))
