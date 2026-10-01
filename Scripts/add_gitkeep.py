"""Add a .gitkeep to every empty folder under Content/DontTrustTheLevels.

Git tracks files, not directories, so an empty folder is invisible to git and
would vanish on a fresh clone. .gitkeep makes the structure survive.

Safe to re-run: only touches folders that are genuinely empty.
"""
import os

ROOT = r"C:\dtl\Content\DontTrustTheLevels"

added, skipped, nonempty = [], [], []

for dirpath, dirnames, filenames in os.walk(ROOT):
    # ignore nothing here - walk everything
    if not dirnames and not filenames:
        keep = os.path.join(dirpath, ".gitkeep")
        with open(keep, "w", encoding="utf-8") as fh:
            fh.write("")
        added.append(os.path.relpath(dirpath, ROOT))
    elif filenames == [".gitkeep"]:
        skipped.append(os.path.relpath(dirpath, ROOT))
    else:
        nonempty.append(os.path.relpath(dirpath, ROOT))

print("ADDED .gitkeep (%d):" % len(added))
for a in sorted(added):
    print("   + " + a)
print("\nALREADY HAD .gitkeep (%d):" % len(skipped))
for s in sorted(skipped):
    print("   = " + s)
print("\nHAS ASSETS, left alone (%d):" % len(nonempty))
for n in sorted(nonempty):
    print("   . " + n)
