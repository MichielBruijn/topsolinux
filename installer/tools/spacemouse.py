#!/usr/bin/env python3
"""SpaceMouse settings for TopSolid: speeds and which SpaceMouse axis drives which motion.

usage: spacemouse.py   (needs WINE and WINEPREFIX, topsolinux-run sets them)

The settings are those of tdxnavlib (wine/patches) in HKCU\\Software\\Wine\\TDxNavLib. tdxnavlib reads
them again at the start of every motion, so a change works right away, also in a running TopSolid.
While Wine runs they are written with "wine reg", otherwise straight into user.reg: starting Wine would
start SQL Server and the PDM too.

The bars show what TopSolid gets from the cap, read from spacenavd like tdxnavlib does.
Exits with 2 without GTK 3; topsolinux-run then opens regedit.
"""
import os
import shlex
import socket
import struct
import subprocess
import sys
import time

os.environ.setdefault('GDK_BACKEND', 'x11')

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import GLib, Gtk
except (ImportError, ValueError):
    sys.exit(2)

KEY = 'Software\\Wine\\TDxNavLib'
# without settings tdxnavlib uses 1.2 and 1.6 and no swaps; these are the installer's (data/reg/tweaks.reg)
DEFAULTS = {'TranslationSpeed': '2.4', 'RotationSpeed': '3.2',
            'AxisSigns': '1,1,-1,1,1,1', 'AxisMap': '0,2,1,3,5,4'}
INPUTS = ['x', 'y', 'z', 'rx', 'ry', 'rz']
# navlib's camera frame: x right, y up, z out of the screen
MOTIONS = ['Pan left / right', 'Pan down / up', 'Zoom', 'Tilt (around left-right)',
           'Turn (around up-down)', 'Roll (around the view direction)']
FULL = 350.0   # spacenavd's range for a fully pushed cap

WINE = os.environ.get('WINE', 'wine')
PREFIX = os.environ.get('WINEPREFIX', os.path.expanduser('~/.wine'))


def wine_running():
    """Whether a wineserver has this prefix open: then user.reg may not be touched."""
    try:
        st = os.stat(PREFIX)
    except OSError:
        return False
    path = '/tmp/.wine-%d/server-%x-%x/socket' % (os.getuid(), st.st_dev, st.st_ino)
    s = socket.socket(socket.AF_UNIX)
    try:
        s.connect(path)
        return True
    except OSError:
        return False
    finally:
        s.close()


def section_name():
    return '[' + KEY.replace('\\', '\\\\') + ']'


def read_user_reg():
    values = {}
    try:
        with open(os.path.join(PREFIX, 'user.reg'), encoding='utf-8', errors='replace') as f:
            inside = False
            for line in f:
                if line.startswith('['):
                    inside = line.split(']')[0] + ']' == section_name()
                elif inside and line.startswith('"') and '"="' in line:
                    name, value = line.strip()[1:-1].split('"="', 1)
                    values[name] = value
    except OSError:
        pass
    return values


