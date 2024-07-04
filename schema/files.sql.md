-- wip

-- we may not even need this table if we are happy that we can use METS as a model for UI.
-- Or rather, not METS directly but something that can be easily serialised to and from METS
-- ... and moreover, Goobi-style METS

```sql
create table if not exists public.files
(
    deposit_id          varchar,
    path                text,
    original_name       text,
    sha256              varchar,
    notes               text
);
```

Maybe we DO need this, for reporting, on file types, formats, across digital and digitised, etc.
Aggregate technical metadata.

-- room for flags, status etc later.
-- maybe a JSON column?

