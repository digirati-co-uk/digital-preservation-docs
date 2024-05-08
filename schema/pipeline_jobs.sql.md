-- wip

```sql
create table if not exists public.pipeline_jobs
(
    id                  varchar,
    deposit_id          varchar,
    mets_file           text, -- path of mets file to read/write
    create_mets         boolean,
    s3_root             text,  -- redundant but maybe needed?
    taken               timestamp,
    finished            timestamp,

    validate_fixity     boolean,
    create_fixity       boolean, -- special dispensation
    add_to_mets         boolean, -- or create our own

    run_antivirus       boolean, -- are all these flags here?
    run_fileformat      boolean, -- or do we record this more flexibly
    run_exif            boolean  -- we may add further activities later
);
```
