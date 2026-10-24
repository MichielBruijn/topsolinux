#!/usr/bin/env python3
"""The newest TopSo'Linux release on GitHub.

latest            print the version, then the URLs of the installer and of SHA256SUMS, one per line
mcp-latest        the same for the TopSolid MCP server (github.com/Julien38300/topsolid-automation-mcp)
download URL FILE download to FILE, printing the percentage done per line (for zenity --progress)
unzip ZIP DIR     unpack a zip made on Windows (backslashes as separators, folders without permissions)

The version comes from where releases/latest redirects to, not from GitHub's API and its rate limit.
"""
import os
import shutil
import sys
import urllib.request
import zipfile

REPO = 'MichielBruijn/topsolinux'
MCP_REPO = 'Julien38300/topsolid-automation-mcp'


def get(url, method='GET'):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={'User-Agent': 'topsolinux'}, method=method), timeout=20)


def latest_tag(repo):
    with get(f'https://github.com/{repo}/releases/latest', 'HEAD') as r:
        tag = r.geturl().rstrip('/').rsplit('/', 1)[-1]
    if not tag.startswith('v'):
        sys.exit(f'no release found ({r.geturl()})')
    return tag, f'https://github.com/{repo}/releases/download/{tag}/'


def latest():
    tag, base = latest_tag(REPO)
    print(tag[1:], f'{base}TopSoLinux-Installer-{tag[1:]}-x86_64.AppImage', f'{base}SHA256SUMS', sep='\n')


def mcp_latest():
    tag, base = latest_tag(MCP_REPO)
    print(tag[1:], f'{base}TopSolidMcpServer-{tag}.zip', f'{base}SHA256SUMS.txt', sep='\n')


def download(url, path):
    with get(url) as r, open(path + '.part', 'wb') as f:
        size, done, shown = int(r.headers.get('Content-Length') or 0), 0, -1
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if size and done * 100 // size != shown:
                shown = done * 100 // size
                print(min(shown, 99), flush=True)  # 100 closes the progress dialog
    os.replace(path + '.part', path)
    print(100, flush=True)


def unzip(path, dest):
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            name = info.filename.replace('\\', '/')
            parts = [p for p in name.split('/') if p not in ('', '.')]
            if not parts or '..' in parts:
                continue
            target = os.path.join(dest, *parts)
            if name.endswith('/'):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, 'wb') as f:
                shutil.copyfileobj(src, f)


if __name__ == '__main__':
    if sys.argv[1:2] == ['latest']:
        latest()
    elif sys.argv[1:2] == ['mcp-latest']:
        mcp_latest()
    elif sys.argv[1:2] == ['unzip'] and len(sys.argv) == 4:
        unzip(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ['download'] and len(sys.argv) == 4:
        download(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
