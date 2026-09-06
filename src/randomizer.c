#include "randomizer.h"

#if RANDOMIZER_AVAILABLE == TRUE
#include "main.h"
#include "new_game.h"
#include "item.h"
#include "event_data.h"
#include "field_control_avatar.h"
#include "pokemon.h"
#include "script.h"
#include "data.h"
#include "data/randomizer/special_form_tables.h"
#include "constants/abilities.h"
#include "data/randomizer/ability_whitelist.h"
#include "constants/abilities.h"
#include "move.h"
#include "constants/moves.h"
#include "constants/pokemon.h"

// Add the mons you wish to be randomized when given as starter/gift mon to this list
const u16 gStarterAndGiftMonTable[STARTER_AND_GIFT_MON_COUNT] =
{
    SPECIES_CYNDAQUIL,
    SPECIES_TOTODILE,
    SPECIES_CHIKORITA,
    SPECIES_TREECKO,
    SPECIES_TORCHIC,
    SPECIES_MUDKIP,
    SPECIES_BELDUM,
    SPECIES_CASTFORM_NORMAL,
    SPECIES_LILEEP,
    SPECIES_ANORITH,
};

// Add the mons you wish to be randomized when given as egg mon to this list
const u16 gEggMonTable[EGG_MON_COUNT] =
{
    SPECIES_WYNAUT, 
};

// This is a list of baby Pokémon that should not cause their evolution
// to count as an evolved pokemon.
// XXX: put this somewhere else?
static const u16 sPreevolutionBabyMons[] =
{
    SPECIES_PICHU,
    SPECIES_CLEFFA,
    SPECIES_IGGLYBUFF,
    SPECIES_TYROGUE,
    SPECIES_SMOOCHUM,
    SPECIES_ELEKID,
    SPECIES_MAGBY,
    SPECIES_AZURILL,
    SPECIES_WYNAUT,
    SPECIES_BUDEW,
    SPECIES_CHINGLING,
    SPECIES_BONSLY,
    SPECIES_MIME_JR,
    SPECIES_HAPPINY,
    SPECIES_MUNCHLAX,
    SPECIES_MANTYKE,
};

bool32 RandomizerFeatureEnabled(enum RandomizerFeature feature)
{
    switch(feature)
    {
        case RANDOMIZE_WILD_MON:
            #ifdef FORCE_RANDOMIZE_WILD_MON
                return FORCE_RANDOMIZE_WILD_MON;
            #else
                return FlagGet(RANDOMIZER_FLAG_WILD_MON);
            #endif
        case RANDOMIZE_FIELD_ITEMS:
            #ifdef FORCE_RANDOMIZE_FIELD_ITEMS
                return FORCE_RANDOMIZE_FIELD_ITEMS;
            #else
                return FlagGet(RANDOMIZER_FLAG_FIELD_ITEMS);
            #endif
        case RANDOMIZE_TRAINER_MON:
            #ifdef FORCE_RANDOMIZE_TRAINER_MON
                return FORCE_RANDOMIZE_TRAINER_MON;
            #else
                return FlagGet(RANDOMIZER_FLAG_TRAINER_MON);
            #endif
        case RANDOMIZE_FIXED_MON:
            #ifdef FORCE_RANDOMIZE_FIXED_MON
                return FORCE_RANDOMIZE_FIXED_MON;
            #else
                return FlagGet(RANDOMIZER_FLAG_FIXED_MON);
            #endif
        case RANDOMIZE_STARTER_AND_GIFT_MON:
            #ifdef FORCE_RANDOMIZE_STARTER_AND_GIFT_MON
                return FORCE_RANDOMIZE_STARTER_AND_GIFT_MON;
            #else
                return FlagGet(RANDOMIZER_FLAG_STARTER_AND_GIFT_MON);
            #endif
        case RANDOMIZE_ABILITIES:
            #ifdef FORCE_RANDOMIZE_ABILITIES
                return FORCE_RANDOMIZE_ABILITIES;
            #else
                return FlagGet(RANDOMIZER_FLAG_ABILITIES);
            #endif
        case RANDOMIZE_LEARNSET:
            #ifdef FORCE_RANDOMIZE_LEARNSET
                return FORCE_RANDOMIZE_LEARNSET;
            #else
                return FlagGet(RANDOMIZER_FLAG_LEARNSET);
            #endif
        default:
            return FALSE;
    }
}

u32 GetRandomizerSeed(void)
{
    #if RANDOMIZER_SEED_IS_TRAINER_ID == TRUE
        return GetTrainerId(gSaveBlock2Ptr->playerTrainerId);
    #else
        u32 result;
        result = ((u32)VarGet(RANDOMIZER_VAR_SEED_H) << 16) | VarGet(RANDOMIZER_VAR_SEED_L);
        return result;
    #endif
}

// Sets the seed that will be used for the randomizer if doing so is possible.
bool32 SetRandomizerSeed(u32 newSeed)
{
    #if RANDOMIZER_SEED_IS_TRAINER_ID == TRUE
        // It isn't possible to set the randomizer seed in this case.
        return FALSE;
    #else
        VarSet(RANDOMIZER_VAR_SEED_L, (u16)newSeed);
        VarSet(RANDOMIZER_VAR_SEED_H, (u16)(newSeed >> 16));
        return TRUE;
    #endif
}

static bool32 IsSpeciesPermitted(u16 species)
{
    // SPECIES_NONE is never valid.
    if (species == SPECIES_NONE)
        return FALSE;
    // This is used to indicate a disabled species.
    if (gSpeciesInfo[species].baseHP == 0)
        return FALSE;
    if (gSpeciesInfo[species].randomizerMode == MON_RANDOMIZER_INVALID)
        return FALSE;

    return TRUE;
};

