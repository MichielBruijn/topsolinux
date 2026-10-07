#!/usr/bin/env python3
"""The newest TopSo'Linux release on GitHub.

latest            print the version, then the URLs of the installer and of SHA256SUMS, one per line
download URL FILE download to FILE, printing the percentage done per line (for zenity --progress)
"""
import json
import os
import sys
import urllib.request

REPO = 'MichielBruijn/topsolinux'


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'topsolinux'}), timeout=20)


def latest():
    rel = json.load(get(f'https://api.github.com/repos/{REPO}/releases/latest'))
    urls = {a['name']: a['browser_download_url'] for a in rel['assets']}
    installer = next(u for n, u in urls.items() if n.startswith('TopSoLinux-Installer-') and n.endswith('.AppImage'))
    print(rel['tag_name'].lstrip('v'), installer, urls['SHA256SUMS'], sep='\n')


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


if __name__ == '__main__':
    if sys.argv[1:2] == ['latest']:
        latest()
    elif sys.argv[1:2] == ['download'] and len(sys.argv) == 4:
        download(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
