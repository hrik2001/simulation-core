
from celery import shared_task
from django.core.cache import cache
import requests
import time
import logging
from pydantic import BaseModel, ValidationError, Field
from typing import List, Optional

logger = logging.getLogger(__name__)

ETHEREUM_MAX_VALIDATOR_COUNT = 3_750_000

@shared_task(name="cache_ecps_parameters_job", time_limit=None, soft_time_limit=None)
def cache_ecps_parameters_job(*args, **kwargs) -> None:
	cache_ecps_parameters(*args, **kwargs)

def cache_ecps_parameters(rated_network_api_key: str, blockpi_network_api_key: str) -> None:

	ecps_parameters = {}

	network_state = get_network_state(rated_network_api_key)
	if network_state:
		ecps_parameters['staking_share'] = network_state.results[0].validator_count / ETHEREUM_MAX_VALIDATOR_COUNT
		ecps_parameters['client_diversity'] = [cp.dict() for cp in network_state.results[0].client_percentages]
		
	time.sleep(1)

	validator_geo_distribution = get_geographical_distribution(rated_network_api_key)
	if validator_geo_distribution:
		ecps_parameters['validator_geo_distribution'] = [loc.dict() for loc in validator_geo_distribution]

	ecps_parameters['exit_queue_length'] = get_exit_queue_length(blockpi_network_api_key)

	cache.set('ecps_parameters', ecps_parameters, timeout=None)

class ClientPercentage(BaseModel):
    client: str
    percentage: float

class RatedNetworkData(BaseModel):
	validator_count: int = Field(alias="validatorCount")
	client_percentages: List[ClientPercentage] = Field(alias="clientPercentages")

class RatedNetworkApiResponse(BaseModel):
	results: List[RatedNetworkData]

def get_network_state(rated_network_api_key: str) -> RatedNetworkApiResponse | None:

	url = 'https://api.rated.network/v1/eth?window=1d'
	headers = {
		'Content-Type': 'application/json',
		'X-Rated-Network': 'mainnet',
		'Authorization': f'Bearer {rated_network_api_key}'
	}

	response = requests.get(url, headers=headers)
	
	if response.status_code == 200:

		try:
			response = RatedNetworkApiResponse(**response.json())
			if len(response.results) == 1:
				return response
		except ValidationError as e:
			logger.error(f'[ECPS] get_network_state: response validation error: {e.errors()}')
			return None

	else:
		logger.error(f'[ECPS] get_network_state: unexpected {str(response.status_code)} error code: {response.json()}')
		return None

class LocationData(BaseModel):
    country: str
    country_code: str = Field(alias="countryCode")
    validator_share: float = Field(alias="validatorShare")

class RatedGeoApiResponse(BaseModel):
	results: List[LocationData]

def get_geographical_distribution(rated_network_api_key: str) -> List[LocationData] | None:

	url = 'https://api.rated.network/v1/eth/geographicalDistributions?distributionType=all'
	headers = {
		'Content-Type': 'application/json',
		'X-Rated-Network': 'mainnet',
		'Authorization': f'Bearer {rated_network_api_key}'
	}

	response = requests.get(url, headers=headers)

	if response.status_code == 200:

		try:
			return RatedGeoApiResponse(**response.json()).results
		except ValidationError as e:
			logger.error(f'[ECPS] get_geographical_distribution: response validation error: {e.errors()}')
			return None

	else:
		logger.error(f'[ECPS] get_geographical_distribution: unexpected {str(response.status_code)} error code: {response.json()}')
		return None

class ValidatorMessage(BaseModel):
    epoch: str

class ValidatorData(BaseModel):
    message: ValidatorMessage

class BlockpiApiResponse(BaseModel):
    data: List[ValidatorData]

def get_exit_queue_length(blockpi_network_api_key: str) -> int | None:

	url = f'https://ethereum-beacon.blockpi.network/rpc/v1/{blockpi_network_api_key}/eth/v1/beacon/pool/voluntary_exits'

	response = requests.get(url, headers={'Content-Type': 'application/json'})

	if response.status_code == 200:

		try:
			api_response = BlockpiApiResponse(**response.json())
			validator_count = sum(1 for validator in api_response.data if validator.message.epoch != "0")
			return validator_count
            
		except ValidationError as e:
			logger.error(f'[ECPS] get_exit_queue_length: response validation error: {e.errors()}')
			return None

	else:
		logger.error(f'[ECPS] get_exit_queue_length: unexpected {str(response.status_code)} error code: {response.json()}')
		return None