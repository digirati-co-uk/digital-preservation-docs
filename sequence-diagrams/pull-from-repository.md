Can this be drop-boxy - don't actually fetch all the files, just make stub keys in S3 from the METS file AND correlate to the Fedora OCFL object

... need to be VERY careful!

Must never write a stub back by mistake.

We only fetch the actual binary from S3 if you want to see it.


-	At any point, even long after it’s preserved, I can pull an object out of preservation and update granular permissions. Typically this only changes a METS file. (impl – are we resuscitating DB rows to do this so we can re-make a METS file?)