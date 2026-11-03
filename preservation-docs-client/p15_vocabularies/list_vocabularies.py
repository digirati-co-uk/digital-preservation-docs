"""
The two controlled vocabularies: access conditions, and logical structure range types.

Both are per-instance configuration. Read them rather than hard-coding a list, because the values
differ between institutions and between an institution's own environments. An instance that has
configured none returns empty vocabularies, with no error - so an empty response means "none
configured", not "something went wrong".
"""
from preservation import get

# The access condition profile: the restriction vocabulary, the labels for the two choices a
# person makes, optionally a grouping of rights statements, and optionally conditions the
# platform derives from those choices (the Leeds "tier"). Only the vocabulary is required.
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

for group in profile["rightsAxis"]["groups"]:
    # When groups exist, offer only the grouped rights statements, under these headings.
    print(f"  {profile['rightsAxis']['label']} group {group['key']!r}: {', '.join(group['members'])}")

for derived in profile["derived"]:
    # Derived conditions are read-only: the platform computes them from the effective restriction
    # and rights statement on every write, and reports them in derivedAccessConditions.
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
