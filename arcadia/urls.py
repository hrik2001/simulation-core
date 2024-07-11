from django.urls import path
from graphene_django.views import GraphQLView
from .schema import schema
from .views import get_risk_params
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('/graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True, schema=schema))),
    path('/get_risk_params/', get_risk_params, name='get_risk_params'),
    # Other URLs for the app
]
