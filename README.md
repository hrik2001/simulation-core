# LlamaRisk Core Component
This repository contains code to create ETL pipelines for EVM events. It stores it in an sql database (could be any sql backend) and serves it via GraphQL.

For each protocol, for which data needs to be loaded in the db, a django app needs to be created with required models and schema types so that logs can be
stored in the database and can be served via GraphQL queries. Such design was chosen for having separation of concern when it comes to models and schema
that are unique to each protocol.

The core component also requires a persistent directory where it will store all the raw data from logs from chain (this is data before the transformation).
For now it's assumed to be `./media` directory.

## Installation
To run the codebase, make sure that you have docker. To run the codebase locally run the following command
```
docker-compose build
```
The above command builds the docker images, once done, the whole backend can be run locally by the following command
```
docker-compose up
```