#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()

LEGACY_TMS = [
    (230, "TORMENT",      "MOVE_TORMENT"),
    (231, "ATTRACT",      "MOVE_ATTRACT"),
    (232, "RETURN",       "MOVE_RETURN"),
    (233, "FRUSTRATION",  "MOVE_FRUSTRATION"),
    (234, "HIDDEN_POWER", "MOVE_HIDDEN_POWER"),
    (235, "STEEL_WING",   "MOVE_STEEL_WING"),
    (236, "SHOCK_WAVE",   "MOVE_SHOCK_WAVE"),
    (237, "IRON_TAIL",    "MOVE_IRON_TAIL"),
    (238, "DOUBLE_TEAM",  "MOVE_DOUBLE_TEAM"),
    (239, "SECRET_POWER", "MOVE_SECRET_POWER"),
    (240, "HAIL",         "MOVE_HAIL"),
    (241, "SNATCH",       "MOVE_SNATCH"),
    (242, "SAFEGUARD",    "MOVE_SAFEGUARD"),
]

FILES = {
    "constants": ROOT / "include/constants/items.h",
    "tmhm": ROOT / "include/constants/tms_hms.h",
    "data_items": ROOT / "src/data/items.h",
    "randomizer_cfg": ROOT / "include/config/randomizer.h",
}

for path in FILES.values():
    if not path.exists():
        sys.exit(f"ERROR: missing {path}. Run this from the pokeemerald-expansion repo root.")

def backup(path):
    bak = path.with_suffix(path.suffix + ".pre_legacy_tm242.bak")
    if not bak.exists():
        shutil.copy2(path, bak)

def item_tm_const(n):
    return f"ITEM_TM{n}"

# Sanity-check that this is the already-migrated TM229 tree.
constants_text = FILES["constants"].read_text(encoding="utf-8")
if "#define ITEM_TM229 810" not in constants_text:
    sys.exit("ERROR: expected ITEM_TM229 810. This script is for the already-migrated TM229 checkout.")
if "#define ITEM_TM230 " in constants_text:
    sys.exit("ERROR: ITEM_TM230 already exists. Refusing to run migration twice.")
if "#define ITEMS_COUNT 960" not in constants_text:
    sys.exit("ERROR: expected ITEMS_COUNT 960 before legacy-TM extension.")

# Confirm the moves still exist in this checkout.
moves_h = (ROOT / "include/constants/moves.h").read_text(encoding="utf-8")
moves_info = (ROOT / "src/data/moves_info.h").read_text(encoding="utf-8")
for _, _, move in LEGACY_TMS:
    if not re.search(rf"^#define {re.escape(move)}\s+\d+\s*$", moves_h, flags=re.M):
        sys.exit(f"ERROR: {move} is missing from include/constants/moves.h")
    if f"[{move}]" not in moves_info:
        sys.exit(f"ERROR: {move} is missing from src/data/moves_info.h")

# 1) include/constants/items.h
p = FILES["constants"]
text = p.read_text(encoding="utf-8")
backup(p)

# Shift every existing numeric item ID at old HM01 (811) and later by +13.
def shift_numeric_item(m):
    name = m.group(1)
    value = int(m.group(2))
    if value >= 811:
        value += 13
    return f"#define {name} {value}"

text = re.sub(
    r"^#define (ITEM_[A-Z0-9_]+) (\d+)\s*$",
    shift_numeric_item,
    text,
    flags=re.M,
)

# Insert TM230..TM242 after TM229.
tm_defs = "\n".join(
    f"#define ITEM_TM{num} {581 + num}"
    for num, _, _ in LEGACY_TMS
)
needle = "#define ITEM_TM229 810"
if needle not in text:
    sys.exit("ERROR: could not find ITEM_TM229 810 after shift.")
text = text.replace(needle, needle + "\n" + tm_defs, 1)

# Add the legacy semantic aliases.
alias_lines = [
    "",
    "// Legacy Emerald compatibility TMs (not part of the canonical SV TM001-TM229 list).",
]
for num, alias, _ in LEGACY_TMS:
    alias_lines.append(f"#define ITEM_TM_{alias} ITEM_TM{num}")
alias_block = "\n".join(alias_lines) + "\n"

# Put aliases immediately after ITEM_TM_UPPER_HAND if present.
upper_hand = "#define ITEM_TM_UPPER_HAND ITEM_TM229"
if upper_hand not in text:
    sys.exit("ERROR: could not find ITEM_TM_UPPER_HAND alias.")