u32 GenerateSeedForRandomizer(void)
{
    u32 data;
    const u32 vblankCounter = gMain.vblankCounter1;
    #if HQ_RANDOM == TRUE
        data = Random32();
    #else
        data = gRngValue;
        Random();
    #endif
    return data ^ vblankCounter;
}

u16 GetRandomizerOption(enum RandomizerOption option)
{
    switch(option) {
        case RANDOMIZER_OPTION_SPECIES_MODE:
            return VarGet(RANDOMIZER_VAR_SPECIES_MODE);
        default: // Unknown option.
            return 0;
    }
}

/* Seeds an SFC32 random number generator state for the randomizer.

SFC32 can be seeded with up to 96 bits of data.
32 are used for the randomizer reason, which is mixed with the seed.
data1 and data2 are 64 bits of data that a caller can use for
any purpose they wish. Certain groups of functions will assign a purpose to
these: for example, RandomizeMon uses data2 for the original species number.
data2 is also mixed with the seed.
*/
struct Sfc32State RandomizerRandSeed(enum RandomizerReason reason, u32 data1, u32 data2)
{
    struct Sfc32State state;
    u32 i;
    const u32 randomizerSeed = GetRandomizerSeed();

    state.a = randomizerSeed + (u32)reason;
    state.b = randomizerSeed ^ data2;
    state.c = data1;
    state.ctr = RANDOMIZER_STREAM;

    for (i = 0; i < 10; i++)
    {
        _SFC32_Next_Stream(&state, RANDOMIZER_STREAM);
    }

    return state;
}


// This uses a slightly accelerated bitmasking method.
u32 RandomizerNextRange(struct Sfc32State* state, u32 range)
{
    u32 next_power_of_two, mask, result;
    if (range < 2)
        return 0;
    else if (range == UINT32_MAX)
        return _SFC32_Next_Stream(state, RANDOMIZER_STREAM);

    next_power_of_two = range;
    --next_power_of_two;
    next_power_of_two |= next_power_of_two >> 1;
    next_power_of_two |= next_power_of_two >> 2;
    next_power_of_two |= next_power_of_two >> 4;
    next_power_of_two |= next_power_of_two >> 8;
    ++next_power_of_two;

    mask = next_power_of_two - 1;

    do
    {
        result = _SFC32_Next_Stream(state, RANDOMIZER_STREAM) & mask;
    } while (result >= range);

    return result;
}

// Functions for producing single seeded random numbers.
u16 RandomizerRand(enum RandomizerReason reason, u32 data1, u32 data2)
{
    struct Sfc32State state;
    state = RandomizerRandSeed(reason, data1, data2);
    return RandomizerNext(&state);
}

u16 RandomizerRandRange(enum RandomizerReason reason, u32 data1, u32 data2, u16 range)
{
    struct Sfc32State state;
    state = RandomizerRandSeed(reason, data1, data2);
    return RandomizerNextRange(&state, range);
}

// Utility functions for the field item randomizer.
static inline bool32 IsItemTMHM(u16 itemId)
{
    return ItemId_GetPocket(itemId) == POCKET_TM_HM;
}

static inline bool32 IsItemHM(u16 itemId)
{
    return itemId >= ITEM_HM01 && IsItemTMHM(itemId);
}

static inline bool32 IsKeyItem(u16 itemId)
{
    return ItemId_GetPocket(itemId) == POCKET_KEY_ITEMS;
}

// Don't randomize HMs or key items, that can make the game unwinnable.
// ITEM_NONE also should not be randomized as it is invalid.
static inline bool32 ShouldRandomizeItem(u16 itemId)
{
    return !(IsItemHM(itemId) || IsKeyItem(itemId) || itemId == ITEM_NONE);
}

#include "data/randomizer/item_whitelist.h"

static u16 GetRandomizerPoolItem(struct Sfc32State *state)
{
    u32 whitelistSize = ARRAY_COUNT(sRandomizerItemWhitelist);

    // Increase this to make TMs more common.
    const u32 tmWeight = 30;

    u32 index = RandomizerNextRange(state, whitelistSize + tmWeight);

    if (index < whitelistSize)
        return sRandomizerItemWhitelist[index];

    // We hit a TM slot, so now choose any TM uniformly.
    return RandomizerNextRange(
        state,
        ITEM_TM100 - ITEM_TM01 + 1
    ) + ITEM_TM01;
}

// Given a found item and its location in the game, returns a replacement for that item.
u16 RandomizeFoundItem(u16 itemId, u8 mapNum, u8 mapGroup, u8 localId)
{
    struct Sfc32State state;
    u16 result;
    u32 mapSeed;

    if (IsKeyItem(itemId) || itemId == ITEM_NONE)
        return itemId;

    // Seed the generator using the original item and the object event that led up
    // to this call.
    mapSeed = ((u32)mapGroup) << 16;
    mapSeed |= ((u32)mapNum) << 8;
    mapSeed |= localId;

    state = RandomizerRandSeed(RANDOMIZER_REASON_FIELD_ITEM, mapSeed, itemId);

    // Randomize TMs to TMs. Because HMs shouldn't be randomized, we can assume
    // this is a TM.
    // Normal TM gifts stay within the TM pool.
    if (IsItemTMHM(itemId) && !IsItemHM(itemId))
    {
        return RandomizerNextRange(
            &state,
            RANDOMIZER_MAX_TM - ITEM_TM01 + 1
        ) + ITEM_TM01;
    }

    // Randomize everything else to everything else.
    do {
        result = GetRandomizerPoolItem(&state);
    } while(!ShouldRandomizeItem(result) || IsItemHM(result));

    return result;

}

