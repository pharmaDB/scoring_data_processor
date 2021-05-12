# resources

This folder contains large miscellaneous files.

`database_latest.tar.gz` stores the entire database (stale state) before it is run through this package.  It can be unzip to this folder to create `resources/database_latest/` folder, and imported automatically using `main.py -rip -ril -rio`


`process_log.tar.gz` stores a record of all documents in the database that are already processed so they are not reprocess on running `python3 main.py`.  This file can be unzipped to this folder to create a `resources/process_log/` folder.

`database_testing` stores a patent and label collection that are imported during unit-tests.

`hosted_folder` includes content that is served when `server.py` is ran.


`Orange_Book` includes all Orange Book archives that are used by module(s) in `orangebook/`.