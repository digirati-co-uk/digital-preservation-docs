-- wip

-- Previously "WorkingObjects"
-- I THINK that there could be multiple rows in this table for the same digital object; 
-- each row represents a time it has been in an editable state by a particular owner.
-- i.e., several rows with same preservation_path but different id.

-- That's why this is flat. You're not browsing this when browsing the hierarchy of the repository.

-- So should it really be called deposits? 

create table if not exists public.deposits
(
    id                  varchar,
    preservation_path   text,       -- maybe explicitly fedora_path?
    owner               text,
    s3_root             text,
    status              text,
    last_modified       timestamp,
    submission_text     text,
    pipeline_ran        timestamp,
    pipeline_job_id     varchar,
    date_preserved      timestamp,
    date_exported       timestamp,
    version_exported    varchar,
    version_saved       varchar
);