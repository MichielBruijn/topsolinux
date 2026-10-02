#!/usr/bin/env python3
"""The installer's progress window: a bar for the current part and one for the whole installation.

usage: progress.py --title TITLE --heading TEXT [--icon PNG]    reads commands from stdin
       progress.py --check                                     exit 0 if GTK 3 with cairo is available

Commands, one per line:
  # TEXT              what happens now (shown above the part bar)
  part SECONDS        a new part; the bar estimates its progress from the expected duration
  N                   the part is at N percent (replaces the estimate, e.g. for a download)
  total FROM TO SECONDS
                      the whole installation goes from FROM to TO percent during this step
End of input closes the window (exit 0); Cancel or closing the window exits 3.

The bars are drawn as rods turning around their long axis, so they show the installer is alive
also when a step gives no progress of its own.
"""
import math
import os
import sys
import time

if '--check' in sys.argv:
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_foreign('cairo')
        from gi.repository import Gtk  # noqa: F401
    except Exception:
        sys.exit(1)
    sys.exit(0)

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_foreign('cairo')
from gi.repository import GdkPixbuf, GLib, Gtk  # noqa: E402

FACETS = 10            # the rod is a 10-sided prism; its turning facets show the rotation
TURN_SECONDS = 2.4     # one full turn


def estimate(elapsed, expected):
    """Linear to 90 % at the expected duration, then slowly towards 99 %."""
    if expected <= 0:
        return 0.0
    if elapsed <= expected:
        return 0.9 * elapsed / expected
    return 0.9 + 0.09 * (1 - math.exp(-(elapsed - expected) / expected))


class Rod(Gtk.DrawingArea):
    def __init__(self, color, height=24):
        super().__init__()
        self.color = color
        self.fraction = 0.0
        self.angle = 0.0
        self.set_size_request(360, height)
        self.connect('draw', self.draw)

    def draw(self, widget, cr):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        r = h / 2
        # the trough
        self.rounded(cr, 0.5, 0.5, w - 1, h - 1, 5)
        cr.set_source_rgba(0.5, 0.55, 0.62, 0.18)
        cr.fill_preserve()
        cr.set_source_rgba(0.3, 0.35, 0.42, 0.35)
        cr.set_line_width(1)
        cr.stroke()
        fw = (w - 2) * max(0.0, min(1.0, self.fraction))
        if fw < 1:
            return
        x0 = 1
        cr.save()
        self.rounded(cr, x0, 1, fw, h - 2, 4)
        cr.clip()
        # the facets that face the viewer, from top to bottom; each is lit by a light from above
        red, green, blue = self.color
        step = 2 * math.pi / FACETS
        for i in range(FACETS):
            a1 = self.angle + i * step
            a2 = a1 + step
            # angle 0 points up, pi/2 towards the viewer
            if math.sin((a1 + a2) / 2) <= 0:
                continue
            y1 = r - (r - 1) * math.cos(a1)
            y2 = r - (r - 1) * math.cos(a2)
            normal = (a1 + a2) / 2
            light = 0.55 + 0.45 * max(0.0, math.cos(normal - 0.9))
            if i % 2:
                light *= 0.74
            cr.rectangle(x0, min(y1, y2), fw, abs(y2 - y1) + 0.6)
            cr.set_source_rgb(red * light, green * light, blue * light)
            cr.fill()
            # the edge between two facets
            cr.rectangle(x0, y1 - 0.5, fw, 1)
            cr.set_source_rgba(0, 0, 0, 0.18 * math.sin(a1) if math.sin(a1) > 0 else 0)
            cr.fill()
        # a fixed highlight: the light doesn't turn with the rod
        cr.rectangle(x0, h * 0.18, fw, h * 0.14)
        cr.set_source_rgba(1, 1, 1, 0.22)
        cr.fill()
        cr.restore()
        # the end face at the progress point
        if fw > r:
            cr.save()
            cr.translate(x0 + fw - r * 0.28, h / 2)
            cr.scale(r * 0.28, r - 1.5)
            cr.arc(0, 0, 1, 0, 2 * math.pi)
            cr.restore()
            cr.set_source_rgba(min(1, red * 1.15), min(1, green * 1.15), min(1, blue * 1.15), 0.95)
            cr.fill()

    @staticmethod
    def rounded(cr, x, y, w, h, radius):
        radius = min(radius, w / 2, h / 2)
        cr.new_sub_path()
        cr.arc(x + w - radius, y + radius, radius, -math.pi / 2, 0)
        cr.arc(x + w - radius, y + h - radius, radius, 0, math.pi / 2)
        cr.arc(x + radius, y + h - radius, radius, math.pi / 2, math.pi)
        cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
        cr.close_path()


