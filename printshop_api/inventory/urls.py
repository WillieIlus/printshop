# inventory/urls.py

from django.urls import path

from .views import MachineViewSet, PaperViewSet

app_name = "inventory"

urlpatterns = [
    path(
        'shops/<slug:shop_slug>/machines/',
        MachineViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='machine-list'
    ),
    path(
        'shops/<slug:shop_slug>/machines/<int:pk>/',
        MachineViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='machine-detail'
    ),
    path(
        'shops/<slug:shop_slug>/paper/',
        PaperViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='paper-list'
    ),
    path(
        'shops/<slug:shop_slug>/paper/<int:pk>/',
        PaperViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='paper-detail'
    ),
    path(
        'shops/<slug:shop_slug>/paper/<int:pk>/adjust/',
        PaperViewSet.as_view({'post': 'adjust'}),
        name='paper-adjust'
    ),
]
