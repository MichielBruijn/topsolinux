#!/usr/bin/env python3
"""Make docs/topsolinux-guide.pdf, the short user guide. Needs python3-reportlab."""
import os

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'topsolinux-guide.pdf')
TITLE = "TopSo'Linux: TopSolid on Linux"

styles = getSampleStyleSheet()
body = ParagraphStyle('body', parent=styles['BodyText'], fontName='Helvetica', fontSize=10, leading=14,
                      alignment=TA_LEFT, spaceAfter=4)
h1 = ParagraphStyle('h1', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=20, leading=24,
                    alignment=TA_LEFT, spaceAfter=2)
sub = ParagraphStyle('sub', parent=body, textColor=colors.HexColor('#555555'), fontSize=11, spaceAfter=10)
h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=13, leading=16,
                    textColor=colors.HexColor('#1f4e9c'), spaceBefore=10, spaceAfter=4)
note = ParagraphStyle('note', parent=body, backColor=colors.HexColor('#fff4e0'), borderPadding=6,
                      borderColor=colors.HexColor('#f5a623'), borderWidth=0.6, spaceBefore=10, spaceAfter=12)
code = ParagraphStyle('code', parent=body, fontName='Courier', fontSize=9, leading=12)
cell = ParagraphStyle('cell', parent=body, fontSize=9, leading=11, spaceAfter=0)


def c(text):
    return f'<font face="Courier">{text}</font>'


def bullets(*items):
    return ListFlowable([ListItem(Paragraph(i, body), leftIndent=12) for i in items],
                        bulletType='bullet', start='•', leftIndent=12, bulletFontSize=9)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#777777'))
    canvas.drawString(20 * mm, 12 * mm, "TopSo'Linux 1.6.14 · unofficial, not affiliated with TOPSOLID SAS")
    canvas.drawRightString(190 * mm, 12 * mm, f'page {doc.page}')
    canvas.restoreState()


APP = 'TopSolid-7.20-TopSoLinux-1.6.14-x86_64.AppImage'
story = [
    Paragraph(TITLE, h1),
    Paragraph('Short guide to installing and using TopSolid 7.20 with its local PDM on Linux', sub),
    Paragraph('TopSo\'Linux is a patched Wine plus an installer that sets up TopSolid from TopSolid\'s installation '
              'media, your own copy or downloaded from TopSolid\'s server: TopSolid, SQL Server Express with the '
              'local PDM server, the Sentinel license server and TopSolid\'Update. No Windows needed.', body),
    Paragraph('TopSo\'Linux is unofficial and not affiliated with or supported by TOPSOLID SAS.', note),

    Paragraph('1. What you need', h2),
    bullets('Ubuntu 24.04 or newer, or another 64-bit distribution with glibc 2.38 or newer.',
            'The TopSolid installation media (the folder with ' + c('Setup.exe') + '), or let the installer '
            'download them from TopSolid\'s server (19 GB).',
            'About 45 GB of free disk space (65 GB when downloading) and an internet connection.',
            'A GPU with a working OpenGL driver. Laptops with NVIDIA and Intel/AMD graphics use the NVIDIA GPU '
            'automatically.'),

    Paragraph('2. Installing', h2),
    bullets('Make ' + c('TopSoLinux-Installer-1.6.14-x86_64.AppImage') + ' executable (file properties, or '
            + c('chmod +x') + ') and start it.',
            'Choose the installation media (found automatically in Downloads, your home folder or a USB drive), '
            'another folder, or the download from TopSolid\'s server.',
            'The installer puts TopSolid in your app menu with <b>Gear Lever</b> and installs SpaceMouse support '
            '(spacenavd); installing them asks for your password.',
            'TopSolid\'s own installer opens: choose the modules you use, click Install and accept the license '
            'agreement. <b>Its installation of SQL Server stops with an error. That is expected:</b> TopSo\'Linux '
            'stops it and installs SQL Server itself. Close the errors and the setup.',
            'Wait: the whole installation takes 30 to 60 minutes. If it is interrupted, start the installer again '
            'and it continues where it stopped.'),
    Paragraph('Everything is installed in ' + c('~/.local/share/topsolinux') + '. The result is ' + c(APP) + ', a '
              'complete, self-contained TopSolid (Gear Lever renames it to ' + c('topsolid_7.20_topsolinux-1.6.14.appimage') + ').', body),

    Paragraph('3. The TopSolid AppImage', h2),
    bullets('Right-click TopSolid\'s icon in the app menu for <i>TopSolid\'Update</i>, the license tool, '
            '<i>Wine settings</i> and <i>Stop background services</i>.',
            'Another computer: copy the AppImage there and start it, and choose <i>Install</i> (app menu, with Gear Lever) or <i>Launch</i>. The first start sets TopSolid up in '
            + c('~/.local/share/topsolinux') + ', which takes a few minutes. Each computer needs its own license.',
            'Only use it on computers you are licensed for, and do not publish it: it contains TopSolid, SQL Server '
            'Express and Microsoft\'s runtimes.'),

    Paragraph('4. First start', h2),
    bullets('License: as on Windows.',
            'PDM connection: choose <b>Local PDM Server</b> and leave user and password empty.',
            'Libraries: import the ones you need from TopSolid.',
            'New Project: enter a name, choose Blank Template and click the green check mark.'),
    Paragraph('SQL Server, the local PDM and the license server start by themselves and stop again when you close '
              'TopSolid. The very first start of the PDM can take a few minutes; TopSo\'Linux shows what it is doing '
              'until TopSolid shows its own splash screen. <i>Command Prediction</i> is off in a new installation (it '
              'keeps a processor core and several GB busy); turn it on in TopSolid\'s options if you want it.',
              body),

    Paragraph('5. Updates', h2),
    Paragraph('Service packs come through TopSolid\'Update (right-click the icon). They update the installation in '
              + c('~/.local/share/topsolinux') + ', not the AppImage file, so Gear Lever\'s update button does not '
              'apply. After <i>Download now</i> the window disappears: the download runs in the background, and a '
              'little later TopSolid asks to install it.', body),

    Paragraph('6. Useful commands and tips', h2),
    Paragraph('The AppImage also accepts a command, e.g. ' + c(APP + ' scale 150') + ':', body),
]

