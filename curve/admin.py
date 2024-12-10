from django.contrib import admin

from curve.models import Top5Debt, CurveMarketSnapshot, CurveMetrics, ControllerMetadata, \
    CurveMarketSoftLiquidations, CurveMarketLosses, CurveMarkets, CurveLlammaEvents, CurveCr, CurveLlammaTrades

admin.site.register(Top5Debt)
admin.site.register(ControllerMetadata)
admin.site.register(CurveMetrics)
admin.site.register(CurveMarketSnapshot)
admin.site.register(CurveLlammaTrades)
admin.site.register(CurveLlammaEvents)
admin.site.register(CurveCr)
admin.site.register(CurveMarkets)
admin.site.register(CurveMarketSoftLiquidations)
admin.site.register(CurveMarketLosses)