def write_user_reg(values):
    path = os.path.join(PREFIX, 'user.reg')
    with open(path, encoding='utf-8', errors='surrogateescape') as f:
        lines = f.readlines()
    head = section_name()
    start = next((i for i, l in enumerate(lines) if l.startswith(head + ' ')), None)
    new = ['"%s"="%s"\n' % (k, values[k]) for k in sorted(values)]
    if start is None:
        filetime = int((time.time() + 11644473600) * 10000000)
        lines += ['\n', '%s %d\n' % (head, int(time.time())), '#time=%x\n' % filetime] + new
    else:
        end = start + 1
        while end < len(lines) and lines[end].strip() and not lines[end].startswith('['):
            end += 1
        kept = [l for l in lines[start + 1:end]
                if not (l.startswith('"') and l[1:].split('"', 1)[0] in values)]
        lines[start + 1:end] = kept + new
    tmp = path + '.spacemouse'
    with open(tmp, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.writelines(lines)
    os.replace(tmp, path)


def read_wine():
    values = {}
    out = subprocess.run([WINE, 'reg', 'query', 'HKCU\\' + KEY], capture_output=True, text=True,
                         errors='replace').stdout
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[1] == 'REG_SZ':
            values[parts[0]] = parts[2].strip()
    return values


def read_settings():
    values = dict(DEFAULTS)
    values.update(read_wine() if wine_running() else read_user_reg())
    return values


def parse_list(text, fallback):
    try:
        items = [int(v) for v in text.split(',')]
        return items if len(items) == 6 else fallback
    except ValueError:
        return fallback


class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title='SpaceMouse')
        self.set_border_width(18)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect('destroy', self.on_destroy)
        self.pending = None
        self.writer = None
        self.timer = 0
        self.updating = False
        self.raw = [0] * 6
        self.last = 0

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(box)

        speeds = Gtk.Grid(column_spacing=12, row_spacing=6)
        box.pack_start(self.heading('Speed'), False, False, 0)
        box.pack_start(speeds, False, False, 0)
        self.translation = self.speed_row(speeds, 0, 'Pan and zoom')
        self.rotation = self.speed_row(speeds, 1, 'Rotate')

        box.pack_start(self.heading('Axes'), False, False, 0)
        hint = Gtk.Label(xalign=0, wrap=True, max_width_chars=60)
        hint.set_markup('<small>Move the cap: the bar of the motion you make should move, to the right '
                        'for right, up, toward you and the turns you make. Pick another SpaceMouse axis '
                        'or Reverse when it doesn\'t. Picking an axis that another motion uses swaps '
                        'the two.</small>')
        box.pack_start(hint, False, False, 0)

        axes = Gtk.Grid(column_spacing=12, row_spacing=6)
        box.pack_start(axes, False, False, 0)
        for col, text in enumerate(['', 'SpaceMouse axis', 'Reverse', 'TopSolid gets']):
            label = Gtk.Label(xalign=0)
            label.set_markup('<small>%s</small>' % text)
            axes.attach(label, col, 0, 1, 1)
        self.combos, self.reverse, self.bars = [], [], []
        for i, name in enumerate(MOTIONS):
            axes.attach(Gtk.Label(label=name, xalign=0), 0, i + 1, 1, 1)
            combo = Gtk.ComboBoxText()
            for text in INPUTS:
                combo.append_text(text)
            combo.connect('changed', self.on_map_changed, i)
            axes.attach(combo, 1, i + 1, 1, 1)
            check = Gtk.CheckButton()
            check.set_halign(Gtk.Align.CENTER)
            check.connect('toggled', lambda b: (self.show_bars(), self.on_changed()))
            axes.attach(check, 2, i + 1, 1, 1)
            bar = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -1, 1, 0.01)
            bar.set_draw_value(False)
            bar.set_has_origin(False)
            bar.set_size_request(160, -1)
            bar.set_can_focus(False)
            bar.connect('button-press-event', lambda *a: True)
            bar.connect('scroll-event', lambda *a: True)
            axes.attach(bar, 3, i + 1, 1, 1)
            self.combos.append(combo)
            self.reverse.append(check)
            self.bars.append(bar)

        self.status = Gtk.Label(xalign=0)
        box.pack_start(self.status, False, False, 0)

        buttons = Gtk.Box(spacing=8)
        reset = Gtk.Button(label='TopSo\'Linux defaults')
        reset.connect('clicked', lambda b: self.load(DEFAULTS, apply=True))
        close = Gtk.Button(label='Close')
        close.connect('clicked', lambda b: self.destroy())
        buttons.pack_start(reset, False, False, 0)
        buttons.pack_end(close, False, False, 0)
        box.pack_start(buttons, False, False, 0)

        self.load(read_settings())
        self.sock = None
        self.connect_spacenavd()
        GLib.timeout_add(50, self.decay)

    @staticmethod
    def heading(text):
        label = Gtk.Label(xalign=0)
        label.set_markup('<b>%s</b>' % text)
        return label

    def speed_row(self, grid, row, text):
        grid.attach(Gtk.Label(label=text, xalign=0), 0, row, 1, 1)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.1, 10, 0.1)
        scale.set_digits(1)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_hexpand(True)
        scale.set_size_request(300, -1)
        scale.connect('value-changed', self.on_changed)
        grid.attach(scale, 1, row, 1, 1)
        return scale

    # --- settings ------------------------------------------------------------------------------------

    def load(self, values, apply=False):
        self.updating = True
        for scale, name, fallback in ((self.translation, 'TranslationSpeed', 1.2),
                                      (self.rotation, 'RotationSpeed', 1.6)):
            try:
                scale.set_value(float(values.get(name, fallback)))
            except ValueError:
                scale.set_value(fallback)
        mapping = parse_list(values.get('AxisMap', ''), list(range(6)))
        signs = parse_list(values.get('AxisSigns', ''), [1] * 6)
        for i in range(6):
            self.combos[i].set_active(mapping[i] if 0 <= mapping[i] < 6 else i)
            self.reverse[i].set_active(signs[i] < 0)
        self.updating = False
        if apply:
            self.on_changed()

    def values(self):
        return {
            'TranslationSpeed': '%.1f' % self.translation.get_value(),
            'RotationSpeed': '%.1f' % self.rotation.get_value(),
            'AxisMap': ','.join(str(c.get_active()) for c in self.combos),
            'AxisSigns': ','.join('-1' if r.get_active() else '1' for r in self.reverse),
        }

    def on_map_changed(self, combo, i):
        if self.updating:
            return
        # keep it a permutation: the motion that had this axis gets this motion's old one
        new = combo.get_active()
        used = [c.get_active() for c in self.combos]
        old = next((v for v in range(6) if v not in used), None)
        for j, c in enumerate(self.combos):
            if j != i and c.get_active() == new and old is not None:
                self.updating = True
                c.set_active(old)
                self.updating = False
        self.show_bars()
        self.on_changed()

    def on_changed(self, *args):
        if self.updating:
            return
        self.pending = self.values()
        self.status.set_markup('<small>Saving...</small>')
        if self.timer:
            GLib.source_remove(self.timer)
        self.timer = GLib.timeout_add(300, self.save)

    def save(self):
        self.timer = 0
        if self.pending is None or self.writer is not None:
            return False
        values, self.pending = self.pending, None
        if wine_running():
            # one "wine reg" each: Wine's cmd would keep the quotes and split on the commas
            script = ' && '.join('%s reg add %s /v %s /t REG_SZ /d %s /f' % (
                shlex.quote(WINE), shlex.quote('HKCU\\' + KEY), name, shlex.quote(value))
                for name, value in values.items())
            self.writer = subprocess.Popen(['sh', '-c', script],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            GLib.child_watch_add(self.writer.pid, self.saved)
        else:
            try:
                write_user_reg(values)
                self.saved(None, 0)
            except OSError as e:
                self.status.set_markup('<small>Saving failed: %s</small>' % GLib.markup_escape_text(str(e)))
        return False

    def saved(self, pid, status):
        self.writer = None
        if self.pending is not None:
            self.save()
        else:
            self.status.set_markup('<small>Saved. TopSolid uses it from the next move of the cap.</small>'
                                   if status == 0 else '<small>Saving failed.</small>')

    # --- live view -----------------------------------------------------------------------------------

    def connect_spacenavd(self):
        path = os.environ.get('SPNAV_SOCKET', '/var/run/spnav.sock')
        try:
            self.sock = socket.socket(socket.AF_UNIX)
            self.sock.connect(path)
            self.sock.setblocking(False)
            self.buf = b''
            GLib.io_add_watch(self.sock.fileno(), GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self.on_event)
        except OSError:
            self.sock = None
            self.status.set_markup('<small>spacenavd isn\'t running: no live view '
                                   '(sudo systemctl enable --now spacenavd)</small>')

    def on_event(self, fd, cond):
        try:
            data = self.sock.recv(4096)
        except BlockingIOError:
            return True
        except OSError:
            data = b''
        if not data:
            self.sock.close()
            self.sock = None
            return False
        self.buf += data
        # old spacenavd protocol: 8 ints, type 0 = motion x y z rx ry rz period
        while len(self.buf) >= 32:
            ev = struct.unpack('8i', self.buf[:32])
            self.buf = self.buf[32:]
            if ev[0] == 0:
                self.raw = list(ev[1:7])
                self.last = time.monotonic()
                self.show_bars()
        return True

    def show_bars(self):
        for i in range(6):
            value = self.raw[self.combos[i].get_active()] / FULL
            if self.reverse[i].get_active():
                value = -value
            self.bars[i].set_value(max(-1.0, min(1.0, value)))

    def decay(self):
        # spacenavd sends no zero when the cap is let go quickly
        if any(self.raw) and time.monotonic() - self.last > 0.3:
            self.raw = [0] * 6
            self.show_bars()
        return True

    def on_destroy(self, *args):
        # a change made just before closing
        if self.writer is not None:
            self.writer.wait()
            self.writer = None
        self.save()
        if self.writer is not None:
            self.writer.wait()
        Gtk.main_quit()


def main():
    Window().show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
