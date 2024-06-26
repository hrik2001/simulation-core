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
If you have made any local changes, then rebuild again and do `docker-compose up`

## Usage
Right now, there's an example uniswap django app that should be used as reference on how to create new apps. First we have to create an admin account.
```
docker-compose exec web python manage.py createsuperuser
```
Once the account is created, log into it at `localhost:8000/admin`, after this has been done, you would be presented with this screen
![image](https://github.com/llama-risk/simulation-core/assets/11733600/8f2d1c93-529d-470c-9215-f0c2e0c19ac5)

The core component codebase comes with a task that can be used to fetch any event from any contract address from any start block to end block, so let us do that first.

Go the the `Chains` section in Core, to add details about various chains, for our example, we will add ethereum

Press add chain button, and fill the form that has been presented
![image](https://github.com/llama-risk/simulation-core/assets/11733600/1116af1e-9e07-4260-b06b-13643adc4379)

Now let's go to "Periodic Tasks" menu from the admin root page, and let's add a task

Name your task something, we are going to go with this config for the example
![image](https://github.com/llama-risk/simulation-core/assets/11733600/08dfb4a8-bfdd-409e-af4f-29bff9657a76)

Exapand the arguement section of the page, and add the following as arguement
![image](https://github.com/llama-risk/simulation-core/assets/11733600/0b63c7fc-0d2e-4e22-a1b9-c45d914ad498)
```json
{
"contract_address": "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f",
"chain_id": 1,
"event_signature": "PairCreated(address indexed token0, address indexed token1, address pair, uint)",
"label": "uniswap_v2_pools",
"start_block": 19000000
}
```
Similarly you can create tasks to ingest any events you want to. Once the events are ingested, you need a task that would transform and load it to the database. For that
kindly check out `task__uniswap_pair_created` task to get an idea on how to write transformer and loader.

At `uniswap/schema.py` you can check out how to write graphql queries. You can try running [this](http://127.0.0.1:8000/protocols/uniswap/graphql/#query=query%20%7B%0A%20%20searchPairs%20%7B%0A%20%20%20%20token0%0A%20%20%20%20token1%0A%20%20%20%20pair%0A%20%20%7D%0A%7D%0A) right off the bat once the TL task has been run

### Executing a task from the command line

To execute a task from the command line, run the following command:
```bash
# docker-compose exec web celery -A sim_core call <task_name>
docker-compose exec web celery -A sim_core call arcadia.tasks.task__arcadia__metric_snapshot
```

## Contributing

### Adding a field to an existing model (or creating a new model)

Add the field to the model in the appropriate app's `models.py` file (ie `uniswap/models.py`)

Update the relevant tasks in the `tasks` directory (ie unideswap/tasks.py) to construct the updated model

Run the following command to apply the changes to the database:
```bash
# First ensure that the web container is running
docker-compose build && docker-compose up

# Then run the following command to apply the changes to the database
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```