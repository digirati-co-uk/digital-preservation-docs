# Create deposit from external file set

Show that we provide a separate API to PUT files to S3 (eg Goobi can do this)


-	I can ask that the Preservation Service fetches the files from a provided location. S3 bucket initially, ambient access; we don’t mind how the files got there and they might just be raw files or they might be a bagit layout (we try to detect this). Can add more sources as needed.