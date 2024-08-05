from django.views.generic import ListView
from django.http import JsonResponse
from .models import DexQuote

class DexQuoteListView(ListView):
    model = DexQuote
    MAX_ROWS = 34560

    def get_queryset(self):
        queryset = super().get_queryset()
        start_timestamp = self.request.GET.get('start')
        end_timestamp = self.request.GET.get('end')
        src = self.request.GET.get("src")
        dst = self.request.GET.get("dst")
        dex_aggregator = self.request.GET.get("dex_aggregator")

        if start_timestamp:
            try:
                start_timestamp = int(start_timestamp)
                queryset = queryset.filter(timestamp__gte=start_timestamp)
            except ValueError:
                return queryset.none()
        if end_timestamp:
            try:
                end_timestamp = int(end_timestamp)
                queryset = queryset.filter(timestamp__lte=end_timestamp)
            except ValueError:
                return queryset.none()
        if src:
            try:
                queryset = queryset.filter(src__iexact=src)
            except ValueError:
                return queryset.none()
        if dst:
            try:
                queryset = queryset.filter(dst__iexact=dst)
            except ValueError:
                return queryset.none()
        if dex_aggregator:
            try:
                queryset = queryset.filter(dex_aggregator__iexact=dex_aggregator)
            except ValueError:
                return queryset.none()

        # Limit the number of rows to MAX_ROWS
        if queryset.count() > self.MAX_ROWS:
            queryset = queryset[:self.MAX_ROWS]

        return queryset

    def render_to_response(self, context, **response_kwargs):
        quotes = context['object_list'].values(
            'dst', 'in_amount', 'out_amount', 'price', 'price_impact', 'src', 'timestamp'
        )

        quotes_list = list(quotes)
        for quote in quotes_list:
            quote['in_amount'] = float(quote['in_amount'])
            quote['out_amount'] = float(quote['out_amount'])

        return JsonResponse(quotes_list, safe=False)

