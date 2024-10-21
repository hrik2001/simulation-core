from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

from ethena.schema import schema
from ethena.views import get_drawdowns

urlpatterns = [
    path("/graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True, schema=schema))),
    path("/get_drawdowns/", csrf_exempt(get_drawdowns), name="get_drawdowns"),
]
