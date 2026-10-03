"""Import the Apple as the level key, and create BP_ExitDoor.

Key art: Items/Fruits/Apple.png  (544x32 = 17 frames of 32px)
  -> T_Key_D, SPF_Key_00..16, FLB_Key

Door: SPR_EndDoor already imported (200x250 uu, TOP_LEFT pivot)
  -> BP_ExitDoor (parent: Actor)
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

SRC = r"C:\dtl\Assets\PixelAdventure\Free\Items\Fruits\Apple.png"
TEX_DIR = "/Game/DontTrustTheLevels/Environment/Textures"
FRM_DIR = "/Game/DontTrustTheLevels/Environment/Sprites/Frames"
FLB_DIR = "/Game/DontTrustTheLevels/Environment/Animations"
PPU = 0.16
FW = 32
NFRAMES = 17
FPS = 12.0

eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()

try:
    # ---- texture ----
    p("=== import key texture ===")
    tex_path = TEX_DIR + "/T_Key_D"
    if eal.does_asset_exist(tex_path):
        p("  already exists")
        tex = eal.load_asset(tex_path)
    else:
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
        p("  T_Key_D = %dx%d" % (tex.blueprint_get_size_x(),
                                 tex.blueprint_get_size_y()))

    # ---- frames ----
    p("")
    p("=== create %d key frames ===" % NFRAMES)
    sprites = []
    for i in range(NFRAMES):
        nm = "SPF_Key_%02d" % i
        dst = FRM_DIR + "/" + nm
        if eal.does_asset_exist(dst):
            sprites.append(eal.load_asset(dst))
            continue
        f = unreal.PaperSpriteFactory()
        spr = at.create_asset(nm, FRM_DIR, unreal.PaperSprite, f)
        if spr is None:
            p("  %s CREATE FAILED" % nm)
            continue
        spr.set_editor_property("source_texture", tex)
        spr.set_editor_property("source_uv", unreal.Vector2D(float(i * FW), 0.0))
        spr.set_editor_property("source_dimension", unreal.Vector2D(float(FW), float(FW)))
        spr.set_editor_property("pixels_per_unreal_unit", PPU)
        spr.set_editor_property("pivot_mode", unreal.SpritePivotMode.TOP_LEFT)
        eal.save_loaded_asset(spr)
        sprites.append(spr)
    p("  frames created: %d/%d" % (len(sprites), NFRAMES))

    # ---- flipbook ----
    p("")
    p("=== create FLB_Key ===")
    flb_path = FLB_DIR + "/FLB_Key"
    if eal.does_asset_exist(flb_path):
        eal.delete_asset(flb_path)
    f2 = unreal.PaperFlipbookFactory()
    fb = at.create_asset("FLB_Key", FLB_DIR, unreal.PaperFlipbook, f2)
    if fb and sprites:
        frames = []
        for s in sprites:
            k = unreal.PaperFlipbookKeyFrame()
            k.set_editor_property("sprite", s)
            k.set_editor_property("frame_run", 1)
            frames.append(k)
        fb.set_editor_property("key_frames", frames)
        fb.set_editor_property("frames_per_second", FPS)
        eal.save_loaded_asset(fb)
        p("  FLB_Key: %d frames @ %.0ffps" % (len(frames), FPS))
    else:
        p("  flipbook CREATE FAILED")

    # ---- BP_ExitDoor ----
    p("")
    p("=== create BP_ExitDoor ===")
    BP_DIR = "/Game/DontTrustTheLevels/Environment/Blueprints"
    if not eal.does_directory_exist(BP_DIR):
        eal.make_directory(BP_DIR)
        p("  created Environment/Blueprints/")
    BP_PATH = BP_DIR + "/BP_ExitDoor"
    if eal.does_asset_exist(BP_PATH):
        p("  already exists - leaving it")
    else:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.Actor)
        bp = at.create_asset("BP_ExitDoor", BP_DIR, unreal.Blueprint, factory)
        if bp:
            eal.save_loaded_asset(bp)
            p("  created BP_ExitDoor (parent: Actor)")
        else:
            p("  CREATE FAILED")

    # ---- BP_Key ----
    p("")
    p("=== create BP_Key ===")
    KP_PATH = BP_DIR + "/BP_Key"
    if eal.does_asset_exist(KP_PATH):
        p("  already exists - leaving it")
    else:
        factory2 = unreal.BlueprintFactory()
        factory2.set_editor_property("parent_class", unreal.Actor)
        kp = at.create_asset("BP_Key", BP_DIR, unreal.Blueprint, factory2)
        if kp:
            eal.save_loaded_asset(kp)
            p("  created BP_Key (parent: Actor)")
        else:
            p("  CREATE FAILED")

    p("")
    p("=== Environment/ contents ===")
    for d in (TEX_DIR, FRM_DIR, FLB_DIR, BP_DIR):
        n = len(list(eal.list_assets(d, recursive=False)))
        p("  %-14s %d" % (d.split("/")[-1], n))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=300)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
