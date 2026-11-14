# Shared by the installer and the TopSolid AppImage (sourced; needs TSL_VERSION and LOG)
GEARLEVER="${GEARLEVER:-it.mijorus.gearlever}"

# the name of a TopSolid AppImage shows the TopSo'Linux version that made it
versioned_name()  # PATH
{
    local dir="${1%/*}" base="${1##*/}"
    base="$(printf %s "$base" | sed -E 's/[-_]topsolinux[-_]([0-9]+(\.[0-9]+)*|dev)//I')"
    case "$base" in
        *-x86_64.*) base="${base/-x86_64./-TopSoLinux-$TSL_VERSION-x86_64.}" ;;
        *.*) base="${base%.*}_topsolinux-$TSL_VERSION.${base##*.}" ;;
        *) base="${base}_topsolinux-$TSL_VERSION" ;;
    esac
    echo "$dir/$base"
}

# the app menu entries that start OLD start NEW
retarget_desktop_files()  # OLD NEW
{
    local f o n
    o="$(printf %s "$1" | sed 's/[][\/.*^$&]/\\&/g')"
    n="$(printf %s "$2" | sed 's/[\/&]/\\&/g')"
    grep -lsF --null "$1" "$HOME/.local/share/applications/"*.desktop |
        while IFS= read -r -d '' f; do sed -i "s/$o/$n/g" "$f"; done
    gearlever_conf "$1" "$2"
}

# Gear Lever keeps its settings per app under the md5 of the path: OLD's go to NEW. A section or option that
# is there twice stops Gear Lever from starting at all (configparser), so those are merged, the last one wins.
gearlever_conf()  # [OLD NEW]
{
    local f="$HOME/.var/app/$GEARLEVER/config/gearlever.conf"
    [ -f "$f" ] || return 0
    python3 -I - "$f" "${1:-}" "${2:-}" 2>>"${LOG:-/dev/null}" <<'EOF'
import hashlib, os, re, sys
path, old, new = sys.argv[1:4]
key = lambda p: 'app.' + hashlib.md5(p.encode()).hexdigest()
text = open(path, encoding='utf-8').read()
sections, order = {}, []   # name -> {option: line}
name = None
for line in text.splitlines():
    m = re.match(r'\[(.*)\]\s*$', line)
    if m:
        name = m.group(1)
        if name not in sections:
            sections[name] = {}
            order.append(name)
        continue
    o = re.match(r'\s*([^=:\s][^=:]*?)\s*[=:]', line)
    if o and name is not None:
        sections[name][o.group(1).lower()] = line
    elif line.strip() and name is not None:
        sections[name]['#%d' % len(sections[name])] = line
if old and new and old != new:
    for suffix in ('', '.update_manager'):
        o, n = key(old) + suffix, key(new) + suffix
        if o in sections:
            if n in sections:
                del sections[n]
                order.remove(n)
            sections[n] = sections.pop(o)
            order[order.index(o)] = n
    n = key(new)
    if n in sections and 'file_path' in sections[n]:
        sections[n]['file_path'] = 'file_path = ' + new
out = ''.join('\n'.join(['[%s]' % s] + list(sections[s].values())) + '\n\n' for s in order)
if out != text:
    open(path + '.tmp', 'w', encoding='utf-8').write(out)
    os.replace(path + '.tmp', path)
EOF
}

# DESKTOPFILE gets action ID (NAME), which runs COMMAND ARG, unless it has it; ADDED_ACTIONS lists the new ones
ADDED_ACTIONS=""
add_action()  # DESKTOPFILE COMMAND ID NAME ARG
{
    local icon
    grep -qs "^\[Desktop Action $3\]" "$1" && return 0
    grep -qs '^Actions=' "$1" || return 0
    icon="$(sed -n '/^\[Desktop Action /q; s/^Icon=//p' "$1" | head -1)"
    sed -i "s/^Actions=\(.*[^;]\);*\$/Actions=\1;$3;/" "$1"
    {
        printf '\n[Desktop Action %s]\nName=%s\n' "$3" "$4"
        [ -n "$icon" ] && printf 'Icon=%s\n' "$icon"
        printf 'Exec=%s %s\n' "$2" "$5"
    } >> "$1"
    case "$ADDED_ACTIONS" in *"$4"*) ;; *) ADDED_ACTIONS="${ADDED_ACTIONS:+$ADDED_ACTIONS, }$4" ;; esac
}

# the app menu starts TopSolid on the integrated GPU and offers the discrete one, GNOME's default
# (1.6.28 to 1.6.35 had it the other way round)
default_gpu()  # DESKTOPFILE
{
    sed -i '/^PrefersNonDefaultGPU=true$/d; /^X-KDE-RunOnDiscreteGpu=true$/d' "$1"
}

