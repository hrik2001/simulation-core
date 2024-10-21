from django.contrib import admin

from .models import (AccountAssets, AuctionFinished, AuctionStarted, Borrow,
                     MetricSnapshot, OracleSnapshot, Repay, SimSnapshot)

admin.site.register(AuctionStarted)
admin.site.register(AuctionFinished)
admin.site.register(Borrow)
admin.site.register(Repay)
admin.site.register(AccountAssets)
admin.site.register(MetricSnapshot)
admin.site.register(SimSnapshot)
admin.site.register(OracleSnapshot)
