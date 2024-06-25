from graphene_django.types import DjangoObjectType
from .models import (
    Borrow,
    AuctionStarted,
    AuctionFinished,
    Repay,
    MetricSnapshot,
    SimSnapshot,
    OracleSnapshot,
    AccountAssets
)

class arcadia__Borrow(DjangoObjectType):
    class Meta:
        model = Borrow
        fields = "__all__" 

class arcadia__AuctionStarted(DjangoObjectType):
    class Meta:
        model = AuctionStarted
        fields = "__all__" 

class arcadia__AuctionFinished(DjangoObjectType):
    class Meta:
        model = AuctionFinished
        fields = "__all__" 

class arcadia__Repay(DjangoObjectType):
    class Meta:
        model = Repay
        fields = "__all__" 

class arcadia__MetricSnapshot(DjangoObjectType):
    class Meta:
        model = MetricSnapshot
        fields = "__all__"

class arcadia__SimSnapshot(DjangoObjectType):
    class Meta:
        model = SimSnapshot
        fields = "__all__"

class arcadia__OracleSnapshot(DjangoObjectType):
    class Meta:
        model = OracleSnapshot
        fields = "__all__"
        
class arcadia__AccountAssets(DjangoObjectType):
    class Meta:
        model = AccountAssets
        fields = "__all__"