# "Wine settings" (winecfg) became "Settings" (1.6.54), which opens winecfg too
settings_action()  # DESKTOPFILE
{
    local name="Settings (scaling, fonts, graphics, Wine)"
    grep -qs '^\[Desktop Action winecfg\]$' "$1" || return 0
    sed -i "/^Actions=/s/\([=;]\)winecfg;/\1settings;/
        /^\[Desktop Action winecfg\]\$/,/^\[/{ s/^\[Desktop Action winecfg\]\$/[Desktop Action settings]/
            s/^Name=.*/Name=$name/; s/^\(Exec=.*\) winecfg\$/\1 settings/; }" "$1"
    case "$ADDED_ACTIONS" in *"$name"*) ;; *) ADDED_ACTIONS="${ADDED_ACTIONS:+$ADDED_ACTIONS, }$name" ;; esac
}

# the right-click actions of TopSolid's app menu entry, in menu order: ID|NAME|ARGUMENTS. The installer's entry
# is made from this, and older entries are brought up to it at every start (sync_actions)
DESKTOP_ACTIONS="update|TopSolid'Update|update
license|TopSolid license|license-tool
spacemouse|SpaceMouse settings|spacemouse
settings|Settings (scaling, fonts, graphics, Wine)|settings
stop|Stop background services|stop
topsolinux|Check for TopSo'Linux updates|topsolinux-update
report|Report a problem|report
mcp|MCP server for AI assistants|mcp-install"

# the Actions line and sections of a new entry whose actions run COMMAND
desktop_actions()  # COMMAND
{
    local id name args
    printf 'Actions=%s;\n' "$(cut -d'|' -f1 <<< "$DESKTOP_ACTIONS" | paste -sd';')"
    while IFS='|' read -r id name args; do
        printf '\n[Desktop Action %s]\nName=%s\nExec=%s %s\n' "$id" "$name" "$1" "$args"
    done <<< "$DESKTOP_ACTIONS"
}

# DESKTOPFILE gets the actions it misses, with this version's names and order; actions that aren't TopSo'Linux's
# stay, behind them. Before 1.6.54 an update only added the actions listed by hand, so entries made by the
# first versions never got "Wine settings"
sync_actions()  # DESKTOPFILE COMMAND
{
    local id name args ids="" rest
    grep -qs '^Actions=' "$1" || return 0
    settings_action "$1"
    while IFS='|' read -r id name args; do
        add_action "$1" "$2" "$id" "$name" "$args"
        sed -i "/^\[Desktop Action $id\]\$/,/^\[/s/^Name=.*/Name=$name/" "$1"
        ids="$ids$id;"
    done <<< "$DESKTOP_ACTIONS"
    rest="$(sed -n 's/^Actions=//p' "$1" | tr ';' '\n' | grep -vxF -e '' $(cut -d'|' -f1 <<< "$DESKTOP_ACTIONS" | sed 's/^/-e /') | tr '\n' ';')"
    [ "$(sed -n 's/^Actions=//p' "$1")" = "$ids$rest" ] || sed -i "s/^Actions=.*/Actions=$ids$rest/" "$1"
}

# the app menu entry, as this version makes it
add_update_action()  # DESKTOPFILE COMMAND
{
    default_gpu "$1"
    sync_actions "$1" "$2"
}

# the app menu entries that start APPIMAGE
add_update_actions()  # APPIMAGE
{
    local f
    while IFS= read -r -d '' f; do add_update_action "$f" "$1"; done \
        < <(grep -lsF --null "$1" "$HOME/.local/share/applications/"*.desktop)
}

# the command that installs a distribution package, run as root
package_install_command()
{
    if command -v apt-get >/dev/null; then echo "apt-get install -y $*"
    elif command -v dnf >/dev/null; then echo "dnf install -y $*"
    elif command -v zypper >/dev/null; then echo "zypper --non-interactive install $*"
    elif command -v pacman >/dev/null; then echo "pacman -S --noconfirm $*"
    fi
}

gearlever_installed() { command -v flatpak >/dev/null && flatpak info "$GEARLEVER" >/dev/null 2>&1; }

# Gear Lever from Flathub, and Flatpak itself when missing (that asks for the password)
install_gearlever()
{
    local cmd
    gearlever_installed && return 0
    if ! command -v flatpak >/dev/null; then
        cmd="$(package_install_command flatpak)"
        [ -n "$cmd" ] && command -v pkexec >/dev/null && pkexec sh -c "$cmd" >> "$LOG" 2>&1
    fi
    command -v flatpak >/dev/null || return 1
    flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo >> "$LOG" 2>&1
    flatpak install --user -y --noninteractive flathub "$GEARLEVER" >> "$LOG" 2>&1
    gearlever_installed
}

# Gear Lever moves FILE to its folder and adds it to the app menu. Prints where FILE is then, with the
# TopSo'Linux version back in its name: Gear Lever names it after the app (topsolid_7.20.appimage)
integrate_appimage()  # FILE
{
    local out new
    gearlever_conf
    out="$(flatpak run "$GEARLEVER" --integrate "$1" -y 2>&1)"
    echo "$out" >> "$LOG"
    out="$(echo "$out" | sed -n 's/^\(\/.*\) was integrated successfully.*/\1/p' | tail -1)"
    [ -f "$out" ] || return 1
    new="$(versioned_name "$out")"
    if [ "$new" != "$out" ] && mv -f "$out" "$new"; then
        retarget_desktop_files "$out" "$new"
        out="$new"
    fi
    echo "$out"
}
