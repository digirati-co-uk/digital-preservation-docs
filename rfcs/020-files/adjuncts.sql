-- https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/adjuncts
-- An adjunct is usually created from an asset, or associated with an asset. But could be for a Manifest, Collection etc.
-- Even for storage collections.
-- pipelines produce adjuncts for API resources
-- users can supply their own adjuncts from outside.
-- pipeline could create an adjunct from another adjunct made by a pipeline, or another adjunct added from outside.

-- the API exposes them under <resource>/adjuncts/<slug>
-- orchestrator exposes them at ... tbc (manifest url, image service url, but what about AV with multiple derivs? Where's the "master"?)

-- If the customer is building their own manifests they can do what they like,
-- but if we are, we might need to say that, when used in a manifest, the asset is expressed on the CANVAS even though it is associated with an asset.

-- does the adjunct table include adjuncts that the DLCS doesn't store?
-- maybe not so we don't have to model them, but we do round trip them in JSON
-- if we do want to record them we should use remote and linking property
-- Leaning towards yes (like a METS file from some other repo, annos in FromthePage etc)

create table if not exists public.adjuncts
(
    id               text,  -- internal identifier... do we need this? yes for storing in S3
    slug             text,  -- url part e.g., b2921371x_0001.xml (this maybe is the id)
    type             text,  -- Text, AnnotationPage, Dataset etc
    media_type       text,  -- e.g., text/xml
    profile          text,  -- e.g., http://www.loc.gov/standards/alto/v3/alto.xsd
    label            json, -- different from label on manifests and collections
    language         text[],  -- e.g., ["en"]
    origin           text,
    roles            text[],
    creator          text,   -- pipeline:OCR/v0.9.1  `id` of pipeline, or some other string for a creator
    source           text,   -- another adjunct (?) e.g., annos from METS-ALTO ... the actual adjunct rather than the pipeline that made that adjunct (need for adjunct.id). May be null. Never an asset id, always an adjunct
    size             integer,

    remote           boolean, -- whether the DLCS even fetches this from origin, for external adjuncts, or just proxies it
    linking_property text,    -- what IIIF prop links this to its resource, usually set by the pipeline's default_linking_property

    for_canvas       boolean,  -- express on canvas when for asset and that asset is painted on canvas (usually true)
                               -- portal will suggest that adjuncts should be on canvas. Or even default to that?

    visible          boolean, -- whether the adjunct is exposed on the manifest, canvas or other container
   
    asset_id         text,  -- was derived from this asset - may be null if for a manifest

    -- either we do this:
    canvas_id        text,
    manifest_id      text,
    collection_id    text


)

-- public_url and content are not in the DB, they are generated



