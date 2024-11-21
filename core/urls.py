from django.urls import path
from .views import DexQuoteListView, DexQuotePairListView, ChainListView, trigger_test_error

urlpatterns = [
    path('quotes/', DexQuoteListView.as_view(), name='get_quotes'),
    path('chains/', ChainListView.as_view(), name='get_chains'),
    path('quote-pairs/', DexQuotePairListView.as_view(), name='get_quote_pairs'),
    path('trigger-error/', trigger_test_error, name='trigger_error'),
]
