from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PortfolioViewSet, PortfolioSummaryView

router = DefaultRouter()
router.register('', PortfolioViewSet, basename='portfolio')

urlpatterns = [
    path('summary/', PortfolioSummaryView.as_view(), name='portfolio-summary'),
    path('', include(router.urls)),
]