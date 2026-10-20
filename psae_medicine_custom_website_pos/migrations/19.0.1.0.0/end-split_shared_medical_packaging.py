from odoo.upgrade.util.orm import env
from odoo.upgrade.util.report import add_to_migration_reports, announce_migration_report


def _unit_word(name):
    # UoM names embed the full breakdown, e.g. "BOX [1B X 20S X 10T]"; keep only the
    # unit word before the bracket and normalise its case -> "Box".
    return name.split("[")[0].strip().capitalize()


def migrate(cr, version):
    """Give each derived medicine UoM its own ``medical_packaging_id``.

    The v18->19 UoM refactor back-filled the dropped ``uom.category``'s
    ``medical_packaging_id`` onto every unit, so units that shared a category now
    share one record (a STRIP and its BOX both read "Strip of 10 Tablets"). Relabel
    each derived unit as ``<unit> of <factor> <reference>s``, the unit word being the
    part before the ``[...]`` breakdown in its name (e.g. "Box of 20 Strips"). Units
    already matching are skipped, so the script is idempotent.
    """
    e = env(cr)

    uoms = e["uom.uom"].search([("medical_packaging_id", "!=", False), ("relative_uom_id", "!=", False)])

    # Map each desired packaging label to the units that should carry it, skipping
    # units that already describe themselves (e.g. the base strip).
    targets = {}  # name -> uom.uom recordset
    for uom in uoms:
        factor = uom.relative_factor
        qty = int(factor) if float(factor).is_integer() else factor
        ref = _unit_word(uom.relative_uom_id.name)
        name = f"{_unit_word(uom.name)} of {qty} {ref if qty == 1 else ref + 's'}"
        if uom.medical_packaging_id.name != name:
            targets[name] = targets.get(name, e["uom.uom"]) | uom

    packagings = e["medicine.packaging.type"].create([{"name": name} for name in targets])
    for packaging, units in zip(packagings, targets.values()):
        units.medical_packaging_id = packaging

    if not packagings:
        return

    add_to_migration_reports(
        message=(
            f"<b>Medicine packaging split per unit</b> -- created <b>{len(packagings)}</b> new "
            f"<code>medicine.packaging.type</code> record(s) so each derived unit of "
            f"measure (e.g. a box) carries its own packaging label instead of inheriting "
            f"its reference unit's. Review the generated names where a unit is not a simple "
            f"multiple of its reference unit."
        ),
        category="PSAE",
        format="html",
    )
    announce_migration_report(cr)