u16 RandomizeGiftItem(u16 itemId, u16 amount, u8 mapNum, u8 mapGroup)
{
    struct Sfc32State state;
    u16 result;
    u32 mapSeed;

    if (!ShouldRandomizeItem(itemId))
        return itemId;

    // Stable identity for this scripted gift.
    // Same save + map + original item + quantity = same replacement.
    mapSeed = ((u32)mapGroup << 24)
            | ((u32)mapNum << 16)
            | amount;

    state = RandomizerRandSeed(
        RANDOMIZER_REASON_GIFT_ITEM,
        mapSeed,
        itemId);

    // Gift TMs remain TMs.
    if (IsItemTMHM(itemId))
        return RandomizerNextRange(
            &state,
            RANDOMIZER_MAX_TM - ITEM_TM01 + 1
        ) + ITEM_TM01;

    // Everything else comes from the normal safe item pool.
    do
    {
        result = GetRandomizerPoolItem(&state);
    }
    while (!ShouldRandomizeItem(result) || IsItemHM(result));

    return result;
}

void GiftItemRandomize_NativeCall(struct ScriptContext *ctx)
{
    if (!RandomizerFeatureEnabled(RANDOMIZE_FIELD_ITEMS))
        return;

    gSpecialVar_0x8000 =
        RandomizeGiftItem(
            gSpecialVar_0x8000,
            gSpecialVar_0x8001,
            gSaveBlock1Ptr->location.mapNum,
            gSaveBlock1Ptr->location.mapGroup
        );
}

// Takes a SpecialVar as an argument to simplify handling separate scripts.
static inline void RandomizeFoundItemScript(u16 *scriptVar)
{
    if (RandomizerFeatureEnabled(RANDOMIZE_FIELD_ITEMS))
    {
        // Pull the object event information from the current object event.
        u8 objEvent = gSelectedObjectEvent;
        *scriptVar = RandomizeFoundItem(
            *scriptVar,
            gObjectEvents[objEvent].mapGroup,
            gObjectEvents[objEvent].mapNum,
            gObjectEvents[objEvent].localId);
    }
}

// These functions are invoked by the scripts that handle found items and
// write the results of the randomization to the correct script variable.
void FindItemRandomize_NativeCall(struct ScriptContext *ctx)
{
    RandomizeFoundItemScript(&gSpecialVar_0x8000);
}

void FindHiddenItemRandomize_NativeCall(struct ScriptContext *ctx)
{
    RandomizeFoundItemScript(&gSpecialVar_0x8005);
}

// Both legendary and mythical Pokémon are included in this category.
static inline bool32 IsRandomizerLegendary(u16 species)
{
    return gSpeciesInfo[species].isLegendary
        || gSpeciesInfo[species].isMythical
        || gSpeciesInfo[species].isUltraBeast;
}

struct SpeciesTable
{
    // Stores the group records for each species.
    u16 groupData[RANDOMIZER_SPECIES_COUNT];
    u16 speciesToGroupIndex[RANDOMIZER_SPECIES_COUNT];
    // Maps a group data index to a species.
    u16 groupIndexToSpecies[RANDOMIZER_SPECIES_COUNT];
};

#define GROUP_INVALID   0xFFFF

static inline u16 GetSpeciesGroup(const struct SpeciesTable* table, u16 species)
{
    u16 groupEntry;
    groupEntry = table->groupData[table->speciesToGroupIndex[species]];

    #ifndef NDEBUG
        MgbaPrintf(MGBA_LOG_INFO, "GetSpeciesGroup: input %lu species %lu group %lu",
            (unsigned long)species+1, (unsigned long)groupEntry.species, (unsigned long)groupEntry.group);
    #endif

    return groupEntry;

}

static void GetGroupRange(u16 group, enum RandomizerSpeciesMode mode, u16 *resultMin, u16 *resultMax)
{
    // This should never be called on a GROUP_INVALID mon, but if it happens,
    // GROUP_INVALID should be the only valid group.
    if (group == GROUP_INVALID)
    {
        *resultMax = *resultMin = group;
        return;
    }

    // BST mode: species can randomize to species with similar BST.
    if (mode == MON_RANDOM_BST)
    {
        // Choose a 10.24% range around the base BST.
        s32 base, minScaled, maxScaled;
        base = group * 1024;
        minScaled = (base - group * 200) / 1024;
        maxScaled = (base + group * 200) / 1024;
        *resultMin = (u16)max(minScaled, 0);
        *resultMax =(u16)min(maxScaled, GROUP_INVALID-1);
    }
    // Species in the same category can randomize to each other.
    else
    {
        *resultMax = *resultMin = group;
    }
}

//
static void GetIndicesFromGroupRange(const struct SpeciesTable *table, u16 minGroup, u16 maxGroup, u16 *start, u16 *end)
{
    u16 index, leftBound, rightBound, maxRightBound;
    maxRightBound = RANDOMIZER_SPECIES_COUNT-1;
    maxGroup = min(0xFFFEu, maxGroup);
    minGroup = min(0xFFFEu, minGroup);
    leftBound = 0;
    rightBound = RANDOMIZER_SPECIES_COUNT-1;
    // Do leftmost binary search to find the lower limit.
    while (leftBound < rightBound)
    {
        u16 leftFoundGroup;
        index = (leftBound + rightBound) / 2;
        leftFoundGroup = table->groupData[index];
        if (leftFoundGroup < minGroup)
            leftBound = index + 1;
        else
        {
            if (leftFoundGroup > maxGroup)
                maxRightBound = index;
            rightBound = index;
        }
    }
    *start = leftBound;

    rightBound = maxRightBound;

    // Do rightmost binary search to find the upper limit.
    while (leftBound < rightBound)
    {
        index = (leftBound + rightBound) / 2;
        if (table->groupData[index] > maxGroup)
            rightBound = index;
        else
            leftBound = index + 1;
    }
    *end = rightBound - 1;
}

