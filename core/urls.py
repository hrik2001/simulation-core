from django.urls import path
from .views import DexQuoteListView

urlpatterns = [
    path('quotes/', DexQuoteListView.as_view(), name='get_quotes'),
]

