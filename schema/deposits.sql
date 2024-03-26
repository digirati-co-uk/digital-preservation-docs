-- wip

create table if not exists public.deposits
(
    asset_id            varchar,
    preservation_path   text,
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