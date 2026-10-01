import json
import os
import shutil
import struct
import sys


# ============================================================
# FINAL SURGICAL BERRY TERRAIN FIX
#
# Each entry:
#   (x, y, expected_current_value, replacement_value)
#
# NO scanning.
# NO automatic detection.
# NO global metatile replacement.
# ============================================================

PATCHES = {
    # --------------------------------------------------------
    # Route 103
    #
    # The old broad fixer ate part of the cliff immediately
    # behind the three former berry trees.
    #
    # Restore the original 0x0479 cliff blocks.
    # --------------------------------------------------------
    103: [
        (58, 4, 0x0001, 0x0479),
        (59, 4, 0x0001, 0x0479),
        (60, 4, 0x0001, 0x0479),
    ],

    # --------------------------------------------------------
    # Route 114
    #
    # Remaining brown berry-bed cap above the balls,
    # plus the tiny leftover dirt piece below.
    # --------------------------------------------------------
    114: [
        (31, 42, 0x3104, 0x3001),
        (32, 42, 0x3105, 0x3001),
        (30, 46, 0x0734, 0x3001),
    ],

    # --------------------------------------------------------
    # Route 115
    #
    # Three-piece berry-bed cap still visible above the balls.
    # --------------------------------------------------------
    115: [
        (30, 63, 0x3103, 0x3001),
        (31, 63, 0x3104, 0x3001),
        (32, 63, 0x3105, 0x3001),
    ],

    # --------------------------------------------------------
    # Route 116
    #
    # These are NOT berry dirt.
    # The broad fixer accidentally erased two forest-edge
    # metatiles. Restore the original 0x35E5 blocks.
    # --------------------------------------------------------
    116: [
        (19, 1, 0x3001, 0x35E5),
        (21, 1, 0x3001, 0x35E5),
    ],

    # --------------------------------------------------------
    # Route 117
    #
    # Same problem: the forest/tree edge above the old berry
    # row was flattened to blank 0x0001 blocks.
    #
    # Restore the original alternating edge.
    # --------------------------------------------------------
    117: [
        (40, 12, 0x0001, 0x05E4),
        (41, 12, 0x0001, 0x05E5),
        (42, 12, 0x0001, 0x05E4),
        (43, 12, 0x0001, 0x05E5),
        (44, 12, 0x0001, 0x05E4),
    ],

    # --------------------------------------------------------
    # Route 118
    #
    # Two leftover berry-bed side pieces.
    # --------------------------------------------------------
    118: [
        (34, 5, 0x3246, 0x3001),
        (38, 5, 0x3247, 0x3001),
    ],

    # --------------------------------------------------------
    # Route 119
    #
    # NOT berry dirt.
    # Two cliff-transition cells were flattened from 0x4069
    # into ordinary 0x4001 terrain.
    #
    # Restore the proper cliff face.
    # --------------------------------------------------------
    119: [
        (30, 91, 0x4001, 0x4069),
        (31, 91, 0x4001, 0x4069),
    ],

    # --------------------------------------------------------
    # Route 120
    #
    # Two tiny leftover berry-bed fragments around the
    # four-ball patch beside the water.
    # --------------------------------------------------------
    120: [
        (3, 78, 0x3103, 0x3001),
        (8, 78, 0x3105, 0x3001),
    ],

    # --------------------------------------------------------
    # Route 121
    #
    # Two tiny leftover berry-bed fragments above the
    # four-ball row.
    # --------------------------------------------------------
    121: [
        (63, 13, 0x3103, 0x3001),
        (68, 13, 0x3105, 0x3001),
    ],
}


# ============================================================
# LOAD LAYOUT DATA
# ============================================================

with open("data/layouts/layouts.json", encoding="utf-8") as f:
    raw = json.load(f)

if isinstance(raw, dict):
    for value in raw.values():
        if (
            isinstance(value, list)
            and value
            and isinstance(value[0], dict)
            and "id" in value[0]
        ):
            raw = value
            break

layouts = {entry["id"]: entry for entry in raw}


def read_u16(data, width, x, y):
    offset = (y * width + x) * 2
    return struct.unpack_from("<H", data, offset)[0]


def write_u16(data, width, x, y, value):
    offset = (y * width + x) * 2
    struct.pack_into("<H", data, offset, value)


# ============================================================
# LOAD EVERYTHING FIRST
# ============================================================

loaded = {}

for route, edits in PATCHES.items():
    map_json = f"data/maps/Route{route}/map.json"

    with open(map_json, encoding="utf-8") as f:
        map_data = json.load(f)

    layout = layouts[map_data["layout"]]
    path = layout["blockdata_filepath"]
    width = layout["width"]
    height = layout["height"]

    with open(path, "rb") as f:
        blocks = bytearray(f.read())

    loaded[route] = {
        "path": path,
        "width": width,
        "height": height,
        "blocks": blocks,
        "edits": edits,
    }


# ============================================================
# VALIDATE EVERY SINGLE CELL BEFORE WRITING ANYTHING
# ============================================================

errors = []

print("Validating berry terrain patch...")
print()

for route, info in loaded.items():
    width = info["width"]
    height = info["height"]
    blocks = info["blocks"]

    print(f"Route {route}:")

    for x, y, expected, replacement in info["edits"]:
        if not (0 <= x < width and 0 <= y < height):
            errors.append(
                f"Route {route} ({x},{y}) is outside "
                f"{width}x{height}"
            )
            print(f"  ERROR ({x},{y}) out of bounds")
            continue

        actual = read_u16(blocks, width, x, y)

        if actual != expected:
            errors.append(
                f"Route {route} ({x},{y}): "
                f"expected 0x{expected:04X}, "
                f"found 0x{actual:04X}"
            )

            print(
                f"  ERROR ({x},{y}) "
                f"expected {expected:04X}, "
                f"found {actual:04X}"
            )
        else:
            print(
                f"  OK    ({x},{y}) "
                f"{expected:04X} -> {replacement:04X}"
            )

    print()


if errors:
    print("=" * 60)
    print("ABORTED.")
    print("Nothing was written.")
    print("=" * 60)

    for error in errors:
        print(error)

    sys.exit(1)


# ============================================================
# MAKE BACKUPS
# ============================================================

print("All checks passed.")
print("Creating backups...")
print()

backed_up = set()

for route, info in loaded.items():
    path = info["path"]

    if path in backed_up:
        continue

    backup = path + ".berry_final_backup"

    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print(f"  {backup}")
    else:
        print(f"  backup already exists: {backup}")

    backed_up.add(path)


# ============================================================
# APPLY EXACT PATCHES
# ============================================================

print()
print("Applying patches...")
print()

for route, info in loaded.items():
    path = info["path"]
    width = info["width"]
    blocks = info["blocks"]

    for x, y, expected, replacement in info["edits"]:
        write_u16(blocks, width, x, y, replacement)

    with open(path, "wb") as f:
        f.write(blocks)

    print(
        f"Route {route}: "
        f"{len(info['edits'])} cell(s) changed"
    )


print()
print("=" * 60)
print("FINAL BERRY TERRAIN PATCH COMPLETE")
print("=" * 60)
print()
print("Route 111 intentionally required no current map edits.")
print("Its former berry-bed cells are already clean in the current map.")
