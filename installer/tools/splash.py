#!/usr/bin/env python3
"""Splash screen while TopSolid starts: TopSolid shows its own only after Wine, SQL Server and the
local PDM are up, which can take a while.

usage: splash.py --status FILE --icon PNG --title TEXT --subtitle TEXT

FILE holds commands, one per line, and is read again when it changes (a file, not a pipe: the Wine
processes started meanwhile would keep a pipe open):
  # TEXT          what happens now (the last one is shown)
  watch CLASS     close as soon as an X11 window of this class (e.g. topsolid.exe) shows something
Removing FILE (topsolinux-run does that when the program has ended) or a click closes it too. There
is no time limit: a slow computer takes longer, not differently.

Needs only python3-gi with GTK 3 (no cairo bindings, Ubuntu doesn't install those by default); without
GTK 3 it shows a zenity progress window instead. The window watching uses libX11 through ctypes.
"""
import ctypes
import ctypes.util
import os
import subprocess
import sys
import time

# an X11 window, like Wine's, so it can be placed in the middle of the screen
os.environ.setdefault('GDK_BACKEND', 'x11')

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gdk, GdkPixbuf, GLib, Gtk
except (ImportError, ValueError):
    # ValueError: no GTK 3 typelib
    Gtk = None

CSS = b'''
.splash-window { background: transparent; }
.splash { background: #1f2733; border-radius: 14px; padding: 26px 36px 30px 36px; }
.splash label { color: #e9eef5; }
.splash .title { font-size: 26pt; font-weight: bold; }
.splash .subtitle { color: #a9b6c6; }
.splash .status { color: #c9d3df; }
.splash progressbar trough { min-height: 6px; border-radius: 3px; background: #2f3a49; border: none; }
.splash progressbar progress { min-height: 6px; border-radius: 3px; background: #f4a623; border: none; }
'''


class Attributes(ctypes.Structure):
    _fields_ = [('x', ctypes.c_int), ('y', ctypes.c_int), ('width', ctypes.c_int), ('height', ctypes.c_int),
                ('border_width', ctypes.c_int), ('depth', ctypes.c_int), ('visual', ctypes.c_void_p),
                ('root', ctypes.c_ulong), ('class_', ctypes.c_int), ('bit_gravity', ctypes.c_int),
                ('win_gravity', ctypes.c_int), ('backing_store', ctypes.c_int), ('backing_planes', ctypes.c_ulong),
                ('backing_pixel', ctypes.c_ulong), ('save_under', ctypes.c_int), ('colormap', ctypes.c_ulong),
                ('map_installed', ctypes.c_int), ('map_state', ctypes.c_int), ('all_event_masks', ctypes.c_long),
                ('your_event_mask', ctypes.c_long), ('do_not_propagate_mask', ctypes.c_long),
                ('override_redirect', ctypes.c_int), ('screen', ctypes.c_void_p)]


class Image(ctypes.Structure):
    # the start of XImage
    _fields_ = [('width', ctypes.c_int), ('height', ctypes.c_int), ('xoffset', ctypes.c_int), ('format', ctypes.c_int),
                ('data', ctypes.c_void_p), ('byte_order', ctypes.c_int), ('bitmap_unit', ctypes.c_int),
                ('bitmap_bit_order', ctypes.c_int), ('bitmap_pad', ctypes.c_int), ('depth', ctypes.c_int),
                ('bytes_per_line', ctypes.c_int), ('bits_per_pixel', ctypes.c_int)]


