from django.urls import path
from .views import DexQuoteListView, ChainListView

urlpatterns = [
    path('quotes/', DexQuoteListView.as_view(), name='get_quotes'),
    path('chains', ChainListView.as_view(), name='get_chains'),
]

