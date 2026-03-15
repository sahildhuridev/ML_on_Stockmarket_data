from rest_framework import serializers
from django.utils import timezone

from .models import (
    PipelineRun,
    Prediction,
    HourlyPrediction,
    ForecastRequest,
    ForecastPrediction,
    SingleStockForecast,
)


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = [
            'id', 'ticker', 'current_price', 'predicted_price',
            'best_model', 'metrics', 'created_at',
        ]


class HourlyPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HourlyPrediction
        fields = [
            'id', 'ticker', 'model_name', 'predicted_price',
            'current_price_at_prediction', 'actual_price',
            'absolute_error', 'pct_error', 'status',
            'predicted_at', 'verified_at',
        ]


class ForecastPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForecastPrediction
        fields = [
            'id', 'ticker', 'best_model', 'current_price_at_request',
            'predicted_price', 'model_predictions', 'model_metrics',
            'actual_price', 'actual_price_timestamp', 'absolute_error',
            'pct_error', 'direction_match', 'status', 'created_at',
            'verified_at',
        ]


class ForecastRequestSerializer(serializers.ModelSerializer):
    portfolio_name = serializers.CharField(source='portfolio.name', read_only=True)
    forecast_predictions = ForecastPredictionSerializer(many=True, read_only=True)

    class Meta:
        model = ForecastRequest
        fields = [
            'id', 'portfolio', 'portfolio_name', 'created_by',
            'prediction_scope', 'interval', 'training_days',
            'requested_tickers', 'target_datetime', 'resolved_target_datetime',
            'requested_at', 'resolved_at', 'status', 'results_json',
            'error_message', 'forecast_predictions',
        ]


class RunForecastInputSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    prediction_scope = serializers.ChoiceField(
        choices=ForecastRequest.SCOPE_CHOICES,
        default='portfolio',
        required=False,
    )
    ticker = serializers.CharField(required=False, allow_blank=True)
    interval = serializers.CharField(default='1h', required=False)
    training_days = serializers.IntegerField(default=30, required=False, min_value=7, max_value=365)
    target_datetime = serializers.DateTimeField()

    def validate_target_datetime(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Target date/time must be in the future.")
        return value

    def validate(self, attrs):
        scope = attrs.get('prediction_scope', 'portfolio')
        ticker = (attrs.get('ticker') or '').strip().upper()
        if scope == 'single_stock' and not ticker:
            raise serializers.ValidationError({"ticker": "Ticker is required for single stock forecasts."})
        attrs['ticker'] = ticker
        return attrs


class SingleStockForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = SingleStockForecast
        fields = [
            'id', 'ticker', 'company_name', 'interval', 'training_days',
            'target_datetime', 'resolved_target_datetime', 'requested_at',
            'resolved_at', 'status', 'current_price', 'predicted_price',
            'best_model', 'model_predictions', 'model_metrics', 'steps_ahead',
            'actual_price', 'actual_price_timestamp', 'absolute_error',
            'pct_error', 'direction_match', 'results_json', 'error_message',
        ]


class RunSingleStockForecastInputSerializer(serializers.Serializer):
    ticker = serializers.CharField(max_length=20)
    company_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    interval = serializers.CharField(default='1h', required=False)
    training_days = serializers.IntegerField(default=30, required=False, min_value=7, max_value=365)
    target_datetime = serializers.DateTimeField()

    def validate_target_datetime(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Target date/time must be in the future.")
        return value

    def validate_ticker(self, value):
        ticker = (value or '').strip().upper()
        if not ticker:
            raise serializers.ValidationError("Ticker is required.")
        return ticker


class PipelineRunSerializer(serializers.ModelSerializer):
    predictions = PredictionSerializer(many=True, read_only=True)
    hourly_predictions = HourlyPredictionSerializer(many=True, read_only=True)
    portfolio_name = serializers.CharField(source='portfolio.name', read_only=True)

    class Meta:
        model = PipelineRun
        fields = [
            'id', 'portfolio', 'portfolio_name', 'triggered_by',
            'status', 'interval', 'training_days',
            'started_at', 'finished_at',
            'results_json', 'error_message',
            'predictions', 'hourly_predictions',
        ]
        read_only_fields = ['status', 'started_at', 'finished_at', 'results_json', 'error_message']


class PipelineRunListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (without nested predictions)."""
    portfolio_name = serializers.CharField(source='portfolio.name', read_only=True)

    class Meta:
        model = PipelineRun
        fields = [
            'id', 'portfolio', 'portfolio_name', 'status',
            'interval', 'training_days', 'started_at', 'finished_at',
        ]


class RunPipelineInputSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    interval = serializers.CharField(default='1h', required=False)
    training_days = serializers.IntegerField(default=30, required=False)
