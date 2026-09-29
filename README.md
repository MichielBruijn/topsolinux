# TopSo'Linux

Run **TopSolid 7** on Linux, including the local PDM server, with one installer.

topsolinux is a patched [Wine](https://www.winehq.org) plus an installer that sets up TopSolid from
TopSolid's installation media, **your own** copy or downloaded from TopSolid's own server. It takes care of everything that doesn't work out of the box
under Wine: .NET, SQL Server Express, the local PDM server, the license server and a few Wine bugs.

> topsolinux is an unofficial project. It is not affiliated with or supported by TOPSOLID SAS.
> You need a TopSolid license (or use TopSolid's evaluation mode).

Tested with TopSolid 7.20 (media 7.20.400.0 RTM, updated to SP6 with TopSolid'Update) on Ubuntu 24.04.

## What you need

- A 64-bit Linux with glibc 2.38 or newer: Ubuntu 24.04 or newer, Debian 13, Fedora 39 or newer, ...
- The TopSolid installation media (the folder with `Setup.exe`), or let the installer download it
  from TopSolid's server (19 GB)
- A TopSolid license file (`lservrc`), can also be added later
- About 45 GB of free disk space (65 GB when downloading the media), and an internet connection during the installation
- A GPU with a working OpenGL driver (NVIDIA, AMD or Intel)

## Installing

1. Download `TopSoLinux-Installer-1.0-x86_64.AppImage` from the
   [releases](../../releases).
2. Make it executable (file properties, or `chmod +x TopSoLinux-Installer-1.0-x86_64.AppImage`) and start it.
3. Follow the steps:
   - use the installation media found on your computer, choose another folder, or let the installer
     download TopSolid from TopSolid's own server (the one `TopSolid.Downloader.exe` uses),
   - options: add TopSolid to the app menu with [Gear Lever](https://flathub.org/apps/it.mijorus.gearlever)
     (recommended, on by default; Flatpak and Gear Lever are installed when missing) and SpaceMouse support.
4. TopSolid's own installer opens. Choose your modules (keep *Sentinel RMS License Manager* on the Server
   tab; *Sentinel Protection Installer* and *TopSolid'Viewer* are not needed), click Install and accept the
   license agreement. SQL Server's installation fails under Wine: click Cancel (or OK and then Cancel/OK on
   its errors) and Close. TopSo'Linux installs and sets up SQL Server itself afterwards.
5. Wait. The whole installation takes 30 to 60 minutes.

The result is always a TopSolid AppImage (`TopSolid-7.20-x86_64.AppImage`). With Gear Lever it is in your app
menu; without, the installer asks where to save it.

Without a desktop, or to script it:

```
./TopSoLinux-Installer-1.0-x86_64.AppImage install --media ~/Downloads/7.20.400.0_RTM \
    [--replace] [--gearlever | --appimage-dir ~/Applications] [--spacemouse]
./TopSoLinux-Installer-1.0-x86_64.AppImage install --download ~/Downloads/TopSolid   # download the media first
```

An interrupted installation continues where it stopped when you start the installer again; an existing
installation can be replaced.
Everything is installed in `~/.local/share/topsolinux` (set `TOPSOLINUX_HOME` to use another folder).

### The TopSolid AppImage

With the AppImage option you get `TopSolid-7.20-x86_64.AppImage`: a complete, self-contained TopSolid.
Open it with [Gear Lever](https://flathub.org/apps/it.mijorus.gearlever) to get a menu entry, or just
double-click it. On another computer it installs itself on the first start; each user adds their own
license. Only use it on computers you are licensed for, and **do not publish it**: it contains TopSolid,
SQL Server Express and Microsoft's runtimes.

Without the AppImage option, the installer adds TopSolid to your application menu directly.

## First start

TopSolid asks for the PDM connection: choose the local PDM server and log in as `admin` (no password).
Then add the libraries you need from TopSolid. The first start of the local PDM can take a few minutes;
a small window shows that it is starting.

## Everyday use

The menu entry (right-click it) and the AppImage (or `~/.local/share/topsolinux/runtime/AppRun`) accept:

| Command | |
|---|---|
| *(none)* | start TopSolid |
| `update` | start TopSolid'Update (service packs) |
| `license FILE` | install a license file |
| `license-tool` | TopSolid's license tool |
| `scale 150` | make text and icons 150% bigger (100 = normal), kept until changed |
| `stop` | stop SQL Server, the PDM and the license server |
| `winecfg`, `regedit`, `shell` | Wine tools, for troubleshooting |

Environment variables: `TOPSOLID_SCALE=150` (same as `scale`), `TOPSOLID_GPU=nvidia|default`
(laptops with NVIDIA and Intel/AMD graphics use the NVIDIA GPU automatically).

Resize a window: hold Super and drag with the middle mouse button, or press Alt+F8.

### SpaceMouse

Install and start [spacenavd](https://spacenav.sourceforge.net) (`sudo apt install spacenavd`).
topsolinux includes a replacement for 3Dconnexion's navigation library that talks to spacenavd, so no
3Dconnexion driver is needed. Axis directions and speeds are in the registry
(`regedit`, `HKEY_CURRENT_USER\Software\Wine\TDxNavLib`): `AxisSigns`, `AxisMap`, `TranslationSpeed`,
`RotationSpeed`.

## Troubleshooting

- **Virtual machines:** TopSolid's 30-day evaluation mode does not start in a virtual machine
  ("UNLICENSED", protection key "Unavailable"): its license protection refuses virtual machines.
  With a real license it works. Without a GPU, TopSolid switches off graphics acceleration.

- Logs: `~/.local/share/topsolinux/install.log` (installation) and `topsolid.log` (TopSolid).
- "Unable to connect to the PDM server" right after starting: wait a minute, the PDM is still starting.
  If it stays, run the `stop` command and start again.
- Everything hangs: `stop` stops all background services.

## How it works

The installer:

1. creates a Wine environment and installs fonts, Visual C++ 2019, .NET 4.8 and .NET 3.5 with winetricks,
2. runs TopSolid's own `Setup.exe` from your media,
3. installs SQL Server Express from your media without the Windows Update check that fails under Wine,
   and the license server and TopSolid'Update if the setup skipped them,
4. finishes SQL Server's configuration (its setup still fails at the very end under Wine: registry,
   system databases, file locations, a login for the Windows administrators group, TCP port 14330),
5. performs the first start of the local PDM server (it only starts the first time while TopSolid's
   PDM server admin tool is running),
6. installs your license and makes the menu entry or AppImage.

On the first start, a small helper keeps TopSolid's PDM "Connection" dialog from hanging
(`installer/tools/unstick.c` explains why).

Wine needed 49 changes for TopSolid, from COM security and NTLM authentication for SQL Server to
certificate handling, services, tooltips and a thread leak. They are in `wine/patches`, on top of the
upstream commit in `wine/UPSTREAM_COMMIT`.

## Building

```
wine/build-wine.sh build/wine-dist     # patched Wine (needs Wine's build dependencies and MinGW)
./build.sh build/wine-dist             # the installer AppImage
```

`build.sh` also needs `ntlm_auth` (package `winbind`), `cabextract`, `winetricks` and `curl`, and
bundles the first three.

## Guide

A two-page user guide: [docs/topsolinux-guide.pdf](docs/topsolinux-guide.pdf).

## License

The topsolinux scripts and tools: MIT. The Wine patches: LGPL 2.1 or later, like Wine.
See [NOTICE.md](NOTICE.md) for trademarks and bundled software.

## Credits

Made with Claude (Anthropic).
