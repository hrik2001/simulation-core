from django.urls import path
from .views import post_simulate_slashing, post_simulate_inactivity

urlpatterns = [
    path('simulate/slashing', post_simulate_slashing),
    path('simulate/inactivity', post_simulate_inactivity),
]