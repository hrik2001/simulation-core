import graphene
from graphene import ObjectType, String, Int, UUID
from .models import Borrow, AuctionStarted, AuctionFinished, Repay
from .types import arcadia__Borrow, arcadia__AuctionStarted, arcadia__AuctionFinished, arcadia__Repay

class Query(ObjectType):
    all_borrows = graphene.List(arcadia__Borrow, pool_address=String(), account=String(), by=String(), to=String())
    all_auctions_started = graphene.List(arcadia__AuctionStarted, pool_address=String(), account=String(), creditor=String())
    all_auctions_finished = graphene.List(arcadia__AuctionFinished, pool_address=String(), account=String(), creditor=String())
    all_repays = graphene.List(arcadia__Repay, pool_address=String(), account=String(), from_address=String())

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

schema = graphene.Schema(query=Query)