# This is intended to convert the unused flags into flags that hide the berries after collection.

import json
from pathlib import Path

MAPS_DIR = Path("data/maps")

FLAG_START = 0x264
FLAG_END = 0x2BB

berry_objects = []

# Find every berry tree first.
for map_file in sorted(MAPS_DIR.glob("*/map.json")):
    with map_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    for obj in data.get("object_events", []):
        if obj.get("graphics_id") == "OBJ_EVENT_GFX_BERRY_TREE":
            berry_objects.append((map_file, obj))

expected = FLAG_END - FLAG_START + 1

print(f"Found {len(berry_objects)} berry trees.")
print(f"Available flags: {expected}")

if len(berry_objects) != expected:
    raise RuntimeError(
        f"Expected exactly {expected} berry trees, "
        f"but found {len(berry_objects)}. Aborting."
    )

# Convert map-by-map so JSON formatting remains sane.
counter = 0

for map_file in sorted(MAPS_DIR.glob("*/map.json")):
    with map_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    changed = False

    for obj in data.get("object_events", []):
        if obj.get("graphics_id") != "OBJ_EVENT_GFX_BERRY_TREE":
            continue

        counter += 1

        obj["graphics_id"] = "OBJ_EVENT_GFX_ITEM_BALL"
        obj["movement_type"] = "MOVEMENT_TYPE_FACE_DOWN"

        # Placeholder item. Field-item randomizer will replace this.
        obj["trainer_sight_or_berry_tree_id"] = "ITEM_POKE_BALL"

        obj["script"] = "Common_EventScript_FindItem"
        obj["flag"] = f"FLAG_ITEM_BERRY_SPOT_{counter:03d}"

        changed = True

    if changed:
        with map_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        print(f"Converted berries in {map_file}")

print(f"\nConverted {counter} berry trees.")