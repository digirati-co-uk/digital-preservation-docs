-- wip

-- Previously "WorkingObjects"
-- I THINK that there could be multiple rows in this table for the same digital object; 
-- each row represents a time it has been in an editable state by a particular owner.
-- i.e., several rows with same preservation_path but different id.

-- That's why this is flat. You're not browsing this when browsing the hierarchy of the repository.

-- So should it really be called deposits? 

-- If we didn't have the ID service / minter, we'd need to store various alternative identifiers in the DB, EMu being the most obvious.
-- Do we still want to store something in here?

```sql
create table if not exists public.deposits
(
    id                  varchar,
    preservation_path   text,       -- maybe explicitly fedora_path?
    created             timestamp,
    createdBy           text,
    lastModified        timestamp,
    lastModifiedBy      text,
    s3_root             text,
    status              text,
    submission_text     text,
    -- pipeline_ran        timestamp,   -- This is the wrong cardinality
    -- pipeline_job_id     varchar,     -- pipeline-jobs references a deposit instead
    date_preserved      timestamp,
    date_exported       timestamp,
    version_exported    varchar,
    version_saved       varchar
);
```
