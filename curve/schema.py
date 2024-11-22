from datetime import datetime

import graphene
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F
from django.db.models.functions import JSONObject
from graphene import Int, String

from core.models import Chain
from curve.models import DebtCeiling, ControllerMetadata, CurveMetrics, CurveMarketSnapshot, CurveLlammaTrades, \
    CurveLlammaEvents, CurveCr
from curve.types import DebtCeilingType, ControllerMetadataType, CurveMetricsType, AggregatedSnapshotsType, \
    SnapshotType, CurveLlammaTradesType, CurveLlammaEventsType, CurveCrType


class Query(graphene.ObjectType):
    debt_ceiling = graphene.List(DebtCeilingType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                 chain=String(), controller=String())
    controller_metadata = graphene.List(ControllerMetadataType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                        chain=String(), controller=String())
    curve_metrics = graphene.List(CurveMetricsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String())
    market_snapshots = graphene.List(AggregatedSnapshotsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                     chain=String(), controller=String())
    llamma_trades = graphene.List(CurveLlammaTradesType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                  chain=String(), controller=String())
    llamma_events = graphene.List(CurveLlammaEventsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                  chain=String(), controller=String())
    cr = graphene.List(CurveCrType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                       chain=String(), controller=String())

    def resolve_debt_ceiling(self, info, start_time=None, end_time=None, limit=None, sort_by=None, chain=None, controller=None):
        queryset = DebtCeiling.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller=controller)
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
            queryset = queryset.filter(controller=controller)
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
        queryset = CurveMarketSnapshot.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller=controller)

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
                    JSONObject(snapshot=F('data'), timestamp=F('timestamp')),
                    ordering=sort_by
                )
            )
        )

        result = []
        for data in aggregated_data:
            snapshots = [
                SnapshotType(
                    snapshot=item['snapshot'],
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

    def resolve_llamma_trades(self, info, start_time=None, end_time=None, limit=None, sort_by=None,
                              chain=None, controller=None):
        queryset = CurveLlammaTrades.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller=controller)

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
            queryset = queryset.filter(controller=controller)

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
            queryset = queryset.filter(controller=controller)

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


schema = graphene.Schema(query=Query)
