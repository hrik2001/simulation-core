import csv
import os.path
from datetime import datetime

import graphene
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F
from django.db.models.functions import JSONObject
from graphene import Int, String

from core.models import Chain
from curve.models import Top5Debt, ControllerMetadata, CurveMetrics, CurveMarketSnapshot, CurveLlammaTrades, \
    CurveLlammaEvents, CurveCr, CurveMarkets, CurveMarketSoftLiquidations, CurveMarketLosses, CurveScores
from curve.tasks import controller_asset_map
from curve.types import Top5DebtType, ControllerMetadataType, CurveMetricsType, AggregatedSnapshotsType, \
    SnapshotType, CurveLlammaTradesType, CurveLlammaEventsType, CurveCrType, CurveMarketsType, CurveScoresType, \
    CurveDebtCeilingScoresType


def _curve_market_helper(model, start_time=None, end_time=None, limit=None, sort_by=None,
                         chain=None, controller=None):
    queryset = model.objects.all()

    if chain is None:
        chain = "ethereum"
    chain_obj = Chain.objects.get(chain_name__iexact=chain)
    queryset = queryset.filter(chain=chain_obj)

    if controller:
        queryset = queryset.filter(controller__iexact=controller)

    if start_time:
        queryset = queryset.filter(timestamp__gte=datetime.fromtimestamp(start_time))
    if end_time:
        queryset = queryset.filter(timestamp__lte=datetime.fromtimestamp(end_time))
    if limit:
        queryset = queryset[:limit]
    if not sort_by:
        sort_by = "timestamp"

    aggregated_data = (
        queryset
        .values('controller')
        .annotate(
            snapshots=ArrayAgg(
                JSONObject(data=F('data'), timestamp=F('timestamp')),
                ordering=sort_by
            )
        )
    )

    result = []
    for data in aggregated_data:
        snapshots = [
            SnapshotType(
                data=item['data'],
                timestamp=item['timestamp'],
            )
            for item in data['snapshots']
        ]
        result.append(AggregatedSnapshotsType(
            chain=chain,
            controller=data['controller'],
            snapshots=snapshots
        ))

    return result


class Query(graphene.ObjectType):
    markets = graphene.List(CurveMarketsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String())
    top_5_debt = graphene.List(Top5DebtType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                 chain=String(), controller=String())
    controller_metadata = graphene.List(ControllerMetadataType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                        chain=String(), controller=String())
    curve_metrics = graphene.List(CurveMetricsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String())
    market_snapshots = graphene.List(AggregatedSnapshotsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                     chain=String(), controller=String())
    soft_liquidations = graphene.List(AggregatedSnapshotsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                      chain=String(), controller=String())
    market_losses = graphene.List(AggregatedSnapshotsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                  chain=String(), controller=String())
    llamma_trades = graphene.List(CurveLlammaTradesType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                  chain=String(), controller=String())
    llamma_events = graphene.List(CurveLlammaEventsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                  chain=String(), controller=String())
    cr = graphene.List(CurveCrType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                       chain=String(), controller=String())
    scores = graphene.List(CurveScoresType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                           chain=String(), controller=String())
    debt_ceiling_score = graphene.List(CurveDebtCeilingScoresType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                       chain=String(), controller=String())

    def resolve_markets(self, info, start_time=None, end_time=None, limit=None, sort_by=None, chain=None):
        queryset = CurveMarkets.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('created_at')
        if limit:
            queryset = queryset[:limit]

        return queryset

    def resolve_top_5_debt(self, info, start_time=None, end_time=None, limit=None, sort_by=None, chain=None, controller=None):
        queryset = Top5Debt.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller__iexact=controller)
        if start_time:
            queryset = queryset.filter(timestamp__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(timestamp__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('timestamp')
        if limit:
            queryset = queryset[:limit]

        return queryset

    def resolve_controller_metadata(self, info, start_time=None, end_time=None, limit=None, sort_by=None, chain=None, controller=None):
        queryset = ControllerMetadata.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller__iexact=controller)
        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('created_at')
        if limit:
            queryset = queryset[:limit]

        return queryset

    def resolve_curve_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = CurveMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('created_at')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_market_snapshots(self, info, start_time=None, end_time=None, limit=None, sort_by=None,
                                 chain=None, controller=None):
        return _curve_market_helper(CurveMarketSnapshot, start_time, end_time, limit, sort_by, chain, controller)

    def resolve_soft_liquidations(self, info, start_time=None, end_time=None, limit=None, sort_by=None,
                                  chain=None, controller=None):
        return _curve_market_helper(CurveMarketSoftLiquidations, start_time, end_time, limit, sort_by, chain, controller)

    def resolve_market_losses(self, info, start_time=None, end_time=None, limit=None, sort_by=None,
                              chain=None, controller=None):
        return _curve_market_helper(CurveMarketLosses, start_time, end_time, limit, sort_by, chain, controller)

    def resolve_llamma_trades(self, info, start_time=None, end_time=None, limit=None, sort_by=None,
                              chain=None, controller=None):
        queryset = CurveLlammaTrades.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller__iexact=controller)

        if start_time:
            queryset = queryset.filter(day__gte=datetime.fromtimestamp(start_time).date())
        if end_time:
            queryset = queryset.filter(day__lte=datetime.fromtimestamp(end_time).date())
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('day')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_llamma_events(self, info, start_time=None, end_time=None, limit=None, sort_by=None,
                              chain=None, controller=None):
        queryset = CurveLlammaEvents.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller__iexact=controller)

        if start_time:
            queryset = queryset.filter(day__gte=datetime.fromtimestamp(start_time).date())
        if end_time:
            queryset = queryset.filter(day__lte=datetime.fromtimestamp(end_time).date())
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('day')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_cr(self, info, start_time=None, end_time=None, limit=None, sort_by=None,
                   chain=None, controller=None):
        queryset = CurveCr.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller__iexact=controller)

        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('created_at')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_scores(self, info, start_time=None, end_time=None, limit=None, sort_by=None,
                       chain=None, controller=None):
        queryset = CurveScores.objects.all()
        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller__iexact=controller)

        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('created_at')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_debt_ceiling_score(self, info, start_time=None, end_time=None, limit=None, sort_by=None,
                                   chain=None, controller=None):
        with open(os.path.join(os.path.dirname(__file__), "debt_ceiling_score.csv"), "r") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                rows.append({**row, "keep": True})

        if start_time:
            for row in rows:
                if row["timestamp"] < start_time:
                    row["keep"] = False

        if end_time:
            for row in rows:
                if row["timestamp"] > end_time:
                    row["keep"] = False

        results = []
        for row in rows:
            if not row["keep"]:
               continue
            for key, value in row.items():
                if key == "timestamp" or key == "keep":
                    continue
                if controller and key != controller:
                    continue
                results.append({
                    "chain": "ethereum",
                    "createdAt": int(row["timestamp"]),
                    "controller": controller_asset_map[key],
                    "score": str(value),
                })

        if sort_by:
            if sort_by.startswith("-"):
                sort_by = sort_by[1:]
                reverse = True
            else:
                reverse = False
            results = sorted(results, key=lambda x: x[sort_by], reverse=reverse)

        x = [CurveDebtCeilingScoresType(**r) for r in results[:limit]]
        return x

schema = graphene.Schema(query=Query)
