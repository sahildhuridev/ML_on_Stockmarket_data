from django.contrib import admin
from .models import PipelineRun, Prediction, HourlyPrediction, SingleStockForecast


@admin.register(PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'portfolio', 'status', 'interval', 'training_days', 'started_at', 'finished_at')
    list_filter = ('status', 'interval')
    readonly_fields = ('results_json',)


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'current_price', 'predicted_price', 'best_model', 'created_at')
    list_filter = ('best_model',)


@admin.register(HourlyPrediction)
class HourlyPredictionAdmin(admin.ModelAdmin):
    list_display = (
        'ticker', 'model_name', 'predicted_price', 'actual_price',
        'pct_error', 'status', 'predicted_at', 'verified_at',
    )
    list_filter = ('status', 'model_name')
    readonly_fields = ('absolute_error', 'pct_error', 'verified_at')


@admin.register(SingleStockForecast)
class SingleStockForecastAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'ticker', 'company_name', 'status', 'interval',
        'training_days', 'target_datetime', 'predicted_price', 'actual_price',
    )
    list_filter = ('status', 'interval', 'best_model')
    search_fields = ('ticker', 'company_name')
    readonly_fields = (
        'resolved_target_datetime', 'requested_at', 'resolved_at',
        'absolute_error', 'pct_error', 'results_json',
    )
