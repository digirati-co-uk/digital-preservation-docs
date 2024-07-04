-- this table is designed to be efficient for the 99% use case but nice to use for the others
-- it's doing four things - canvases, painting annotations on the canvas, body of the painting annotation, Choice items if body is a choice

-- seeAlsos and annotations come from adjuncts which belong to ASSETS
-- tbc how we do that for annos

create table if not exists public.canvas_paintings
(
    manifest_id        varchar,
    canvas_id          varchar,
    canvas_original_id text,
    canvas_order       integer,
    choice_order       integer,
    asset_id           text,
    thumbnail          text,
    label              json,
    canvas_label       json,
    target             text,   -- could be json, or jsonb
    static_width       integer,
    static_height      integer 

    --do we need timestamps on these rows?
);

comment on column public.canvas_paintings.manifest_id is 'from  the manifest table';

-- canvases in manifests always use a flat id, something like https://dlcs.io/iiif/canvases/ae4567rd, rather than anything path-based
-- if requested directly, DLCS returns canvas from this table with partOf pointing at manifest(s)
comment on column public.canvas_paintings.canvas_id is 'might not be unique within this table if in more than one manifest';

comment on column public.canvas_paintings.canvas_original_id is 'FQ URL where canvas id not managed; e.g., manifest was made externally';

-- this keeps incrementing for successive paintings on the same canvas, it is always >= number of canvases in the manifest
-- for most manifests, the number of rows equals the highest value of this.
-- BUT it stays the same for successive content resources within a choice (see choice_order)
-- it gets recalculated on a Manifest save by walking through the manifest.items, incrementing as we go.
comment on column public.canvas_paintings.canvas_order is 'canvas sequence order within a manifest';

-- when the successive content resources are items in a Choice body, canvas_order holds constant and this row increments.
comment on column public.canvas_paintings.choice_order is 'normally null; positive integer indicates painting anno is part of a Choice body. Multiple choice bodies share same value of order.';

-- This is the resource that is the body (or one of the choice items), which may have further services, adjuncts that the DLCS knows about.
-- But we don't store the body JSON here, and if it's not a DLCS asset, we don't have any record of the body - JSON is king.
comment on column public.canvas_paintings.asset_id is 'DLCS asset ID to be painted on the canvas - may be null if external';

comment on column public.canvas_paintings.thumbnail is 'As with manifest - URI of a 100px thumb. Could be derived from asset id though? So may be null most of the time.';

-- label 
-- canvas_label
comment on column public.canvas_paintings.label is 'Stored language map, is the same as the on the canvas, may be null where it is not contributing to the canvas, should be used for choice, multiples etc.';
comment on column public.canvas_paintings.canvas_label is 'Only needed if the canvas label is not to be the first asset label; multiple assets on a canvas use the first';

comment on column public.canvas_paintings.target is 'null if fills whole canvas, otherwise a parseable IIIF selector (fragment or JSON)';

-- These next two default to 0 in which case the largest thumbnail size is used - which may be a secret thumbnail 
comment on column public.canvas_paintings.static_width is 'for images, the width of the image for which the IIIF API is a service';

comment on column public.canvas_paintings.static_width is 'for images, the height of the image for which the IIIF API is a service';


alter table public.canvas_paintings
    owner to postgres;

