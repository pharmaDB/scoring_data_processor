

# scoring_data_processor
This package maps changes in drug label to patent claims using the Orange Book Table's of Exclusivity.

Running this package without any optional argument will calculate and store diffs between adjacent labels (by date) for
each drug as defined by NDA number(s) into the label collection of the MongoDB database. The diffs will also be collated to patent claims from the patents collection of the MongoDB database. Labels that are already processed are stored in `resources/processed_log/processed_id_diff.csv` and `resources/processed_log/processed_id_similarity.csv`. These labels will not be re-processed unless optional argument `-r` is set. Running optional arguments other than `-r` will not additionally run the diffing steps or diffs-to-patent-claims mapping unless those flags are set.

## MongoDB Set Up
The connection info for the Mongo DB instance is set in the `.env` file. This should work for a standard MongoDB set up on localhost. If using a different set of DB configs, this file must be updated.

A sample docker set up for mongo, that maps to `localhost:27017` can be found [here](https://github.com/pharmaDB/etl_pipeline). This set up also includes the Mongo Express viewer.

![Mongo Express Labels Info](./assets/mongo_express.png)

To load the bson collection files into the docker container, after running `docker-compose up` per the docker and MongoDB setup [here](https://github.com/pharmaDB/etl_pipeline), find the docker container using `docker ps -a`.  Assuming that `docker ps -a` indicates that `mongo_local` is the name of the docker container that is running MongoDB, then confirm that `MONGODB_HOST` and `MONGODB_PORT` from `.env` matches the address and port underneath `PORTS` of `docker ps -a` for `mongo_local`.

Then you may use either of the following two sets of commands to loads the test collections into the databases:

```
docker cp assets/database_before/labels.bson mongo_local:.
docker cp assets/database_before/patents.bson mongo_local:.

docker exec -it mongo_local sh
mongoimport --db test --collection labels --file labels.bson
mongoimport --db test --collection labels --file patents.bson
```
or 

`python3 main.py -rip -ril` once the Install instructions below are completed.  This will load the `assets/database_latest/` collections into MongoDB.  **(Warning: `python3 main.py -rip -ril` is for the import of collections during testing and development period, and should not be used for production!  In production, the databases are already populated, by scripts from other repositories.  In which case, this module merely performs the diffing and similarity comparisons on data that is already stored on MongoDB.)**

Testing data will operate on data in `assets/database_before/` to turn into the collections in `assets/database_after/`.


## Running the Code
Requires a minimum python version of `3.6` to run.

### Install

To install:

`pip3 install -r requirements.txt`

or

`pipenv install`

If `pipenv` is used all subsequent `python3` commands should be replaced with `pipenv run python`.

### Usage Examples

To run sequential label diff and similarity comparisons of diffs to patent claims (from scratch):

`python3 main.py -r`

If `-r` is omitted, labels that have already been processed and stored in `resources/processed_log` with not be reprocessed.

To download latest Orange Book:

`python3 main.py -ob`

To output a list of all NDA numbers from the Orange Book:

`python3 main.py -an <filename>`

To output a list of all patents from the Orange Book:

`python3 main.py -ap <filename>`

To output a list of all patents from the Orange Book as a json file:

`python3 main.py -apj <filename>`

To output a list of missing NDA from the database that are in the Orange Book:

`python3 main.py -mn <filename>`

To output a list of missing patents from the database that are in the Orange Book:

`python3 main.py -mp <filename>`

To output a list of missing patents from the database that are in the Orange Book as a json file:

`python3 main.py -mpj <filename>`

These outputs will require confirmation if the file already exists, so use the following to output all files into the `asset/` directory:

`yes | python3 main.py -ob -an -ap -apj -mn -mp -mpj`

To output all addition and patent claim set from the database excluding all scores.

`python3 main.py -db2file`

To read help:

`python3 main.py -h`

## Running the Tests

Unit tests are run with:

`python3 -m unittest`

## Generating File Export of All DB entries

To export all MongoDB data to file, use the follow.  It is suggested to change the `.env` file to a different `MONGODB_NAME`, since these command will wipe the database, then re-import all patent and label collections.

```
python3 main.py -rip -rip -diff -r
python3 generate_files.py
```

Alternatively, a compressed version of the export with stale data is located at `analysis/db2file.tar.gz`


## Code Formatting
It is recommended to use the [Black Code Formatter](https://github.com/psf/black) which can be installed as a plugin for most IDEs. `pyproject.toml` holds the formatter settings.
