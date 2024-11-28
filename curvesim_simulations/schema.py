import graphene
from graphene_django import DjangoObjectType
from django.db.models import Prefetch
from django.utils import timezone
from typing import Dict, Any
from .types import PoolType, SimulationRunType, TimeseriesDataType
from .models import Pool, SimulationRun, TimeseriesData

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

    def resolve_simulation_by_pool_and_date(self, info, pool_name, date=None):
        pool = Pool.objects.filter(name=pool_name).first()
        if not pool:
            return None

        query = SimulationRun.objects.filter(parameters__params_dict=pool.params_dict)

        if date:
            try:
                date_obj = timezone.datetime.strptime(date, "%Y-%m-%d").date()
                query = query.filter(run_date__date=date_obj)
            except ValueError:
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
        pool = Pool.objects.filter(name=pool_name).first()
        if not pool:
            return []

        return (
            SimulationRun.objects.filter(parameters__params_dict=pool.params_dict)
            .values_list("run_date", flat=True)
            .order_by("-run_date")
            .distinct()
        )

    def resolve_simulations_summary(self, info) -> Dict[str, Any]:
        pools = Pool.objects.filter(enabled=True)
        simulations = SimulationRun.objects.all().order_by("-run_date").select_related("parameters")

        return {
            "simulations": [
                {
                    "id": sim.pool_name,
                    "run_date": sim.run_date,
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
            "dates_by_pool": {
                pool.name: list(
                    SimulationRun.objects.filter(parameters__params_dict=pool.params_dict)
                    .values_list("run_date", flat=True)
                    .order_by("-run_date")
                    .distinct()
                )
                for pool in pools
            },
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
