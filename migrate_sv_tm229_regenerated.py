#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()

TM_NAMES = [
"Take Down","Charm","Fake Tears","Agility","Mud-Slap","Scary Face","Protect","Fire Fang","Thunder Fang","Ice Fang",
"Water Pulse","Low Kick","Acid Spray","Acrobatics","Struggle Bug","Psybeam","Confuse Ray","Thief","Disarming Voice","Trailblaze",
"Pounce","Chilling Water","Charge Beam","Fire Spin","Facade","Poison Tail","Aerial Ace","Bulldoze","Hex","Snarl",
"Metal Claw","Swift","Magical Leaf","Icy Wind","Mud Shot","Rock Tomb","Draining Kiss","Flame Charge","Low Sweep","Air Cutter",
"Stored Power","Night Shade","Fling","Dragon Tail","Venoshock","Avalanche","Endure","Volt Switch","Sunny Day","Rain Dance",
"Sandstorm","Snowscape","Smart Strike","Psyshock","Dig","Bullet Seed","False Swipe","Brick Break","Zen Headbutt","U-turn",
"Shadow Claw","Foul Play","Psychic Fangs","Bulk Up","Air Slash","Body Slam","Fire Punch","Thunder Punch","Ice Punch","Sleep Talk",
"Seed Bomb","Electro Ball","Drain Punch","Reflect","Light Screen","Rock Blast","Waterfall","Dragon Claw","Dazzling Gleam","Metronome",
"Grass Knot","Thunder Wave","Poison Jab","Stomping Tantrum","Rest","Rock Slide","Taunt","Swords Dance","Body Press","Spikes",
"Toxic Spikes","Imprison","Flash Cannon","Dark Pulse","Leech Life","Eerie Impulse","Fly","Skill Swap","Iron Head","Dragon Dance",
"Power Gem","Gunk Shot","Substitute","Iron Defense","X-Scissor","Drill Run","Will-O-Wisp","Crunch","Trick","Liquidation",
"Giga Drain","Aura Sphere","Tailwind","Shadow Ball","Dragon Pulse","Stealth Rock","Hyper Voice","Heat Wave","Energy Ball","Psychic",
"Heavy Slam","Encore","Surf","Ice Spinner","Flamethrower","Thunderbolt","Play Rough","Amnesia","Calm Mind","Helping Hand",
"Pollen Puff","Baton Pass","Earth Power","Reversal","Ice Beam","Electric Terrain","Grassy Terrain","Psychic Terrain","Misty Terrain","Nasty Plot",
"Fire Blast","Hydro Pump","Blizzard","Fire Pledge","Water Pledge","Grass Pledge","Wild Charge","Sludge Bomb","Earthquake","Stone Edge",
"Phantom Force","Giga Impact","Blast Burn","Hydro Cannon","Frenzy Plant","Outrage","Overheat","Focus Blast","Leaf Storm","Hurricane",
"Trick Room","Bug Buzz","Hyper Beam","Brave Bird","Flare Blitz","Thunder","Close Combat","Solar Beam","Draco Meteor","Steel Beam",
"Tera Blast","Roar","Charge Beam","Haze","Toxic","Sand Tomb","Spite","Gravity","Smack Down","Gyro Ball",
"Knock Off","Bug Bite","Super Fang","Vacuum Wave","Lunge","High Horsepower","Icicle Spear","Scald","Heat Crash","Solar Blade",
"Uproar","Focus Punch","Weather Ball","Grassy Glide","Burning Jealousy","Flip Turn","Dual Wingbeat","Poltergeist","Lash Out","Scale Shot",
"Misty Explosion","Pain Split","Psych Up","Double-Edge","Endeavor","Petal Blizzard","Temper Flare","Whirlpool","Muddy Water","Supercell Slam",
"Electroweb","Triple Axel","Coaching","Sludge Wave","Scorching Sands","Feather Dance","Future Sight","Expanding Force","Skitter Smack","Meteor Beam",
"Throat Chop","Breaking Swipe","Metal Sound","Curse","Hard Press","Dragon Cheer","Alluring Voice","Psychic Noise","Upper Hand",
]

assert len(TM_NAMES) == 229

FILES = {
    "constants": ROOT / "include/constants/items.h",
    "tmhm": ROOT / "include/constants/tms_hms.h",
    "item_h": ROOT / "include/item.h",
    "data_items": ROOT / "src/data/items.h",
    "moves": ROOT / "src/data/moves_info.h",
    "item_menu": ROOT / "src/item_menu.c",
    "randomizer": ROOT / "src/randomizer.c",
    "randomizer_cfg": ROOT / "include/config/randomizer.h",
}

for p in FILES.values():
    if not p.exists():
        sys.exit(f"ERROR: missing {p}. Run this script from the pokeemerald-expansion repo root.")

