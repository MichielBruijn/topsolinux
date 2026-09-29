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
TITLE = 'topsolinux: TopSolid on Linux'

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


def c(text):
    return f'<font face="Courier">{text}</font>'


def bullets(*items):
    return ListFlowable([ListItem(Paragraph(i, body), leftIndent=12) for i in items],
                        bulletType='bullet', start='•', leftIndent=12, bulletFontSize=9)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#777777'))
    canvas.drawString(20 * mm, 12 * mm, 'topsolinux · unofficial, not affiliated with TOPSOLID SAS')
    canvas.drawRightString(190 * mm, 12 * mm, f'page {doc.page}')
    canvas.restoreState()


APP = 'TopSolid-7.20-x86_64.AppImage'
story = [
    Paragraph(TITLE, h1),
    Paragraph('Short guide to installing and using TopSolid 7 with its local PDM under Linux', sub),
    Paragraph('topsolinux is a patched Wine plus an installer that sets up TopSolid from <b>your own</b> '
              'TopSolid installation media: TopSolid, SQL Server Express with the local PDM server, the '
              'Sentinel license server and TopSolid\'Update. Nothing from Windows has to be installed.', body),
    Paragraph('topsolinux is unofficial and not affiliated with or supported by TOPSOLID SAS. You need your own '
              'TopSolid installation media and license.', note),

    Paragraph('1. What you need', h2),
    bullets('Ubuntu 24.04 or newer, or another 64-bit distribution with glibc 2.38 or newer.',
            'The TopSolid installation media (the folder with ' + c('Setup.exe') + '), or let the installer '
            'download it from TopSolid\'s server (19 GB).',
            'A TopSolid license file (' + c('lservrc') + '), can also be added later.',
            'About 45 GB of free disk space and an internet connection (for Microsoft\'s .NET runtimes).',
            'A GPU with a working OpenGL driver. Laptops with NVIDIA and Intel/AMD graphics use the NVIDIA GPU '
            'automatically.',
            'For a SpaceMouse: ' + c('sudo apt install spacenavd') + '.'),
    Paragraph('Do not install the package <b>fuse</b> on Ubuntu: it removes parts of the desktop. What AppImages '
              'need (fuse3) is already there.', note),

    Paragraph('2. Installing', h2),
    bullets('Make ' + c('topsolinux-installer-x86_64.AppImage') + ' executable (file properties, or '
            + c('chmod +x') + ') and start it.',
            'Choose the installation media (found automatically in Downloads) or the download from TopSolid\'s '
            'server, your license file (or skip it for the evaluation mode), '
            'and whether to also build a TopSolid AppImage (on by default).',
            'TopSolid\'s own installer opens: choose your modules, click Install and accept the license agreement. '
            'The automatic installation of SQL Server fails under Wine: click <b>Cancel</b>, then OK, close the log '
            'window and click Close. topsolinux installs and repairs SQL Server itself.',
            'For a SpaceMouse, tick <i>SpaceMouse support</i>: it installs spacenavd and asks for your password.',
            'Wait: the whole installation takes 30 to 60 minutes. If it is interrupted, start the installer again '
            'and it continues where it stopped.'),
    Paragraph('Everything is installed in ' + c('~/.local/share/topsolinux') + '.', body),

    Paragraph('3. The TopSolid AppImage', h2),
    Paragraph('With the AppImage option you get ' + c(APP) + ', a complete, self-contained TopSolid.', body),
    bullets('Install <b>Gear Lever</b> (Software app or Flathub), open the AppImage with it and choose <i>Unlock</i> '
            'and <i>Move to the app menu</i>. TopSolid is then in your application menu.',
            'On this computer the AppImage uses the existing installation. On another computer the first start '
            'copies the installation to ' + c('~/.local/share/topsolinux') + ', which takes a few minutes; each '
            'user adds their own license.',
            'Only use it on computers you are licensed for, and do not publish it: it contains TopSolid, SQL Server '
            'Express and Microsoft\'s runtimes.'),
    Paragraph('Without the AppImage option the installer adds TopSolid to the application menu directly. Right-click '
              'the menu entry for TopSolid\'Update, the license tool and <i>Stop background services</i>.', body),

    Paragraph('4. First start', h2),
    bullets('License question: answer it as you would on Windows.',
            'PDM connection: choose the local PDM server and leave user and password empty.',
            'Libraries: import the ones you need from TopSolid.',
            'New Project: enter a name, choose Blank Template and click the green check mark.'),
    Paragraph('SQL Server, the local PDM and the license server start by themselves and stop again when you close '
              'TopSolid. The very first start of the PDM can take a few minutes; a small window shows it is starting.',
              body),

    Paragraph('5. Updates', h2),
    Paragraph('TopSolid reports new service packs itself. After <i>Download now</i> the window disappears: the '
              'download runs invisibly in the background. A little later TopSolid asks to install it, and restarts '
              'by itself afterwards.', body),

    Paragraph('6. Useful commands and tips', h2),
    Paragraph('The AppImage (or ' + c('~/.local/share/topsolinux/runtime/AppRun') + ' without it) accepts a command:',
              body),
]

table = Table([
    [c(f'{APP} scale 150'), 'bigger text and icons (100 = normal), from the next start'],
    [c(f'{APP} update'), 'start TopSolid\'Update'],
    [c(f'{APP} license FILE'), 'install a license file'],
    [c(f'{APP} stop'), 'stop SQL Server, the PDM and the license server'],
    [c(f'{APP} regedit'), 'Wine\'s registry editor'],
], colWidths=[82 * mm, 88 * mm])
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
            + c('AxisMap') + ', ' + c('TranslationSpeed') + ', ' + c('RotationSpeed') + ').'),

    Paragraph('7. If something goes wrong', h2),
    bullets('Logs: ' + c('~/.local/share/topsolinux/install.log') + ' (installation) and '
            + c('topsolid.log') + ' (TopSolid) in the same folder.',
            '<i>Unable to connect to the PDM server</i> right after starting: wait a minute, the PDM is still '
            'starting. If it stays, run the ' + c('stop') + ' command and start again.',
            'Connecting to another PDM server (the Connection dialog) can hang under Wine: the green check mark '
            'stays grey. The helper that prevents this only runs until the first connection is saved.',
            'Backup: copy ' + c('~/.local/share/topsolinux') + ' while TopSolid is closed. Your PDM projects are '
            'in it.',
            'Starting over: remove that folder and install again. Your PDM projects are lost then.'),

    Paragraph('Credits', h2),
    Paragraph('The Wine changes, the installer and this guide were made with Claude (Anthropic).', body),
]

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                        bottomMargin=20 * mm, title=TITLE, author='', subject='', creator='', producer='')
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
