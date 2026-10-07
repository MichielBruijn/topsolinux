#!/bin/bash
# Samba's ntlm_auth with its libraries, taken from Ubuntu 24.04 in an LXD container, for build.sh.
# Taken from the build machine it needs that machine's glibc (2.43 on Ubuntu 26.04), while TopSo'Linux
# runs from glibc 2.38 on. Without ntlm_auth SQL Server refuses every login ("Cannot generate SSPI context").
#
# usage: ./ntlm-auth.sh   makes build/ntlm_auth (bin/ntlm_auth.real and lib/); build.sh calls it when missing
# Needs: LXD (snap lxd, user in group lxd)

set -euo pipefail
TOP="$(dirname "$(readlink -f "$0")")"
OUT="$TOP/build/ntlm_auth"
CT=topsolinux-noble

lxc info "$CT" >/dev/null 2>&1 || lxc launch ubuntu:24.04 "$CT"
lxc start "$CT" 2>/dev/null || true
for _ in $(seq 60); do
    lxc exec "$CT" -- sh -c 'getent hosts archive.ubuntu.com' >/dev/null 2>&1 && break
    sleep 2
done
lxc exec "$CT" -- sh -c 'command -v ntlm_auth >/dev/null ||
    { apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends winbind; }' >&2

rm -rf "$OUT"
mkdir -p "$OUT"
# the same libraries as build.sh's bundle(): everything except glibc itself
lxc exec "$CT" -- sh -c '
    set -e
    rm -rf /tmp/na && mkdir -p /tmp/na/bin /tmp/na/lib
    cp -L "$(command -v ntlm_auth)" /tmp/na/bin/ntlm_auth.real
    ldd "$(command -v ntlm_auth)" | awk "/=> \\// {print \$3}" | while read -r lib; do
        case "$(basename "$lib")" in
            libc.so*|libm.so*|libdl.so*|libpthread.so*|librt.so*|ld-linux*|libresolv.so*) ;;
            *) cp -L "$lib" /tmp/na/lib/ ;;
        esac
    done
    ntlm_auth --version > /tmp/na/VERSION
    # the packages, for NOTICE.md
    for f in "$(command -v ntlm_auth)" /tmp/na/lib/*; do dpkg -S "$(basename "$f")" | head -1 | cut -d: -f1; done |
        sort -u | xargs dpkg-query -W -f="\${Package} \${Version} (source: \${source:Package} \${source:Version})\n" \
        > /tmp/na/versions.txt
    tar -C /tmp/na -c .' | tar -C "$OUT" -x
echo "ntlm_auth $(cat "$OUT/VERSION") from Ubuntu 24.04 in $OUT"
