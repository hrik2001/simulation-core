from celery import shared_task
from .models import Pool
from django.utils import timezone
import logging

import curvesim
from curvesim.metrics.results.sim_results import SimResults


@shared_task(name="run_simulation_task")
def run_simulation_task():
    print(f"Simulation task started at {timezone.now()}")

    # Fetch enabled pools
    enabled_pools = Pool.objects.filter(enabled=True)

    for pool in enabled_pools:
        logging.info(f"Running simulation for pool {pool.name}")
        results = _run_simulation(pool)

    return f"Found {enabled_pools.count()} enabled pools"


def _run_simulation(pool: Pool):
    # Fetch the latest simulation run
    pool_obj = curvesim.pool.get(pool.address)

    # Estraiamo i parametri dal params_dict
    A_params = pool.params_dict["A"]  # lista [100, 200]
    fee_params = pool.params_dict["fee"]  # lista [0.01]

    raw_results: SimResults = curvesim.autosim(pool.address, A=[1707629], fee=[1000000])
    return _format_results(raw_results)


def _format_results(raw_results: SimResults):
    # Estraiamo i dati da raw_results e li formattiamo per salvarli nel database
    pass
