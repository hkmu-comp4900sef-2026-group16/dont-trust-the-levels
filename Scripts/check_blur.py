"""Is the animation up to date, and why is the player blurry?

Blur in pixel art comes from NON-INTEGER screen-pixels-per-texel. Compute it for
the current room camera ortho width, for both the tiles and the player sprite.

  tile   = 16 px at ppu 0.16 -> 100 uu
  player = 32 px at ppu 0.16 -> 200 uu
  px_per_texel = screen_width / (ortho_width / sprite_uu * sprite_px)
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
    ell = unreal.EditorLevelLibrary

    p("=== room camera ===")
    for a in ell.get_all_level_actors():
        if not a.get_actor_label().startswith("DTL_RoomCamera"):
            continue
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        p("  loc=(%.0f,%.0f,%.0f) yaw=%.0f" % (loc.x, loc.y, loc.z, rot.yaw))
        for cc in a.get_components_by_class(unreal.CameraComponent):
            for prop in ("projection_mode", "ortho_width", "aspect_ratio"):
                try:
                    p("  %-18s = %s" % (prop, cc.get_editor_property(prop)))
                except Exception:
                    pass

    p("")
    p("=== sprite frame ppu (player) ===")
    s = eal.load_asset(
        "/Game/DontTrustTheLevels/Player/Sprites/Frames/SPF_Player_Idle_00")
    if s:
        uv = s.get_editor_property("source_uv")
        dim = s.get_editor_property("source_dimension")
        ppu = s.get_editor_property("pixels_per_unreal_unit")
        p("  SPF_Player_Idle_00: dim=(%.0f,%.0f) ppu=%.4f -> %.0f x %.0f uu" % (
            dim.x, dim.y, ppu, dim.x / ppu, dim.y / ppu))

    p("")
    p("=== tile sprite ppu ===")
    s2 = eal.load_asset(
        "/Game/DontTrustTheLevels/Environment/Sprites/SPR_GrassFloor_Mid")
    if s2:
        dim = s2.get_editor_property("source_dimension")
        ppu = s2.get_editor_property("pixels_per_unreal_unit")
        p("  SPR_GrassFloor_Mid: dim=(%.0f,%.0f) ppu=%.4f -> %.0f x %.0f uu" % (
            dim.x, dim.y, ppu, dim.x / ppu, dim.y / ppu))

    p("")
    p("=== flipbook: is it up to date? ===")
    for nm in ("FLB_Player_Idle", "FLB_Player_Run"):
        fb = eal.load_asset("/Game/DontTrustTheLevels/Player/Animations/" + nm)
        if fb:
            kfs = fb.get_editor_property("key_frames")
            p("  %s: %d frames @ %.0ffps" % (
                nm, len(kfs), fb.get_editor_property("frames_per_second")))
            for i, k in enumerate(kfs[:3]):
                sp = k.get_editor_property("sprite")
                if sp:
                    uv = sp.get_editor_property("source_uv")
                    p("     frame %d: %s uv=(%.0f,%.0f)" % (
                        i, sp.get_name(), uv.x, uv.y))

except Exception:
    p("EXC: " + traceback.format_exc())

open(r"C:\dtl\Scripts\_verify_out.txt", "w").write("\n".join(out))
'''

r = ue.run(CODE, timeout=180)
print("success:", r.get("success"))
OUT = r"C:\dtl\Scripts\_verify_out.txt"
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8", errors="replace").read())

# ---- the maths ----
print("=" * 70)
print("PIXEL-PERFECT SCALING ANALYSIS (1080p = 1920 px wide)")
print("=" * 70)
print()
print("A tile  = 16 px at ppu 0.16 -> 100 uu")
print("Player  = 32 px at ppu 0.16 -> 200 uu")
print()
print("%-8s %-9s %-14s %-14s %s" % (
    "ORTHO", "TILES", "tile px/texel", "player px/texel", "VERDICT"))
print("-" * 70)
for ortho in (1200, 1500, 1600, 2000, 2400, 3000, 4000):
    tiles = ortho / 100.0
    tile_texels = tiles * 16
    tile_ppt = 1920 / tile_texels
    plyr_texels = (ortho / 200.0) * 32
    plyr_ppt = 1920 / plyr_texels
    ti = abs(tile_ppt - round(tile_ppt)) < 1e-9
    pi = abs(plyr_ppt - round(plyr_ppt)) < 1e-9
    if ti and pi:
        verdict = "CRISP (both)"
    elif ti or pi:
        verdict = "partly crisp"
    else:
        verdict = "BLURRY (both)"
    print("%-8d %-9.1f %-14.2f %-14.2f %s" % (
        ortho, tiles, tile_ppt, plyr_ppt, verdict))
print()
print("Current ortho = 1600 (16 tiles) -> 7.50 px/texel for BOTH = fractional = blur")
print()
print("Room is 16 tiles wide, so ortho must be 1600 to show it all.")
print("To be pixel-perfect the room width must divide 120 tiles:")
print("  12, 15, 20, 24, 30, 40, 60 tiles")
print("  15 tiles (1500 uu) -> 8 px/texel for both  <- closest to 16")
