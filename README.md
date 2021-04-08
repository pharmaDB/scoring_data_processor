

# scoring_data_processor
Scripts to map drug label sections to patent claims using the Orange Book Table's of Exclusivity and the scispaCy model.


## MongoDB Set Up
The connection info for the Mongo DB instance is set in the `.env` file. This should work for a standard MongoDB set up on localhost. If using a different set of DB configs, this file must be updated.

A sample docker set up for mongo, that maps to `localhost:27017` can be found [here](https://github.com/pharmaDB/etl_pipeline). This set up also includes the Mongo Express viewer.

![Mongo Express Labels Info](./assets/mongo_express.png)

## Running the Code
Requires a minimum python version of `3.6` to run.
1. `pip3 install -r requirements.txt`
2. For usage and args, run `python3 main.py`


## Running the Tests
```
python -m unittest
```

### Usage Examples

[TBD]

## Code Formatting
It is recommended to use the [Black Code Formatter](https://github.com/psf/black) which can be installed as a plugin for most IDEs. `pyproject.toml` holds the formatter settings.
