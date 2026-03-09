from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import StockViewSet, StockSearchView

router = DefaultRouter()
router.register('', StockViewSet, basename='stock')

urlpatterns = [
    path('search/', StockSearchView.as_view(), name='stock-search'),
] + router.urls