table = Table([[Paragraph(c(a), cell), Paragraph(b, cell)] for a, b in [
    ('scale 150', 'text and icons at 150% (100 = normal); by default TopSolid follows the desktop'),
    ('scale auto', 'follow the desktop\'s scale again'),
    ('update', 'start TopSolid\'Update'),
    ('license FILE', 'install a license file'),
    ('stop', 'stop SQL Server, the PDM and the license server'),
    ('debug', 'TopSolid hangs: write its stacks to a file in your home folder, for a bug report'),
]], colWidths=[40 * mm, 130 * mm])
table.setStyle(TableStyle([
    ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#f2f5fb'), colors.white]),
    ('LEFTPADDING', (0, 0), (-1, -1), 5),
]))
story += [
    table,
    Spacer(1, 6),
    bullets('Resize a window: hold Super (the Windows key) and drag with the middle mouse button, or press Alt+F8. '
            'Dragging the window edge does not work.',
            'The close button does not work in some dialogs: use the green check mark or the red cross at the '
            'bottom, or Esc.',
            'SpaceMouse: works through spacenavd, no 3Dconnexion driver needed. Axis directions and speeds are in '
            'the registry under ' + c('HKCU\\Software\\Wine\\TDxNavLib') + ' (' + c('AxisSigns') + ', '
            + c('AxisMap') + ', ' + c('TranslationSpeed') + ', ' + c('RotationSpeed') + ').',
            'Numbers and units follow the desktop\'s <i>Formats</i>: Dutch formats give a decimal comma and mm. '
            'To change them: ' + c('regedit') + ', ' + c('HKCU\\Control Panel\\International') + ' ('
            + c('sDecimal') + ', ' + c('iMeasure') + ' 0 = metric).',
            'Ubuntu: do not install the package <b>fuse</b>, it removes parts of the desktop. What AppImages need is '
            'already there.'),

    Paragraph('7. If something goes wrong', h2),
    bullets('Logs: ' + c('~/.local/share/topsolinux/install.log') + ' (installation) and '
            + c('topsolid.log') + ' (TopSolid) in the same folder.',
            '<i>Unable to connect to the PDM server</i> right after starting: wait a minute, the PDM is still '
            'starting. If it stays, run the ' + c('stop') + ' command and start again.',
            'Do not run two TopSolid installations at the same time: they use the same ports.',
            'Backup: copy ' + c('~/.local/share/topsolinux') + ' while TopSolid is closed. Your PDM projects are '
            'in it. Or package your projects in TopSolid.',
            'Newer TopSo\'Linux: start the new installer and choose <i>Update the AppImage</i>. Your installation '
            'and projects stay. Starting over: choose <i>Replace</i>; your PDM projects are lost then.'),

    Paragraph('How this was made', h2),
    Paragraph('Completely vibe coded: the Wine changes, the installer and this guide were written by Claude Opus 5.5 '
              '(Anthropic), directed and tested by a TopSolid user who wanted TopSolid on a Linux desktop.', body),
]

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=15 * mm,
                        bottomMargin=18 * mm, title=TITLE, author='', subject='', creator='', producer='')
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
