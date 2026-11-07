"""Editor-time BP_EnemyPlatform generation from Paper2D floor tiles.

This module is imported by the editor's ``init_unreal.py`` (live auto-sync) and
by ``Scripts/_plan_enemy_platforms.py`` through the Unreal remote-execution
bridge. It only uses the editor Python API; it is never shipped or run in a
packaged game.

The tile map is the source of truth: one floor tile is 100 uu in L_Level_01.
Every Floor tile whose tile above is empty is a walkable surface, unless a tile
on the obstacle layer (``Wall`` by default) occupies that cell or the cell
directly above it. That finds floating platforms and the ground, and stops a
marker run at a solid wall/block tile.
"""
import hashlib

import unreal

DEFAULT_ACTOR = "TM_Background"
DEFAULT_LAYER = "Floor"
DEFAULT_OBSTACLE_LAYER = "Wall"
DEFAULT_Y_EXTENT = 50.0
DEFAULT_Z_EXTENT = 20.0
DEFAULT_MIN_WIDTH = 300.0
DEFAULT_MAX_WIDTH = 0.0
DEFAULT_PATROL_INSET = 80.0
DEFAULT_CLASS_PATH = (
    "/Game/DontTrustTheLevels/Enemies/Blueprints/"
    "BP_EnemyPlatform.BP_EnemyPlatform_C"
)
DEFAULT_AUTO_TAG = "EnemyPlatform.Auto"


def find_tile_map(actor_label=DEFAULT_ACTOR, layer_match=DEFAULT_LAYER):
    """Return (actor, component, tile_map, layer_names) or Nones.

    An actor with an exact layer name wins over one with only a partial match,
    so a decorative ``FloorDeco`` layer cannot hide the real ``Floor``.
    """
    match = layer_match.lower()
    fallback = None
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if not isinstance(actor, unreal.PaperTileMapActor):
            continue
        if actor_label and actor.get_actor_label() != actor_label:
            continue
        for component in actor.get_components_by_class(unreal.PaperTileMapComponent):
            tile_map = component.get_editor_property("tile_map")
            if not tile_map:
                continue
            names = [
                str(layer.get_editor_property("layer_name"))
                for layer in tile_map.get_editor_property("tile_layers")
            ]
            if any(name.lower() == match for name in names):
                return actor, component, tile_map, names
            if fallback is None and any(match in name.lower() for name in names):
                fallback = (actor, component, tile_map, names)
    if fallback:
        return fallback
    return None, None, None, []


def _match_layer(layers, layer_match):
    """Return (index, name), preferring an exact layer name over a partial one."""
    if not layer_match:
        return None, ""
    match = layer_match.lower()
    partial = None
    for index, layer in enumerate(layers):
        name = str(layer.get_editor_property("layer_name"))
        if name.lower() == match:
            return index, name
        if partial is None and match in name.lower():
            partial = (index, name)
    return partial if partial else (None, "")


