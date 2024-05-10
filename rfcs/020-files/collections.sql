create table if not exists public.collections
(
    id                    varchar,
    slug                  text,
    id_in_json            text,
    parent                varchar,
    items_order           integer,
    label                 text,
    thumbnail             text,
    locked_by             varchar,
    created               timestamp,
    modified              timestamp,
    modified_by           varchar,
    tags                  text[],
    is_storage_collection boolean,
    public                boolean
);

comment on column public.collections.id is 'from id minter';

comment on column public.collections.slug is 'path element, if addressed hierarchically, defaults to null if not supplied';

-- Is this the way to do it? Presentation proxy reads this from S3 json - stream the head?
comment on column public.collections.id_in_json is 'the id of the Canifest last time it was persisted to S3';

comment on column public.collections.parent is 'id of parent collection (storage or actual)';

comment on column public.collections.items_order is 'Order within parent collection (unused if parent is storage)';

comment on column public.collections.label is 'derived from the stored IIIF collection JSON - a single value on the default language';

comment on column public.collections.thumbnail is 'not the IIIF JSON, just a single path or URI to 100px';

comment on column public.collections.locked_by is 'null normally; user id if being edited';

comment on column public.collections.modified is 'last updated';

comment on column public.collections.modified_by is 'Who last committed a change to this Collection';

comment on column public.collections.tags is 'arbitrary strings to tag Collection, used to create virtual collections';

comment on column public.collections.is_storage_collection is 'default false is proper IIIF collection; will have JSON in S3';

comment on column public.collections.public is 'Whether the collection is available at dlcs.io/iiif/<path>';

alter table public.collections
    owner to postgres;

