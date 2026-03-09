from django.urls import path
from .views import (
    PriceGraphView,
    PERatioView,
    VolumePortfolioView,
    VolumeChartView,
    DiscountedValueView,
)
from .cluster import ClusterAnalysisView
from .regression import StockPotentialView
from .movement import MovementProbabilityView

urlpatterns = [
    path('price-chart/', PriceGraphView.as_view()),
    path('pe-ratio/', PERatioView.as_view()),
    path('volume-portfolio/', VolumePortfolioView.as_view()),
    path('volume-chart/', VolumeChartView.as_view()),
    path('discounted-value/', DiscountedValueView.as_view()),
    path('clustering/', ClusterAnalysisView.as_view(), name='clustering'),
    path('stock-potential/', StockPotentialView.as_view(), name='stock-potential'),
    path('movement-probability/', MovementProbabilityView.as_view(), name='movement-probability'),
]