

# scoring_data_processor
Scripts to map changes in drug label to patent claims using the Orange Book Table's of Exclusivity.


## MongoDB Set Up
The connection info for the Mongo DB instance is set in the `.env` file. This should work for a standard MongoDB set up on localhost. If using a different set of DB configs, this file must be updated.

A sample docker set up for mongo, that maps to `localhost:27017` can be found [here](https://github.com/pharmaDB/etl_pipeline). This set up also includes the Mongo Express viewer.

![Mongo Express Labels Info](./assets/mongo_express.png)

To load the bson collection files into the docker container, after running `docker-compose up` per the docker and MongoDB setup [here](https://github.com/pharmaDB/etl_pipeline), find the docker container using:

```docker ps -a```

Assuming that the command above indicates that `mongo_local` is the name of the docker container that is running MongoDB, then confirm that `MONGODB_HOST` and `MONGODB_PORT` from `.env` matches the address and port underneath `PORTS` of `docker ps -a` for `mongo_local`.

Then you may use either of the following two sets of commands to loads the test collections into the databases:

```
docker cp assets/database_before/labels.bson mongo_local:.
docker cp assets/database_before/patents.bson mongo_local:.

docker exec -it mongo_local sh
mongoimport --db test --collection labels --file labels.bson
mongoimport --db test --collection labels --file patents.bson
```
or 

```python3 main.py -rip -ril```

This will load the `database_before` collections into MongoDB.  The following code can then be run to turn collections in `assets/database_before/` into the collections in `assets/database_after/`.

## Running the Code
Requires a minimum python version of `3.6` to run.

To install:

`pip3 install -r requirements.txt`

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

To output a list of missing NDA from the database that are in the Orange Book:

`python3 main.py -mn <filename>`

To output a list of missing patents from the database that are in the Orange Book:

`python3 main.py -mp <filename>`


To read help:

`python3 main.py -h`

## Running the Tests

Unit tests are run with:

`
python -m unittest
`

## Code Formatting
It is recommended to use the [Black Code Formatter](https://github.com/psf/black) which can be installed as a plugin for most IDEs. `pyproject.toml` holds the formatter settings.
