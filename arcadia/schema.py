from datetime import datetime
import graphene
from graphene import ObjectType, String, Int, UUID
from .models import Borrow, AuctionStarted, AuctionFinished, Repay, MetricSnapshot, SimSnapshot, OracleSnapshot
from .types import arcadia__Borrow, arcadia__AuctionStarted, arcadia__AuctionFinished, arcadia__Repay, arcadia__MetricSnapshot, arcadia__SimSnapshot, arcadia__OracleSnapshot

class Query(ObjectType):
    all_borrows = graphene.List(arcadia__Borrow, pool_address=String(), account=String(), by=String(), to=String())
    all_auctions_started = graphene.List(arcadia__AuctionStarted, pool_address=String(), account=String(), creditor=String())
    all_auctions_finished = graphene.List(arcadia__AuctionFinished, pool_address=String(), account=String(), creditor=String())
    all_repays = graphene.List(arcadia__Repay, pool_address=String(), account=String(), from_address=String())
    all_snapshots = graphene.List(arcadia__MetricSnapshot, start_time=Int(), end_time=Int())
    all_sim_snapshots = graphene.List(arcadia__SimSnapshot, sim_id=String(), start_time=Int(), end_time=Int())
    all_oracle_snapshots = graphene.List(arcadia__OracleSnapshot, start_time=Int(), end_time=Int())

    def resolve_all_snapshots(self, info, start_time=None, end_time=None):
        queryset = MetricSnapshot.objects.all()
        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        return queryset.order_by('created_at')

    def resolve_all_borrows(self, info, pool_address=None, account=None, by=None, to=None):
        queryset = Borrow.objects.all()
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        if account:
            queryset = queryset.filter(account=account)
        if by:
            queryset = queryset.filter(by=by)
        if to:
            queryset = queryset.filter(to=to)
        return queryset.order_by('block_number')

    def resolve_all_auctions_started(self, info, pool_address=None, account=None, creditor=None):
        queryset = AuctionStarted.objects.all()
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        if account:
            queryset = queryset.filter(account=account)
        if creditor:
            queryset = queryset.filter(creditor=creditor)
        return queryset.order_by('block_number')

    def resolve_all_auctions_finished(self, info, pool_address=None, account=None, creditor=None):
        queryset = AuctionFinished.objects.all()
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        if account:
            queryset = queryset.filter(account=account)
        if creditor:
            queryset = queryset.filter(creditor=creditor)
        return queryset.order_by('block_number')

    def resolve_all_repays(self, info, pool_address=None, account=None, from_address=None):
        queryset = Repay.objects.all()
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        if account:
            queryset = queryset.filter(account=account)
        if from_address:
            queryset = queryset.filter(from_address=from_address)
        return queryset.order_by('block_number')

    def resolve_all_sim_snapshots(self, info, sim_id=None, start_time=None, end_time=None):
        queryset = SimSnapshot.objects.all()
        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        if sim_id:
            queryset = queryset.filter(sim_id=sim_id)
        return queryset.order_by('created_at')

    def resolve_all_oracle_snapshots(self, info, start_time=None, end_time=None):
        queryset = OracleSnapshot.objects.all()
        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        return queryset.order_by('created_at')

schema = graphene.Schema(query=Query)