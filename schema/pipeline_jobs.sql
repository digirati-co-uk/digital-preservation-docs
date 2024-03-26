-- wip

create table if not exists public.pipeline_jobs
(
    id                  varchar,
    mets_file           text, -- path of mets file to read/write
    create_mets         boolean,
    s3_root             text,  -- redundant but maybe needed?
    taken               timestamp,
    finished            timestamp,

    validate_fixity     boolean,
    create_fixity       boolean, -- special dispensation
    add_to_mets         boolean, -- or create our own
    run_antivirus       boolean,
    run_fileformat      boolean
);