from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django import forms
from .services import simulate_slashing, simulate_inactivity
from .tasks import cache_ecps_parameters_job
from django.core.cache import cache
from django.conf import settings
import json
from enum import Enum


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"
    PATCH = "PATCH"


class SimulateSlashingRequest(forms.Form):
    staking_share = forms.FloatField(min_value=0.0, max_value=100.0)
    exit_queue_length = forms.IntegerField(min_value=0, max_value=3750000)
    slashed_validator_share = forms.FloatField(min_value=0.0, max_value=100.0)


@csrf_exempt
def post_simulate_slashing(request) -> JsonResponse:

    if request.method == HttpMethod.OPTIONS:
        response = JsonResponse({})
        response["Allow"] = ",".join([HttpMethod.POST, HttpMethod.OPTIONS])
        return response

    if request.method != HttpMethod.POST:
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)

    form = SimulateSlashingRequest(data)
    if not form.is_valid():
        return JsonResponse({"error": form.errors}, status=400)

    request = form.cleaned_data

    day_array, day_fields, exit_queue_epoch = simulate_slashing(
        32, request["staking_share"], request["exit_queue_length"], request["slashed_validator_share"]
    )

    return JsonResponse({"day_array": day_array, "day_fields": day_fields, "exit_queue_epoch": exit_queue_epoch})


class SimulatePenaltyRequest(forms.Form):
    staking_share = forms.FloatField(min_value=0.0, max_value=100.0)
    inactive_share = forms.FloatField(min_value=0.0, max_value=100.0)


@csrf_exempt
def post_simulate_inactivity(request) -> JsonResponse:

    if request.method == HttpMethod.OPTIONS:
        response = JsonResponse({})
        response["Allow"] = ",".join([HttpMethod.POST, HttpMethod.OPTIONS])
        return response

    if request.method != HttpMethod.POST:
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = json.loads(request.body)

    form = SimulatePenaltyRequest(data)
    if not form.is_valid():
        return JsonResponse({"error": form.errors}, status=400)

    request = form.cleaned_data

    day_array, day_fields, enter_exit_queue_epoch, leave_exit_queue_epoch, inactivity_leak_stop_epoch = (
        simulate_inactivity(request["staking_share"], request["inactive_share"])
    )

    return JsonResponse(
        {
            "day_array": day_array,
            "day_fields": day_fields,
            "enter_exit_queue_epoch": enter_exit_queue_epoch,
            "leave_exit_queue_epoch": leave_exit_queue_epoch,
            "inactivity_leak_stop_epoch": inactivity_leak_stop_epoch,
        }
    )


def get_parameters(request) -> JsonResponse:

    if request.method == HttpMethod.OPTIONS:
        response = JsonResponse({})
        response["Allow"] = ",".join([HttpMethod.GET, HttpMethod.OPTIONS])
        return response

    if request.method != HttpMethod.GET:
        return JsonResponse({"error": "Invalid request method"}, status=400)

    response = cache.get("ecps_parameters", None)
    if not response:
        cache_ecps_parameters_job.delay(settings.RATED_NETWORK_API_KEY, settings.BLOCKPI_NETWORK_API_KEY) # adds it to the job queue
        
        return JsonResponse({'error': 'Cache not ready yet'}, status=503)

    return JsonResponse(response, safe=False)
