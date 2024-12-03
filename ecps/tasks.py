from .client import get_network_state, get_geographical_distribution, get_exit_queue_length
from celery import shared_task
from django.core.cache import cache
import time

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

	cache.set('ecps_parameters', ecps_parameters, timeout=86400) # 24 hours expiry
