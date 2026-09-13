import glob
import json
import os
import shutil
import struct

# SAFE BERRY DIRT CLEANUP
# Only touches known berry-bed metatiles immediately around former berry spots.

BERRY_BED_METATILES = {
    0x14B, 0x14C, 0x14D,
    0x113, 0x114, 0x115,
    0x10B, 0x10C, 0x10D,
    0x273, 0x275, 0x27B, 0x27D,
    0x29B, 0x293, 0x294, 0x29C,
    0x2D5, 0x2DD, 0x2E5,
    0x2E6,
}

RADIUS = 1

with open("data/layouts/layouts.json", encoding="utf-8") as f:
    layout_data = json.load(f)

if isinstance(layout_data, dict):
    for value in layout_data.values():
        if isinstance(value, list) and value and isinstance(value[0], dict) and "id" in value[0]:
            layout_data = value
            break

layouts = {layout["id"]: layout for layout in layout_data}

def read_block(data, width, x, y):
    offset = (y * width + x) * 2
    return struct.unpack_from("<H", data, offset)[0]

def write_block(data, width, x, y, block):
    offset = (y * width + x) * 2
    struct.pack_into("<H", data, offset, block)

def metatile_id(block):
    return block & 0x03FF

def make_grass(block):
    # Preserve all non-metatile bits; replace only the low 10-bit metatile id.
    return (block & 0xFC00) | 0x0001

layouts_to_spots = {}

for map_path in glob.glob("data/maps/*/map.json"):
    with open(map_path, encoding="utf-8") as f:
        map_data = json.load(f)

    berry_spots = [
        obj for obj in map_data.get("object_events", [])
        if str(obj.get("flag", "")).startswith("FLAG_ITEM_BERRY_SPOT_")
    ]

    if not berry_spots:
        continue

    layout = layouts[map_data["layout"]]
    block_path = layout["blockdata_filepath"]

    entry = layouts_to_spots.setdefault(block_path, {
        "layout": layout,
        "maps": set(),
        "spots": [],
    })

    entry["maps"].add(map_path)

    for obj in berry_spots:
        entry["spots"].append((obj["x"], obj["y"], obj["flag"], map_path))

total_changed = 0

for block_path, info in layouts_to_spots.items():
    layout = info["layout"]
    width = layout["width"]
    height = layout["height"]

    with open(block_path, "rb") as f:
        original = f.read()

    data = bytearray(original)
    changed_coords = set()

    print()
    print(block_path)

    for spot_x, spot_y, flag, map_path in info["spots"]:
        for dy in range(-RADIUS, RADIUS + 1):
            for dx in range(-RADIUS, RADIUS + 1):
                x = spot_x + dx
                y = spot_y + dy

                if not (0 <= x < width and 0 <= y < height):
                    continue
                if (x, y) in changed_coords:
                    continue

                block = read_block(data, width, x, y)

                if metatile_id(block) not in BERRY_BED_METATILES:
                    continue

                replacement = make_grass(block)
                if replacement == block:
                    continue

                print(f"  {flag} ({x},{y}) 0x{block:04X} -> 0x{replacement:04X}")

                write_block(data, width, x, y, replacement)
                changed_coords.add((x, y))
                total_changed += 1

    if data == original:
        print("  unchanged")
        continue

    backup = block_path + ".pre_safe_berry_cleanup"
    if not os.path.exists(backup):
        shutil.copy2(block_path, backup)

    with open(block_path, "wb") as f:
        f.write(data)

    for map_path in info["maps"]:
        os.utime(map_path, None)

    print(f"  updated ({len(changed_coords)} tiles)")

print()
print("DONE")
print(f"Berry-bed tiles changed: {total_changed}")
