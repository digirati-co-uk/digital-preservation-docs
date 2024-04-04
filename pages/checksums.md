# Checksums

Different behaviours

 - expect to find in S3 metadata
 - expect to find in bagit, will add to S3 metadata
 - expect to find in existing mets
 - supplied in client upload
 - not supplied, want Preservation to calculate (rare, special dispensation!)

 In the latter we insert `premis:fixity` into METS

 