text = text.replace(upper_hand, upper_hand + alias_block, 1)

text = re.sub(
    r"^#define ITEMS_COUNT 960\s*$",
    "#define ITEMS_COUNT 973",
    text,
    flags=re.M,
)
text = re.sub(
    r"^#define NUM_TECHNICAL_MACHINES 229\s*$",
    "#define NUM_TECHNICAL_MACHINES 242",
    text,
    flags=re.M,
)

p.write_text(text, encoding="utf-8")

# 2) include/constants/tms_hms.h
p = FILES["tmhm"]
text = p.read_text(encoding="utf-8")
backup(p)

# Append F(230)..F(242) to FOREACH_TM, keeping the 3-digit numeric style.
m = re.search(
    r"(#define FOREACH_TM\(F\) \\\n)(.*?)(\n\n#define FOREACH_HM\(F\))",
    text,
    flags=re.S,
)
if not m:
    sys.exit("ERROR: could not locate FOREACH_TM macro.")

body = m.group(2)
if "F(230)" in body:
    sys.exit("ERROR: FOREACH_TM already contains TM230.")

# Ensure the current final F(229) gains a continuation slash.
body = re.sub(r"(\n\s*F\(229\))\s*$", r"\1 \\", body)
extra = "".join(
    f"\n    F({num})" + (" \\" if num != 242 else "")
    for num, _, _ in LEGACY_TMS
)
new_macro = m.group(1) + body + extra + m.group(3)
text = text[:m.start()] + new_macro + text[m.end():]
p.write_text(text, encoding="utf-8")

# 3) src/data/items.h
p = FILES["data_items"]
text = p.read_text(encoding="utf-8")
backup(p)

if "sTechnicalMachineDesc" not in text:
    sys.exit("ERROR: sTechnicalMachineDesc not found; expected the prior TM229 migration.")

hm_match = re.search(r"\n\s*\[ITEM_HM_[A-Z0-9_]+\]\s*=\s*\{", text)
if not hm_match:
    sys.exit("ERROR: could not find first HM item entry in src/data/items.h.")

entries = []
for num, alias, move in LEGACY_TMS:
    entries.append(f"""
    [ITEM_TM{num}] =
    {{
        .name = _("TM{num:03d}"),
        .price = 3000,
        .description = sTechnicalMachineDesc,
        .importance = I_REUSABLE_TMS,
        .pocket = POCKET_TM_HM,
        .type = ITEM_USE_PARTY_MENU,
        .fieldUseFunc = ItemUseOutOfBattle_TMHM,
        .secondaryId = {move},
    }},
""")

legacy_block = "".join(entries).rstrip() + "\n"
text = text[:hm_match.start()] + "\n" + legacy_block + text[hm_match.start():]
p.write_text(text, encoding="utf-8")

# 4) Randomizer ceiling.
p = FILES["randomizer_cfg"]
text = p.read_text(encoding="utf-8")
backup(p)
text, count = re.subn(
    r"^#define RANDOMIZER_MAX_TM\s+ITEM_TM229\s*$",
    "#define RANDOMIZER_MAX_TM           ITEM_TM242",
    text,
    flags=re.M,
)
if count != 1:
    sys.exit(f"ERROR: expected exactly one RANDOMIZER_MAX_TM ITEM_TM229 line, changed {count}.")
p.write_text(text, encoding="utf-8")

print("Legacy TM extension complete.")
print()
print("Added:")
for num, alias, move in LEGACY_TMS:
    print(f"  TM{num:03d} {alias.replace('_', ' ').title()} -> {move}")
print()
print("New layout:")
print("  ITEM_TM242           = 823")
print("  ITEM_HM01            = 824")
print("  ITEM_HM08            = 831")
print("  ITEM_PORTABLE_HEAL   = 971")
print("  ITEM_INFINITE_REPEL  = 972")
print("  ITEMS_COUNT          = 973")
print("  NUM_TECHNICAL_MACHINES = 242")
print("  RANDOMIZER_MAX_TM    = ITEM_TM242")
print()
print("Backups created as *.pre_legacy_tm242.bak")
print()
print("Now run:")
print('  grep -n "ITEM_TM230\\|ITEM_TM242\\|ITEM_HM01\\|ITEM_PORTABLE_HEAL\\|ITEM_INFINITE_REPEL\\|ITEMS_COUNT\\|NUM_TECHNICAL_MACHINES" include/constants/items.h')
print("  make -j$(nproc)")
