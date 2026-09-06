EventScript_UseSurf::
	lockall
	msgbox gText_WantToUseSurf, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_ReleaseUseSurf

	@ No Surf Pokemon required.
	setfieldeffectargument 0, 0
	dofieldeffect FLDEFF_USE_SURF
EventScript_ReleaseUseSurf::
	releaseall
EventScript_EndUseSurf::
	end
