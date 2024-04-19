from django.contrib import admin
from .models import (
    AuctionStarted,
    AuctionFinished,
    Borrow,
    Repay,
)

admin.site.register(AuctionStarted)
admin.site.register(AuctionFinished)
admin.site.register(Borrow)
admin.site.register(Repay)