class Progress(Gtk.Window):
    def __init__(self, title, heading, icon):
        super().__init__(title=title)
        self.set_default_size(560, -1)
        self.set_resizable(False)
        self.set_border_width(18)
        if icon:
            try:
                self.set_icon_from_file(icon)
            except GLib.Error:
                icon = None
        self.cancelled = False
        self.connect('delete-event', self.on_cancel)

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.add(outer)
        if icon:
            img = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(icon, 56, 56))
            img.set_valign(Gtk.Align.START)
            outer.pack_start(img, False, False, 0)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.pack_start(box, True, True, 0)

        head = Gtk.Label(xalign=0)
        head.set_markup('<big><b>%s</b></big>' % GLib.markup_escape_text(heading))
        box.pack_start(head, False, False, 0)

        self.text = Gtk.Label(label='Preparing...', xalign=0)
        self.text.set_line_wrap(True)
        self.text.set_max_width_chars(60)
        box.pack_start(self.text, False, False, 6)

        self.part = Rod((0.36, 0.56, 0.82))
        self.part_pct = Gtk.Label(label='', xalign=1, width_chars=5)
        box.pack_start(self.row(self.part, self.part_pct), False, False, 0)

        total_label = Gtk.Label(xalign=0)
        total_label.set_markup('<small>Total</small>')
        box.pack_start(total_label, False, False, 6)
        self.total = Rod((0.96, 0.65, 0.14))
        self.total_pct = Gtk.Label(label='', xalign=1, width_chars=5)
        box.pack_start(self.row(self.total, self.total_pct), False, False, 0)

        self.elapsed = Gtk.Label(xalign=0)
        self.elapsed.get_style_context().add_class('dim-label')
        buttons = Gtk.Box(spacing=6)
        buttons.pack_start(self.elapsed, True, True, 0)
        cancel = Gtk.Button(label='Cancel')
        cancel.connect('clicked', self.on_cancel)
        buttons.pack_end(cancel, False, False, 0)
        box.pack_start(buttons, False, False, 10)

        self.start = time.monotonic()
        self.part_start, self.part_secs, self.part_exact = self.start, 0, None
        self.total_start, self.total_from, self.total_to, self.total_secs = self.start, 0.0, 0.0, 0

        self.pending = b''
        GLib.io_add_watch(sys.stdin.fileno(), GLib.PRIORITY_DEFAULT, GLib.IO_IN | GLib.IO_HUP, self.on_input)
        GLib.timeout_add(33, self.tick)
        self.show_all()

    @staticmethod
    def row(rod, pct):
        r = Gtk.Box(spacing=10)
        rod.set_valign(Gtk.Align.CENTER)
        r.pack_start(rod, True, True, 0)
        r.pack_start(pct, False, False, 0)
        return r

    def on_cancel(self, *args):
        self.cancelled = True
        Gtk.main_quit()
        return True

    def on_input(self, fd, condition):
        data = os.read(fd, 65536)
        if not data:
            Gtk.main_quit()
            return False
        *lines, self.pending = (self.pending + data).split(b'\n')
        for line in lines:
            self.command(line.decode(errors='replace'))
        return True

    def command(self, line):
        now = time.monotonic()
        words = line.split()
        if line.startswith('#'):
            self.text.set_text(line[1:].strip())
        elif words[:1] == ['part'] and len(words) == 2:
            self.part_start, self.part_secs, self.part_exact = now, float(words[1]), None
        elif words[:1] == ['total'] and len(words) == 4:
            self.total_from, self.total_to, self.total_secs = (float(w) for w in words[1:])
            self.total_start = now
        elif len(words) == 1:
            try:
                self.part_exact = max(0.0, min(100.0, float(words[0]))) / 100
            except ValueError:
                pass

    def tick(self):
        now = time.monotonic()
        part = self.part_exact
        if part is None:
            part = estimate(now - self.part_start, self.part_secs)
        # a part with real progress (a download) moves the total too; otherwise the step's estimate does
        within = part if self.part_exact is not None else estimate(now - self.total_start, self.total_secs)
        total = (self.total_from + (self.total_to - self.total_from) * within) / 100
        # never backwards
        self.total.fraction = max(self.total.fraction, total)
        self.part.fraction = part
        self.part_pct.set_text('%d %%' % (part * 100))
        self.total_pct.set_text('%d %%' % (self.total.fraction * 100))
        e = int(now - self.start)
        self.elapsed.set_text('%d:%02d' % (e // 60, e % 60))
        turn = 2 * math.pi * (now - self.start) / TURN_SECONDS
        self.part.angle = turn * 1.5
        self.total.angle = turn
        self.part.queue_draw()
        self.total.queue_draw()
        return True


def main():
    args = {'--title': "TopSo'Linux", '--heading': '', '--icon': None}
    it = iter(sys.argv[1:])
    for a in it:
        if a in args:
            args[a] = next(it, None)
    win = Progress(args['--title'], args['--heading'], args['--icon'])
    Gtk.main()
    sys.exit(3 if win.cancelled else 0)


if __name__ == '__main__':
    main()