#if RANDOMIZER_DYNAMIC_SPECIES == TRUE

struct RamSpeciesTable
{
    enum RandomizerSpeciesMode mode;
    bool16 tableInitialized;
    struct SpeciesTable speciesTable;
};

EWRAM_DATA static struct RamSpeciesTable sRamSpeciesTable = {0};

static void FillSpeciesGroupsRandom(struct SpeciesTable* entries)
{
    u16 i;
    for (i = 0; i < RANDOMIZER_SPECIES_COUNT; i++)
    {
        entries->groupIndexToSpecies[i] = i;
        if (IsSpeciesPermitted(i))
            entries->groupData[i] = 0;
        else
            entries->groupData[i] = GROUP_INVALID;
    }
}

static void FillSpeciesGroupsBST(struct SpeciesTable* entries)
{
    u16 i;
    for(i = 0; i < RANDOMIZER_SPECIES_COUNT; i++)
    {
        const struct SpeciesInfo *curSpeciesInfo;
        u16 group;

        entries->groupIndexToSpecies[i] = i;

        if (IsSpeciesPermitted(i))
        {
            curSpeciesInfo = &gSpeciesInfo[i];

            group = curSpeciesInfo->baseAttack;
            group += curSpeciesInfo->baseDefense;
            group += curSpeciesInfo->baseSpAttack;
            group += curSpeciesInfo->baseSpDefense;
            group += curSpeciesInfo->baseHP;
            group += curSpeciesInfo->baseSpeed;

        }
        else
            group = GROUP_INVALID;

        entries->groupData[i] = group;
    }
}

static void FillSpeciesGroupsLegendary(struct SpeciesTable* entries)
{
    u16 i;
    for(i = 0; i < RANDOMIZER_SPECIES_COUNT; i++)
    {
        entries->groupIndexToSpecies[i] = i;
        if (!IsSpeciesPermitted(i))
            entries->groupData[i] = GROUP_INVALID;
        else
            entries->groupData[i] = IsRandomizerLegendary(i);
    }
}

static void MarkEvolutions(struct SpeciesTable *entries, u16 species, u16 stage)
{
    const struct Evolution *evos;
    if (stage == RANDOMIZER_MAX_EVO_STAGES)
        return;

    evos = GetSpeciesEvolutions(species);
    if (evos != NULL)
    {
        u32 i;
        for (i = 0; evos[i].method != 0xFFFF; i++)
        {
            if(entries->groupData[species-1] <= stage)
                MarkEvolutions(entries, evos[i].targetSpecies, stage+1);
        }
    }
    entries->groupIndexToSpecies[species] = species;
    entries->groupData[species] = stage;
}

static void FillSpeciesGroupsEvolution(struct SpeciesTable* entries)
{
    u16 i;
    static const u8 EVO_GROUP_LEGENDARY = 0x81;
    static const u8 EVO_GROUP_NO_EVO = RANDOMIZER_MAX_EVO_STAGES+1;

    // Step 0: zero everything
    memset(entries, 0, sizeof(sRamSpeciesTable.speciesTable));

    // Step 1: pre-visit the special babies, and mark them as basic mons.
    for (i = 0; i < ARRAY_COUNT(sPreevolutionBabyMons); i++)
    {
        u16 babyMonIndex = sPreevolutionBabyMons[i];
        entries->groupIndexToSpecies[babyMonIndex] = babyMonIndex;
        if(IsSpeciesPermitted(babyMonIndex))
            entries->groupData[babyMonIndex] = 0;
        else
            entries->groupData[babyMonIndex] = GROUP_INVALID;
    }

    for(i = 0; i < RANDOMIZER_SPECIES_COUNT; i++)
    {
        if (entries->groupIndexToSpecies[i] == 0)
        {
            // This entry hasn't been visited yet, so we don't know if it evolves.
            const struct Evolution *evos = GetSpeciesEvolutions(i);
            entries->groupIndexToSpecies[i] = i;
            if (!IsSpeciesPermitted(i)) // This shouldn't show up in randomization.
                entries->groupData[i] = GROUP_INVALID;
            else if (IsRandomizerLegendary(i)) // Legendaries get their own group.
                entries->groupData[i] = EVO_GROUP_LEGENDARY;
            else if (evos == NULL || evos->method == 0xFFFF)
                entries->groupData[i] = EVO_GROUP_NO_EVO;
            else // There are evolutions! Let's check it out.
                MarkEvolutions(entries, i, 0);
        }
    }
}

static inline u16 LeftChildIndex(u16 index)
{
    return 2*index + 1;
}

static inline void SwapSpeciesAndGroup(struct SpeciesTable* table, u16 indexA, u16 indexB)
{
    u16 temp;
    SWAP(table->groupData[indexA], table->groupData[indexB], temp);
    SWAP(table->groupIndexToSpecies[indexA], table->groupIndexToSpecies[indexB], temp);
}

