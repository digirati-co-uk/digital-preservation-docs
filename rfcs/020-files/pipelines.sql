-- pipelines produce adjuncts for API resources

-- You don't have to add pipelines individually to assets, they in

create table if not exists public.pipelines
(
    id                        text,  -- pdf/v0.9.1
    name                      text,  -- pdf
    version                   text,  -- 0.9.1
    scope                     varchar,  -- ? Asset | Canvas | Manifest | Collection | Space | Storage Collection
    depends_on_pipeline       text,  -- id self reference*
    output_type               text,  -- Text, DataSet, AnnotationPage etc
    output_format             text,  -- text/xml, application/pdf etc
    output_profile            text,  -- http://www.loc.gov/standards/alto/v3/alto.xsd    
    default_linking_property  text,      -- rendering, annotations, seeAlso

    hook                      text, -- how is the pipeline invoked?  -- pass this hook... what?
    -- Does a pipeline execution have to write to the DB?
    -- no, it's handler does. The handler feeds it the things it needs to process and takes the output,
    -- and marks the joining table running=false when done.
)

-- *what if the pipeline depends on something that isn't the output of a pipeline, and isn't an asset?
-- I'm thinking a manually added external adjunct. The pipeline table can't depend on a specific adjunct; the pipeline properties have to be used to matcn, so could be:
-- depends_on_type, depends_on_format, depends_on_profile (sometimes the last of these not needed)

create table if not exists public.manifest_pipeline
(
    manifest_id         text,
    pipeline_id         text,  -- id of pipeline that has scope=Manifest or scope=Asset
    last_ran            timestamp,
    run_id              text,  -- unique id for this run
    running             boolean,
    error               text
)

create table if not exists public.space_pipeline
(
    manifest_id         text,
    space_id            text,  -- id of pipeline that has scope=Space or scope=Asset
    last_ran            timestamp,
    run_id              text,  -- unique id for this run
    running             boolean,
    error               text
)

-- and other joining tables ^^^


create_table if not exists customer.default_pipelines
(
    customer_id       int,
    pipeline_id       text
)