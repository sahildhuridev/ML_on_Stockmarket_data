from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/accounts/', include('accounts.urls')),
    path('api/portfolios/', include('portfolios.urls')),
    path('api/stocks/', include('stocks.urls')),
    path('api/analysis/', include('analysis.urls')),
    path('api/ml_models/', include('ml_models.urls')),
    path('api/ml_flow/', include('ml_flow.urls')),
    path('api/sentiment/', include('sentiment_analysis.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
