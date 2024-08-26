from django.contrib import admin

from ethena.models import ChainMetrics, CollateralMetrics, ReserveFundMetrics, ReserveFundBreakdown, UniswapMetrics, \
    CurvePoolMetrics, CurvePoolSnapshots

admin.site.register(ChainMetrics)
admin.site.register(CollateralMetrics)
admin.site.register(ReserveFundMetrics)
admin.site.register(ReserveFundBreakdown)
admin.site.register(UniswapMetrics)
admin.site.register(CurvePoolMetrics)
admin.site.register(CurvePoolSnapshots)