static void BuildRandomizerSpeciesTable(enum RandomizerSpeciesMode mode)
{
    u16 i, start, end;
    struct SpeciesTable* speciesTable;

    sRamSpeciesTable.tableInitialized = TRUE;
    sRamSpeciesTable.mode = mode;
    speciesTable = &sRamSpeciesTable.speciesTable;

    switch(mode)
    {
        case MON_RANDOM_LEGEND_AWARE:
            FillSpeciesGroupsLegendary(speciesTable);
            break;
        case MON_RANDOM_BST:
            FillSpeciesGroupsBST(speciesTable);
            break;
        case MON_EVOLUTION:
            FillSpeciesGroupsEvolution(speciesTable);
            break;
        case MON_RANDOM:
        default:
            FillSpeciesGroupsRandom(speciesTable);
    }

    // Heap sort the table.
    start = RANDOMIZER_SPECIES_COUNT/2;
    end = RANDOMIZER_SPECIES_COUNT-1;

    while (end > 1)
    {
        u16 root;
        if (start > 0)
            start = start - 1;
        else
        {
            end = end - 1;
            SwapSpeciesAndGroup(speciesTable, end, 0);
        }
        root = start;
        while(LeftChildIndex(root) < end)
        {
            u16 child;
            child = LeftChildIndex(root);

            if (child+1 < end
                && speciesTable->groupData[child] < speciesTable->groupData[child+1])
            {
                child = child + 1;
            }

            if (speciesTable->groupData[root] < speciesTable->groupData[child])
            {
                SwapSpeciesAndGroup(speciesTable, root, child);
                root = child;
            }
            else
                break;
        }
    }


    // Build the species index. This is needed for getting a group from a species.
    for (i = 0; i < RANDOMIZER_SPECIES_COUNT; i++)
    {
        u16 targetIndex = speciesTable->groupIndexToSpecies[i];
        speciesTable->speciesToGroupIndex[targetIndex] = i;
    }
}

static const struct SpeciesTable* GetSpeciesTable(enum RandomizerSpeciesMode mode)
{
    if (!sRamSpeciesTable.tableInitialized || mode != sRamSpeciesTable.mode )
        BuildRandomizerSpeciesTable(mode);

    return &sRamSpeciesTable.speciesTable;
}

void PreloadRandomizationTables(void)
{
    GetSpeciesTable(GetRandomizerOption(RANDOMIZER_OPTION_SPECIES_MODE));
}

#endif

static u16 RandomizeMonTableLookup(struct Sfc32State* state, enum RandomizerSpeciesMode mode, u16 species)
{
    u16 minGroup, maxGroup, originalGroup, resultIndex;
    u16 minIndex, maxIndex;
    const struct SpeciesTable *table;

    table = GetSpeciesTable(mode);
    originalGroup = GetSpeciesGroup(table, species);

    if (originalGroup == GROUP_INVALID)
        return species;

    GetGroupRange(originalGroup, mode, &minGroup, &maxGroup);
    GetIndicesFromGroupRange(table, minGroup, maxGroup, &minIndex, &maxIndex);
    resultIndex = RandomizerNextRange(state, maxIndex - minIndex + 1) + minIndex;
    return table->groupIndexToSpecies[resultIndex];
}

static u16 RandomizeMonFromSeed(struct Sfc32State *state, enum RandomizerSpeciesMode mode, u16 species)
{
    if (!IsSpeciesPermitted(species))
        return species;

    if (mode >= MAX_MON_MODE)
        mode = MON_RANDOM;

    return RandomizeMonTableLookup(state, mode, species);

}

// Fills an array with count Pokémon, with no repeats.
void GetUniqueMonList(enum RandomizerReason reason, enum RandomizerSpeciesMode mode, u32 seed1, u16 seed2, u8 count, const u16 *originalSpecies, u16 *resultSpecies)
{
    u32 i, curMon;
    u32 seenMonBitVector[(RANDOMIZER_SPECIES_COUNT-1)/32+1] = {};
    struct Sfc32State state = RandomizerRandSeed(reason, seed1, seed2);

    for (i = 0; i < count; i++)
    {
        u16 curOriginal = originalSpecies[i];
        bool32 foundNextMon = FALSE;
        if (!IsSpeciesPermitted(curOriginal))
        {
            // If there's non-permitted Pokémon in here, something is wrong.
            // Just pass them through without marking.
            curMon = curOriginal;
            continue;
        }

        // Find the next mon.
        while (!foundNextMon)
        {
            u16 wordIndex, adjustedCurMon;
            u32 bitVectorWord;
            u8 bitIndex;

            // Generate a Pokémon. If it has already been generated, keep generating new ones
            // until one that hasn't been seen is picked.

            curMon = RandomizeMonFromSeed(&state, mode, curOriginal);

            // Compute the bit address of this mon.
            adjustedCurMon = curMon - 1;
            wordIndex = adjustedCurMon / 32;
            bitIndex = adjustedCurMon & 31;
            bitVectorWord = seenMonBitVector[wordIndex];

            // If set, this mon has been seen already.
            if (bitVectorWord & (1 << bitIndex))
                continue;

            bitVectorWord |= 1 << bitIndex;
            seenMonBitVector[wordIndex] = bitVectorWord;
            foundNextMon = TRUE;
        }
        resultSpecies[i] = curMon;
    }
}

u16 RandomizeMonBaseForm(enum RandomizerReason reason, enum RandomizerSpeciesMode mode, u32 seed, u16 species)
{
    struct Sfc32State state;
    state = RandomizerRandSeed(reason, seed, species);
    return RandomizeMonFromSeed(&state, mode, species);
}

static u16 ChooseRandomForm(struct Sfc32State *state, const u16 baseSpecies)
{
    const u16 *formsTable = gSpeciesInfo[baseSpecies].formSpeciesIdTable;
    if (formsTable)
    {
        u32 formCount = 0;
        while (formsTable[formCount] != FORM_SPECIES_END)
        {
            formCount++;
        }
        return formsTable[RandomizerNextRange(state, formCount)];
    }

    return baseSpecies;
}

static u16 GetFormFromRareFormInfo(struct Sfc32State *state, const struct RandomizerRareFormInfo *info)
{
    if (RandomizerNextRange(state, info->inverseRareFormChance) > 0)
        return info->commonForm;
    else
        return info->rareForm;
}

