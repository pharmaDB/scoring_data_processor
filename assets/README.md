# assets

This folder contains miscellaneous files.

`database_testing` stores a patent and label collection that are imported during unit-tests.

`database_latest` stores the entire database (stale state) before it is run through this package.  It can be imported automatically using `main.py -rip -ril`

`all_NDA`, `all_patents`, `all_patents.json`, `missing_NDA`, `missing_patents`, `missing_patents.json` are various files exported by this package to indicate the state of the database.

`hosted_folder` includes content that is served when `server.py` is ran.