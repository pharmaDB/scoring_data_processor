

# scoring_data_processor
Scripts to map changes in drug label to patent claims using the Orange Book Table's of Exclusivity.


## MongoDB Set Up
The connection info for the Mongo DB instance is set in the `.env` file. This should work for a standard MongoDB set up on localhost. If using a different set of DB configs, this file must be updated.

A sample docker set up for mongo, that maps to `localhost:27017` can be found [here](https://github.com/pharmaDB/etl_pipeline). This set up also includes the Mongo Express viewer.

![Mongo Express Labels Info](./assets/mongo_express.png)

To load the bson collection files into the docker container, after running `docker-compose up` per the docker and MongoDB setup [here](https://github.com/pharmaDB/etl_pipeline), find the docker container using:

```docker ps -a```

Assuming that the command above indicates that `mongo_local` is the name of the docker container that is running MongoDB, then from this folder with this README.md run:

```
docker cp assets/database_before/labels.bson mongo_local:.
docker cp assets/database_before/patents.bson mongo_local:.

docker exec -it mongo_local sh
mongoimport --db test --collection labels --file labels.bson
mongoimport --db test --collection labels --file patents.bson
```

This will load the before collections into MongoDB.  The following code can then be run to turn collections in `assets/database_before/` into the collections in `assets/database_after/`.

## Running the Code
Requires a minimum python version of `3.6` to run.

To install:

`pip3 install -r requirements.txt`

### Usage Examples

To run (from scratch):

`python3 main.py -r`

To download latest Orange Book:

`python3 main.py -ob`

To read help

`python3 main.py -h`

## Running the Tests
```
python -m unittest
```

## Code Formatting
It is recommended to use the [Black Code Formatter](https://github.com/psf/black) which can be installed as a plugin for most IDEs. `pyproject.toml` holds the formatter settings.