def build_plan(actor_label=DEFAULT_ACTOR, layer_match=DEFAULT_LAYER,
               max_width=DEFAULT_MAX_WIDTH, min_width=DEFAULT_MIN_WIDTH,
               y_extent=DEFAULT_Y_EXTENT, z_extent=DEFAULT_Z_EXTENT,
               obstacle_layer=DEFAULT_OBSTACLE_LAYER):
    """Scan the tile map and return a JSON-serializable placement plan."""
    actor, component, tile_map, names = find_tile_map(actor_label, layer_match)
    if not component:
        return {"error": "no tile map actor/layer found"}

    map_width = tile_map.get_editor_property("map_width")
    map_height = tile_map.get_editor_property("map_height")
    tile_width = tile_map.get_editor_property("tile_width")
    tile_height = tile_map.get_editor_property("tile_height")
    layers = tile_map.get_editor_property("tile_layers")
    floor_index, floor_name = _match_layer(layers, layer_match)
    if floor_index is None:
        return {"error": "layer not found: " + layer_match}

    obstacle_index, obstacle_name = _match_layer(layers, obstacle_layer)
    if obstacle_index == floor_index:
        obstacle_index = None
        obstacle_name = ""

    location = actor.get_actor_location()
    scale = actor.get_actor_scale3d()
    tile_world_x = tile_width * scale.x
    tile_world_z = tile_height * scale.z
    if tile_world_x <= 0.0 or tile_world_z <= 0.0:
        return {"error": "tile map has zero scale"}
    # A Floor tile is walkable when the tile above it is empty. This finds
    # floating platforms as well as the ground and ignores the interior of a
    # thick floor. A Wall tile on the same cell, or directly above it, blocks
    # that cell so a run cannot continue through a solid prop.
    floors = set()
    for x in range(map_width):
        for y in range(map_height):
            info = component.get_tile(x, y, floor_index)
            if info and info.get_editor_property("tile_set") is not None:
                floors.add((x, y))

    obstacles = set()
    if obstacle_index is not None:
        for x in range(map_width):
            for y in range(map_height):
                info = component.get_tile(x, y, obstacle_index)
                if info and info.get_editor_property("tile_set") is not None:
                    obstacles.add((x, y))

    surfaces = set()
    blocked_floor_tiles = 0
    for (x, y) in floors:
        if obstacle_index is not None and (
                (x, y) in obstacles or (x, y - 1) in obstacles):
            blocked_floor_tiles += 1
            continue
        if y == 0 or (x, y - 1) not in floors:
            surfaces.add((x, y))

    # One run per contiguous horizontal surface. Different rows have different
    # Z, so they are always separate runs.
    runs = []
    for y in range(map_height):
        x = 0
        while x < map_width:
            if (x, y) not in surfaces:
                x += 1
                continue
            start = x
            while x + 1 < map_width and (x + 1, y) in surfaces:
                x += 1
            runs.append({"start": start, "end": x, "row": y})
            x += 1

    tiles_per_segment = None
    if max_width > 0.0:
        tiles_per_segment = max(1, int(max_width // tile_world_x))

    plan = []
    for run in runs:
        start = run["start"]
        while start <= run["end"]:
            end = run["end"]
            if tiles_per_segment:
                end = min(end, start + tiles_per_segment - 1)
            count = end - start + 1
            local0 = component.get_tile_center_position(start, run["row"])
            local1 = component.get_tile_center_position(end, run["row"])
            world_x0 = location.x + local0.x * scale.x
            world_x1 = location.x + local1.x * scale.x
            world_y = location.y + local0.y * scale.y
            world_z = location.z + local0.z * scale.z
            surface_z = world_z + tile_world_z / 2.0
            width = count * tile_world_x
            plan.append({
                "zone_id": "P_{:02d}".format(len(plan)),
                "start_tile": start,
                "end_tile": end,
                "tiles": count,
                "row": run["row"],
                "width": round(width, 1),
                "center_x": round((world_x0 + world_x1) / 2.0, 1),
                "center_y": round(world_y, 1),
                "surface_z": round(surface_z, 1),
                "box_extent_x": round(width / 2.0, 1),
                "box_extent_y": round(y_extent, 1),
                "box_extent_z": round(z_extent, 1),
                "patrol_eligible": width >= min_width,
            })
            start = end + 1

    return {
        "actor": actor.get_actor_label(),
        "layer": floor_name,
        "layers": names,
        "obstacle_layer": obstacle_name,
        "blocked_floor_tiles": blocked_floor_tiles,
        "map_width": map_width,
        "map_height": map_height,
        "tile_uu": round(tile_world_x, 1),
        "tile_uu_z": round(tile_world_z, 1),
        "max_width": max_width,
        "min_width": min_width,
        "runs_found": len(runs),
        "zones": plan,
    }


def _find_zone(actor):
    for box in actor.get_components_by_class(unreal.BoxComponent):
        if box.get_name().lower() == "zone":
            return box
    return None


def _set_actor_prop(actor, names, value):
    for name in names:
        try:
            actor.set_editor_property(name, value)
            return True
        except Exception:
            pass
    return False


def apply_plan(data, class_path=DEFAULT_CLASS_PATH,
               auto_tag=DEFAULT_AUTO_TAG,
               patrol_inset=DEFAULT_PATROL_INSET, save=False,
               skip_narrow=True):
    """Delete previous auto markers and spawn fresh ones from ``data``."""
    if data.get("error"):
        return {"error": data["error"]}

    marker_class = unreal.load_class(None, class_path)
    if not marker_class:
        return {"error": "could not load marker class: " + class_path}

    # Zone may be created by the Blueprint Construction Script, so the CDO does
    # not necessarily list it. Preflight a throwaway actor instead.
    probe = None
    zone_template = None
    try:
        probe = unreal.EditorLevelLibrary.spawn_actor_from_class(
            marker_class, unreal.Vector(0.0, 0.0, 100000.0),
            unreal.Rotator(0.0, 0.0, 0.0))
        if probe:
            zone_template = _find_zone(probe)
    finally:
        if probe:
            unreal.EditorLevelLibrary.destroy_actor(probe)
    if not zone_template:
        return {
            "error": (
                "BP_EnemyPlatform has no BoxComponent named Zone. "
                "Add it once in the Blueprint, then re-run generation."
            )
        }

    deleted = 0
    for old in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        try:
            old_tags = [str(tag) for tag in old.get_editor_property("tags")]
        except Exception:
            continue
        if auto_tag in old_tags:
            unreal.EditorLevelLibrary.destroy_actor(old)
            deleted += 1

    spawned = 0
    skipped = 0
    warnings = []
    for zone_plan in data.get("zones", []):
        if skip_narrow and not zone_plan["patrol_eligible"]:
            skipped += 1
            continue

        location = unreal.Vector(
            zone_plan["center_x"],
            zone_plan["center_y"],
            zone_plan["surface_z"],
        )
        marker = unreal.EditorLevelLibrary.spawn_actor_from_class(
            marker_class, location, unreal.Rotator(0.0, 0.0, 0.0))
        label = "BP_EnemyPlatform_Auto_{:02d}".format(spawned)
        if not marker:
            warnings.append(label + ": spawn failed")
            continue
        marker.set_actor_label(label)
        marker.set_editor_property(
            "tags", ["Enemy", "Enemy.Platform", auto_tag])

        zone = _find_zone(marker)
        if not zone:
            warnings.append(label + ": spawned without a Zone component")
            unreal.EditorLevelLibrary.destroy_actor(marker)
            continue

        try:
            zone.set_box_extent(unreal.Vector(
                zone_plan["box_extent_x"],
                zone_plan["box_extent_y"],
                zone_plan["box_extent_z"],
            ))
            zone.set_collision_profile_name("NoCollision")
            zone.set_hidden_in_game(True)
        except Exception as exc:
            warnings.append(label + ": could not configure Zone: {}".format(exc))
            unreal.EditorLevelLibrary.destroy_actor(marker)
            continue

        if not _set_actor_prop(marker, ("PatrolInset", "patrol_inset"),
                               float(patrol_inset)):
            warnings.append(label + ": PatrolInset variable missing")
        # The first BP_EnemyPlatform build used `bEnable`; keep accepting both
        # spellings until the variable is renamed to the documented `bEnabled`.
        if not _set_actor_prop(
                marker, ("bEnabled", "bEnable", "b_enabled", "b_enable"), True):
            warnings.append(label + ": bEnabled/bEnable variable missing")
        if not _set_actor_prop(marker, ("PlatformId", "platform_id"),
                               unreal.Name(zone_plan["zone_id"])):
            warnings.append(label + ": PlatformId variable missing")
        spawned += 1

    if save:
        try:
            saved = unreal.EditorLevelLibrary.save_current_level()
            if saved is False:
                warnings.append("save_current_level returned False")
        except Exception as exc:
            warnings.append("save failed: {}".format(exc))

    return {
        "deleted": deleted,
        "spawned": spawned,
        "skipped_narrow": skipped,
        "warnings": warnings,
    }


def _expected_markers(data, skip_narrow=True):
    expected = []
    for zone_plan in data.get("zones", []):
        if skip_narrow and not zone_plan["patrol_eligible"]:
            continue
        expected.append((
            round(zone_plan["center_x"], 1),
            round(zone_plan["center_y"], 1),
            round(zone_plan["surface_z"], 1),
            round(zone_plan["width"], 1),
        ))
    return sorted(expected)


def markers_match_plan(data, auto_tag=DEFAULT_AUTO_TAG):
    """True when the baked auto markers already match this plan."""
    if data.get("error"):
        return False
    actual = []
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        try:
            tags = [str(tag) for tag in actor.get_editor_property("tags")]
        except Exception:
            continue
        if auto_tag not in tags:
            continue
        zone = _find_zone(actor)
        if not zone:
            actual.append(("missing-zone", actor.get_actor_label()))
            continue
        location = actor.get_actor_location()
        extent = zone.get_editor_property("box_extent")
        actual.append((
            round(location.x, 1),
            round(location.y, 1),
            round(location.z, 1),
            round(extent.x * 2.0, 1),
        ))
    return sorted(actual) == _expected_markers(data)


def tile_signature(actor_label=DEFAULT_ACTOR, layer_match=DEFAULT_LAYER,
                   obstacle_layer=DEFAULT_OBSTACLE_LAYER):
    """Hash the floor and obstacle layers so the watcher sees edits cheaply."""
    actor, component, tile_map, names = find_tile_map(actor_label, layer_match)
    if not component:
        return None
    map_width = tile_map.get_editor_property("map_width")
    map_height = tile_map.get_editor_property("map_height")
    tile_width = tile_map.get_editor_property("tile_width")
    tile_height = tile_map.get_editor_property("tile_height")
    layers = tile_map.get_editor_property("tile_layers")
    floor_index, _floor_name = _match_layer(layers, layer_match)
    if floor_index is None:
        return None

    obstacle_index, _obstacle_name = _match_layer(layers, obstacle_layer)
    if obstacle_index == floor_index:
        obstacle_index = None

    location = actor.get_actor_location()
    scale = actor.get_actor_scale3d()
    digest = hashlib.sha1()
    header = "{},{},{},{},{},{},{},{},{},{},{},{},{}".format(
        map_width, map_height, tile_width, tile_height, floor_index,
        -1 if obstacle_index is None else obstacle_index,
        "|".join(names), location.x, location.y, location.z,
        scale.x, scale.y, scale.z)
    digest.update(header.encode("utf-8"))

    for layer_index in (floor_index, obstacle_index):
        if layer_index is None:
            continue
        digest.update("LAYER:{};".format(layer_index).encode("utf-8"))
        for x in range(map_width):
            for y in range(map_height):
                info = component.get_tile(x, y, layer_index)
                if not info:
                    continue
                tile_set = info.get_editor_property("tile_set")
                if tile_set is None:
                    continue
                packed = info.get_editor_property("packed_tile_index")
                digest.update("{}:{}:{}:{};".format(
                    x, y, tile_set.get_path_name(), packed).encode("utf-8"))
    return digest.hexdigest()

