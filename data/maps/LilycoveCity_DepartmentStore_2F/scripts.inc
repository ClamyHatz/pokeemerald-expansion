LilycoveCity_DepartmentStore_2F_MapScripts::
	.byte 0

LilycoveCity_DepartmentStore_2F_EventScript_Cook::
	msgbox LilycoveCity_DepartmentStore_2F_Text_LearnToUseItemsProperly, MSGBOX_NPC
	end

LilycoveCity_DepartmentStore_2F_EventScript_PokefanF::
	msgbox LilycoveCity_DepartmentStore_2F_Text_GoodGiftForHusband, MSGBOX_NPC
	end

LilycoveCity_DepartmentStore_2F_EventScript_Sailor::
	msgbox LilycoveCity_DepartmentStore_2F_Text_StockUpOnItems, MSGBOX_NPC
	end

LilycoveCity_DepartmentStore_2F_EventScript_ClerkLeft::
	lock
	faceplayer
	message gText_HowMayIServeYou
	waitmessage
	pokemart LilycoveCity_DepartmentStore_2F_Pokemart1
	msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
	release
	end

	.align 2

	LilycoveCity_DepartmentStore_2F_Pokemart2:
	.2byte ITEM_FIRE_STONE
.2byte ITEM_WATER_STONE
.2byte ITEM_THUNDER_STONE
.2byte ITEM_LEAF_STONE
.2byte ITEM_ICE_STONE
.2byte ITEM_SUN_STONE
.2byte ITEM_MOON_STONE
.2byte ITEM_SHINY_STONE
.2byte ITEM_DUSK_STONE
.2byte ITEM_DAWN_STONE

.2byte ITEM_SWEET_APPLE
.2byte ITEM_TART_APPLE
.2byte ITEM_CRACKED_POT
.2byte ITEM_CHIPPED_POT
.2byte ITEM_GALARICA_CUFF
.2byte ITEM_GALARICA_WREATH

.2byte ITEM_DRAGON_SCALE
.2byte ITEM_UPGRADE
.2byte ITEM_PROTECTOR
.2byte ITEM_ELECTIRIZER
.2byte ITEM_MAGMARIZER
.2byte ITEM_DUBIOUS_DISC
.2byte ITEM_REAPER_CLOTH
.2byte ITEM_PRISM_SCALE
.2byte ITEM_WHIPPED_DREAM
.2byte ITEM_SACHET
.2byte ITEM_OVAL_STONE

.2byte ITEM_STRAWBERRY_SWEET
.2byte ITEM_LOVE_SWEET
.2byte ITEM_BERRY_SWEET
.2byte ITEM_CLOVER_SWEET
.2byte ITEM_FLOWER_SWEET
.2byte ITEM_STAR_SWEET
.2byte ITEM_RIBBON_SWEET

.2byte ITEM_LINKING_CORD

pokemartlistend

LilycoveCity_DepartmentStore_2F_EventScript_ClerkRight::
	lock
	faceplayer
	message gText_HowMayIServeYou
	waitmessage
	pokemart LilycoveCity_DepartmentStore_2F_Pokemart2
	msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
	release
	end

	.align 2
LilycoveCity_DepartmentStore_2F_Pokemart1:
	.2byte ITEM_POKE_BALL
	.2byte ITEM_GREAT_BALL
	.2byte ITEM_ULTRA_BALL
	.2byte ITEM_HEAL_BALL
	.2byte ITEM_NET_BALL
	.2byte ITEM_NEST_BALL
	.2byte ITEM_DIVE_BALL
	.2byte ITEM_DUSK_BALL
	.2byte ITEM_TIMER_BALL
	.2byte ITEM_QUICK_BALL
	.2byte ITEM_REPEAT_BALL
	.2byte ITEM_LUXURY_BALL
	.2byte ITEM_LEVEL_BALL
	.2byte ITEM_LURE_BALL
	.2byte ITEM_MOON_BALL
	.2byte ITEM_FRIEND_BALL
	.2byte ITEM_LOVE_BALL
	.2byte ITEM_FAST_BALL
	.2byte ITEM_HEAVY_BALL
	.2byte ITEM_CHERISH_BALL
	pokemartlistend

LilycoveCity_DepartmentStore_2F_Text_LearnToUseItemsProperly:
	.string "Learn to use items properly.\n"
	.string "That's basic, really.$"

LilycoveCity_DepartmentStore_2F_Text_GoodGiftForHusband:
	.string "My husband is waiting at home.\n"
	.string "What would make a good gift for him?$"

LilycoveCity_DepartmentStore_2F_Text_StockUpOnItems:
	.string "I'm leaving on a long journey soon.\n"
	.string "I need to stock up on items.$"

