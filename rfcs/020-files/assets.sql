-- A mini assets table for experimenting with the other tables.

create table if not exists public.assets
(
    id           text,
    customer     integer,
    space        integer,
    origin       text,
    content_type text,
    created      timestamp,
    width        integer,
    height       integer,
    duration     double precision,

    -- new field - the manifest this asset was INTRODUCED in.
    -- doesn't mean it hasn't been used in other manifests since - but that's not going to be normal.
    manifest_context  varchar
);

comment on table public.assets is '(This is the Images table in protagonist!)';

alter table public.assets
    owner to postgres;

