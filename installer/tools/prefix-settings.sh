# Shared by the installer and the TopSolid AppImage (sourced; needs WINE and WINEPREFIX)
#
# Settings the installer puts in the prefix, by level. A prefix made by an older version gets the
# levels it misses on its next start, each once, so the user's own changes to earlier settings stay
# (re-importing tweaks.reg would reset their SpaceMouse speeds, for example).
# A new setting: add settings_N with the next N and raise SETTINGS_LEVEL. Never change an existing level.
# Settings that should follow the desktop on every start (scale, formats) belong in topsolinux-run.
SETTINGS_LEVEL=5

# 1.6.5: the installer's settings up to here (tweaks.reg, DLL overrides, crash dialog)
settings_1() { :; }

# 1.6.25: the window manager gives the keyboard focus itself; with WM_TAKE_FOCUS, mutter's request was
# sometimes ignored and keys went to another program
settings_2() { "$WINE" reg add 'HKCU\Software\Wine\X11 Driver' /v UseTakeFocus /d N /f >/dev/null 2>&1; }

# 1.6.34: undo 1.6.33's ServicesPipeTimeout of 60 seconds (never released): SQL Server's first start then
# hung for the whole minute instead of 10 seconds before the starter started it again
settings_3()
{
    "$WINE" reg delete 'HKLM\System\CurrentControlSet\Control' /v ServicesPipeTimeout /f >/dev/null 2>&1
    return 0
}

# 1.6.34: SQL Server starts SamSs while it starts itself. Wine names the control pipe of a service process
# after a counter that SamSs's process then moves on, so SQL Server opened SamSs's pipe and its start
# failed after 10 seconds (the starter's retry started it). Started as a dependency, SamSs runs already
settings_4()
{
    "$WINE" reg add 'HKLM\System\CurrentControlSet\Services\MSSQL$SQLTOPSOLID' /v DependOnService /t REG_MULTI_SZ \
        /d SamSs /f >/dev/null 2>&1
}

# TopSolid's first start turns hardware rendering off on any GPU but NVIDIA or AMD Pro (Intel, Radeon) and
# draws with its own Mesa on the CPU (bin/mesadrv) instead. Realistic rendering and environments need the GPU,
# so they were greyed out or left trails. Wine's OpenGL works on Intel and Radeon: the check is done, hardware on.
hardware_rendering()
{
    local d conf
    for d in "$WINEPREFIX/drive_c/Program Files/TOPSOLID/TopSolid 7."*; do
        [ -d "$d" ] || continue
        conf="$WINEPREFIX/drive_c/ProgramData/TOPSOLID/TopSolid/${d##*TopSolid }/TopSolid/Kernel/SX"
        mkdir -p "$conf" &&
            python3 "$TOOLS/userconfig.py" "$conf/Config.ConfigData.xml" TopSolid/Kernel/WG/Application \
                GraphicCardCompatibilityCheckDone Bool True &&
            python3 "$TOOLS/userconfig.py" "$conf/Config.ConfigData.xml" TopSolid/Kernel/GR/GL/State \
                SoftwareRendering Bool False || return 1
    done
}

# 1.6.40: hardware rendering, also when TopSolid turned it off (see hardware_rendering)
settings_5() { hardware_rendering; }

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
