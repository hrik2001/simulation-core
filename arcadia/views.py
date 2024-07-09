from django.shortcuts import render
from django.http import JsonResponse
from django.core.cache import cache
from .tasks import task__arcadia__risk_params

def get_risk_params(request):
    # Extract query parameters
    pool_address = request.GET.get('pool_address')
    numeraire_address = request.GET.get('numeraire_address')
    
    # Validate parameters
    if not pool_address or not numeraire_address:
        return JsonResponse({'error': 'Missing pool_address or numeraire_address'}, status=400)
    
    # Define cache key
    cache_key = f'risk_params_{pool_address}_{numeraire_address}'
    
    # Try to get data from cache
    risk_params = cache.get(cache_key)
    
    # If cache is empty, call the task and cache the result
    if not risk_params:
        risk_params = task__arcadia__risk_params(pool_address, numeraire_address)
        cache.set(cache_key, risk_params, 86400)  # Cache for 1 day (86400 seconds)
    
    # Return the JSON response
    return JsonResponse(risk_params, safe=False)
