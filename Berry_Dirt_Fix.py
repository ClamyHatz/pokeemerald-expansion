"""
This tells you info. about the "berry dirt".
Then it replaces all dirt with near-by tiles
so everything looks even.
"""

'''
# What is berry dirt?
import struct

path = "data/layouts/Route102/map.bin"
width = 50

with open(path, "rb") as f:
    data = f.read()

def block(x, y):
    off = (y * width + x) * 2
    return struct.unpack_from("<H", data, off)[0]

for y in range(0, 5):
    for x in range(22, 29):
        print(f"({x:2},{y:2}) = 0x{block(x,y):04X}", end="   ")
    print()

# Where is berry dirt?
import json

p = "data/maps/Route102/map.json"

with open(p) as f:
    m = json.load(f)

for obj in m["object_events"]:
    if str(obj.get("flag", "")).startswith("FLAG_ITEM_BERRY_SPOT_"):
        print(obj["flag"], obj["x"], obj["y"])

# How many berry dirts?
import json
import struct

with open("data/layouts/layouts.json") as f:
    layouts = json.load(f)

if isinstance(layouts, dict):
    for value in layouts.values():
        if isinstance(value, list) and value and isinstance(value[0], dict) and "id" in value[0]:
            layouts = value
            break

layout_by_id = {x["id"]: x for x in layouts}

results = {}

import glob
for map_path in glob.glob("data/maps/*/map.json"):
    with open(map_path) as f:
        m = json.load(f)

    berries = [
        obj for obj in m.get("object_events", [])
        if str(obj.get("flag", "")).startswith("FLAG_ITEM_BERRY_SPOT_")
    ]

    if not berries:
        continue

    layout = layout_by_id[m["layout"]]
    width = layout["width"]

    with open(layout["blockdata_filepath"], "rb") as f:
        data = f.read()

    for obj in berries:
        x, y = obj["x"], obj["y"]
        off = (y * width + x) * 2
        block = struct.unpack_from("<H", data, off)[0]

        results[block] = results.get(block, 0) + 1
        print(f'{obj["flag"]}: {map_path} ({x},{y}) = 0x{block:04X}')

print("\nBLOCK COUNTS:")
for block, count in sorted(results.items(), key=lambda x: -x[1]):
    print(f"0x{block:04X}: {count}")

# How is berry dirt?
import glob, json, struct

with open("data/layouts/layouts.json") as f:
    layouts_json = json.load(f)

if isinstance(layouts_json, dict):
    for value in layouts_json.values():
        if isinstance(value, list) and value and isinstance(value[0], dict) and "id" in value[0]:
            layouts_json = value
            break

layouts = {x["id"]: x for x in layouts_json}

for map_path in glob.glob("data/maps/*/map.json"):
    with open(map_path) as f:
        m = json.load(f)

    spots = [
        o for o in m.get("object_events", [])
        if str(o.get("flag", "")).startswith("FLAG_ITEM_BERRY_SPOT_")
    ]
    if not spots:
        continue

    layout = layouts[m["layout"]]
    width = layout["width"]
    height = layout["height"]

    with open(layout["blockdata_filepath"], "rb") as f:
        data = f.read()

    def block(x, y):
        off = (y * width + x) * 2
        return struct.unpack_from("<H", data, off)[0]

    for o in spots:
        x, y = o["x"], o["y"]
        vals = []

        for d in range(0, 6):
            yy = y + d
            if yy < height:
                vals.append(f"+{d}=0x{block(x,yy):04X}")

        print(o["flag"], map_path, f"({x},{y})", " ".join(vals))

'''
import glob
import json
import os
import struct
from collections import Counter, defaultdict


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

# How far around each former berry tree we inspect for berry-bed borders.
SCAN_RADIUS = 2

# A tile needs to occur near at least this many berry spots before it can
# automatically be considered part of a berry patch.
MIN_NEAR_OCCURRENCES = 2

# At least this fraction of all uses of a metatile in a layout must occur
# near former berry spots before we consider it berry-specific.
MIN_BERRY_CONCENTRATION = 0.60

# These are ordinary terrain blocks we've seen around the berry patches.
# Never automatically erase them.
SAFE_GROUND_BLOCKS = {
    0x3001,
    0x3004,
    0x300D,
    0x300E,
    0x300F,
    0x1170,
    0x3170,
    0x10A1,
    0x5001,
}


# ------------------------------------------------------------
# LOAD LAYOUT INFORMATION
# ------------------------------------------------------------

with open("data/layouts/layouts.json", encoding="utf-8") as f:
    layout_data = json.load(f)

if isinstance(layout_data, dict):
    for value in layout_data.values():
        if (
            isinstance(value, list)
            and value
            and isinstance(value[0], dict)
            and "id" in value[0]
        ):
            layout_data = value
            break

layouts = {layout["id"]: layout for layout in layout_data}


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def read_block(blocks, width, x, y):
    offset = (y * width + x) * 2
    return struct.unpack_from("<H", blocks, offset)[0]


