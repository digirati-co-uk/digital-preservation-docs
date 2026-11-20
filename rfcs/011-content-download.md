# RFC 011: Content download

**Status: draft for discussion.**

## Purpose

This RFC is a proposal for how staff at Leeds get preserved files back out of the repository,
other than via the existing mechanism of exporting to a deposit. It is the design deliverable for
SoW9 milestone M4, "Repository Content Download Discovery and Design"
([#456](https://github.com/digirati-co-uk/digital-preservation/issues/456)). It follows the
workshop with Leeds on 11 November 2026.

A first, simple part of the design has been built for dev, so that Leeds can try it while reading
this.

## Context

Someone is putting together an exhibition, and asks for the master image of one page of a
digitised manuscript - the full-size TIFF, not the version on the website. The person they ask
can sign in to the Preservation UI, browse to the Archival Group and find the file. They can see
its name, its format, how big it is, even its checksum. There is a link, but it has a "no entry"
sign beside it.

There is one way to get the file today. A platform user can export the Archival Group into a new
deposit, and then fetch the file from the deposits bucket (if they have access to that bucket).
But an export copies every file in the Archival Group. That is unwieldy when you just want one
file, and the Archival Group might hold thousands.

This is the requirement in SoW9 M4:

> UoL has identified a requirement for authorised users or website processes to request and
> download content from the repository for a range of use cases such as exhibitions, content reuse
> and supplying files to users. Examples include high-resolution TIFFs, AV files or documents not
> intended for general IIIF access. This is distinct from derivative content made available as IIIF
> such as Image API endpoints or transcoded AV, which is what iiif-builder mediates.

Making that link work is not a difficult technical problem; the Storage API can already stream
any preserved file. The difficulty is who should be able to do it, to which files, what trace it
leaves, and how to do it without opening up the preservation bucket. The milestone asks for "an
agreed design and an initial basic implementation", and suggests the implementation could let
any user who has been granted access download any content, with anything more granular left for
later.

So this RFC is mostly about policy. The mechanism we propose doesn't force the policy decisions
to be made now. It even supports a policy in which the platform doesn't deliver files to people
at all (see [Should the platform deliver files at all?](#should-the-platform-deliver-files-at-all)).

## Current behaviour

The link is in a row labelled "Content" on the file's page: "Binary content (Storage API)". It
was never meant to work for a person:

* It points at the Storage API, which will stream the file (`GET /content/{path}`,
  [`ContentController.cs`](https://github.com/digirati-co-uk/digital-preservation/blob/main/src/DigitalPreservation/Storage.API/Features/Binaries/ContentController.cs)),
  but only to the platform's own services. A person in a browser has no client ID and secret to
  present to it.
* The Preservation API deliberately has no content route. It will give you a METS file
  (`?view=mets`), because the UI needs that, and nothing else.

[#300](https://github.com/digirati-co-uk/digital-preservation/issues/300) is the open issue about
these content links. This work stops the UI using them, but the API still gives every file a
`content` address that almost no caller can reach. Whether it should stays open there.

Export to a deposit is the one access mechanism that does work. A background job in the Storage
API copies an Archival Group's files out of the preservation bucket and records what it did. It
copies all of them (or just the METS file); you can't export a selection. We come back to it
[later](#things-we-could-build-next).

## Guiding considerations

* **The preservation bucket stays buried.** It holds the OCFL objects. Nothing reaches it except
  Fedora, the Storage API and the importer; access is granted by role, and only those three have
  one. A download must not become the exception.
* **Files shouldn't travel through our services on their way to the user.** The requirement names
  high-resolution TIFFs and AV masters.
* **Who may download is external to the application.** That means roles in Entra, not rules built into the
  code.
* **Every request leaves a record.**
* **The first build shouldn't close anything off.** "Shopping Carts", zips, whole Archival Groups, download
  by access tier, files over 5 GB and delivery by some other means are not in the first build,
  but none of them should require it to be thrown away.

## The approach: request, copy, link

A user doesn't download a file from the repository: they request it. The platform makes a copy
of the file in a separate downloads bucket, and gives the user a link to the copy. The copy goes
away after a while.

A download request has a state:

1. **Copying.** A user asks for a file. The Preservation API checks that they are allowed to (see
   [Who may download](#who-may-download)), asks the Storage API to make the copy, and records the
   request (see [The record](#the-record)).
2. **Ready.** The copy is in the downloads bucket, and a link to it can be had. For most files
   this takes seconds.
3. **Expired**, or **deleted**. The copy has gone. The record of the request stays.

A request is **failed** if the copy never appears. A request for something that isn't a file is
refused, and isn't recorded.

Even a small download is a request with a state, because that is the shape of the things that
will take a while: a 100 GB master, a selection of files, a whole Archival Group, or a file that
has to be restored from a colder storage class (nothing is in one today). The harder cases then
use the same request and the same page.

The Storage API makes the copy in the background, S3 to S3. S3 computes the SHA-256 of the copy,
and if that doesn't match the digest of the preserved file, the copy is removed.

### Who does what

* **The Storage API** makes the copy, removes it, and signs the links to it. It is the only
  service with any permission on the downloads bucket.
* **The Preservation API** holds the gate and the record. It never touches either bucket. When a
  permitted user wants a link, it asks the Storage API for one.
* **The UI** replaces the "no entry" link with a *Request download* action, and has a Downloads
  page listing the requests: their state, the link, and a button to delete the copy.

There is one downloads bucket per environment. A copy's key is the request's identifier followed
by the file's name, so the bucket makes sense to someone looking at it directly. That matters for
[staged delivery](#should-the-platform-deliver-files-at-all).

### The link

The user's browser finally follows a link signed by S3, which works for a short time. S3 serves
the file directly, at any size, and a download that drops can be resumed.

That is not the link the user keeps. The link the user keeps is a route in the UI. Each time it
is followed, the Preservation API checks the user and the request again, records that a link was
issued, and gets a freshly signed S3 link from the Storage API. The signed link lasts two
minutes, which is long enough to start the download.

There are two reasons. A raw S3 link is a bearer token - anyone who has it can use it, and we
can't take it back. And a link signed with a service's temporary credentials stops working when
those credentials rotate, within hours, so a link meant to last for days can't be a raw S3 link
anyway.

> The workshop notes also raise an opaque, short-lived or one-time link that could be passed on
> to someone else. That would be the same route, with a token in place of a signed-in user. It
> isn't in the first build, and whether Leeds want it depends on the answer to
> [Should the platform deliver files at all?](#should-the-platform-deliver-files-at-all)

## Who may download

The check is in the Preservation API, so that it covers machine callers as well as people. It is
a setting that holds a list of roles. A caller may request and download files if they hold any
one of them.

| Setting | Meaning |
|---|---|
| Empty, or absent | Nobody. This is the default, so an environment that hasn't been configured can't hand out content by accident |
| `*any*` | Any authenticated caller |
| `Content.Download` | Only callers with that Entra role |

`*any*` is a stepping stone, needed because the role doesn't exist yet. Dev starts on `*any*`.
Leeds create a `Content.Download` app role in Entra and assign it to people (and later to any
client application that needs it). We then replace `*any*` with `Content.Download`, and verify
that content can only be downloaded with the role. Production stays empty until Leeds decide to
switch it on.

Roles arrive in the caller's token, as for the app role introduced for per-caller identities
([RFC-0001](https://github.com/digirati-co-uk/digital-preservation/blob/main/docs/rfc-0001-api-caller-identity.md)).
The UI calls the Preservation API with the signed-in user's own token, so a role assigned to a
person on the API's Entra registration reaches the check.

### Later: download by access tier

In the first build you may download everything, or nothing. At the workshop it was suggested
that the public access tiers might do for staff as well. One design is a role per tier -
`Content.Download.0` to `Content.Download.5` - where a user may download files in their tier or
below. Every file already has an evaluated access condition, shown on its page in the UI. The
tiers themselves are the subject of
[#433](https://github.com/digirati-co-uk/digital-preservation/issues/433) and
[PR #434](https://github.com/digirati-co-uk/digital-preservation/pull/434).

Three things would need settling first:

* What is a file with no access condition? The most open tier, the most closed, or refused? We'd
  suggest the most closed.
* Access conditions live in the METS. Anyone who can edit a deposit can lower a file's tier,
  preserve it, and then download it.
* The Leeds profile derives the tier from two things, one of which is copyright status. The tier
  is an ordered scale; copyright status isn't. Does download follow the derived tier alone?

The mapping from tier to role would be configuration, not code.

## The record

At a minimum, the record says who initiated each request. We propose that it holds:

* who asked;
* which file - its path in the repository, and its digest;
* the file's size;
* when;
* why (a free-text reason);
* the request's state, and when it expires;
* each time a link was issued, and to whom.

The record lives in the Preservation API's database. It is not written into the Archival Group as
a PREMIS event, because that would change the preserved object every time somebody downloaded
from it.

We propose that whether a reason is compulsory depends on the file. If a file's evaluated access
is the Open tier, no reason is needed. For anything else, you have to say why you are generating
a link (or, later, a zip of a selection of files, or of an Archival Group). A file with no access
condition counts as not Open. In the first build the reason is optional, because this rule
depends on PR #434, which isn't merged yet.

Who may see a request, and use its link - only the person who made it, or anyone with the
download role? In the first build, anyone with the role sees the whole list.

## How long a copy lasts

A copy lasts 7 days by default. The default and the maximum are configuration.

A user could choose a shorter life when making the request, but never a longer one (this isn't
in the first build). A user can also delete a copy early, from the Downloads page.

The application enforces expiry: once a request has expired, no more links are issued and the
copy is deleted. S3's lifecycle rules apply to a whole bucket and work in whole days, so they
can't honour a per-request expiry. A lifecycle rule set a little above the maximum is the
backstop.

## Large files

A single S3 copy call handles up to 5 GB. That is also the platform's limit for a preserved file
today, which is the subject of RFC 009
([docs PR #66](https://github.com/digirati-co-uk/digital-preservation-docs/pull/66)).

When the work in RFC 009 lands, larger files will need a multipart copy. That change is confined
to the copy step: the request, the record and the UI stay as they are. The download itself is
unaffected - S3 will serve any size, with resume.

## Things we could build next

None of these are in the first build. They are here so that Leeds can say which of them matter.

* **A cart.** Users add files to a cart as they browse, then request the cart: one request, many
  files.
* **A page of links.** The cheapest form of a cart. The request copies each file, and its page
  lists a link and a checksum for each one. No zip is made. For a handful of large files this is
  better than a zip, because each download can be resumed on its own.
* **A zip of a selection.** A background job reads the files and writes one zip into the downloads
  bucket. It would use zip64 (for size) and store without compressing (media files don't
  compress). The zip should carry a manifest of checksums.
* **A whole Archival Group**, as a zip or as a folder of copies. Export to a deposit already
  copies an Archival Group out of the preservation bucket as a tracked background job. We'd reuse
   that, with the downloads bucket as the destination.  Building a
  very large Archival Group is slow today
  ([#244](https://github.com/digirati-co-uk/digital-preservation/issues/244)).
* **Website processes as requesters.** The SoW mentions these. A website process is a client
  application with its own Entra registration; it would be given the download role and would call
  the same Preservation API routes as the UI. 

## Should the platform deliver files at all?

This came up at the workshop: is it the Preservation platform's job to deliver files to people?

In the alternative, a user still requests files, and the platform still copies them (and
sometimes zips them) into the downloads bucket and records the request. But the platform stops
there. Someone with access to that bucket arranges the transfer of the files to whoever they are
for, by a scheme that Leeds build and control. The UI shows which copies exist and when they
expire, and lets a user delete them once they have been delivered.

The two policies share the request, the copy, the downloads bucket, the record and the expiry.
They differ only in the last step. In one, the application hands the user a link. In the other,
Leeds collect from the bucket.

So choosing between them later doesn't cost much. If Leeds prefer staged delivery, we switch off
the links and keep everything else. It's also possible to have both - a direct link for a member
of staff who needs a file themselves, staged delivery for supplying files to someone outside the
University.

Staged delivery does mean that more people, or more systems, need access to the downloads
bucket. Who they are is for Leeds to decide.

## The first build

This is for dev, for Leeds to try while reading this RFC:

* a downloads bucket on dev, with permissions for the Storage API only;
* in the Storage API, copy one file to the downloads bucket, sign a link to it, delete it;
* in the Preservation API, the gate (set to `*any*` on dev) and the record of requests;
* in the UI, *Request download* in place of the "no entry" link, with an optional reason, and a
  Downloads page of requests with their state, a link and a delete button;
* single files, up to the platform's current 5 GB, from the current version of an Archival Group.

It doesn't include carts, zips or whole Archival Groups; roles by tier; the rule that makes a
reason compulsory; a lifetime chosen by the user; links for people who aren't signed in; or staged
delivery. It doesn't switch anything on in production, where the setting stays empty.

It takes three shortcuts:

* A request's state is only brought up to date when someone looks at it. An expired copy is
  removed the next time the Downloads page is opened, or by the bucket's lifecycle rule, which is
  set a day longer than the lifetime.
* The Storage API keeps its queue of copies in memory. If a copy fails, or the Storage API
  restarts before making it, the request shows as failed after 15 minutes. The reason is in the
  Storage API's log, not on the page, and the user has to request the file again.
* Only files in the current version of an Archival Group can be requested.

## What we need from Leeds

The workshop agenda listed decisions 16 to 23 for this milestone. This table says where each one
stands after this paper, and what we still need.

| # | Decision | Where it stands | Still needed from Leeds |
|---|---|---|---|
| 16 | Who requests downloads | Staff, through the UI, first. Website processes would use the same routes with the download role ([Things we could build next](#things-we-could-build-next)) | The names of any website processes that need to request files, and how often they would |
| 17 | Who may download | Proposed: a `Content.Download` role, checked in the Preservation API; nobody by default; `*any*` on dev until the role exists ([Who may download](#who-may-download)) | Agreement. Then create the role in Entra and say who gets it |
| 18 | Staff download rules, and the access tiers | Open. One design is a role per tier ([Later: download by access tier](#later-download-by-access-tier)). Not in the first build | Do the tiers suit staff download, or do staff need rules of their own (by collection, by content type)? And answers to the three questions in that section |
| 19 | Restricted or sensitive material | Nothing is excluded in the first build. Requiring a reason ([The record](#the-record)) is a first step | Which material must never be downloadable without approval, and who approves |
| 20 | How files are delivered | Proposed: request, copy to a downloads bucket, expiring link. Not streamed, and the preservation bucket is never exposed ([The approach](#the-approach-request-copy-link)) | Agreement. And the policy question: direct links, staged delivery by Leeds' own means, or both ([Should the platform deliver files at all?](#should-the-platform-deliver-files-at-all)) |
| 21 | Wait, link lifetime, largest file | Proposed: seconds for most files; 7 days, configurable, and users may shorten it; 5 GB today, more after RFC 009 ([How long a copy lasts](#how-long-a-copy-lasts), [Large files](#large-files)) | Is 7 days right? Should users be able to choose a shorter life? |
| 22 | What must be recorded | Proposed: who, what, when and why, plus each link issued, kept in the Preservation API ([The record](#the-record)) | Is a reason required for anything that isn't Open? Who may see requests, and who reads the record? |
| 23 | The disabled link in the UI | Settled: it becomes *Request download* in the first build | Nothing |

We'd also like to know:

* which of the [things we could build next](#things-we-could-build-next) matter;
* two or three real requests from the last year: what was asked for, how big it was, who asked,
  and how it was supplied;
* who reviews this RFC, and by when.

## What we haven't verified

* The gate has been tested with roles in a token, but not with a real Entra role assigned to a
  real person.
* The first build passes its automated tests, but the copy and the signed link haven't yet been
  exercised on dev against real S3.
* "Seconds for most files" is what S3 copies normally take. It isn't a measurement on this
  platform.

## Appendix: rejected approaches

### Streaming the file through our services

Add a content route to the Preservation API and let the UI proxy it, as it already does for METS.
The file would pass through three services on its way to the browser (Storage API, Preservation
API, UI).

This would be fine for small files, but not for high-resolution TIFFs and AV masters:

* The Storage API's content route sends no length and supports no ranges, so a download can't be
  resumed. A 100 GB download that fails at 95 GB starts again.
* The Preservation API's client read a whole response into memory before passing it on
  (`GetContentStream` in
  [`PreservationApiClient.cs`](https://github.com/digirati-co-uk/digital-preservation/blob/e10744e9/src/DigitalPreservation/Preservation.Client/PreservationApiClient.cs)).
  That could be fixed, but every hop would need the same care.
* Every download in progress would occupy a connection in three services for as long as it
  lasted.
* The user downloads to their own machine, one file at a time, and then still has to get the file
  to whoever asked for it.

### A signed link straight to the preservation bucket

S3 can sign a link to a single object with no copy made at all. This is the least work, but it
breaks the rule that the preservation bucket stays buried: it hands a browser a way in, and tells
the user the bucket's name and the object's key. With a copy, what becomes more reachable is one
copy of one file, for a limited time.
