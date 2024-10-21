from django.contrib import admin

from .models import (PriceErrorDistribution, SimulationParameters,
                     SimulationRun, SummaryMetrics, TimeseriesData)

admin.site.register(SimulationParameters)
admin.site.register(SimulationRun)
admin.site.register(TimeseriesData)
admin.site.register(PriceErrorDistribution)
admin.site.register(SummaryMetrics)
