from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django import forms
from .services import simulate_slashing, simulate_inactivity
import json

class SimulateSlashingRequest(forms.Form):
    staking_share = forms.FloatField(min_value=0., max_value=100.)
    exit_queue_length = forms.IntegerField(min_value=0, max_value=3750000)
    slashed_validator_share = forms.FloatField(min_value=0., max_value=100.)

@csrf_exempt
def post_simulate_slashing(request):

    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response['Allow'] = 'POST, OPTIONS'
        return response

    if request.method != 'POST':
    	return JsonResponse({'error': 'Invalid request method'}, status=400)

    data = json.loads(request.body)

    form = SimulateSlashingRequest(data)
    if not form.is_valid():
    	return JsonResponse({'error': form.errors}, status=400)

    request = form.cleaned_data
    
    day_array, day_fields, exit_queue_epoch = simulate_slashing(32, request['staking_share'], request['exit_queue_length'], request['slashed_validator_share'])
        
    return JsonResponse({
    	'day_array': day_array,
    	'day_fields': day_fields,
    	'exit_queue_epoch': exit_queue_epoch})

class SimulatePenaltyRequest(forms.Form):
    staking_share = forms.FloatField(min_value=0., max_value=100.)
    inactive_share = forms.FloatField(min_value=0., max_value=100.)

@csrf_exempt
def post_simulate_inactivity(request):

    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response['Allow'] = 'POST, OPTIONS'
        return response
        
    if request.method != 'POST':
    	return JsonResponse({'error': 'Invalid request method'}, status=400)

    data = json.loads(request.body)

    form = SimulatePenaltyRequest(data)
    if not form.is_valid():
    	return JsonResponse({'error': form.errors}, status=400)

    request = form.cleaned_data
    
    day_array, day_fields, enter_exit_queue_epoch, leave_exit_queue_epoch, inactivity_leak_stop_epoch = simulate_inactivity(request['staking_share'], request['inactive_share'])
    
    return JsonResponse({
    	'day_array': day_array,
    	'day_fields': day_fields,
    	'enter_exit_queue_epoch': enter_exit_queue_epoch,
    	'leave_exit_queue_epoch': leave_exit_queue_epoch,
    	'inactivity_leak_stop_epoch': inactivity_leak_stop_epoch})
    