#define RANDOM_FROM_ARRAY(arr)  (arr[RandomizerNextRange(state, ARRAY_COUNT(arr))])
#define RARE_FORM(infoStruct)   (GetFormFromRareFormInfo(state, &infoStruct))
static u16 ChooseFormSpecial(struct Sfc32State *state, const u16 baseSpecies)
{
    switch (baseSpecies) {
        // These species do almost ordinary ordinary random form selection processes.
        // However, their form tables include forms that shouldn't normally be
        // selected, so they need to have special hard-coded form tables.
        case SPECIES_FLOETTE:
            return RANDOM_FROM_ARRAY(sFloetteFormChoices);
        case SPECIES_TAUROS_PALDEA_COMBAT:
            return RANDOM_FROM_ARRAY(sPaldeanTaurosFormChoices);
        case SPECIES_MINIOR:
            return RANDOM_FROM_ARRAY(sMiniorFormChoices);
        // These are species, first appearing in Gen 8, that have one common
        // form and one rare form.
        // Note that as Maushold can only appear in raid battles in Gen 9, it
        // normally does not behave this way in the wild, but for a randomizer
        // this seems like a reasonable choice.
        case SPECIES_MAUSHOLD:
            return RARE_FORM(sMausholdRareFormInfo);
        case SPECIES_SINISTEA:
            return RARE_FORM(sSinisteaRareFormInfo);
        case SPECIES_SINISTCHA:
            return RARE_FORM(sSinistchaRareFormInfo);
        case SPECIES_POLTEAGEIST:
            return RARE_FORM(sPolteageistRareFormInfo);
        case SPECIES_DUDUNSPARCE:
            return RARE_FORM(sDudunsparceRareFormInfo);
        default:
            return baseSpecies;
    }

}
#undef RANDOM_FROM_ARRAY
#undef RARE_FORM

u16 RandomizeMon(enum RandomizerReason reason, enum RandomizerSpeciesMode mode, u32 seed, u16 species)
{
    u32 speciesMode;
    u16 resultSpecies;
    struct Sfc32State state;

    if (!IsSpeciesPermitted(species))
        return species;

    state = RandomizerRandSeed(reason, seed, species);

    resultSpecies = RandomizeMonFromSeed(&state, mode, species);
    speciesMode = gSpeciesInfo[resultSpecies].randomizerMode;

    switch (speciesMode)
    {
        case MON_RANDOMIZER_RANDOM_FORM:
            return ChooseRandomForm(&state, resultSpecies);
        case MON_RANDOMIZER_SPECIAL_FORM:
            return ChooseFormSpecial(&state, resultSpecies);
        case MON_RANDOMIZER_NORMAL:
        default:
            return resultSpecies;
    }
}

u16 RandomizeWildEncounter(u16 species, u8 mapNum, u8 mapGroup, enum WildArea area, u8 slot)
{
    if (RandomizerFeatureEnabled(RANDOMIZE_WILD_MON))
    {
        // Randomization is done based on the map number, the WildArea, and the encounter slot.
        // This means a distinct species can appear in each encounter slot.
        u32 seed;
        seed = ((u32)mapGroup) << 24;
        seed |= ((u32)mapNum) << 16;
        seed |= ((u32)area) << 8;
        seed |= slot;

        return RandomizeMon(RANDOMIZER_REASON_WILD_ENCOUNTER, GetRandomizerOption(RANDOMIZER_OPTION_SPECIES_MODE), seed, species);
    }

    return species;
}


// This is used in the Pokédex area map code.
bool32 IsRandomizationPossible(u16 originalSpecies, u16 targetSpecies)
{
    const enum RandomizerSpeciesMode mode = GetRandomizerOption(RANDOMIZER_OPTION_SPECIES_MODE);
    if (!IsSpeciesPermitted(targetSpecies) || !IsSpeciesPermitted(originalSpecies))
    {
        // For a species that is not permitted, randomization is disabled.
        // Therefore, if the species are the same, they will "randomize".
        return originalSpecies == targetSpecies;
    }

    if (mode != MON_RANDOM && mode < MAX_MON_MODE)
    {
        u16 minGroupOriginal, maxGroupOriginal, minGroupTarget, maxGroupTarget,
            originalGroup, targetGroup;
        const struct SpeciesTable* table;
        table = GetSpeciesTable(mode);
        originalGroup = GetSpeciesGroup(table, originalSpecies);
        targetGroup = GetSpeciesGroup(table, targetSpecies);
        GetGroupRange(originalGroup, mode, &minGroupOriginal, &maxGroupOriginal);
        GetGroupRange(targetGroup, mode, &minGroupTarget, &maxGroupTarget);

        // If the group ranges intersect, randomization is possible.
        return maxGroupOriginal >= minGroupTarget && minGroupOriginal <= maxGroupTarget;
    }

    return TRUE;
}

u16 RandomizeTrainerMon(u16 trainerId, u8 slot, u8 totalMons, u16 species)
{
    if (RandomizerFeatureEnabled(RANDOMIZE_TRAINER_MON))
    {
        // The seed is based on the internal trainer number, the number of
        // Pokémon in that trainer's party, and which party position it is in.
        u32 seed;
        seed = (u32)trainerId << 16;
        seed |= (u32)totalMons << 8;
        seed |= slot;

        return RandomizeMon(RANDOMIZER_REASON_TRAINER_PARTY, GetRandomizerOption(RANDOMIZER_OPTION_SPECIES_MODE), seed, species);
    }

    return species;
}

u16 RandomizeFixedEncounterMon(u16 species, u8 mapNum, u8 mapGroup, u8 localId)
{
    if (RandomizerFeatureEnabled(RANDOMIZE_FIXED_MON))
    {
        // The seed is based on the location of the object event.
        u32 seed;
        seed = (u32)mapNum << 16;
        seed |= (u32)mapGroup << 8;
        seed |= localId;

        return RandomizeMon(RANDOMIZER_REASON_FIXED_ENCOUNTER, GetRandomizerOption(RANDOMIZER_OPTION_SPECIES_MODE), seed, species);
    }

    return species;
}