class Windows:
    """The windows shown on the X11 display (_NET_CLIENT_LIST)."""

    class ClassHint(ctypes.Structure):
        # raw pointers: Xlib allocated them and XFree must get them back
        _fields_ = [('res_name', ctypes.c_void_p), ('res_class', ctypes.c_void_p)]

    def __init__(self):
        self.x = ctypes.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6')
        x = self.x
        x.XOpenDisplay.restype = ctypes.c_void_p
        x.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x.XDefaultRootWindow.restype = ctypes.c_ulong
        x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x.XInternAtom.restype = ctypes.c_ulong
        x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x.XGetWindowProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_long,
                                         ctypes.c_long, ctypes.c_int, ctypes.c_ulong,
                                         ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
                                         ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                                         ctypes.POINTER(ctypes.c_void_p)]
        x.XGetClassHint.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(self.ClassHint)]
        x.XFree.argtypes = [ctypes.c_void_p]
        x.XGetWindowAttributes.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Attributes)]
        x.XGetImage.restype = ctypes.POINTER(Image)
        x.XGetImage.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
                                ctypes.c_uint, ctypes.c_ulong, ctypes.c_int]
        # a window can be gone by the time it is asked for its class: ignore the X error
        self.handler = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)(lambda d, e: 0)
        x.XSetErrorHandler(self.handler)
        self.dpy = x.XOpenDisplay(None)
        if not self.dpy:
            raise OSError('no X11 display')
        self.root = x.XDefaultRootWindow(self.dpy)
        self.clients = x.XInternAtom(self.dpy, b'_NET_CLIENT_LIST', 0)

    def painted(self, window):
        """Whether the window shows something. A transparent one (TopSolid's splash covers the whole screen)
        starts empty: look for pixels on three lines across it."""
        x = self.x
        a = Attributes()
        if not x.XGetWindowAttributes(self.dpy, window, ctypes.byref(a)) or a.map_state != 2:  # IsViewable
            return False
        if a.depth != 32:
            return True
        for y in (a.height // 3, a.height // 2, a.height * 2 // 3):
            img = x.XGetImage(self.dpy, window, 0, y, a.width, 1, 0xffffffff, 2)  # ZPixmap
            if not img:
                continue
            row = ctypes.string_at(img.contents.data, img.contents.bytes_per_line)
            x.XFree(img.contents.data)
            x.XFree(img)
            if row.strip(b'\0'):
                return True
        return False

    def shown(self, wm_class):
        """Whether a window of this class is on the screen and shows something."""
        return any(self.painted(w) for w in self.windows(wm_class))

    def windows(self, wm_class):
        x = self.x
        typ, fmt, n, after, prop = ctypes.c_ulong(), ctypes.c_int(), ctypes.c_ulong(), ctypes.c_ulong(), ctypes.c_void_p()
        # 33 = XA_WINDOW
        if x.XGetWindowProperty(self.dpy, self.root, self.clients, 0, 65536, 0, 33, ctypes.byref(typ),
                                ctypes.byref(fmt), ctypes.byref(n), ctypes.byref(after), ctypes.byref(prop)) != 0:
            return []
        found = []
        if prop.value:
            windows = ctypes.cast(prop, ctypes.POINTER(ctypes.c_ulong))
            for i in range(n.value):
                hint = self.ClassHint()
                if x.XGetClassHint(self.dpy, windows[i], ctypes.byref(hint)):
                    names = set()
                    for p in (hint.res_name, hint.res_class):
                        if p:
                            names.add(ctypes.string_at(p).decode(errors='replace').lower())
                            x.XFree(p)
                    if wm_class in names:
                        found.append(windows[i])
            x.XFree(prop)
        return found


class Watcher:
    """The status file and the window to wait for, for the GTK and the zenity splash."""

    def __init__(self, status):
        self.status_file, self.seen, self.text, self.watch_class, self.windows = status, None, '', None, None

    def read(self):
        """Take text and watch_class from the file; False when it is gone."""
        try:
            st = os.stat(self.status_file)
            if (st.st_mtime_ns, st.st_size) != self.seen:
                self.seen = (st.st_mtime_ns, st.st_size)
                for line in open(self.status_file, encoding='utf-8', errors='replace').read().splitlines():
                    line = line.strip()
                    if line.startswith('#'):
                        self.text = line[1:].strip()
                    elif line.startswith('watch ') and self.watch_class is None:
                        self.watch_class = line[len('watch '):].strip().lower()
        except OSError:
            return False
        return True

    def done(self):
        if not self.read():
            return True
        if not self.watch_class:
            return False
        try:
            if self.windows is None:
                self.windows = Windows()
            return self.windows.shown(self.watch_class)
        except OSError:
            # no X11 display to watch: the end of the program closes the splash
            self.watch_class = None
            return False


class Splash(Gtk.Window if Gtk else object):
    def __init__(self, watcher, icon, title, subtitle):
        super().__init__(type=Gtk.WindowType.TOPLEVEL, title=title)
        self.watcher = watcher
        self.set_decorated(False)
        self.set_type_hint(Gdk.WindowTypeHint.SPLASHSCREEN)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        screen = self.get_screen()
        # rounded corners need a compositor; without one the window is a plain rectangle
        if screen.get_rgba_visual() and screen.is_composited():
            self.set_visual(screen.get_rgba_visual())
            self.get_style_context().add_class('splash-window')
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class('splash')
        events = Gtk.EventBox()
        events.set_visible_window(False)
        events.add(card)
        events.connect('button-press-event', lambda *a: Gtk.main_quit())
        self.add(events)

        if icon:
            try:
                img = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(icon, 128, 128))
                card.pack_start(img, False, False, 4)
            except GLib.Error:
                pass
        for text, cls in ((title, 'title'), (subtitle, 'subtitle')):
            label = Gtk.Label(label=text)
            label.get_style_context().add_class(cls)
            card.pack_start(label, False, False, 0)
        self.status = Gtk.Label(label='Starting...')
        self.status.get_style_context().add_class('status')
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(48)
        self.status.set_justify(Gtk.Justification.CENTER)
        card.pack_start(self.status, False, False, 10)
        self.bar = Gtk.ProgressBar()
        self.bar.set_pulse_step(0.04)
        self.bar.set_size_request(360, -1)
        card.pack_start(self.bar, False, False, 0)

        self.check()
        GLib.timeout_add(50, self.tick)
        GLib.timeout_add(250, self.check)
        self.show_all()

    def check(self):
        if self.watcher.done():
            Gtk.main_quit()
            return False
        if self.watcher.text:
            self.status.set_text(self.watcher.text)
        return True

    def tick(self):
        self.bar.pulse()
        return True


