from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from django.http import JsonResponse
from django.db.models import Q, F
from .models import DexQuote, DexQuotePair, Chain

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
            if start_timestamp.isdigit():
                queryset = queryset.filter(timestamp__gte=int(start_timestamp))
            else:
                return queryset.none()

        if end_timestamp:
            if end_timestamp.isdigit():
                queryset = queryset.filter(timestamp__lte=int(end_timestamp))
            else:
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

        max_rows = self.request.GET.get('max_rows')
        if max_rows:
            if max_rows.isdigit():
                max_rows = int(max_rows)
            else:
                return queryset.none()
        else:
            max_rows = self.DEFAULT_MAX_ROWS
            
        paginator = Paginator(queryset, max_rows)

        page = self.request.GET.get('page')
        if page:
            if page.isdigit():
                queryset = paginator.page(int(page))
            else:
                return queryset.none()
        else:
            queryset = paginator.page(1)

        return queryset

    def render_to_response(self, context, **response_kwargs):
        context = self.get_context_data()
        page_obj = context.get('object_list', None)

        if page_obj:
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

class ChainListView(ListView):
    model = Chain

    def get_queryset(self):

        return super().get_queryset().order_by('chain_id')

    def render_to_response(self, context, **response_kwargs):
        context = self.get_context_data()
        page_obj = context.get('object_list', None)

        if page_obj:
            return JsonResponse({'chains': list(page_obj.values())}, safe=False)
        else:
            return JsonResponse({'chains': []}, safe=False)

class DexQuotePairListView(ListView):
    model = DexQuotePair
    DEFAULT_MAX_ROWS = 10000

    def get_queryset(self):
        queryset = super().get_queryset().select_related('src_asset__chain').annotate(
            src_id=F('src_asset'),
            dst_id=F('dst_asset'),
            src_symbol=F('src_asset__symbol'),
            dst_symbol=F('dst_asset__symbol'),
            src_name=F('src_asset__name'),
            dst_name=F('dst_asset__name'),
            chain_id=F('src_asset__chain__chain_id'),
        )

        queryset = queryset.order_by('chain_id')

        max_rows = self.request.GET.get('max_rows')
        if max_rows:
            if max_rows.isdigit():
                max_rows = int(max_rows)
            else:
                return queryset.none()
        else:
            max_rows = self.DEFAULT_MAX_ROWS
                         
        paginator = Paginator(queryset, max_rows)

        page = self.request.GET.get('page')
        if page:
            if page.isdigit():
                queryset = paginator.page(int(page))
            else:
                return queryset.none()
        else:
            queryset = paginator.page(1)

        return queryset

    def render_to_response(self, context, **response_kwargs):
        context = self.get_context_data()
        page_obj = context.get('object_list', None)

        if page_obj:

            pagination_info = {
                'current_page': page_obj.number,
                'total_pages': page_obj.paginator.num_pages,
                'total_items': page_obj.paginator.count,
            }

            return JsonResponse({
                'quote_pairs': list(page_obj.object_list.values(
                    'src_id', 'dst_id', 'src_name', 'dst_name', 'src_symbol', 'dst_symbol', 'chain_id')),
                'pagination': pagination_info
            }, safe=False)

        else:
            return JsonResponse({
                'quote_pairs': [],
                'pagination': {
                    'current_page': 0,
                    'total_pages': 0,
                    'total_items': 0
                }
            }, safe=False)
