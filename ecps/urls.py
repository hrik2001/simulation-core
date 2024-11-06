from django.urls import path
from .views import post_simulate_slashing, post_simulate_inactivity, get_parameters

urlpatterns = [
    path('simulate/slashing', post_simulate_slashing),
    path('simulate/inactivity', post_simulate_inactivity),
    path('simulate/parameters/', get_parameters),
]