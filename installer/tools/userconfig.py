#!/usr/bin/env python3
"""Set a value in a TopSolid configuration file (Config.ConfigData.xml), creating folders as needed.

usage: userconfig.py FILE FOLDER/FOLDER/... NAME TYPE VALUE
       e.g. userconfig.py Config.ConfigData.xml TopSolid/Pdm/UI/Connections/ConnectionDialog \
            HasLocalPdmAlreadyStarted Bool True

The file keeps its byte order mark, XML declaration and line endings, so TopSolid reads it as before.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

EMPTY = ('<?xml version="1.0" encoding="utf-16"?>\n<ConfigData xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
         'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n  <Folders />\n</ConfigData>')


def main():
    path, folders, name, vtype, value = sys.argv[1:6]
    raw = open(path, 'rb').read() if os.path.exists(path) else b''
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig') if raw else EMPTY
    crlf = '\r\n' in text
    text = text.replace('\r\n', '\n')
    declaration, _, body = text.partition('\n') if text.startswith('<?xml') else ('', '', text)

    root_tag = re.search(r'<ConfigData\b[^>]*?/?>', body).group(0).rstrip('/>').rstrip() + '>'
    root = ET.fromstring(body)
    node = root.find('Folders')
    if node is None:
        node = ET.SubElement(root, 'Folders')
    for folder in folders.split('/'):
        child = next((f for f in node.findall('Folder') if f.get('name') == folder), None)
        if child is None:
            child = ET.SubElement(node, 'Folder', name=folder)
        node = child
    val = next((v for v in node.findall('Value') if v.get('name') == name), None)
    if val is None:
        val = ET.SubElement(node, 'Value', name=name)
    val.set('type', vtype)
    val.set('resettable', 'False')
    val.text = value

    ET.indent(root, space='  ')
    xml = re.sub(r'<ConfigData\b[^>]*>', root_tag, ET.tostring(root, encoding='unicode'), count=1)
    out = (declaration + '\n' if declaration else '') + xml + '\n'
    if crlf:
        out = out.replace('\n', '\r\n')
    data = out.encode('utf-8')
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write((b'\xef\xbb\xbf' if bom or not raw else b'') + data)
    os.replace(tmp, path)


if __name__ == '__main__':
    main()
