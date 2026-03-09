from django.urls import path
from .views import GoldSilverAnalysisView, GoldSilverUnivariateAnalysisView, CryptoAnalysisView, TimeSeriesAnalysisView

urlpatterns = [
    path('gold-silver/', GoldSilverAnalysisView.as_view(), name='gold_silver_analysis'),
    path('gold-silver-univariate/', GoldSilverUnivariateAnalysisView.as_view(), name='gold_silver_univariate_analysis'),
    path('crypto/', CryptoAnalysisView.as_view(), name='crypto_analysis'),
    path('time-series/', TimeSeriesAnalysisView.as_view(), name='time_series_analysis'),
]
