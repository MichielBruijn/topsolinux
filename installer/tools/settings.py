#!/usr/bin/env python3
"""TopSo'Linux settings: scale, font smoothing, numbers and units, graphics, update check, Wine's tools.

usage: settings.py   (needs TOPSOLINUX_HOME, WINEPREFIX and TOPSOLINUX_RUN; topsolinux-run sets them)

Each choice is a file in TOPSOLINUX_HOME, as the commands scale and update-check write them; no file is the
default. topsolinux-run puts them in Wine's registry when TopSolid starts, so this never touches the prefix
and works the same while TopSolid runs. Exits with 2 without GTK 3; topsolinux-run then opens winecfg.
"""
import os
import re
import socket
import subprocess
import sys

os.environ.setdefault('GDK_BACKEND', 'x11')

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import GLib, Gtk
except (ImportError, ValueError):
    sys.exit(2)

DATA = os.environ.get('TOPSOLINUX_HOME') or os.path.expanduser('~/.local/share/topsolinux')
PREFIX = os.environ.get('WINEPREFIX', os.path.join(DATA, 'prefix'))
RUN = os.environ.get('TOPSOLINUX_RUN', '')
TOOLS = os.path.dirname(os.path.abspath(__file__))

FONTS = [('greyscale', 'Greyscale (Wine\'s default)'), ('subpixel', 'Subpixel (ClearType, sharper on most screens)'),
         ('off', 'Off')]


def path(name):
    return os.path.join(DATA, name)


def read(name):
    try:
        with open(path(name)) as f:
            return f.read().strip()
    except OSError:
        return ''


def write(name, value):
    """VALUE in the file NAME; None removes it (the default)."""
    if value is None:
        try:
            os.remove(path(name))
        except FileNotFoundError:
            pass
    else:
        os.makedirs(DATA, exist_ok=True)
        with open(path(name) + '.tmp', 'w') as f:
            f.write(value + '\n')
        os.replace(path(name) + '.tmp', path(name))


