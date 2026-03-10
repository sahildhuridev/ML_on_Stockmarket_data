from rest_framework import serializers
from .models import PipelineRun, Prediction, HourlyPrediction


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
