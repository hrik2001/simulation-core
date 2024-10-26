from django.contrib import admin
from .models import SimulationParameters, SimulationRun, TimeseriesData, PriceErrorDistribution, SummaryMetrics

admin.site.register(SimulationParameters)
admin.site.register(SimulationRun)
admin.site.register(TimeseriesData)
admin.site.register(PriceErrorDistribution)
admin.site.register(SummaryMetrics)