def user_reg(section, name):
    """The raw value of NAME in user.reg's [SECTION], read only: "2" or dword:00000001."""
    head = '[' + section.replace('\\', '\\\\') + ']'
    inside = False
    try:
        with open(os.path.join(PREFIX, 'user.reg'), encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.startswith('['):
                    inside = line.startswith(head)
                elif inside and line.startswith('"%s"=' % name):
                    return line.strip().split('=', 1)[1]
    except OSError:
        pass
    return ''


def desktop_percent():
    try:
        dpi = int(subprocess.run([os.path.join(TOOLS, 'desktop-dpi')], capture_output=True, text=True,
                                 timeout=5).stdout.strip())
        return round(dpi * 100 / 96)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def locale_value(keyword):
    try:
        return subprocess.run(['locale', keyword], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ''


def wine_running():
    """Whether a wineserver has the prefix open, as in spacemouse.py."""
    try:
        st = os.stat(PREFIX)
    except OSError:
        return False
    s = socket.socket(socket.AF_UNIX)
    try:
        s.connect('/tmp/.wine-%d/server-%x-%x/socket' % (os.getuid(), st.st_dev, st.st_ino))
        return True
    except OSError:
        return False
    finally:
        s.close()


def primary_gpu_vendor():
    for card in sorted(os.listdir('/sys/class/drm')):
        if not re.fullmatch(r'card\d+', card):
            continue
        try:
            with open('/sys/class/drm/%s/device/boot_vga' % card) as f:
                if f.read().strip() == '1':
                    with open('/sys/class/drm/%s/device/vendor' % card) as v:
                        return v.read().strip()
        except OSError:
            pass
    return ''


class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title='TopSolid settings')
        self.set_border_width(18)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect('destroy', self.on_destroy)
        self.loading = True
        self.children = []

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(box)

        # --- scale
        box.pack_start(self.heading('Size of text and icons'), False, False, 0)
        desk = desktop_percent()
        self.follow = Gtk.RadioButton.new_with_label(
            None, 'Follow the desktop' + (' (now %d%%)' % desk if desk else ''))
        box.pack_start(self.follow, False, False, 0)
        row = Gtk.Box(spacing=8)
        self.fixed = Gtk.RadioButton.new_with_label_from_widget(self.follow, 'Fixed:')
        self.percent = Gtk.SpinButton.new_with_range(50, 400, 25)
        self.percent.set_numeric(True)
        row.pack_start(self.fixed, False, False, 0)
        row.pack_start(self.percent, False, False, 0)
        row.pack_start(Gtk.Label(label='%'), False, False, 0)
        box.pack_start(row, False, False, 0)
        scale = read('scale')
        self.percent.set_value(int(scale) if scale.isdigit() else (desk or 100))
        (self.fixed if scale.isdigit() else self.follow).set_active(True)
        self.percent.set_sensitive(self.fixed.get_active())
        if os.environ.get('TOPSOLID_SCALE'):
            box.pack_start(self.small('TOPSOLID_SCALE=%s is set and comes first.'
                                      % os.environ['TOPSOLID_SCALE']), False, False, 0)
        self.fixed.connect('toggled', self.on_scale)
        self.percent.connect('value-changed', self.on_scale)

        # --- text and numbers; one grid keeps the combo boxes aligned
        grid = Gtk.Grid(column_spacing=12, row_spacing=6)
        grid.attach(self.heading('Text'), 0, 0, 2, 1)
        self.fonts = self.combo(grid, 1, 'Font smoothing', FONTS, self.current_fonts())
        self.fonts.connect('changed', lambda c: self.save('font-smoothing', c.get_active_id()))

        # as apply_formats
        heading = self.heading('Numbers and units')
        heading.set_margin_top(6)
        grid.attach(heading, 0, 2, 2, 1)
        dec = locale_value('decimal_point')
        measure = 'US' if locale_value('measurement') == '2' else 'metric'
        self.decimal = self.combo(grid, 3, 'Decimal separator', [
            ('', 'Follow the desktop (%s)' % ('comma' if dec == ',' else 'point')),
            ('point', 'Point'), ('comma', 'Comma')], read('decimal'))
        self.measure = self.combo(grid, 4, 'Measurement system', [
            ('', 'Follow the desktop (%s)' % measure), ('metric', 'Metric (mm)'), ('us', 'US (inch)')], read('measure'))
        self.decimal.connect('changed', self.on_format, 'decimal')
        self.measure.connect('changed', self.on_format, 'measure')
        grid.set_margin_top(6)
        box.pack_start(grid, False, False, 0)

        # --- graphics, only what this computer can use (setup_gpu)
        nvidia = os.path.isdir('/proc/driver/nvidia')
        intel = primary_gpu_vendor() == '0x8086'
        if nvidia or intel:
            box.pack_start(self.heading('Graphics'), False, False, 6)
        if nvidia:
            self.gpu = Gtk.CheckButton(label='Always draw on the NVIDIA GPU')
            self.gpu.set_active(read('gpu') == 'nvidia')
            self.gpu.connect('toggled', lambda b: self.save('gpu', 'nvidia' if b.get_active() else None))
            box.pack_start(self.gpu, False, False, 0)
            if primary_gpu_vendor() not in ('', '0x10de'):
                box.pack_start(self.small('Otherwise the integrated GPU, unless you choose <i>Launch using '
                                          'Discrete Graphics Card</i> in the app menu.'), False, False, 0)
        if intel:
            self.zink = Gtk.CheckButton(label='OpenGL through Intel\'s Vulkan driver (zink)')
            self.zink.set_active(read('gl') == 'zink')
            self.zink.connect('toggled', lambda b: self.save('gl', 'zink' if b.get_active() else None))
            box.pack_start(self.zink, False, False, 0)
            box.pack_start(self.small('Try it when the 3D view draws wrong. Cut faces are then not hatched.'),
                           False, False, 0)
            if nvidia:
                # setup_gpu: only for the Intel GPU
                self.gpu.bind_property('active', self.zink, 'sensitive', 6)  # SYNC_CREATE | INVERT_BOOLEAN

        # --- TopSo'Linux
        box.pack_start(self.heading('TopSo\'Linux'), False, False, 6)
        self.updates = Gtk.CheckButton(label='Look for TopSo\'Linux updates when TopSolid starts (once a day)')
        self.updates.set_active(read('update-check') != 'off')
        self.updates.connect('toggled', self.on_updates)
        box.pack_start(self.updates, False, False, 0)

        self.status = self.small('Changes are used from the next start of TopSolid.')
        box.pack_start(self.status, False, False, 10)

        buttons = Gtk.Box(spacing=8)
        for label, command, tip in (
                ('Wine configuration...', 'winecfg', 'Wine\'s own settings (winecfg). A scale set there '
                                                     'is replaced by a fixed one set here.'),
                ('Registry editor...', 'regedit', None)):
            b = Gtk.Button(label=label)
            if tip:
                b.set_tooltip_text(tip)
            b.connect('clicked', self.on_tool, command)
            b.set_sensitive(bool(RUN))
            buttons.pack_start(b, False, False, 0)
        close = Gtk.Button(label='Close')
        close.connect('clicked', lambda b: self.destroy())
        buttons.pack_end(close, False, False, 0)
        box.pack_start(buttons, False, False, 0)
        self.loading = False

    # --- widgets ---------------------------------------------------------------------------------------

    @staticmethod
    def heading(text):
        label = Gtk.Label(xalign=0)
        label.set_markup('<b>%s</b>' % text)
        return label

    @staticmethod
    def small(markup):
        label = Gtk.Label(xalign=0, wrap=True, max_width_chars=60)
        label.set_markup('<small>%s</small>' % markup)
        return label

    @staticmethod
    def combo(grid, row, text, items, active):
        grid.attach(Gtk.Label(label=text, xalign=0), 0, row, 1, 1)
        combo = Gtk.ComboBoxText()
        for key, label in items:
            combo.append(key, label)
        combo.set_active_id(active if active in [k for k, _ in items] else items[0][0])
        grid.attach(combo, 1, row, 1, 1)
        return combo

    @staticmethod
    def current_fonts():
        chosen = read('font-smoothing')
        if chosen in [k for k, _ in FONTS]:
            return chosen
        if user_reg('Control Panel\\Desktop', 'FontSmoothing') == '"0"':
            return 'off'
        if user_reg('Control Panel\\Desktop', 'FontSmoothingType') == 'dword:00000002':
            return 'subpixel'
        return 'greyscale'

    # --- saving ----------------------------------------------------------------------------------------

    def save(self, name, value, *also_remove):
        if self.loading:
            return
        try:
            write(name, value)
            for extra in also_remove:
                write(extra, None)
        except OSError as e:
            self.status.set_markup('<small>Saving failed: %s</small>' % GLib.markup_escape_text(str(e)))
            return
        self.status.set_markup('<small>Saved. %s</small>' % (
            'Close TopSolid and start it again to use it.' if wine_running()
            else 'Used from the next start of TopSolid.'))

    def on_scale(self, *args):
        self.percent.set_sensitive(self.fixed.get_active())
        if self.fixed.get_active():
            self.save('scale', str(self.percent.get_value_as_int()))
        else:
            # as "scale auto": also a scale set in winecfg goes back to the desktop's
            self.save('scale', None, '.auto-dpi')

    def on_format(self, combo, name):
        # the next start sets them, also over values changed with regedit
        self.save(name, combo.get_active_id() or None, '.auto-formats')

    def on_updates(self, button):
        if button.get_active():
            self.save('update-check', None, '.update-check', '.update-skip')
        else:
            self.save('update-check', 'off')

    def on_tool(self, button, command):
        self.children.append(subprocess.Popen([RUN, command], stdin=subprocess.DEVNULL))

    def on_destroy(self, *args):
        # the AppImage stays mounted while this runs: wait for winecfg or regedit
        self.hide()
        for child in self.children:
            child.wait()
        Gtk.main_quit()


def main():
    Window().show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
