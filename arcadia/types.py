from graphene_django.types import DjangoObjectType
from .models import (
    Borrow,
    AuctionStarted,
    AuctionFinished,
    Repay
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