def backup(path):
    bak = path.with_suffix(path.suffix + ".pre_sv_tm229.bak")
    if not bak.exists():
        shutil.copy2(path, bak)

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def item_tm_const(n):
    return f"ITEM_TM{n:02d}" if n < 100 else f"ITEM_TM{n}"

# Build display-name -> MOVE_* mapping from this checkout itself.
moves_text = FILES["moves"].read_text(encoding="utf-8")
entry_re = re.compile(
    r"\[(MOVE_[A-Z0-9_]+)\]\s*=\s*\{(?P<body>.*?)(?=\n\s*\[MOVE_[A-Z0-9_]+\]\s*=|\Z)",
    re.S,
)
name_re = re.compile(r'\.name\s*=\s*COMPOUND_STRING\("([^"]+)"\)')
move_by_name = {}
for m in entry_re.finditer(moves_text):
    nm = name_re.search(m.group("body"))
    if nm:
        move_by_name[norm(nm.group(1))] = m.group(1)

resolved = []
missing = []
for n, display in enumerate(TM_NAMES, 1):
    move = move_by_name.get(norm(display))
    if move is None:
        missing.append((n, display))
    resolved.append(move)

if missing:
    print("ERROR: these Scarlet/Violet TM moves were not found in src/data/moves_info.h:")
    for n, display in missing:
        print(f"  TM{n:03d}: {display}")
    sys.exit(1)

suffixes = [m.removeprefix("MOVE_") for m in resolved]

# Report duplicates. Canonical SV has Charge Beam twice (TM023/TM173).
seen = {}
duplicates = []
for n, suffix in enumerate(suffixes, 1):
    if suffix in seen:
        duplicates.append((suffix, seen[suffix], n))
    else:
        seen[suffix] = n

print(f"Resolved all {len(resolved)} TM moves against this checkout.")
if duplicates:
    print("Duplicate move(s) in canonical SV TM numbering:")
    for suffix, first, later in duplicates:
        print(f"  {suffix}: TM{first:03d} and TM{later:03d}; ITEM_TM_{suffix} alias will point to TM{first:03d}.")

# 1) include/constants/items.h
p = FILES["constants"]
text = p.read_text(encoding="utf-8")
backup(p)

if "#define ITEM_TM229 " in text:
    sys.exit("ERROR: ITEM_TM229 already exists. Refusing to run migration twice.")

# Shift every existing numeric ITEM_* constant from old HM01 (682) onward by +129.
def shift_item_define(m):
    name, value = m.group(1), int(m.group(2))
    if value >= 682:
        value += 129
    return f"#define {name} {value}"

text = re.sub(r"^#define (ITEM_[A-Z0-9_]+) (\d+)\s*$", shift_item_define, text, flags=re.M)

# Insert TM101..TM229 after existing TM100.
new_tm_defs = "\n".join(f"#define {item_tm_const(n)} {581+n}" for n in range(101, 230))
needle = "#define ITEM_TM100 681"
if needle not in text:
    sys.exit("ERROR: could not find original ITEM_TM100 681 after shift pass.")
text = text.replace(needle, needle + "\n" + new_tm_defs, 1)

# Add stable named aliases. For duplicate moves, alias the first occurrence.
alias_lines = [
    "",
    "// Scarlet/Violet TM move aliases (first occurrence used for duplicate moves)."
]
for suffix, n in seen.items():
    alias_lines.append(f"#define ITEM_TM_{suffix} {item_tm_const(n)}")
alias_block = "\n".join(alias_lines) + "\n"
text = text.replace(new_tm_defs, new_tm_defs + alias_block, 1)

text = re.sub(r"^#define ITEMS_COUNT 831\s*$", "#define ITEMS_COUNT 960", text, flags=re.M)
text = re.sub(r"^#define NUM_TECHNICAL_MACHINES 100\s*$",
              "#define NUM_TECHNICAL_MACHINES 229", text, flags=re.M)
p.write_text(text, encoding="utf-8")

# 2) include/constants/tms_hms.h
# FOREACH_TM now enumerates numeric TM slots; named move aliases live in items.h.
p = FILES["tmhm"]
text = p.read_text(encoding="utf-8")
backup(p)
tm_lines = ["#define FOREACH_TM(F) \\"]
for n in range(1, 230):
    end = " \\" if n != 229 else ""
    tm_lines.append(f"    F({n:03d}){end}")
new_tm_macro = "\n".join(tm_lines)

text, count = re.subn(
    r"#define FOREACH_TM\(F\) \\\n.*?(?=\n\n#define FOREACH_HM\(F\))",
    new_tm_macro,
    text,
    flags=re.S,
)
if count != 1:
    sys.exit(f"ERROR: expected to replace FOREACH_TM once, replaced {count}.")
p.write_text(text, encoding="utf-8")

