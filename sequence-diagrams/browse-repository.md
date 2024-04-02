# Browse Repository

-	Browse the repository containers (subject to permissions) to choose where something is going to go. Some workflows make that choice for me, my thing can only go in one place.


-	(Do we record a map of the preservation content and also store that in the repository? – especially if we have a hashed-ntuple layout)

-	The platform is a window to the repository as well as being an ingest / deposit mechanism. That means it can see the stuff that Goobi has deposited, too, and while you won’t be allowed to edit the things Goobi has put there, you can still view the file layouts, and create sharing links for ad hoc digitisation outputs that may not even be going through to asset delivery. This suggests that a view should be possible from just a METS file (Goobi’s METS file), and not have to project into rows in a DB.

-	I want to preview content within the preservation environment, before it is preserved and therefore before it is accessible to Asset Delivery; before is has had IIIF created. How does this work? The “staging” buckets are just as available to Asset Delivery as Fedora’s origins. Is there some super-secure access mechanism? Even if it’s slow compared to public delivery? But we don’t want to be transcoding video just for one person to see. Or do we?