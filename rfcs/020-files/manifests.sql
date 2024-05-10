create table if not exists public.manifests
(
    id          varchar,
    slug        text,
    use_path    boolean,
    id_in_json  text,
    parent      varchar,
    space       integer,
    items_order integer,
    label       json,
    thumbnail   text,
    locked_by   varchar,
    locked_at   timestamp,
    created     timestamp,
    modified    timestamp,
    modified_by varchar,
    tags        text[],
    simple      boolean,
    sheet       text
);

comment on column public.manifests.id is 'from id minter';

comment on column public.manifests.slug is 'path element, if addressed hierarchically';

-- The one can redirect to the other if requested on the "wrong" canonical URL
comment on column public.manifests.use_path is 'Whether the id (url) of the stored manifest is its fixed id, or is the path from slugs';

-- Is this the way to do it? Presentation proxy reads this from S3 json - stream the head?
comment on column public.manifests.id_in_json is 'the id of the manifest last time it was persisted to S3';

comment on column public.manifests.parent is 'Parent collection (storage or actual)';

-- maybe this should default to minting a new space per manifest, to reduce naming collisions.
-- That might be counterproductive as it inhibits moving.
-- we should encourage asset IDs _after_ the /<space>/ that are unique to the customer, e.g., include some aspect of the manifest in the asset id
comment on column public.manifests.space is 'Use this space to store assets for this manifest (creates if non-existent; defaults to 0)';
-- There's no requirement that a manifest must use assets from a particular space, they could be from any space

comment on column public.manifests.items_order is 'Order within parent collection (unused if parent is storage)';

comment on column public.manifests.label_json is 'The stored manifest label JSON';

comment on column public.manifests.thumbnail is 'not the IIIF JSON, just a single path or URI to 100px';

-- when locked, updates via the API happen to a working locked copy (which has items and paintedAssets props)
-- rather than the "live" version.
-- api to publish (save to live version, release the lock)
comment on column public.manifests.locked_by is 'null normally; user id if being edited';
comment on column public.manifests.locked_at is 'When a lock was last applied';

comment on column public.manifests.modified is 'last updated';

comment on column public.manifests.modified_by is 'Who last committed a change to this Manifest';

comment on column public.manifests.tags is 'arbitrary strings to tag manifest, used to create virtual collections';

-- i.e., manifest.items could be recreated entirely from the canvas_paintings table
comment on column public.manifests.simple is 'One canvas_painting per canvas, no external assets, no non-null targets, no additional resources on canvas that are not known adjuncts or services';

comment on column public.manifests.sheet is 'A Google Sheet or online Excel 365 sheet that the Manifest was created from, and can synchronise with.';

alter table public.manifests
    owner to postgres;

