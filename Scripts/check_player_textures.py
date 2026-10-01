"""Do the player textures already have the Paper2D pixel-art settings, and do
the sprites/flipbooks still reference them correctly?

If the texture settings are already correct, no reimport/re-create is needed.
If a setting differs, we fix the texture only - sprites do NOT need recreating
for texture-setting changes (they store texture ref + UV rect + dim + ppu,
none of which depend on filter/compression/mip).
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
    eal = unreal.EditorAssetLibrary
    TEX = "/Game/DontTrustTheLevels/Player/Textures"

    p("=== PLAYER TEXTURE SETTINGS ===")
    p("%-24s %-14s %-16s %-18s %-6s %s" % (
        "TEXTURE", "FILTER", "COMPRESSION", "MIPGEN", "SRGB", "SIZE"))
    p("-" * 100)
    names = []
    for a in sorted(eal.list_assets(TEX, recursive=False)):
        names.append(a.split("/")[-1].split(".")[0])
    for n in names:
        t = eal.load_asset(TEX + "/" + n)
        if not t:
            p("%-24s MISSING" % n)
            continue
        f = t.get_editor_property("filter")
        c = t.get_editor_property("compression_settings")
        m = t.get_editor_property("mip_gen_settings")
        s = t.get_editor_property("srgb")
        try:
            w = t.blueprint_get_size_x()
            h = t.blueprint_get_size_y()
            size = "%dx%d" % (w, h)
        except Exception:
            size = "?"
        p("%-24s %-14s %-16s %-18s %-6s %s" % (
            n,
            str(f).split(".")[-1].rstrip(": 0123456789>"),
            str(c).split(".")[-1].rstrip(": 0123456789>"),
            str(m).split(".")[-1].rstrip(": 0123456789>"),
            s, size))

    p("")
    p("=== EXPECTED (Paper2D pixel-art) ===")
    p("  filter      = TF_NEAREST")
    p("  compression = TC_EDITOR_ICON   (UserInterface2D RGBA)")
    p("  mip_gen     = TMGS_NO_MIPMAPS")
    p("  srgb        = True")

    p("")
    p("=== DO SPRITES STILL REFERENCE THE TEXTURES? ===")
    SPR = "/Game/DontTrustTheLevels/Player/Sprites/Frames"
    checked = 0
    bad = 0
    for a in sorted(eal.list_assets(SPR, recursive=False)):
        nm = a.split("/")[-1].split(".")[0]
        s = eal.load_asset(SPR + "/" + nm)
        if not s:
            p("  %-30s LOAD FAILED" % nm)
            bad += 1
            continue
        tex = s.get_editor_property("source_texture")
        uv = s.get_editor_property("source_uv")
        dim = s.get_editor_property("source_dimension")
        ppu = s.get_editor_property("pixels_per_unreal_unit")
        ok = tex is not None and dim.x == 32 and dim.y == 32
        if not ok:
            p("  %-30s PROBLEM tex=%s dim=(%.0f,%.0f)" % (
                nm, tex.get_name() if tex else None, dim.x, dim.y))
            bad += 1
        checked += 1
    p("  checked %d frames, %d problems" % (checked, bad))

    p("")
    p("=== FLIPBOOKS ===")
    FLB = "/Game/DontTrustTheLevels/Player/Animations"
    for a in sorted(eal.list_assets(FLB, recursive=False)):
        nm = a.split("/")[-1].split(".")[0]
        fb = eal.load_asset(FLB + "/" + nm)
        if not fb:
            p("  %-30s LOAD FAILED" % nm)
            continue
        kfs = fb.get_editor_property("key_frames")
        first = kfs[0].get_editor_property("sprite") if kfs else None
        p("  %-30s %2d frames  first=%s" % (
            nm, len(kfs), first.get_name() if first else None))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=180)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())
