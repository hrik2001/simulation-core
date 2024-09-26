from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from django.http import JsonResponse
from .models import DexQuote

class DexQuoteListView(ListView):
    model = DexQuote
    DEFAULT_MAX_ROWS = 10000

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
            queryset = queryset.filter(src__iexact=src)
        if dst:
            queryset = queryset.filter(dst__iexact=dst)
        if dex_aggregator:
            queryset = queryset.filter(dex_aggregator__iexact=dex_aggregator)

        queryset = queryset.order_by('-timestamp')

        max_rows = self.request.GET.get('max_rows', self.DEFAULT_MAX_ROWS)
        try:
            max_rows = int(max_rows)
        except ValueError:
            max_rows = self.DEFAULT_MAX_ROWS

        page = self.request.GET.get('page', 1)
        paginator = Paginator(queryset, max_rows)

        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)
        except EmptyPage:
            queryset = []

        return queryset

    def render_to_response(self, context, **response_kwargs):
        # Get the paginated queryset
        page_obj = context['object_list']

        # Access the object_list from the paginator's Page object and use values()
        quotes_list = list(page_obj.object_list.values(
            'dst', 'in_amount', 'out_amount', 'price', 'price_impact', 'src', 'timestamp'
        ))

        for quote in quotes_list:
            quote['in_amount'] = float(quote['in_amount'])
            quote['out_amount'] = float(quote['out_amount'])

        return JsonResponse(quotes_list, safe=False)
