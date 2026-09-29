# Notices

## Trademarks

TopSolid is a trademark of TOPSOLID SAS. SQL Server, .NET and Windows are trademarks of Microsoft.
topsolinux is an independent, unofficial project. It is not affiliated with, endorsed by or supported
by TOPSOLID SAS or Microsoft.

## What topsolinux does and does not contain

The installer contains **no** TopSolid, SQL Server or .NET files. TopSolid, SQL Server Express and the
Sentinel license server are installed from the user's own TopSolid installation media, under the license
agreements the user accepts in TopSolid's own setup. The .NET Framework and Visual C++ runtimes are
downloaded from Microsoft by winetricks during the installation.

A TopSolid AppImage made by the installer (the "build an AppImage" option) **does** contain TopSolid,
SQL Server Express and the Microsoft runtimes. It is meant for computers you are licensed to use it on.
Do not publish it.

## Bundled third-party software

| Component | License | Source |
|-----------|---------|--------|
| Wine, with the patches in `wine/patches` | LGPL 2.1 or later | https://gitlab.winehq.org/wine/wine at the commit in `wine/UPSTREAM_COMMIT`, plus `wine/patches` (build with `wine/build-wine.sh`) |
| winetricks | LGPL 2.1 or later | https://github.com/Winetricks/winetricks |
| Samba `ntlm_auth` and the libraries it needs | GPL 3 (Samba) and the licenses of the libraries | Ubuntu source packages, versions listed in `bundled-versions.txt` inside the installer (`usr/share/doc/topsolinux`), available from https://launchpad.net/ubuntu/+source/samba |
| cabextract, libmspack | GPL 3, LGPL 2.1 | https://www.cabextract.org.uk/ |
| appimagetool, AppImage type 2 runtime | MIT | https://github.com/AppImage |

On request, the exact source code of every bundled GPL or LGPL component in a released installer is
provided for three years after that release (open an issue on the project page).
