from django.apps import AppConfig
from .tasks import cache_ecps_parameters_job
from dotenv import load_dotenv
import os

class EcpsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ecps'

    def ready(self):

        load_dotenv()
        rated_network_api_key = os.getenv('RATED_NETWORK_API_KEY')
        blockpi_network_api_key = os.getenv('BLOCKPI_NETWORK_API_KEY')
        cache_ecps_parameters_job(rated_network_api_key, blockpi_network_api_key)
