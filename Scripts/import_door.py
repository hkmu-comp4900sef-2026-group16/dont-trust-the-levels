"""Import the medieval door as a texture + sprite.

Source: C:\\dtl\\Assets\\PixelDoors\\Medieval\\door-2.png  (32x40 px)
  -> texture  T_EndDoor_D
  -> sprite   SPR_EndDoor   (32x40 px at ppu 0.16 = 200x250 uu)

Placed in Environment/ (it owns shared scenery) per Structure.md.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

PROJECT = "DontTrustTheLevels"

ue = UERemote()
node, addr = ue.connect(timeout=20, expected_project=PROJECT)
print("connected:", node["data"].get("project_name"))

CODE = r'''
import unreal, traceback
out = []
def p(s):
    out.append(str(s))

SRC = r"C:\dtl\Assets\PixelDoors\Medieval\door-2.png"
TEX_DIR = "/Game/DontTrustTheLevels/Environment/Textures"
SPR_DIR = "/Game/DontTrustTheLevels/Environment/Sprites"
PPU = 0.16
W, H = 32, 40

eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()

try:
    # ---- texture ----
    p("=== import texture ===")
    tex_path = TEX_DIR + "/T_EndDoor_D"
    if eal.does_asset_exist(tex_path):
        p("  already exists")
        tex = eal.load_asset(tex_path)
    else:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", SRC)
        task.set_editor_property("destination_path", TEX_DIR)
        task.set_editor_property("destination_name", "T_EndDoor_D")
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("save", True)
        at.import_asset_tasks([task])
        tex = eal.load_asset(tex_path)

    if tex is None:
        p("  IMPORT FAILED")
    else:
        tex.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
        tex.set_editor_property("compression_settings",
                                unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        tex.set_editor_property("mip_gen_settings",
                                unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("srgb", True)
        eal.save_loaded_asset(tex)
        p("  T_EndDoor_D = %dx%d  filter=%s comp=%s mip=%s" % (
            tex.blueprint_get_size_x(), tex.blueprint_get_size_y(),
            str(tex.get_editor_property("filter")).split(".")[-1].rstrip(": 0123456789>"),
            str(tex.get_editor_property("compression_settings")).split(".")[-1].rstrip(": 0123456789>"),
            str(tex.get_editor_property("mip_gen_settings")).split(".")[-1].rstrip(": 0123456789>")))

    # ---- sprite ----
    p("")
    p("=== create sprite ===")
    spr_path = SPR_DIR + "/SPR_EndDoor"
    if eal.does_asset_exist(spr_path):
        eal.delete_asset(spr_path)
        p("  deleted stale sprite")
    f = unreal.PaperSpriteFactory()
    spr = at.create_asset("SPR_EndDoor", SPR_DIR, unreal.PaperSprite, f)
    if spr is None:
        p("  CREATE FAILED")
    else:
        spr.set_editor_property("source_texture", tex)
        spr.set_editor_property("source_uv", unreal.Vector2D(0.0, 0.0))
        spr.set_editor_property("source_dimension", unreal.Vector2D(float(W), float(H)))
        spr.set_editor_property("pixels_per_unreal_unit", PPU)
        spr.set_editor_property("pivot_mode", unreal.SpritePivotMode.TOP_LEFT)
        eal.save_loaded_asset(spr)
        p("  SPR_EndDoor created")
        p("     dim = %dx%d px" % (W, H))
        p("     ppu = %.2f" % PPU)
        p("     -> %.0f x %.0f uu  (%.1f x %.1f tiles)" % (
            W / PPU, H / PPU, W / PPU / 100, H / PPU / 100))

    # ---- also a 1-frame flipbook so traps/doors can share the component type ----
    p("")
    p("=== create FLB_EndDoor (1 frame) ===")
    FLB_DIR = "/Game/DontTrustTheLevels/Environment/Animations"
    if not eal.does_directory_exist(FLB_DIR):
        eal.make_directory(FLB_DIR)
        p("  created Animations/ folder")
    flb_path = FLB_DIR + "/FLB_EndDoor"
    if eal.does_asset_exist(flb_path):
        eal.delete_asset(flb_path)
    f2 = unreal.PaperFlipbookFactory()
    fb = at.create_asset("FLB_EndDoor", FLB_DIR, unreal.PaperFlipbook, f2)
    if fb:
        k = unreal.PaperFlipbookKeyFrame()
        k.set_editor_property("sprite", spr)
        k.set_editor_property("frame_run", 1)
        fb.set_editor_property("key_frames", [k])
        fb.set_editor_property("frames_per_second", 10.0)
        eal.save_loaded_asset(fb)
        p("  FLB_EndDoor created (1 frame)")
    else:
        p("  flipbook CREATE FAILED")

    p("")
    p("=== Environment/ contents ===")
    for d in (TEX_DIR, SPR_DIR, FLB_DIR):
        p("  %s/" % d.split("/")[-1])
        for a in sorted(eal.list_assets(d, recursive=False)):
            p("     %s" % a.split("/")[-1].split(".")[0])

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=240)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