EWRAM_DATA static u32 sLastMonRandomizerSeed = 0;
EWRAM_DATA static u16 sRandomizedMons[STARTER_AND_GIFT_MON_COUNT] = {0};

u16 RandomizeStarterAndGiftMon(u16 originalSlot, const u16* originalStarterAndGiftMons)
{
    if (RandomizerFeatureEnabled(RANDOMIZE_STARTER_AND_GIFT_MON))
    {
        if (sLastMonRandomizerSeed != GetRandomizerSeed() || sRandomizedMons[0] == SPECIES_NONE)
        {
            // The randomized starter table is stale or uninitialized. Fix that!

            // Hash the starter list so that which starters there are influences the seed.
            u32 starterHash = 5381;
            u32 i;
            for (i = 0; i < STARTER_AND_GIFT_MON_COUNT; i++)
            {
                u16 originalStarter = originalStarterAndGiftMons[i];
                starterHash = ((starterHash << 5) + starterHash) ^ (u8)originalStarter;
                starterHash = ((starterHash << 5) + starterHash) ^ (u8)(originalStarter >> 8);
            }

            GetUniqueMonList(RANDOMIZER_REASON_STARTER_AND_GIFT_MON, GetRandomizerOption(RANDOMIZER_OPTION_SPECIES_MODE),
                starterHash, 0, STARTER_AND_GIFT_MON_COUNT, originalStarterAndGiftMons, sRandomizedMons);
        }
        return sRandomizedMons[originalSlot];
    }

    return originalStarterAndGiftMons[originalSlot];
}

EWRAM_DATA static u32 sLastEggMonRandomizerSeed = 0;
EWRAM_DATA static u16 sRandomizedEggMons[EGG_MON_COUNT] = {0};

u16 RandomizeEggMon(u16 originalSlot, const u16* originalEggMons)
{
    if (RandomizerFeatureEnabled(RANDOMIZE_EGG_MON))
    {
        if (sLastEggMonRandomizerSeed != GetRandomizerSeed() || sRandomizedEggMons[0] == SPECIES_NONE)
        {
            // The randomized egg table is stale or uninitialized. Fix that!

            // Hash the egg list so that which eggs there are influences the seed.
            u32 eggHash = 5381;
            u32 i;
            for (i = 0; i < EGG_MON_COUNT; i++)
            {
                u16 originalEgg = originalEggMons[i];
                eggHash = ((eggHash << 5) + eggHash) ^ (u8)originalEgg;
                eggHash = ((eggHash << 5) + eggHash) ^ (u8)(originalEgg >> 8);
            }

            GetUniqueMonList(RANDOMIZER_REASON_EGG, GetRandomizerOption(RANDOMIZER_OPTION_SPECIES_MODE),
                eggHash, 0, EGG_MON_COUNT, originalEggMons, sRandomizedEggMons);
        }
        return sRandomizedEggMons[originalSlot];
    }

    return originalEggMons[originalSlot];
}

static inline bool32 IsAbilityIllegal(u16 ability)
{
    if (ability == ABILITY_NONE || ability == ABILITY_WONDER_GUARD)
        return TRUE;
    return FALSE;
}

#define RANDOMIZER_LEARNSET_COUNT 21
#define RANDOMIZER_LEARNSET_CACHE_SIZE 4

enum RandomLearnsetMoveKind
{
    RANDOM_MOVE_STAB_DAMAGE,
    RANDOM_MOVE_STATUS,
    RANDOM_MOVE_NONSTAB_DAMAGE,
};

struct RandomLearnsetCache
{
    u16 species;
    u32 seed;
    struct LevelUpMove moves[RANDOMIZER_LEARNSET_COUNT + 1];
};

EWRAM_DATA static struct RandomLearnsetCache
    sRandomLearnsetCache[RANDOMIZER_LEARNSET_CACHE_SIZE] = {0};

EWRAM_DATA static u8 sRandomLearnsetCacheNext = 0;

static const u8 sRandomLearnsetLevels[RANDOMIZER_LEARNSET_COUNT] =
{
     1,  4,  7,
    10, 13, 16,
    19, 22, 25,
    28, 31, 34,
    37, 40, 43,
    46, 49, 52,
    55, 58, 61,
};

static bool32 IsRandomizerMoveUsable(u16 move)
{
    if (move == MOVE_NONE
     || move == MOVE_STRUGGLE
     || move == MOVE_SKETCH)
        return FALSE;

    // Don't directly give Z-Moves or Max/G-Max moves as learnset moves.
    if (move >= FIRST_Z_MOVE)
        return FALSE;

    // Skip placeholder / unfinished moves.
    if (GetMoveEffect(move) == EFFECT_PLACEHOLDER)
        return FALSE;

    return TRUE;
}

static bool32 MoveMatchesRandomLearnsetKind(
    u16 species,
    u16 move,
    enum RandomLearnsetMoveKind kind)
{
    const u8 type1 = gSpeciesInfo[species].types[0];
    const u8 type2 = gSpeciesInfo[species].types[1];
    const u8 moveType = GetMoveType(move);
    const u8 category = GetMoveCategory(move);

    const bool32 isStab = (moveType == type1 || moveType == type2);
    const bool32 isStatus = (category == DAMAGE_CATEGORY_STATUS);
    const bool32 isDamaging = !isStatus && GetMovePower(move) > 0;

    switch (kind)
    {
    case RANDOM_MOVE_STAB_DAMAGE:
        return isDamaging && isStab;

    case RANDOM_MOVE_STATUS:
        return isStatus;

    case RANDOM_MOVE_NONSTAB_DAMAGE:
        return isDamaging && !isStab;
    }

