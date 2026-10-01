"""Import Level 0 textures into Content/DontTrustTheLevels, with pixel-art
settings applied at import time (nearest filter, UI2D compression, no mipmaps).

Runs in the LIVE editor via remote execution, guarded to this project only.
Idempotent: skips textures that already exist.

Source PNGs: C:\\dtl\\Assets\\PixelAdventure\\Free
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

PROJECT = "DontTrustTheLevels"

# (source png, destination folder, asset name)
IMPORTS = [
    (r"Terrain\Terrain (16x16).png",        "/Game/DontTrustTheLevels/Environment/Textures", "T_Terrain_D"),
    (r"Background\Blue.png",                "/Game/DontTrustTheLevels/Environment/Textures", "T_Background_Blue_D"),
    (r"Traps\Spikes\Idle.png",              "/Game/DontTrustTheLevels/Traps/Textures",       "T_Spikes_D"),
    (r"Traps\Saw\On (38x38).png",           "/Game/DontTrustTheLevels/Traps/Textures",       "T_Saw_D"),
    (r"Traps\Spiked Ball\Spiked Ball.png",  "/Game/DontTrustTheLevels/Traps/Textures",       "T_SpikedBall_D"),
]

ue = UERemote()
node, addr = ue.connect(timeout=15, expected_project=PROJECT)   # <-- guard
print("connected:", node["data"].get("project_name"),
      "| engine", node["data"].get("engine_version"))
print("importing %d textures\n" % len(IMPORTS))

CODE_TEMPLATE = r'''
import unreal

SRC_ROOT = r"C:\dtl\Assets\PixelAdventure\Free"
IMPORTS = __IMPORTS__

eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
out = []
def p(s):
    out.append(str(s))

for src_rel, dst, name in IMPORTS:
    src = SRC_ROOT + "\\" + src_rel
    dst_path = dst + "/" + name

    if eal.does_asset_exist(dst_path):
        p("SKIP (exists): " + name)
        continue
    if not unreal.Paths.file_exists(src):
        p("MISSING SOURCE: " + src)
        continue

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", dst)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)

    try:
        at.import_asset_tasks([task])
    except Exception as e:
        p("IMPORT FAILED %s: %s" % (name, repr(e)[:160]))
        continue

    tex = eal.load_asset(dst_path)
    if tex is None:
        p("IMPORTED but not loadable: " + name)
        continue

    # --- pixel-art settings (the ones learned the hard way) ---
    try:
        tex.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("srgb", True)
        eal.save_loaded_asset(tex)
    except Exception as e:
        p("  settings FAILED for %s: %s" % (name, repr(e)[:160]))

    # read back
    f = tex.get_editor_property("filter")
    c = tex.get_editor_property("compression_settings")
    m = tex.get_editor_property("mip_gen_settings")
    p("OK %-22s %sx%s  filter=%s comp=%s mip=%s" % (
        name, tex.blueprint_get_size_x(), tex.blueprint_get_size_y(), f, c, m))

print("\n".join(out))
'''

CODE = CODE_TEMPLATE.replace("__IMPORTS__", repr(IMPORTS))

res = ue.run(CODE, timeout=120)
print("success:", res.get("success"))
for entry in res.get("output", []):
    print("  [%s] %s" % (entry.get("type"), entry.get("output", "").rstrip()))
