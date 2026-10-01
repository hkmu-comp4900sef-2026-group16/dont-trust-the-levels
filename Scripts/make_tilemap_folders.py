"""Add the TileSets/ and TileMaps/ folders under Environment/ (Structure.md 2a).

Idempotent. Guarded to this project.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ue_remote import UERemote

PROJECT = "DontTrustTheLevels"
ROOT = "/Game/DontTrustTheLevels"

FOLDERS = [
    "Environment/TileSets",
    "Environment/TileMaps",
]

ue = UERemote()
node, addr = ue.connect(timeout=15, expected_project=PROJECT)
print("connected:", node["data"].get("project_name"))

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
        (made if eal.make_directory(path) else failed).append(rel)
    except Exception as e:
        failed.append("%s (%s)" % (rel, repr(e)[:60]))
print("CREATED: %s" % made)
print("EXISTED: %s" % existed)
if failed:
    print("FAILED: %s" % failed)
'''
CODE = CODE_TEMPLATE.replace("__FOLDERS__", repr(FOLDERS))

res = ue.run(CODE)
print("success:", res.get("success"))
for entry in res.get("output", []):
    print("  [%s] %s" % (entry.get("type"), entry.get("output", "").rstrip()))
