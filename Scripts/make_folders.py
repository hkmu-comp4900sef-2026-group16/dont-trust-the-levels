"""Create the Content/DontTrustTheLevels folder tree (Structure.md section 2).

Runs in the LIVE editor via remote execution, guarded to this project only.
Idempotent - safe to re-run; existing folders are left alone.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

PROJECT = "DontTrustTheLevels"
ROOT = "/Game/DontTrustTheLevels"

# every folder we want, in creation order (parents before children)
FOLDERS = [
    "Core",
    "Core/Blueprints",
    "Core/Interfaces",
    "Core/Data",

    "Player",
    "Player/Blueprints",
    "Player/Sprites",
    "Player/Sprites/Frames",
    "Player/Animations",
    "Player/Textures",

    "Traps",
    "Traps/Blueprints",
    "Traps/Sprites",
    "Traps/Textures",

    "Weapons",
    "Weapons/Blueprints",
    "Weapons/Sprites",
    "Weapons/Textures",

    "Enemies",
    "Enemies/Blueprints",
    "Enemies/Sprites",
    "Enemies/Sprites/Frames",
    "Enemies/Animations",
    "Enemies/Textures",

    "Environment",
    "Environment/Sprites",
    "Environment/Textures",
    "Environment/Materials",

    "Levels",
    "UI",
    "Audio",
]

ue = UERemote()
node, addr = ue.connect(timeout=15, expected_project=PROJECT)   # <-- guard
print("connected:", node["data"].get("project_name"),
      "| engine", node["data"].get("engine_version"))
print("creating %d folders under %s\n" % (len(FOLDERS), ROOT))

CODE_TEMPLATE = r'''
import unreal

ROOT = "/Game/DontTrustTheLevels"
FOLDERS = __FOLDERS__

eal = unreal.EditorAssetLibrary
made, existed, failed = [], [], []

for rel in FOLDERS:
    path = ROOT + "/" + rel
    if eal.does_directory_exist(path):
        existed.append(rel)
        continue
    try:
        ok = eal.make_directory(path)
        (made if ok else failed).append(rel)
    except Exception as e:
        failed.append("%s (%s)" % (rel, repr(e)[:80]))

print("CREATED (%d):" % len(made))
for m in made:
    print("   + " + m)
print("ALREADY EXISTED (%d):" % len(existed))
for e in existed:
    print("   = " + e)
if failed:
    print("FAILED (%d):" % len(failed))
    for f in failed:
        print("   ! " + f)
print("TOTAL now under root: %d" % len(FOLDERS))
'''

CODE = CODE_TEMPLATE.replace("__FOLDERS__", repr(FOLDERS))

res = ue.run(CODE)
print("success:", res.get("success"))
for entry in res.get("output", []):
    print("  [%s] %s" % (entry.get("type"), entry.get("output", "").rstrip()))