    return FALSE;
}

static bool32 MoveAlreadyChosen(
    const struct LevelUpMove *learnset,
    u32 count,
    u16 move)
{
    u32 i;

    for (i = 0; i < count; i++)
    {
        if (learnset[i].move == move)
            return TRUE;
    }

    return FALSE;
}

static u16 PickRandomLearnsetMove(
    struct Sfc32State *state,
    u16 species,
    enum RandomLearnsetMoveKind kind,
    const struct LevelUpMove *learnset,
    u32 chosenCount)
{
    u32 attempts;

    // Random probing is cheap here and avoids needing huge move-pool arrays.
    for (attempts = 0; attempts < 4096; attempts++)
    {
        const u16 move =
            (u16)(RandomizerNextRange(state, FIRST_Z_MOVE - MOVE_POUND)
                + MOVE_POUND);

        if (!IsRandomizerMoveUsable(move))
            continue;

        if (!MoveMatchesRandomLearnsetKind(species, move, kind))
            continue;

        if (MoveAlreadyChosen(learnset, chosenCount, move))
            continue;

        return move;
    }

    // Fallback scan, in case random probing somehow fails.
    {
        u16 move;

        for (move = MOVE_POUND; move < FIRST_Z_MOVE; move++)
        {
            if (!IsRandomizerMoveUsable(move))
                continue;

            if (!MoveMatchesRandomLearnsetKind(species, move, kind))
                continue;

            if (MoveAlreadyChosen(learnset, chosenCount, move))
                continue;

            return move;
        }
    }

    // Extremely defensive fallback.
    return MOVE_TACKLE;
}

static void BuildRandomSpeciesLearnset(
    struct RandomLearnsetCache *cache,
    u16 species)
{
    struct Sfc32State state;
    u32 i;

    cache->species = species;
    cache->seed = GetRandomizerSeed();

    state = RandomizerRandSeed(
        RANDOMIZER_REASON_LEARNSET,
        species,
        0x4C454152); // "LEAR", just extra seed separation

    for (i = 0; i < RANDOMIZER_LEARNSET_COUNT; i++)
    {
        enum RandomLearnsetMoveKind kind;

        // Interleave:
        // STAB, Status, Non-STAB, STAB, Status, Non-STAB...
        switch (i % 3)
        {
        case 0:
            kind = RANDOM_MOVE_STAB_DAMAGE;
            break;
        case 1:
            kind = RANDOM_MOVE_STATUS;
            break;
        default:
            kind = RANDOM_MOVE_NONSTAB_DAMAGE;
            break;
        }

        cache->moves[i].move =
            PickRandomLearnsetMove(
                &state,
                species,
                kind,
                cache->moves,
                i);

        cache->moves[i].level = sRandomLearnsetLevels[i];
    }

    cache->moves[RANDOMIZER_LEARNSET_COUNT].move = LEVEL_UP_MOVE_END;
    cache->moves[RANDOMIZER_LEARNSET_COUNT].level = 0;
}

const struct LevelUpMove *RandomizeSpeciesLearnset(u16 species)
{
    u32 i;
    struct RandomLearnsetCache *cache;

    species = SanitizeSpeciesId(species);

    if (!RandomizerFeatureEnabled(RANDOMIZE_LEARNSET)
     || species == SPECIES_NONE)
    {
        const struct LevelUpMove *learnset =
            gSpeciesInfo[species].levelUpLearnset;

        if (learnset == NULL)
            return gSpeciesInfo[SPECIES_NONE].levelUpLearnset;

        return learnset;
    }

    // Look for a valid cached version first.
    for (i = 0; i < RANDOMIZER_LEARNSET_CACHE_SIZE; i++)
    {
        if (sRandomLearnsetCache[i].species == species
         && sRandomLearnsetCache[i].seed == GetRandomizerSeed())
        {
            return sRandomLearnsetCache[i].moves;
        }
    }

    cache = &sRandomLearnsetCache[sRandomLearnsetCacheNext];

    sRandomLearnsetCacheNext++;
    if (sRandomLearnsetCacheNext >= RANDOMIZER_LEARNSET_CACHE_SIZE)
        sRandomLearnsetCacheNext = 0;

    BuildRandomSpeciesLearnset(cache, species);

    return cache->moves;
}

static u16 GetRandomizerEvolutionRoot(u16 species)
{
    u16 previous;

    while ((previous = GetSpeciesPreEvolution(species)) != SPECIES_NONE
        && previous != species)
    {
        species = previous;
    }

    return species;
}

// Given a species and an abilityNum, returns a replacement for that ability.
u16 RandomizeAbility(u16 species, u8 abilityNum, u16 originalAbility)
{
    if (species == SPECIES_SHEDINJA)
        return originalAbility;

    if (RandomizerFeatureEnabled(RANDOMIZE_ABILITIES) && originalAbility != ABILITY_NONE)
    {
        struct Sfc32State state;
        u16 result;
        u32 seed;

        u16 abilitySpecies = GetRandomizerEvolutionRoot(species);

        // Seed by evolutionary family + ability slot.
        // Evolutions therefore preserve their randomized ability.
        seed = ((u32)abilitySpecies) << 8;
        seed |= abilityNum;

        state = RandomizerRandSeed(
            RANDOMIZER_REASON_ABILITIES,
            seed,
            abilitySpecies);

        // Randomize abilities
        do
        {
            result = sRandomizerAbilityWhitelist[RandomizerNextRange(&state, ABILITY_WHITELIST_SIZE)];
        } while(IsAbilityIllegal(result));

        return result;
    }

    return originalAbility;
}

#endif // RANDOMIZER_AVAILABLE
