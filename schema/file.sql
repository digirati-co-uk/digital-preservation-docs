-- wip

create table if not exists public.files
(
    deposit_id          varchar,
    path                text,
    original_name       text,
    sha256              varchar,
    notes               text
);

-- room for flags, status etc later.
-- maybe a JSON column?

