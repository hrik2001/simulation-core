from django.contrib import admin
from .models import Chain, CryoLogsMetadata, Transaction, ERC20, UniswapLPPosition, DexQuote, DexQuotePair

# Register your models here.
admin.site.register(Chain)
admin.site.register(CryoLogsMetadata)
admin.site.register(ERC20)
admin.site.register(UniswapLPPosition)
admin.site.register(DexQuote)
admin.site.register(DexQuotePair)