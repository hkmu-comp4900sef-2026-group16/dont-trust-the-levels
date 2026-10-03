"""Import Key 9 GOLD as the level key, replacing the Apple placeholder.

  1. remove the old Apple-based key assets (T_Key_D, SPF_Key_*, FLB_Key)
  2. copy the source PNG into the project
  3. import as T_Key_D (9x30 px)
  4. create SPR_Key + FLB_Key (1 frame)

Note: the pack is CC0, so no licensing concern.
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

SRC = r"C:\dtl\Assets\PixelKeys\Key 9 - GOLD.png"
TEX_DIR = "/Game/DontTrustTheLevels/Environment/Textures"
SPR_DIR = "/Game/DontTrustTheLevels/Environment/Sprites"
FRM_DIR = "/Game/DontTrustTheLevels/Environment/Sprites/Frames"
FLB_DIR = "/Game/DontTrustTheLevels/Environment/Animations"
PPU = 0.16
W, H = 9, 30

eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()

try:
    # ---- 1. remove the old Apple-based key assets ----
    p("=== 1. remove old Apple-based key assets ===")
    removed = 0
    for path in [TEX_DIR + "/T_Key_D", FLB_DIR + "/FLB_Key"]:
        if eal.does_asset_exist(path):
            eal.delete_asset(path)
            p("  deleted %s" % path.split("/")[-1])
            removed += 1
    for i in range(17):
        path = FRM_DIR + "/SPF_Key_%02d" % i
        if eal.does_asset_exist(path):
            eal.delete_asset(path)
            removed += 1
    p("  removed %d asset(s)" % removed)

    # ---- 2. import the new texture ----
    p("")
    p("=== 2. import Key 9 GOLD ===")
    tex_path = TEX_DIR + "/T_Key_D"
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", SRC)
    task.set_editor_property("destination_path", TEX_DIR)
    task.set_editor_property("destination_name", "T_Key_D")
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
        p("  T_Key_D = %dx%d  filter=NEAREST comp=UI2D mip=NONE" % (
            tex.blueprint_get_size_x(), tex.blueprint_get_size_y()))

    # ---- 3. sprite ----
    p("")
    p("=== 3. create SPR_Key ===")
    spr_path = SPR_DIR + "/SPR_Key"
    if eal.does_asset_exist(spr_path):
        eal.delete_asset(spr_path)
    f = unreal.PaperSpriteFactory()
    spr = at.create_asset("SPR_Key", SPR_DIR, unreal.PaperSprite, f)
    if spr is None:
        p("  CREATE FAILED")
    else:
        spr.set_editor_property("source_texture", tex)
        spr.set_editor_property("source_uv", unreal.Vector2D(0.0, 0.0))
        spr.set_editor_property("source_dimension", unreal.Vector2D(float(W), float(H)))
        spr.set_editor_property("pixels_per_unreal_unit", PPU)
        spr.set_editor_property("pivot_mode", unreal.SpritePivotMode.TOP_LEFT)
        eal.save_loaded_asset(spr)
        p("  SPR_Key: %dx%d px -> %.0f x %.0f uu  (%.1f x %.1f tiles)" % (
            W, H, W / PPU, H / PPU, W / PPU / 100, H / PPU / 100))

    # ---- 4. flipbook ----
    p("")
    p("=== 4. create FLB_Key (1 frame) ===")
    flb_path = FLB_DIR + "/FLB_Key"
    if eal.does_asset_exist(flb_path):
        eal.delete_asset(flb_path)
    f2 = unreal.PaperFlipbookFactory()
    fb = at.create_asset("FLB_Key", FLB_DIR, unreal.PaperFlipbook, f2)
    if fb and spr:
        k = unreal.PaperFlipbookKeyFrame()
        k.set_editor_property("sprite", spr)
        k.set_editor_property("frame_run", 1)
        fb.set_editor_property("key_frames", [k])
        fb.set_editor_property("frames_per_second", 10.0)
        eal.save_loaded_asset(fb)
        p("  FLB_Key created (1 frame)")
    else:
        p("  flipbook CREATE FAILED")

    p("")
    p("=== Environment/ contents ===")
    for d in (TEX_DIR, SPR_DIR, FRM_DIR, FLB_DIR):
        p("  %s/" % d.split("/")[-1])
        for a in sorted(eal.list_assets(d, recursive=False)):
            p("     %s" % a.split("/")[-1].split(".")[0])

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=300)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
