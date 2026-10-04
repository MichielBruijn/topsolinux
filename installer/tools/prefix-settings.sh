# Shared by the installer and the TopSolid AppImage (sourced; needs WINE and WINEPREFIX)
#
# Settings the installer puts in the prefix, by level. A prefix made by an older version gets the
# levels it misses on its next start, each once, so the user's own changes to earlier settings stay
# (re-importing tweaks.reg would reset their SpaceMouse speeds, for example).
# A new setting: add settings_N with the next N and raise SETTINGS_LEVEL. Never change an existing level.
# Settings that should follow the desktop on every start (scale, formats) belong in topsolinux-run.
SETTINGS_LEVEL=1

# 1.6.5: the installer's settings up to here (tweaks.reg, DLL overrides, crash dialog)
settings_1() { :; }

# e.g.
# settings_2() { "$WINE" reg add 'HKCU\Software\Wine\X11 Driver' /v UseXIM /d N /f >/dev/null 2>&1; }

# the level of the prefix, 0 for one made before levels existed
settings_level() { local l; l="$(cat "$WINEPREFIX/.topsolinux-settings" 2>/dev/null)"; echo "${l:-0}"; }

# bring the prefix up to SETTINGS_LEVEL; one made by a newer version is left as it is
update_settings()
{
    local level
    level="$(settings_level)"
    while [ "$level" -lt "$SETTINGS_LEVEL" ]; do
        level=$((level + 1))
        "settings_$level" || return 1
        echo "$level" > "$WINEPREFIX/.topsolinux-settings"
    done
}

# a new installation has all settings
settings_done() { echo "$SETTINGS_LEVEL" > "$WINEPREFIX/.topsolinux-settings"; }
