from django.contrib import admin
from .models import Chain, CryoLogsMetadata, Transaction

# Register your models here.
admin.site.register(Chain)
admin.site.register(CryoLogsMetadata)