def write_block(blocks, width, x, y, value):
    offset = (y * width + x) * 2
    struct.pack_into("<H", blocks, offset, value)


def make_grass(block):
    """
    Keep the upper metadata/elevation nibble but replace the underlying
    metatile with ordinary grass (metatile 1).

    Examples:
        0x354C -> 0x3001
        0x554C -> 0x5001
    """
    return (block & 0xF000) | 0x0001


# ------------------------------------------------------------
# FIND ALL MAPS CONTAINING OUR CONVERTED BERRY SPOTS
# ------------------------------------------------------------

maps = []

for map_path in glob.glob("data/maps/*/map.json"):
    with open(map_path, encoding="utf-8") as f:
        map_data = json.load(f)

    berry_spots = [
        obj
        for obj in map_data.get("object_events", [])
        if str(obj.get("flag", "")).startswith("FLAG_ITEM_BERRY_SPOT_")
    ]

    if not berry_spots:
        continue

    layout = layouts[map_data["layout"]]

    maps.append(
        {
            "map_path": map_path,
            "map_data": map_data,
            "berry_spots": berry_spots,
            "layout": layout,
        }
    )


# ------------------------------------------------------------
# PROCESS EACH MAP
# ------------------------------------------------------------

total_centers_changed = 0
total_borders_changed = 0

for entry in maps:
    map_path = entry["map_path"]
    berry_spots = entry["berry_spots"]
    layout = entry["layout"]

    width = layout["width"]
    height = layout["height"]
    block_path = layout["blockdata_filepath"]

    with open(block_path, "rb") as f:
        blocks = bytearray(f.read())

    berry_coords = {
        (obj["x"], obj["y"])
        for obj in berry_spots
    }

    # --------------------------------------------------------
    # Count every block in this layout.
    # --------------------------------------------------------

    layout_counts = Counter()

    for y in range(height):
        for x in range(width):
            layout_counts[read_block(blocks, width, x, y)] += 1

    # --------------------------------------------------------
    # Count blocks occurring close to berry spots.
    #
    # We count each coordinate only once even if two berries' scan
    # areas overlap.
    # --------------------------------------------------------

    nearby_coords = set()

    for obj in berry_spots:
        bx = obj["x"]
        by = obj["y"]

        for dy in range(-SCAN_RADIUS, SCAN_RADIUS + 1):
            for dx in range(-SCAN_RADIUS, SCAN_RADIUS + 1):
                x = bx + dx
                y = by + dy

                if 0 <= x < width and 0 <= y < height:
                    nearby_coords.add((x, y))

    nearby_counts = Counter(
        read_block(blocks, width, x, y)
        for x, y in nearby_coords
    )

    # --------------------------------------------------------
    # Automatically determine which block IDs are probably
    # berry-patch borders.
    # --------------------------------------------------------

    berry_patch_blocks = set()

    for block, near_count in nearby_counts.items():
        if block in SAFE_GROUND_BLOCKS:
            continue

        total_count = layout_counts[block]

        if near_count < MIN_NEAR_OCCURRENCES:
            continue

        concentration = near_count / total_count

        if concentration >= MIN_BERRY_CONCENTRATION:
            berry_patch_blocks.add(block)

    print()
    print(map_path)

    if berry_patch_blocks:
        print(
            "  Auto-detected berry border blocks:",
            " ".join(
                f"0x{x:04X}"
                for x in sorted(berry_patch_blocks)
            ),
        )
    else:
        print("  No extra berry border blocks detected.")

    # --------------------------------------------------------
    # First fix every actual former berry-tree square.
    # --------------------------------------------------------

    for obj in berry_spots:
        x = obj["x"]
        y = obj["y"]

        original = read_block(blocks, width, x, y)

        # Route130's berry already sits on ordinary terrain.
        if original == 0x1170:
            continue

        replacement = make_grass(original)

        if replacement != original:
            write_block(blocks, width, x, y, replacement)
            total_centers_changed += 1

    # --------------------------------------------------------
    # Then remove automatically detected border blocks, but ONLY
    # inside the small area surrounding a known former berry spot.
    # --------------------------------------------------------

    changed_coords = set()

    for obj in berry_spots:
        bx = obj["x"]
        by = obj["y"]

        # Slightly wider than the analysis radius so large berry beds,
        # including Route123, get their outer rails.
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                x = bx + dx
                y = by + dy

                if not (0 <= x < width and 0 <= y < height):
                    continue

                if (x, y) in changed_coords:
                    continue

                value = read_block(blocks, width, x, y)

                if value not in berry_patch_blocks:
                    continue

                replacement = make_grass(value)

                if replacement != value:
                    write_block(blocks, width, x, y, replacement)
                    changed_coords.add((x, y))
                    total_borders_changed += 1

    # --------------------------------------------------------
    # Save layout and touch map.json so make rebuilds the map.
    # --------------------------------------------------------

    with open(block_path, "wb") as f:
        f.write(blocks)

    os.utime(map_path, None)


print()
print("DONE")
print(f"Former berry squares changed: {total_centers_changed}")
print(f"Berry-border squares changed: {total_borders_changed}")

