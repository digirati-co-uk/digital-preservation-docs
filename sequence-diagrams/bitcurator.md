# BitCurator workflows

- I can do anything I like in BitCurator, it is completely independent of the Preservation UI. I can do several tasks in BitCurator that may later be done again by the Preservation Service standard pipelines, but that’s OK. Use BitCurator to assess material and prepare a set of files that can then enter the system like any other set of files. 

- Q – can I see the internet from BitCurator? Could I upload from there? 

- A - Yes, in its default configuration. But there may be good reasons for not allowing internet access while evaluating potentially malware-ridden material.

- I can upload a BagIt bag as content (this might have come from BitCurator, but could have come from elsewhere). I can do so as a zip file, or as an unpackaged directory, using a client side helper tool to upload the directory. This is a preferred mechanism as they all come with checksums. There are many off the shelf components we could use, but we must calculate sha-256 in the browser for each file. 

- The rest of the system has no dependence on or awareness of BitCurator, and there's no need to use BitCurator if some other forensic tool is better.