"""Phase 1: import the trap art we need first - Spikes and Saw.

Follows the naming standard:
  Traps/Textures/    T_<Name>_D
  Traps/Sprites/     SPR_<Name>            (single-frame sprites)
  Traps/Sprites/Frames/  SPF_<Name>_NN     (animation frames)
  Traps/Animations/  FLB_<Name>            (flipbooks)

Idempotent. Guarded to this project.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

PROJECT = "DontTrustTheLevels"

# (source png relative to Traps/, texture name, frame width, frame count, fps)
SHEETS = [
    ("Spikes/Idle.png",        "Spikes",  16,  1, 10.0),
    ("Saw/On (38x38).png",     "Saw",     38,  8, 14.0),
    ("Saw/Chain.png",          "SawChain", 8,  1, 10.0),
    ("Saw/Off.png",            "SawOff",  38,  1, 10.0),
]

ue = UERemote()
node, addr = ue.connect(timeout=20, expected_project=PROJECT)
print("connected:", node["data"].get("project_name"))
print("importing %d trap sheets\n" % len(SHEETS))

CODE_TEMPLATE = r'''
import unreal, traceback
out = []
def p(s):
    out.append(str(s))

SRC_ROOT = r"C:\dtl\Assets\PixelAdventure\Free\Traps"
TEX_DIR  = "/Game/DontTrustTheLevels/Traps/Textures"
SPR_DIR  = "/Game/DontTrustTheLevels/Traps/Sprites"
FRM_DIR  = "/Game/DontTrustTheLevels/Traps/Sprites/Frames"
FLB_DIR  = "/Game/DontTrustTheLevels/Traps/Animations"
SHEETS   = __SHEETS__
PPU      = 0.16

eal = unreal.EditorAssetLibrary
at  = unreal.AssetToolsHelpers.get_asset_tools()

def import_texture(src, name):
    dst = TEX_DIR + "/" + name
    if eal.does_asset_exist(dst):
        p("  tex SKIP: %s" % name)
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
        p("  tex IMPORT FAILED %s: %s" % (name, repr(e)[:110]))
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
            p("  tex settings FAILED %s" % name)
    p("  tex OK: %-18s %dx%d" % (
        name, t.blueprint_get_size_x() if t else 0,
        t.blueprint_get_size_y() if t else 0))
    return t

def make_sprite(name, texture, fw, fh, uv_x, dest_dir):
    dst = dest_dir + "/" + name
    if eal.does_asset_exist(dst):
        return eal.load_asset(dst)
    f = unreal.PaperSpriteFactory()
    spr = at.create_asset(name, dest_dir, unreal.PaperSprite, f)
    if spr is None:
        p("    sprite CREATE FAILED: %s" % name)
        return None
    try:
        spr.set_editor_property("source_texture", texture)
        spr.set_editor_property("source_uv", unreal.Vector2D(float(uv_x), 0.0))
        spr.set_editor_property("source_dimension",
                                unreal.Vector2D(float(fw), float(fh)))
        spr.set_editor_property("pixels_per_unreal_unit", PPU)
        spr.set_editor_property("pivot_mode", unreal.SpritePivotMode.TOP_LEFT)
        eal.save_loaded_asset(spr)
    except Exception as e:
        p("    sprite props FAILED %s: %s" % (name, repr(e)[:100]))
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
        p("    flipbook props FAILED %s: %s" % (name, repr(e)[:110]))
        return None
    kfs = fb.get_editor_property("key_frames")
    p("    flipbook OK: %-20s %d frames @ %.0ffps" % (name, len(kfs), fps))
    return fb

try:
    for src_rel, base, fw, nframes, fps in SHEETS:
        p("=== %s (%d frame(s), %dpx) ===" % (base, nframes, fw))
        src = SRC_ROOT + "\\" + src_rel.replace("/", "\\")
        if not unreal.Paths.file_exists(src):
            p("  SOURCE MISSING: %s" % src)
            continue

        tex = import_texture(src, "T_%s_D" % base)
        if tex is None:
            continue

        fh = fw  # square frames in this pack
        if nframes == 1:
            s = make_sprite("SPR_%s" % base, tex, fw, fh, 0, SPR_DIR)
            p("  sprite: %s" % ("OK" if s else "FAILED"))
        else:
            sprites = []
            for i in range(nframes):
                nm = "SPF_%s_%02d" % (base, i)
                s = make_sprite(nm, tex, fw, fh, i * fw, FRM_DIR)
                if s:
                    sprites.append(s)
            p("  frames: %d/%d" % (len(sprites), nframes))
            if sprites:
                make_flipbook("FLB_%s" % base, sprites, fps)
        p("")

    p("=== SUMMARY ===")
    for d, label in ((TEX_DIR, "textures"), (SPR_DIR, "sprites"),
                     (FRM_DIR, "frames"), (FLB_DIR, "flipbooks")):
        n = len(list(eal.list_assets(d, recursive=False)))
        p("  %-10s %d" % (label, n))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

CODE = CODE_TEMPLATE.replace("__SHEETS__", repr(SHEETS))

r = ue.run(CODE, timeout=300)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
