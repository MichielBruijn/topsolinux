#!/usr/bin/env python3
"""Ask what goes wrong, for a problem report: zenity's multi-line field is a few characters wide.

usage: report-text.py TITLE [ICON]   prints the text; exit 1 = cancelled, 2 = no GTK 3
"""
import sys

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
except (ImportError, ValueError):
    sys.exit(2)

dialog = Gtk.Dialog(title=sys.argv[1] if len(sys.argv) > 1 else 'Report a problem')
if len(sys.argv) > 2:
    try:
        dialog.set_icon_from_file(sys.argv[2])
    except Exception:
        pass
dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Next', Gtk.ResponseType.OK)
dialog.set_default_size(620, 360)
box = dialog.get_content_area()
box.set_spacing(8)
box.set_border_width(12)
label = Gtk.Label(xalign=0)
label.set_markup('<b>Report a problem</b>\nWhat goes wrong, and what did you do just before?')
box.pack_start(label, False, False, 0)
view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, left_margin=6, right_margin=6, top_margin=6)
scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
scroll.add(view)
box.pack_start(scroll, True, True, 0)
dialog.show_all()
view.grab_focus()
if dialog.run() != Gtk.ResponseType.OK:
    sys.exit(1)
buf = view.get_buffer()
print(buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False))
