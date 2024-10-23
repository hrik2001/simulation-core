from django.contrib import admin
from .models import Chain, CryoLogsMetadata, Transaction, ERC20, UniswapLPPosition, DexQuote, DexQuotePair

# Custom admin class for DexQuote
class DexQuoteAdmin(admin.ModelAdmin):
    list_display = ('dex_aggregator', 'network', 'src', 'dst', 'timestamp')
    search_fields = ('dex_aggregator', 'src', 'dst')
    raw_id_fields = ('pair',)  # Use raw_id_fields to remove the dropdown for ForeignKey

# Custom admin class for DexQuotePair
class DexQuotePairAdmin(admin.ModelAdmin):
    # list_display = ('src_asset', 'dst_asset', 'ingest')
    search_fields = ('src_asset__symbol', 'dst_asset__symbol')
    raw_id_fields = ('src_asset', 'dst_asset')  # Use raw_id_fields for ForeignKey fields

# Custom Admin class for ERC20
class ERC20Admin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'chain', 'contract_address', 'uuid_display')
    readonly_fields = ('uuid_display',)

    def uuid_display(self, obj):
        return obj.id

    uuid_display.short_description = 'UUID'

    def get_queryset(self, request):
        # Exclude ERC20 entries that have a related UniswapLPPosition
        qs = super().get_queryset(request)
        return qs.filter(uniswaplpposition__isnull=True)

# Register the models with the custom admin classes
admin.site.register(Chain)
admin.site.register(CryoLogsMetadata)
admin.site.register(ERC20, ERC20Admin)
admin.site.register(UniswapLPPosition)
admin.site.register(DexQuote, DexQuoteAdmin)
admin.site.register(DexQuotePair, DexQuotePairAdmin)