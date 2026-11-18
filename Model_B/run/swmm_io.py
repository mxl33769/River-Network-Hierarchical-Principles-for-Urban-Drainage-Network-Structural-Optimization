"""SWMM input/output and catalogue helpers; no routing algorithm."""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import heapq
import json
import math
from collections import defaultdict, deque
from pathlib import Path
TABLE_S3_MM = [150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1200, 1400, 1600, 2000]
EPS = 1e-08

def require(condition, message):
    if not condition:
        raise ValueError(message)

class Inp:
    """Preserve untouched lines/comments and only replace selected data records."""

    def __init__(self, text):
        self.blocks = {'': []}
        self.headers = {}
        section = ''
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('[') and stripped.endswith(']'):
                section = stripped.upper()
                require(section not in self.blocks, f'Duplicate section: {section}')
                self.blocks[section] = []
                self.headers[section] = line
            else:
                self.blocks[section].append(line)

    def rows(self, section):
        result = {}
        for line in self.blocks.get(section, []):
            tokens = line.split(';', 1)[0].split()
            if tokens:
                require(tokens[0] not in result, f'Duplicate ID in {section}: {tokens[0]}')
                result[tokens[0]] = tokens
        return result

    def patch(self, section, replacements=None, remove=()):
        replacements = dict(replacements or {})
        removed = set(remove)
        lines = []
        for line in self.blocks.get(section, []):
            tokens = line.split(';', 1)[0].split()
            if not tokens:
                lines.append(line)
            elif tokens[0] in removed:
                continue
            elif tokens[0] in replacements:
                suffix = ' ;' + line.split(';', 1)[1] if ';' in line else ''
                lines.append('  '.join(map(str, replacements.pop(tokens[0]))) + suffix)
            else:
                lines.append(line)
        lines.extend(('  '.join(map(str, row)) for row in replacements.values()))
        self.blocks[section] = lines
        self.headers.setdefault(section, section)

    def text(self):
        result = []
        for section, lines in self.blocks.items():
            if section:
                result.append(self.headers[section])
            result.extend(lines)
        return '\n'.join(result) + '\n'

def num(value):
    return format(float(value), '.12g')

def model_units(inp):
    options = inp.rows('[OPTIONS]')
    flow = options.get('FLOW_UNITS', ['', 'CFS'])[1].upper()
    require(flow in {'CFS', 'GPM', 'MGD', 'CMS', 'LPS', 'MLD'}, 'Unknown FLOW_UNITS')
    offsets = options.get('LINK_OFFSETS', ['', 'DEPTH'])[1].upper()
    require(offsets == 'DEPTH', 'This version requires LINK_OFFSETS DEPTH. It will not reinterpret absolute offsets.')
    return (flow, 'ft' if flow in {'CFS', 'GPM', 'MGD'} else 'm')

def catalogue(cfg, unit):
    mode = cfg.get('catalogue_mode', 'physical_mm')
    require(mode in {'physical_mm', 'legacy_numeric'}, 'Unknown catalogue_mode')
    divisor = 304.8 if unit == 'ft' and mode == 'physical_mm' else 1000.0
    return [x / divisor for x in TABLE_S3_MM]

def size_pipe(old, factor, sizes):
    require(old > 0 and math.isfinite(old), 'Diameter must be positive and finite')
    require(old <= sizes[-1] + EPS, f'Existing affected diameter {old} exceeds catalogue maximum {sizes[-1]}; refusing to shrink.')
    target = old * factor
    selected = next((s for s in sizes if s + EPS >= target), sizes[-1])
    return (max(old, selected), target > sizes[-1] + EPS)

def parse_model(inp):
    junctions = inp.rows('[JUNCTIONS]')
    outfalls = inp.rows('[OUTFALLS]')
    require(not set(junctions) & set(outfalls), 'Node appears as both junction and outfall')
    nodes = {}
    for node, row in junctions.items():
        row = row + ['0'] * max(0, 6 - len(row))
        inv, full = (float(row[1]), float(row[2]))
        require(math.isfinite(inv) and full > 0, f'Explicit positive MaxDepth required: {node}')
        nodes[node] = {'invert': inv, 'ground': inv + full, 'row': row, 'kind': 'junction'}
    for node, row in outfalls.items():
        nodes[node] = {'invert': float(row[1]), 'row': row, 'kind': 'outfall'}
    for section in ['[STORAGE]', '[DIVIDERS]', '[PUMPS]', '[ORIFICES]', '[WEIRS]', '[OUTLETS]']:
        require(not inp.rows(section), f'{section} is unsupported; use a conduit/junction/outfall model.')
    conduits = {}
    xs = inp.rows('[XSECTIONS]')
    for link, row in inp.rows('[CONDUITS]').items():
        row = row + ['0'] * max(0, 9 - len(row))
        require(row[1] in nodes and row[2] in nodes, f'Unknown end node: {link}')
        require(row[1] != row[2], f'Self-loop: {link}')
        length = float(row[3])
        require(math.isfinite(length) and length > 0, f'Invalid length: {link}')
        require(link in xs and xs[link][1].upper() == 'CIRCULAR', f'Circular section required: {link}')
        diameter = float(xs[link][2])
        require(math.isfinite(diameter) and diameter > 0, f'Invalid diameter: {link}')
        barrels = float(xs[link][6]) if len(xs[link]) > 6 else 1.0
        require(math.isfinite(barrels) and barrels >= 1 and barrels.is_integer(), f'Invalid barrel count: {link}')
        require(all((float(row[i]) >= 0 for i in (5, 6))), f'Negative depth offset: {link}')
        conduits[link] = {'row': row, 'u': row[1], 'v': row[2], 'length': length, 'oi': float(row[5]), 'oo': float(row[6]), 'diameter': float(xs[link][2]), 'xs': xs[link]}
    return (nodes, conduits)

def slope(nodes, pipe):
    return (nodes[pipe['u']]['invert'] + pipe['oi'] - (nodes[pipe['v']]['invert'] + pipe['oo'])) / pipe['length']

def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
