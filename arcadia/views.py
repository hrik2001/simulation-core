from django.shortcuts import render
from django.http import JsonResponse
from django.core.cache import cache
from .tasks import task__arcadia__cache_risk_params

def get_risk_params(request):
    
    
    risk_params = task__arcadia__cache_risk_params()
    
    return JsonResponse(risk_params, safe=False)
