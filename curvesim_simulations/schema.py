import graphene
from graphene_django import DjangoObjectType
from django.db.models import Prefetch
from django.utils import timezone
from typing import Dict, Any
from .types import PoolType, SimulationRunType, TimeseriesDataType
from .models import Pool, SimulationRun, TimeseriesData, SimulationParameters

from graphene import Schema
import json
import hashlib
from django.core.cache import cache


class Query(graphene.ObjectType):
    all_pools = graphene.List(PoolType)
    all_simulations = graphene.List(SimulationRunType)
    simulation_by_pool_and_date = graphene.Field(
        SimulationRunType, pool_name=graphene.String(required=True), date=graphene.String()
    )
    pool_dates = graphene.List(graphene.DateTime, pool_name=graphene.String(required=True))
    simulations_summary = graphene.JSONString()

    def resolve_all_pools(self, info):
        return Pool.objects.filter(enabled=True)

    def resolve_all_simulations(self, info):
        return SimulationRun.objects.all().order_by("-run_date").select_related("parameters")

    @staticmethod
    def _build_params_filter(params_dict):
        filter_kwargs = {}

        for key, value in params_dict.items():
            if value is not None and key in ["A", "D", "fee", "fee_mul", "admin_fee"]:
                if key == "fee" and isinstance(value, list):
                    # Converti i valori fee da intero a float
                    fee_values = [float(v) / 1e10 for v in value]
                    filter_kwargs[f"{key}__in"] = fee_values
                else:
                    filter_kwargs[f"{key}__in"] = value

        return filter_kwargs

    def resolve_simulation_by_pool_and_date(self, info, pool_name, date=None):
        pool = Pool.objects.filter(name=pool_name).first()
        print(f"1. Pool trovato: {pool}")
        if not pool:
            return None

        # Get the parameters that match the pool's params_dict
        filter_kwargs = Query._build_params_filter(pool.params_dict)
        print(f"2. Filter kwargs costruiti: {filter_kwargs}")

        params = SimulationParameters.objects.filter(**filter_kwargs)
        print(f"3. Parametri trovati: {list(params.values())}")

        if date:
            try:
                date_obj = timezone.datetime.strptime(date[:19], "%Y-%m-%dT%H:%M:%S")
                query = SimulationRun.objects.filter(parameters__in=params, run_date__date=date_obj.date())
                print(f"4. Query costruita per data {date_obj.date()}")
                print(f"5. SQL Query: {query.query}")
                result = query.prefetch_related(
                    "parameters",
                    "summary_metrics",
                    Prefetch("timeseries_data", queryset=TimeseriesData.objects.order_by("timestamp")),
                    "price_error_distribution",
                ).first()
                print(f"6. Risultato trovato: {result}")
                return result
            except ValueError as e:
                print(f"Errore nel parsing della data: {e}")
                return None
        else:
            query = query.order_by("-run_date")
            return query.prefetch_related(
                "parameters",
                "summary_metrics",
                Prefetch("timeseries_data", queryset=TimeseriesData.objects.order_by("timestamp")),
                "price_error_distribution",
            ).first()

    def resolve_pool_dates(self, info, pool_name):
        # 1. Prima verifichiamo il pool
        pool = Pool.objects.filter(name=pool_name).first()
        if not pool:
            print(f"Pool non trovato: {pool_name}")
            return []

        # 2. Stampiamo il params_dict per vedere cosa contiene
        print(f"Pool params_dict: {pool.params_dict}")

        # 3. Costruiamo e stampiamo il filtro
        filter_kwargs = Query._build_params_filter(pool.params_dict)
        print(f"Filter kwargs: {filter_kwargs}")

        # 4. Vediamo quanti parametri troviamo
        params = SimulationParameters.objects.filter(**filter_kwargs)
        params_count = params.count()
        print(f"Found {params_count} matching parameters")
        if params_count > 0:
            print(f"First param example: {params.first().__dict__}")

        # 5. Eseguiamo la query finale e vediamo quante date troviamo
        dates = (
            SimulationRun.objects.filter(parameters__in=params)
            .values_list("run_date", flat=True)
            .order_by("-run_date")
            .distinct()
        )
        dates_list = list(dates)
        print(f"Found {len(dates_list)} dates")
        if dates_list:
            print(f"Date example: {dates_list[0]}")

        return dates_list

    def resolve_simulations_summary(self, info) -> Dict[str, Any]:
        pools = Pool.objects.filter(enabled=True)
        simulations = SimulationRun.objects.all().order_by("-run_date").select_related("parameters")

        dates_by_pool = {}
        for pool in pools:
            filter_kwargs = Query._build_params_filter(pool.params_dict)
            params = SimulationParameters.objects.filter(**filter_kwargs)
            dates = list(
                SimulationRun.objects.filter(parameters__in=params)
                .values_list("run_date", flat=True)
                .order_by("-run_date")
                .distinct()
            )
            # Convertiamo i datetime in stringhe ISO
            dates_by_pool[pool.name] = [d.isoformat() for d in dates]

        return {
            "simulations": [
                {
                    "id": sim.pool_name,
                    "run_date": sim.run_date.isoformat(),  # Convertiamo in stringa ISO
                    "A": sim.parameters.A,
                    "fee": sim.parameters.fee,
                    "D": sim.parameters.D,
                    "fee_mul": sim.parameters.fee_mul,
                }
                for sim in simulations
            ],
            "pools": [
                {
                    "name": pool.name,
                    "address": pool.address,
                    "params": pool.params_dict,
                }
                for pool in pools
            ],
            "dates_by_pool": dates_by_pool,
        }


class CachedSchema(Schema):
    def __init__(self, ttl=3600, **kwargs):
        super().__init__(**kwargs)
        self.ttl = ttl

    def execute(self, *args, **kwargs):
        query = kwargs.get("query", args[0] if args else "")
        variables = kwargs.get("variables", {})

        if kwargs.get("operation_name", "").lower() == "mutation":
            return super().execute(*args, **kwargs)

        cache_key = f"graphql:{hashlib.md5(f'{query}:{json.dumps(variables, sort_keys=True)}'.encode()).hexdigest()}"

        cached = cache.get(cache_key)

        if cached:
            return cached

        result = super().execute(*args, **kwargs)
        if result:
            cache.set(cache_key, result, self.ttl)

        return result


schema = CachedSchema(query=Query, ttl=86400)
