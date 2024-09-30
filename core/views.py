from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from django.http import JsonResponse
from django.db.models import Q
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
        tokens = self.request.GET.get("tokens")  # Comma-separated token addresses

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

        if tokens:
            token_list = [token.strip() for token in tokens.split(",")]
            src_queryset = queryset.filter(src__iregex=r'^(' + '|'.join(token_list) + ')$')
            dst_queryset = queryset.filter(dst__iregex=r'^(' + '|'.join(token_list) + ')$')
            queryset = src_queryset & dst_queryset

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
            queryset = paginator.page(paginator.num_pages)

        return queryset

    def render_to_response(self, context, **response_kwargs):
        context = self.get_context_data()
        page_obj = context.get('object_list', None)

        if page_obj is not None:
            quotes_list = list(page_obj.object_list.values(
                'dst', 'in_amount', 'out_amount', 'price', 'price_impact', 'src', 'timestamp'
            ))

            for quote in quotes_list:
                quote['in_amount'] = float(quote['in_amount'])
                quote['out_amount'] = float(quote['out_amount'])

            pagination_info = {
                'current_page': page_obj.number,
                'total_pages': page_obj.paginator.num_pages,
                'total_items': page_obj.paginator.count,
            }

            return JsonResponse({
                'quotes': quotes_list,
                'pagination': pagination_info
            }, safe=False)

        else:
            return JsonResponse({
                'quotes': [],
                'pagination': {
                    'current_page': 0,
                    'total_pages': 0,
                    'total_items': 0
                }
            }, safe=False)
