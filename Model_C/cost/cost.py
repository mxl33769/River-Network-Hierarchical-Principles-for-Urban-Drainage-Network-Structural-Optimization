"""Price A-to-C201 diameter changes using only in-range Clark equations.

Run: python cost.py --source C201.zip --out cost.json
The source is the unchanged C201 release, including pipes.csv, A.inp and C.inp.
An incomplete cost schedule cannot produce an optimization budget.
"""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile


def unit_cost(diameter_mm):
    """Return equation and $/ft rate, or (None, None) outside both ranges."""
    if not math.isfinite(diameter_mm) or diameter_mm <= 0:
        raise ValueError("Diameter must be positive and finite")
    inches = diameter_mm / 25.4
    if 304.8 <= diameter_mm <= 1371.6:
        return "Eq. 5", 11.7 + 0.51 * inches ** 1.38
    if 1524.0 <= diameter_mm <= 3657.6:
        return "Eq. 6", 7.9 + 1.30 * inches ** 1.25
    return None, None


def total_budget(rows):
    """Never treat a required but unpriced replacement as free."""
    if any(row["replacement_cost_usd"] is None for row in rows):
        return None
    return math.fsum(row["replacement_cost_usd"] for row in rows)


def parse_inp(text):
    sections = {}
    section = None
    for line in text.splitlines():
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line.upper()
            sections[section] = {}
        elif section:
            row = line.split()
            if section in {"[OPTIONS]", "[CONDUITS]", "[XSECTIONS]"}:
                if row[0] in sections[section]:
                    raise ValueError("Duplicate input identifier")
                sections[section][row[0]] = row
    if sections["[OPTIONS]"]["FLOW_UNITS"][1] != "CFS":
        raise ValueError("This audit expects the released CFS/ft models")
    return sections


def analyze(source):
    with ZipFile(source) as archive:
        required = ["pipes.csv", "A.inp", "C.inp"]
        blobs = {name: archive.read(name) for name in required}
    table = list(csv.DictReader(io.StringIO(blobs["pipes.csv"].decode("utf-8-sig"))))
    a = parse_inp(blobs["A.inp"].decode("utf-8-sig"))
    c = parse_inp(blobs["C.inp"].decode("utf-8-sig"))
    ids = [r["Pipe"] for r in table]
    if len(ids) != len(set(ids)) or set(ids) != set(a["[CONDUITS]"]) or set(ids) != set(c["[CONDUITS]"]):
        raise ValueError("Pipe IDs in table and models do not agree")
    changed = []
    for row in table:
        pipe_id = row["Pipe"]
        old_mm, new_mm, length_ft, barrels = [float(row[k]) for k in
            ("A_mm", "NewC_mm", "Length_ft", "Barrels")]
        if not all(math.isfinite(x) and x > 0 for x in (old_mm, new_mm, length_ft, barrels)):
            raise ValueError(f"Invalid geometry: {pipe_id}")
        if not barrels.is_integer():
            raise ValueError("Barrel count must be integral")
        for model, diameter in ((a, old_mm), (c, new_mm)):
            xs = model["[XSECTIONS]"][pipe_id]
            conduit = model["[CONDUITS]"][pipe_id]
            model_barrels = float(xs[6]) if len(xs) > 6 else 1.0
            if xs[1] != "CIRCULAR" or not math.isclose(float(xs[2]) * 304.8, diameter, abs_tol=1e-6):
                raise ValueError(f"Table/model diameter mismatch: {pipe_id}")
            if not math.isclose(float(conduit[3]), length_ft, abs_tol=1e-8) or model_barrels != barrels:
                raise ValueError(f"Table/model length or barrels mismatch: {pipe_id}")
        if math.isclose(old_mm, new_mm, abs_tol=1e-6):
            continue
        if new_mm < old_mm:
            raise ValueError(f"Unexpected downsizing: {pipe_id}")
        equation, rate = unit_cost(new_mm)
        changed.append({
            "pipe_id": pipe_id, "old_mm": old_mm, "new_mm": new_mm,
            "length_ft": length_ft, "barrels": int(barrels),
            "new_inches": new_mm / 25.4, "equation": equation,
            "unit_cost_usd_per_ft": rate,
            "replacement_cost_usd": None if rate is None else length_ft * barrels * rate,
            "status": "unpriced" if rate is None else "priced",
        })
    changed.sort(key=lambda r: (r["new_mm"], int(r["pipe_id"])))
    groups = []
    for diameter in sorted({row["new_mm"] for row in changed}):
        group = [r for r in changed if r["new_mm"] == diameter]
        equation, rate = unit_cost(diameter)
        groups.append({"new_mm": diameter, "pipes": len(group),
            "length_ft": math.fsum(r["length_ft"] * r["barrels"] for r in group),
            "equation": equation, "unit_cost_usd_per_ft": rate,
            "subtotal_usd": total_budget(group)})
    result = {
        "source": "C201.zip: pipes.csv, A_mm to NewC_mm; verified against A.inp and C.inp",
        "sha256": {name: hashlib.sha256(blob).hexdigest() for name, blob in blobs.items()},
        "scope": "Only diameter-changed pipes, relative to A; full new-pipe component cost",
        "price_basis_year": 1997,
        "source_article": "Clark et al. (2002), Table 2 and Use of Indices",
        "doi": "10.1061/(ASCE)0733-9496(2002)128:5(312)",
        "equation_input_unit": "inches", "unit_cost_unit": "USD/ft",
        "extrapolation_allowed": False,
        "material_assumption": "Diameter-based choice of the supplied product equation, not verified installed material",
        "total_pipes_checked": len(table), "changed_pipes": len(changed),
        "priced_pipes": sum(r["status"] == "priced" for r in changed),
        "unpriced_pipes": sum(r["status"] == "unpriced" for r in changed),
        "priced_subtotal_usd": math.fsum(r["replacement_cost_usd"] for r in changed if r["status"] == "priced"),
        "total_replacement_budget_usd": total_budget(changed),
        "optimization_started": False,
        "optimization_blocker": "Unit costs missing for changed diameters outside both published ranges",
        "groups": groups, "pipes": changed,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("cost.json"))
    args = parser.parse_args()
    result = analyze(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"pipes", "sha256"}}, indent=2))


if __name__ == "__main__":
    main()
