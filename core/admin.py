from django.contrib import admin
from .models import Chain, CryoLogsMetadata, Transaction, ERC20, UniswapLPPosition

# Register your models here.
admin.site.register(Chain)
admin.site.register(CryoLogsMetadata)
admin.site.register(ERC20)
admin.site.register(UniswapLPPosition)