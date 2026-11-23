"""
The two controlled vocabularies: access conditions, and logical structure range types.

Both are per-instance configuration. Read them rather than hard-coding a list, because the values
differ between institutions and between an institution's own environments. An instance that has
configured none returns empty vocabularies, with no error - so an empty response means "none
configured", not "something went wrong".
"""
from preservation import get

# The access condition profile: the restriction vocabulary, the labels for the choices a person
# makes, and - only on an instance with a statement profile (Leeds) - the statements a person
# chooses instead of a rights statement, what each publishes in IIIF, and the conditions derived
# from them (the Leeds "tier"). Only the vocabulary is required.
profile = get("/access-conditions").json()
restrictions = profile["restrictionAxis"]["values"]
if restrictions:
    print(f"{len(restrictions)} {profile['restrictionAxis']['label']} values:")
    for condition in restrictions:
        # `value` is what is recorded against a file, folder or Range, and what comes back in
        # accessRestrictions. `label` is for showing to a person.
        print(f"  {condition['value']:<20} {condition['label']}")
else:
    print("This instance has no access conditions configured")

statements = profile.get("statements")
if statements:
    # Chosen instead of a rights statement, written to METS under statements['type'] and inherited
    # like the restriction. Each names its category (a matrix column) and a IIIF entry: the
    # `rights` URI (also written to METS by the platform) and `requiredStatement` text it publishes.
    iiif = {entry["id"]: entry for entry in statements.get("iiif", {}).get("entries", [])}
    print(f"{len(statements['values'])} {statements['label']} values (METS type {statements['type']!r}):")
    for statement in statements["values"]:
        rights = iiif.get(statement.get("iiif"), {}).get("rights", "-")
        print(f"  {statement['value']:<28} {statement.get('category', ''):<18} {rights}")

    for derived in statements["derived"]:
        # Derived conditions are read-only: the platform computes them from the effective
        # restriction and statement on every write, and reports them in otherAccessConditions.
        values = ", ".join(v["value"] for v in derived["values"])
        print(f"  derived {derived['type']!r} ({derived['label']}): {values}")

range_types = get("/range-types").json()
if range_types:
    # A plain list of strings: the permitted Type of a Range in a logical structure.
    print(f"\nRange types: {', '.join(range_types)}")
else:
    print("\nThis instance has no range types configured")

# Both are cheap and change only when the instance is reconfigured, so a client fetches them
# once and caches them - the platform's own UI caches the profile for five minutes and the range
# types for an hour.
