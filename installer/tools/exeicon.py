#!/usr/bin/env python3
"""Save the largest icon of a Windows executable as PNG.

usage: exeicon.py FILE.exe OUT.png
Only the standard library is used, so it runs on any system with python3.
"""
import struct
import sys
import zlib

RT_ICON, RT_GROUP_ICON = 3, 14


def read_resources(data):
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if data[pe:pe + 4] != b'PE\0\0':
        raise ValueError('not a PE file')
    nsect, optsize = struct.unpack_from('<H12xH', data, pe + 6)
    opt = pe + 24
    magic = struct.unpack_from('<H', data, opt)[0]
    rsrc_rva = struct.unpack_from('<I', data, opt + (112 if magic == 0x20b else 96) + 2 * 8)[0]
    sections = []
    for i in range(nsect):
        s = opt + optsize + 40 * i
        vsize, va, rawsize, raw = struct.unpack_from('<IIII', data, s + 8)
        sections.append((va, max(vsize, rawsize), raw))

    def offset(rva):
        for va, size, raw in sections:
            if va <= rva < va + size:
                return rva - va + raw
        raise ValueError('rva outside sections')

    base = offset(rsrc_rva)

    def entries(off):
        named, ids = struct.unpack_from('<12xHH', data, base + off)
        for i in range(named + ids):
            name, target = struct.unpack_from('<II', data, base + off + 16 + 8 * i)
            yield name, target

    res = {}
    for type_id, t in entries(0):
        if type_id not in (RT_ICON, RT_GROUP_ICON) or not t & 0x80000000:
            continue
        for name_id, n in entries(t & 0x7fffffff):
            for _, leaf in entries(n & 0x7fffffff):
                rva, size = struct.unpack_from('<II', data, base + leaf)
                res.setdefault(type_id, {})[name_id] = data[offset(rva):offset(rva) + size]
    return res


def dib_to_png(dib):
    hsize, width, height, _, bpp = struct.unpack_from('<IiiHH', dib, 0)
    height //= 2  # the mask is counted too
    if bpp != 32:
        raise ValueError('only 32-bit icons are supported')
    pixels = dib[hsize:hsize + width * height * 4]
    rows = []
    for y in range(height - 1, -1, -1):
        row = pixels[y * width * 4:(y + 1) * width * 4]
        rgba = bytearray(row)
        rgba[0::4], rgba[2::4] = row[2::4], row[0::4]
        rows.append(b'\0' + bytes(rgba))

    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body))

    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b''))


def main():
    data = open(sys.argv[1], 'rb').read()
    res = read_resources(data)
    best = None
    for group in res.get(RT_GROUP_ICON, {}).values():
        count = struct.unpack_from('<4xH', group)[0]
        for i in range(count):
            w, h, _, _, _, bpp, _, icon_id = struct.unpack_from('<BBBBHHIH', group, 6 + 14 * i)
            size = (w or 256, bpp)
            if icon_id in res.get(RT_ICON, {}) and (best is None or size > best[0]):
                best = (size, res[RT_ICON][icon_id])
    if best is None:
        sys.exit('no icon found')
    icon = best[1]
    png = icon if icon.startswith(b'\x89PNG') else dib_to_png(icon)
    open(sys.argv[2], 'wb').write(png)


if __name__ == '__main__':
    main()
