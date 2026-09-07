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

BERRY_PATCH_BLOCKS = {
    0x3113,
    0x3114,
    0x3115,
    0x327B,
    0x327D,
    0x328C,
    0x328E,
}

import glob
import json
import struct
import os

with open("data/layouts/layouts.json") as f:
    layout_data = json.load(f)

if isinstance(layout_data, dict):
    for value in layout_data.values():
        if isinstance(value, list) and value and isinstance(value[0], dict) and "id" in value[0]:
            layout_data = value
            break

layouts = {layout["id"]: layout for layout in layout_data}

for map_path in glob.glob("data/maps/*/map.json"):
    with open(map_path) as f:
        map_data = json.load(f)

    berry_spots = [
        obj for obj in map_data.get("object_events", [])
        if str(obj.get("flag", "")).startswith("FLAG_ITEM_BERRY_SPOT_")
    ]

    if not berry_spots:
        continue

    layout = layouts[map_data["layout"]]
    width = layout["width"]
    height = layout["height"]
    block_path = layout["blockdata_filepath"]

    with open(block_path, "rb") as f:
        blocks = bytearray(f.read())

    berry_coords = {(obj["x"], obj["y"]) for obj in berry_spots}

    def get_block(x, y):
        offset = (y * width + x) * 2
        return struct.unpack_from("<H", blocks, offset)[0]

    def set_block(x, y, value):
        offset = (y * width + x) * 2
        struct.pack_into("<H", blocks, offset, value)

    for obj in berry_spots:
        x = obj["x"]
        y = obj["y"]

        original = get_block(x, y)

        if original != 0x1170:
            replacement = (original & 0xF000) | 0x0001
            set_block(x, y, replacement)

        for dy in range(0, 2):
            for dx in range(-2, 3):
                nx = x + dx
                ny = y + dy

                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue

                value = get_block(nx, ny)

                if value in BERRY_PATCH_BLOCKS:
                    replacement = (value & 0xF000) | 0x0001
                    set_block(nx, ny, replacement)

    with open(block_path, "wb") as f:
        f.write(blocks)

    os.utime(map_path, None)