# 3) include/item.h
# TM aliases are now #defines in constants/items.h. The old sequential enum
# cannot represent canonical SV cleanly because Charge Beam appears twice.
p = FILES["item_h"]
text = p.read_text(encoding="utf-8")
backup(p)
old_block_re = re.compile(
    r"#define ENUM_TM\(id\) CAT\(ITEM_TM_, id\),\s*\n"
    r"#define ENUM_HM\(id\) CAT\(ITEM_HM_, id\),\s*\n"
    r"enum\s*\{\s*\n"
    r"\s*ENUM_TM_START_ = ITEM_TM01 - 1,\s*\n"
    r"\s*FOREACH_TM\(ENUM_TM\)\s*\n\s*\n"
    r"\s*ENUM_HM_START_ = ITEM_HM01 - 1,\s*\n"
    r"\s*FOREACH_HM\(ENUM_HM\)\s*\n"
    r"\};\s*\n"
    r"#undef ENUM_TM\s*\n"
    r"#undef ENUM_HM",
    re.S,
)
new_block = """#define ENUM_HM(id) CAT(ITEM_HM_, id),
enum
{
    ENUM_HM_START_ = ITEM_HM01 - 1,
    FOREACH_HM(ENUM_HM)
};
#undef ENUM_HM"""
text, count = old_block_re.subn(new_block, text)
if count != 1:
    sys.exit(f"ERROR: expected to replace TM/HM alias enum once in include/item.h, replaced {count}.")
p.write_text(text, encoding="utf-8")

# 4) src/data/items.h
p = FILES["data_items"]
text = p.read_text(encoding="utf-8")
backup(p)

if "sTechnicalMachineDesc" not in text:
    qmark = 'static const u8 sQuestionMarksDesc[]  = _("?????");'
    if qmark not in text:
        sys.exit("ERROR: could not find sQuestionMarksDesc insertion point.")
    text = text.replace(
        qmark,
        qmark + '\nstatic const u8 sTechnicalMachineDesc[] = _("Teaches the shown\\nmove to a Pokémon.");',
        1,
    )

# Replace the full existing TM data block, ending immediately before HM data.
start_match = re.search(r"\n\s*\[(?:ITEM_TM_[A-Z0-9_]+|ITEM_TM0?1)\]\s*=\s*\{", text)
hm_match = re.search(r"\n\s*\[ITEM_HM_[A-Z0-9_]+\]\s*=\s*\{", text)
if not start_match or not hm_match or hm_match.start() <= start_match.start():
    sys.exit("ERROR: could not locate TM -> HM block in src/data/items.h.")

entries = []
for n, move in enumerate(resolved, 1):
    entries.append(f"""
    [{item_tm_const(n)}] =
    {{
        .name = _("TM{n:03d}"),
        .price = 3000,
        .description = sTechnicalMachineDesc,
        .importance = I_REUSABLE_TMS,
        .pocket = POCKET_TM_HM,
        .type = ITEM_USE_PARTY_MENU,
        .fieldUseFunc = ItemUseOutOfBattle_TMHM,
        .secondaryId = {move},
    }},
""")
new_tm_data = "".join(entries).rstrip() + "\n"
text = text[:start_match.start()] + "\n" + new_tm_data + text[hm_match.start():]
p.write_text(text, encoding="utf-8")

# 5) Bag TM numbering: 3 digits.
p = FILES["item_menu"]
text = p.read_text(encoding="utf-8")
backup(p)
old = "ConvertIntToDecimalStringN(gStringVar1, itemId - ITEM_TM01 + 1, STR_CONV_MODE_LEADING_ZEROS, 2);"
new = "ConvertIntToDecimalStringN(gStringVar1, itemId - ITEM_TM01 + 1, STR_CONV_MODE_LEADING_ZEROS, 3);"
if old not in text:
    sys.exit("ERROR: could not find 2-digit TM bag formatter.")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

# 6) Randomizer upper bound.
p = FILES["randomizer_cfg"]
text = p.read_text(encoding="utf-8")
backup(p)
text, count = re.subn(
    r"^#define RANDOMIZER_MAX_TM\s+ITEM_TM\d+\s*$",
    "#define RANDOMIZER_MAX_TM           ITEM_TM229",
    text,
    flags=re.M,
)
if count != 1:
    sys.exit(f"ERROR: expected one RANDOMIZER_MAX_TM definition, found {count}.")
p.write_text(text, encoding="utf-8")

p = FILES["randomizer"]
text = p.read_text(encoding="utf-8")
backup(p)
text = text.replace("ITEM_TM100 - ITEM_TM01 + 1", "RANDOMIZER_MAX_TM - ITEM_TM01 + 1")
p.write_text(text, encoding="utf-8")

print()
print("SV TM229 migration written successfully.")
print("Important: item IDs >= old HM01 shifted by +129; use a NEW SAVE.")
print("Backups were created as *.pre_sv_tm229.bak.")
print()
print("Next run:")
print('  grep -R -n "ITEM_TM100 - ITEM_TM01\\|NUM_TECHNICAL_MACHINES 100\\|ITEM_TM229\\|ITEM_HM01" include src | head -80')
print("  make -j$(nproc)")
