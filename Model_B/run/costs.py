"""Discrete pipe choices and the user-approved Clark Equation (5) cost budget."""
import math
import numpy as np
from swmm_io import Inp, parse_model, model_units, catalogue, require, num


def barrels(pipe):
    return float(pipe['xs'][6]) if len(pipe['xs']) > 6 else 1.0


def rate(diameter_ft):
    """USD/ft; diameter must enter Clark's equation in INCHES."""
    require(math.isfinite(diameter_ft) and diameter_ft > 0, 'Invalid diameter')
    return 11.7 + .51 * (12 * diameter_ft) ** 1.38


def replacement(pipe, diameter_ft):
    require(diameter_ft >= pipe['diameter'] - 1e-9, 'Downsizing is prohibited')
    if abs(diameter_ft - pipe['diameter']) <= 1e-9:
        return 0.0
    return pipe['length'] * barrels(pipe) * rate(diameter_ft)


def volume(pipes):
    return math.fsum(math.pi / 4 * p['length'] * barrels(p) * p['diameter'] ** 2 for p in pipes.values())


class CostDesign:
    def __init__(self, original_text, reference_text, cfg):
        self.text = original_text
        self.inp = Inp(original_text)
        self.nodes, self.pipes = parse_model(self.inp)
        self.flow, self.unit = model_units(self.inp)
        require(self.unit == 'ft', 'This release uses the supplied CFS/ft model')
        reference = Inp(reference_text)
        _, cp = parse_model(reference)
        require(model_units(reference) == (self.flow, self.unit), 'Reference units differ')
        require(set(cp) == set(self.pipes), 'Reference pipe IDs differ')
        for key, p in self.pipes.items():
            require(p['length'] == cp[key]['length'] and barrels(p) == barrels(cp[key]), 'Reference length/barrel mismatch')
            require(cp[key]['diameter'] >= p['diameter'] - 1e-9, 'Reference downsizes a pipe')
        self.base_volume, self.c_volume = volume(self.pipes), volume(cp)
        self.reference_cost = math.fsum(replacement(p, cp[k]['diameter']) for k, p in self.pipes.items())
        self.budget = float(cfg['replacement_budget_usd'])
        require(math.isfinite(self.budget) and self.budget > 0, 'Invalid cost budget')
        self.max_count = int(cfg['max_enlarged_pipes'])
        require(0 < self.max_count <= len(self.pipes), 'Invalid pipe-count limit')
        self.ids = list(self.pipes)
        self.choices, self.volumes, self.costs, self.audit = [], [], [], []
        sizes = catalogue({'catalogue_mode': 'physical_mm'}, self.unit)
        for key in self.ids:
            p = self.pipes[key]
            ceilings = [float(self.nodes[n]['row'][2]) - off for n, off in
                        [(p['u'], p['oi']), (p['v'], p['oo'])] if self.nodes[n]['kind'] == 'junction']
            clearance = min(ceilings) if ceilings else math.inf
            require(p['diameter'] <= clearance + 1e-8, 'Baseline exceeds fixed junction depth')
            choices = [p['diameter']] + [s for s in sizes if s > p['diameter'] + 1e-9 and s <= clearance + 1e-9]
            choices = [s for s in choices if replacement(p, s) <= self.budget + 1e-8]
            factor = math.pi / 4 * p['length'] * barrels(p)
            self.choices.append(np.asarray(choices))
            self.costs.append(np.asarray([replacement(p, s) for s in choices]))
            self.volumes.append(np.asarray([factor * (s * s - p['diameter'] ** 2) for s in choices]))
            self.audit.append({'Link': key, 'OriginalDiameter_ft': p['diameter'],
                'MaximumDiameterWithoutRimChange_ft': clearance,
                'AllowableDiameters_ft': ';'.join(num(s) for s in choices),
                'ReplacementCosts_USD': ';'.join(num(replacement(p, s)) for s in choices),
                'EnlargementOptions': len(choices) - 1})
        self.upper = np.asarray([len(v) - 1 for v in self.choices], dtype=int)
        require(np.any(self.upper > 0), 'No enlargement choices')

    def cost(self, x):
        return math.fsum(self.costs[i][int(v)] for i, v in enumerate(x))

    def added_volume(self, x):
        return math.fsum(self.volumes[i][int(v)] for i, v in enumerate(x))

    def repair(self, x):
        x = np.clip(np.rint(x).astype(int), 0, self.upper)
        active = np.flatnonzero(x)
        if len(active) > self.max_count:
            x[np.random.choice(active, len(active) - self.max_count, replace=False)] = 0
        while self.cost(x) > self.budget + 1e-8:
            x[int(np.random.choice(np.flatnonzero(x)))] -= 1
        return x

    def render(self, x):
        x = np.asarray(x, dtype=int)
        require(len(x) == len(self.ids) and np.all(x >= 0) and np.all(x <= self.upper), 'Invalid choice indices')
        require(np.count_nonzero(x) <= self.max_count, 'Pipe-count limit exceeded')
        require(self.cost(x) <= self.budget + 1e-8, 'Cost budget exceeded')
        inp = Inp(self.text)
        updates = {}
        for i, key in enumerate(self.ids):
            if x[i]:
                row = self.pipes[key]['xs'][:]
                row[2] = num(self.choices[i][x[i]])
                updates[key] = row
        inp.patch('[XSECTIONS]', updates)
        text = inp.text()
        self.verify(text)
        return text

    def verify(self, text):
        obj = Inp(text)
        require(set(obj.blocks) == set(self.inp.blocks), 'Section set changed')
        for section in self.inp.blocks:
            if section != '[XSECTIONS]':
                require(obj.blocks[section] == self.inp.blocks[section], f'Non-diameter change: {section}')
        xs = obj.rows('[XSECTIONS]')
        require(set(xs) == set(self.pipes), 'Pipe IDs changed')
        costs, extra, count, extrapolated = [], [], 0, 0
        for i, key in enumerate(self.ids):
            p, row = self.pipes[key], xs[key]
            require(p['xs'][:2] + p['xs'][3:] == row[:2] + row[3:], 'Other cross-section field changed')
            d = float(row[2])
            require(min(abs(d - choice) for choice in self.choices[i]) < 1e-8, 'Unapproved diameter')
            costs.append(replacement(p, d))
            extra.append(math.pi / 4 * p['length'] * barrels(p) * (d * d - p['diameter'] ** 2))
            changed = d > p['diameter'] + 1e-9
            count += int(changed)
            extrapolated += int(changed and not (12 <= 12 * d <= 54))
        total = math.fsum(costs)
        require(count <= self.max_count, 'Exported pipe count exceeded')
        require(total <= self.budget + 1e-5, 'Exported cost exceeded')
        return {'only_diameters_changed': True, 'enlarged_pipes': count,
                'replacement_cost_usd': total, 'budget_usd': self.budget,
                'added_volume_ft3': math.fsum(extra), 'added_volume_m3': math.fsum(extra) * .3048 ** 3,
                'extrapolated_replacements': extrapolated}
