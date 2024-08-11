from django.contrib import admin

from ethena.models import ChainMetrics, CollateralMetrics, ReserveFundMetrics

admin.site.register(ChainMetrics)
admin.site.register(CollateralMetrics)
admin.site.register(ReserveFundMetrics)
