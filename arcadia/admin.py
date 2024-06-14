from django.contrib import admin
from .models import (
    AuctionStarted,
    AuctionFinished,
    Borrow,
    Repay,
    AccountAssets,
    MetricSnapshot,
    SimSnapshot
)

admin.site.register(AuctionStarted)
admin.site.register(AuctionFinished)
admin.site.register(Borrow)
admin.site.register(Repay)
admin.site.register(AccountAssets)
admin.site.register(MetricSnapshot)
admin.site.register(SimSnapshot)