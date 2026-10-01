"""Import Ninja Frog art and build the Paper2D chain for the player.

Steps:
  1. Import the 7 sprite sheets as textures (pixel-art settings)
  2. Slice each sheet into 32x32 sprite frames
  3. Assemble frames into flipbooks

Runs in the LIVE editor, guarded to this project.
Idempotent: skips assets that already exist.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

PROJECT = "DontTrustTheLevels"

# (source filename, base name, frame count, flipbook fps)
SHEETS = [
    ("Idle (32x32).png",        "Idle",        11, 10.0),
    ("Run (32x32).png",         "Run",         12, 14.0),
    ("Jump (32x32).png",        "Jump",         1, 10.0),
    ("Fall (32x32).png",        "Fall",         1, 10.0),
    ("Double Jump (32x32).png", "DoubleJump",   6, 12.0),
    ("Hit (32x32).png",         "Hit",          7, 12.0),
    ("Wall Jump (32x32).png",   "WallJump",     5, 12.0),
]

ue = UERemote()
node, addr = ue.connect(timeout=15, expected_project=PROJECT)
print("connected:", node["data"].get("project_name"))
print("importing %d Ninja Frog sheets\n" % len(SHEETS))

CODE_TEMPLATE = r'''
import unreal, traceback
out = []
def p(s):
    out.append(str(s))

SRC_ROOT = r"C:\dtl\Assets\PixelAdventure\Free\Main Characters\Ninja Frog"
TEX_DIR  = "/Game/DontTrustTheLevels/Player/Textures"
SPR_DIR  = "/Game/DontTrustTheLevels/Player/Sprites/Frames"
FLB_DIR  = "/Game/DontTrustTheLevels/Player/Animations"
SHEETS   = __SHEETS__
PPU      = 0.16
FRAME    = 32

eal = unreal.EditorAssetLibrary
at  = unreal.AssetToolsHelpers.get_asset_tools()

def import_texture(src, name):
    dst = TEX_DIR + "/" + name
    if eal.does_asset_exist(dst):
        p("  tex SKIP (exists): %s" % name)
        return eal.load_asset(dst)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", TEX_DIR)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    try:
        at.import_asset_tasks([task])
    except Exception as e:
        p("  tex IMPORT FAILED %s: %s" % (name, repr(e)[:120]))
        return None
    t = eal.load_asset(dst)
    if t:
        try:
            t.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
            t.set_editor_property("compression_settings",
                                  unreal.TextureCompressionSettings.TC_EDITOR_ICON)
            t.set_editor_property("mip_gen_settings",
                                  unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            t.set_editor_property("srgb", True)
            eal.save_loaded_asset(t)
        except Exception as e:
            p("  tex settings FAILED %s: %s" % (name, repr(e)[:100]))
    p("  tex OK: %s" % name)
    return t

def make_frame(texture, name, uv_x):
    dst = SPR_DIR + "/" + name
    if eal.does_asset_exist(dst):
        return eal.load_asset(dst)
    f = unreal.PaperSpriteFactory()
    spr = at.create_asset(name, SPR_DIR, unreal.PaperSprite, f)
    if spr is None:
        p("    frame CREATE FAILED: %s" % name)
        return None
    try:
        spr.set_editor_property("source_texture", texture)
        spr.set_editor_property("source_uv", unreal.Vector2D(float(uv_x), 0.0))
        spr.set_editor_property("source_dimension",
                                unreal.Vector2D(float(FRAME), float(FRAME)))
        spr.set_editor_property("pixels_per_unreal_unit", PPU)
        eal.save_loaded_asset(spr)
    except Exception as e:
        p("    frame props FAILED %s: %s" % (name, repr(e)[:100]))
    return spr

def make_flipbook(name, sprites, fps):
    dst = FLB_DIR + "/" + name
    if eal.does_asset_exist(dst):
        eal.delete_asset(dst)
    f = unreal.PaperFlipbookFactory()
    fb = at.create_asset(name, FLB_DIR, unreal.PaperFlipbook, f)
    if fb is None:
        p("    flipbook CREATE FAILED: %s" % name)
        return None
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
        p("    flipbook props FAILED %s: %s" % (name, repr(e)[:120]))
        return None
    kfs = fb.get_editor_property("key_frames")
    p("    flipbook OK: %s -> %d frames @ %.0ffps" % (name, len(kfs), fps))
    return fb

try:
    for src_file, base, nframes, fps in SHEETS:
        p("=== %s (%d frames) ===" % (base, nframes))
        src = SRC_ROOT + "\\" + src_file
        if not unreal.Paths.file_exists(src):
            p("  SOURCE MISSING: %s" % src)
            continue

        tex = import_texture(src, "T_Player_%s_D" % base)
        if tex is None:
            continue

        sprites = []
        for i in range(nframes):
            nm = "SPF_Player_%s_%02d" % (base, i)
            s = make_frame(tex, nm, i * FRAME)
            if s:
                sprites.append(s)
        p("  frames created: %d/%d" % (len(sprites), nframes))

        if sprites:
            make_flipbook("FLB_Player_%s" % base, sprites, fps)
        p("")

    p("=== SUMMARY ===")
    for d, label in ((TEX_DIR, "textures"), (SPR_DIR, "frames"), (FLB_DIR, "flipbooks")):
        assets = list(eal.list_assets(d, recursive=False))
        p("  %-10s %d" % (label, len(assets)))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

CODE = CODE_TEMPLATE.replace("__SHEETS__", repr(SHEETS))

res = ue.run(CODE, timeout=300)
print("success:", res.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
