"""
The two controlled vocabularies: access conditions, and logical structure range types.

Both are per-instance configuration. Read them rather than hard-coding a list, because the values
differ between institutions and between an institution's own environments. An instance that has
configured none returns an empty list, with no error - so an empty response means "none
configured", not "something went wrong".
"""
from preservation import get

access_conditions = get("/access-conditions").json()
if access_conditions:
    print(f"{len(access_conditions)} access conditions:")
    for condition in access_conditions:
        # `value` is what is recorded against a file, folder or Range, and what comes back in
        # accessRestrictions. `label` is for showing to a person.
        print(f"  {condition['value']:<20} {condition['label']}")
else:
    print("This instance has no access conditions configured")

range_types = get("/range-types").json()
if range_types:
    # A plain list of strings: the permitted Type of a Range in a logical structure.
    print(f"\nRange types: {', '.join(range_types)}")
else:
    print("\nThis instance has no range types configured")

# Both are cheap and change only when the instance is reconfigured, so a client fetches them
# once and caches them - the platform's own UI caches for an hour.
