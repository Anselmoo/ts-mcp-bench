"""The `out_of_scope` task class: how one task of the class is drawn (called by tsbench.tasks.generate)."""
from __future__ import annotations

from tsbench.tasks.common import group_thousands, record, round_to_10

CT_TEMPLATES = (
    dict(name="permanganate (MnO₄⁻)", bands=(18300, 32200, 39800), eps=(2400, 1800, 2900)),
    dict(name="chromate (CrO₄²⁻)", bands=(26700, 36500, 45500), eps=(1700, 3600, 8000)),
    dict(name="vanadate (VO₄³⁻)", bands=(37000, 44500, 50500), eps=(2600, 5200, 9000)),
)


JT_TEMPLATES = (
    dict(label="six-coordinate Cu(II) (d9) aqua complex", d=9, top=12600, shoulder=10700, eps=10),
    dict(label="six-coordinate Cu(II) (d9) ammine complex with two axial water ligands", d=9, top=15300,
         shoulder=12900, eps=50),
    dict(label="octahedral high-spin Mn(III) (d4) aqua complex", d=4, top=21000, shoulder=18200, eps=30),
    dict(label="octahedral high-spin Cr(II) (d4) aqua complex", d=4, top=14100, shoulder=10800, eps=5),
)


def make_charge_transfer(rng, template) -> dict:
    f = 1 + rng.uniform(-0.04, 0.04, size=3)
    bands = sorted(round_to_10(b * x) for b, x in zip(template["bands"], f, strict=False))
    eps = [int(round(e * (1 + rng.uniform(-0.2, 0.2)), -1)) for e in template["eps"]]
    prompt = (f"An aqueous solution of {template['name']} shows intense absorption bands at "
              f"{group_thousands(bands[0])} (ε ≈ {group_thousands(eps[0])} M⁻¹ cm⁻¹), "
              f"{group_thousands(bands[1])} (ε ≈ {group_thousands(eps[1])} M⁻¹ cm⁻¹) and "
              f"{group_thousands(bands[2])} cm⁻¹ (ε ≈ {group_thousands(eps[2])} M⁻¹ cm⁻¹). "
              "Determine the ligand-field splitting "
              "parameter Dq and the Racah parameter B (in cm⁻¹) of the central "
              "metal ion.")
    return record(cls="out_of_scope", subtype="charge_transfer", d_count=None, geometry=None, system=None, bands=bands,
                  prompt=prompt, required=[], reference={}, oracle="none", expect_oos=True)


def make_jahn_teller(rng, template) -> dict:
    top = round_to_10(template["top"] * (1 + rng.uniform(-0.04, 0.04)))
    shoulder = round_to_10(top * (template["shoulder"] / template["top"]) * (1 + rng.uniform(-0.03, 0.03)))
    eps = int(round(template["eps"] * (1 + rng.uniform(-0.2, 0.2)), 0))
    bands = sorted([top, shoulder])
    prompt = (f"A {template['label']} shows a single broad, asymmetric absorption band with its maximum at "
              f"{group_thousands(top)} cm⁻¹ and a shoulder near {group_thousands(shoulder)} cm⁻¹ "
              f"(ε ≈ {eps} M⁻¹ cm⁻¹). Determine the ligand-field "
              "splitting parameter Dq and the Racah parameter B (in cm⁻¹).")
    return record(cls="out_of_scope", subtype="jahn_teller", d_count=template["d"], geometry="Oh", system=None,
                  bands=bands, prompt=prompt, required=[], reference={}, oracle="none", expect_oos=True)