def zenity(watcher, title, subtitle):
    """Without GTK 3 for Python: a zenity progress window with the same text."""
    try:
        z = subprocess.Popen(['zenity', '--progress', '--pulsate', '--no-cancel', '--auto-close', '--width=420',
                              '--title=' + title, '--text=' + subtitle], stdin=subprocess.PIPE, text=True)
    except OSError:
        return
    shown = None
    try:
        while z.poll() is None and not watcher.done():
            if watcher.text != shown:
                shown = watcher.text
                z.stdin.write('# %s — %s\n' % (subtitle, shown))
                z.stdin.flush()
            time.sleep(0.25)
        z.stdin.write('100\n')
        z.stdin.flush()
        z.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    try:
        z.wait(timeout=5)
    except subprocess.TimeoutExpired:
        z.kill()


def main():
    args = {'--status': None, '--icon': None, '--title': "TopSo'Linux", '--subtitle': ''}
    it = iter(sys.argv[1:])
    for a in it:
        if a in args:
            args[a] = next(it, None)
    if not args['--status']:
        sys.exit(__doc__)
    watcher = Watcher(args['--status'])
    if Gtk is None:
        print('splash: no GTK 3 for Python (python3-gi, gir1.2-gtk-3.0), using zenity', file=sys.stderr)
        zenity(watcher, args['--title'], args['--subtitle'])
        return
    Splash(watcher, args['--icon'], args['--title'], args['--subtitle'])
    Gtk.main()


if __name__ == '__main__':
    main()
