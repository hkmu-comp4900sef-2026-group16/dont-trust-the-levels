"""Can Python set the flipbook on an INHERITED sprite component?

Key distinction:
  - Components added via new_object() on a CDO do NOT instantiate on spawn
  - Components inherited from a PARENT's SCS DO exist on spawn

So setting source_flipbook on BP_TrapBase's Sprite (an SCS component) may
persist. Test it, and also create BP_Trap_Spikes as a child.
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

try:
    eal = unreal.EditorAssetLibrary
    at = unreal.AssetToolsHelpers.get_asset_tools()

    TB = "/Game/DontTrustTheLevels/Traps/Blueprints/BP_TrapBase"

    # ---- 1. what components does BP_TrapBase's CDO expose? ----
    p("=== 1. BP_TrapBase CDO components ===")
    cls = eal.load_blueprint_class(TB)
    p("  class: %s" % cls)
    cdo = unreal.get_default_object(cls) if cls else None
    if cdo:
        for ccls, label in ((unreal.BoxComponent, "BoxComponent"),
                            (unreal.PaperFlipbookComponent, "PaperFlipbook"),
                            (unreal.SceneComponent, "SceneComponent")):
            try:
                comps = cdo.get_components_by_class(ccls)
                for c in comps:
                    p("  %-18s %s" % (label, c.get_name()))
            except Exception:
                pass

    # ---- 2. create FLB_Spikes (1-frame flipbook) so a static sprite can be shown ----
    p("")
    p("=== 2. create FLB_Spikes (1 frame) ===")
    FLB_DIR = "/Game/DontTrustTheLevels/Traps/Animations"
    flb_path = FLB_DIR + "/FLB_Spikes"
    if eal.does_asset_exist(flb_path):
        p("  already exists")
    else:
        spr = eal.load_asset("/Game/DontTrustTheLevels/Traps/Sprites/SPR_Spikes")
        if spr is None:
            p("  SPR_Spikes MISSING")
        else:
            f = unreal.PaperFlipbookFactory()
            fb = at.create_asset("FLB_Spikes", FLB_DIR, unreal.PaperFlipbook, f)
            if fb:
                k = unreal.PaperFlipbookKeyFrame()
                k.set_editor_property("sprite", spr)
                k.set_editor_property("frame_run", 1)
                fb.set_editor_property("key_frames", [k])
                fb.set_editor_property("frames_per_second", 10.0)
                eal.save_loaded_asset(fb)
                p("  created FLB_Spikes (1 frame)")
            else:
                p("  CREATE FAILED")

    # ---- 3. try assigning the flipbook to the inherited Sprite component ----
    p("")
    p("=== 3. set Sprite's flipbook (inherited component) ===")
    cls = eal.load_blueprint_class(TB)
    cdo = unreal.get_default_object(cls)
    comps = cdo.get_components_by_class(unreal.PaperFlipbookComponent)
    p("  sprite components found: %d" % len(comps))
    for c in comps:
        p("     %s" % c.get_name())
        fb = eal.load_asset(flb_path)
        if fb:
            try:
                c.set_editor_property("source_flipbook", fb)
                p("     set source_flipbook -> %s" % fb.get_name())
                p("     readback: %s" % c.get_editor_property("source_flipbook"))
            except Exception as ex:
                p("     FAILED: %s" % repr(ex)[:130])
        else:
            p("     FLB_Spikes not loadable")

    # save
    bp = eal.load_asset(TB)
    if bp:
        eal.save_loaded_asset(bp)
        p("  saved BP_TrapBase")

    # ---- 4. create BP_Trap_Spikes as a CHILD of BP_TrapBase ----
    p("")
    p("=== 4. create BP_Trap_Spikes (child of BP_TrapBase) ===")
    SP = "/Game/DontTrustTheLevels/Traps/Blueprints/BP_Trap_Spikes"
    if eal.does_asset_exist(SP):
        p("  already exists")
    else:
        parent_cls = eal.load_blueprint_class(TB)
        p("  parent class: %s" % parent_cls)
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent_cls)
        child = at.create_asset("BP_Trap_Spikes", 
                                "/Game/DontTrustTheLevels/Traps/Blueprints",
                                unreal.Blueprint, factory)
        if child is None:
            p("  CREATE FAILED")
        else:
            p("  created BP_Trap_Spikes")
            eal.save_loaded_asset(child)

    p("")
    p("=== 5. verify child inherits components ===")
    ccls = eal.load_blueprint_class(SP)
    p("  child class: %s" % ccls)
    if ccls:
        ccdo = unreal.get_default_object(ccls)
        for xcls, label in ((unreal.BoxComponent, "BoxComponent"),
                            (unreal.PaperFlipbookComponent, "PaperFlipbook")):
            comps2 = ccdo.get_components_by_class(xcls)
            p("  %-18s %d  %s" % (label, len(comps2),
                                  [c.get_name() for c in comps2]))
        for c in ccdo.get_components_by_class(unreal.PaperFlipbookComponent):
            try:
                p("  child sprite flipbook: %s" % c.get_editor_property("source_flipbook"))
            except Exception:
                pass

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=240)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
