# Shared by the installer and the TopSolid AppImage (sourced)
#
# With the kernel's ntsync driver, Wine waits on events, mutexes and semaphores in the kernel instead of
# asking the wineserver, which does all its work in one thread for every Wine program (TopSolid, SQL Server,
# the PDM). Distributions such as Ubuntu build it as a module without loading it. Wine uses it from the
# next start of the wineserver.

NTSYNC_LOAD="echo ntsync > /etc/modules-load.d/ntsync.conf && modprobe ntsync"

# on, off (a module that isn't loaded) or none (not in this kernel)
ntsync_state()
{
    if [ -r /dev/ntsync ]; then echo on
    elif grep -qs '/ntsync\.ko' "/lib/modules/$(uname -r)/modules.dep"; then echo off
    else echo none
    fi
}

# load it now and at every boot; asks for the password
ntsync_load() { pkexec sh -c "$NTSYNC_LOAD" && [ -r /dev/ntsync ]; }
