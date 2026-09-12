# Internals

How the platform is built, deployed and run. **Current documentation, not superseded material** —
unlike `documentation/`, which holds the originals being ported to the site.

These pages are deliberately *not* on the [documentation site](https://digirati-co-uk.github.io/digital-preservation-docs).
The site is for people using the platform: a developer with credentials calling the Preservation
API, or library staff using the Preservation UI. What is here answers a different question — how to
run the thing — for a different reader, and it changes on a different rhythm. Deployment detail in
particular dates quickly, and will date faster still as backends other than S3 arrive; it is better
kept where nobody mistakes it for a stable contract.

| Page | What it covers |
|---|---|
| [overview.md](./overview.md) | The six running services, how work reaches them, where the code lives. |
| [pipeline-api.md](./pipeline-api.md) | SNS and SQS, the job claim, the tool chain, how a run proceeds and how it fails. |
| [deployment.md](./deployment.md) | Images, build and deploy workflows, configuration sections, feature flags, databases, running locally. |

## What is not here

**iiif-builder.** Leeds have taken the service and now run their own version, so a description of
the copy in this repository would document something nobody operates. Further IIIF support is
planned in the Preservation API itself, which should make building an equivalent easier; that will
be documented on the site when it exists. The activity stream it consumes *is* documented, at
[Activity Stream](https://digirati-co-uk.github.io/digital-preservation-docs/preservation-api/activity-stream/).

**WorkspaceManager and the METS libraries.** These moved onto the site, as
[Libraries](https://digirati-co-uk.github.io/digital-preservation-docs/preservation-api/libraries/),
because they answer a question an API caller actually has: the API will not take your bytes, so what
is there to help you assemble a deposit? They are also to be released as standalone libraries.

## Keeping these honest

Nothing checks these pages. They carry no build, no link checking and no verification pass, which is
part of why they are here rather than on the site. Treat anything infrastructural in them as a lead
rather than a fact, and check it against the code, the workflows in `.github/workflows/` and the
`appsettings.Example.json` files before relying on it.
