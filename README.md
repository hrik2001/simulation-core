# LlamaRisk Core Component
This repository contains code to create ETL pipelines for EVM events. It stores it in an sql database (could be any sql backend) and serves it via GraphQL.

For each protocol, for which data needs to be loaded in the db, a django app needs to be created with required models and schema types so that logs can be
stored in the database and can be served via GraphQL queries. Such design was chosen for having separation of concern when it comes to models and schema
that are unique to each protocol.

The core component also requires a persistent directory where it will store all the raw data from logs from chain (this is data before the transformation).
For now it's assumed to be `./media` directory.

## Installation
The codebase assumes that the python version is 3.10.12 (having any release of 3.10 would be fine). 

It is recommended to use a virtual environment for developing this. To create one, kindly run the following command at the root of the project

```
python3.10 -m venv .venv
```

To activate the virtual environment, kindly run the following command
```
source .venv/bin/activate
```
To install the dependencies, the following command should install it all
```
pip install -r requirements.txt
```
To update the `requirements.txt`, the following command should be called
```
pip freeze > requirements.txt
```

## Running
You can run the core component locally by running `./dev.sh`, you can also check the job queue using `./flower_dev.sh`. Please make sure that redis is already running.
`./dev.sh` will start the django backend locally along with an instance of scheduler and worker.
