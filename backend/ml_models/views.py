from django.shortcuts import render
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import os
import json

from .gold_silver_prediction import analyze_gold_silver_multivariate
from .gold_silver_univariate_prediction import analyze_gold_silver_univariate

class GoldSilverAnalysisView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return self._analyze(request, method='GET')
        
    def post(self, request):
        return self._analyze(request, method='POST')
        
    def _analyze(self, request, method):
        # Default parameter
        interval = '1y'
        if method == 'POST':
            interval = request.data.get('interval', '1y')
            
        try:
            result = analyze_gold_silver_multivariate(interval)
            if "error" in result:
                return Response(result, status=400)
            return Response(result, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class GoldSilverUnivariateAnalysisView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return self._analyze(request, method='GET')
        
    def post(self, request):
        return self._analyze(request, method='POST')
        
    def _analyze(self, request, method):
        # Default parameter
        interval = '1y'
        if method == 'POST':
            interval = request.data.get('interval', '1y')
            
        try:
            result = analyze_gold_silver_univariate(interval)
            if "error" in result:
                return Response(result, status=400)
            return Response(result, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

from .crypto_analysis import analyze_crypto

class CryptoAnalysisView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Default parameters
        symbol = request.data.get('symbol', 'BTC-USD')
        interval = request.data.get('interval', '1d')
        period = request.data.get('period', '1mo')
        models = request.data.get('models', []) # e.g. ['sma', 'ema', 'trend']
        
        try:
            result = analyze_crypto(symbol, interval, period, models)
            if "error" in result:
                return Response(result, status=400)
            return Response(result, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class TimeSeriesAnalysisView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        symbol = request.data.get('symbol', 'AAPL')
        interval = request.data.get('interval', '1d')
        period = request.data.get('period', '1y')
        models = request.data.get('models', [])
        
        try:
            from .time_series_prediction import analyze_time_series
            result = analyze_time_series(symbol, interval, period, models)
            if "error" in result:
                return Response(result, status=400)
            return Response(result, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
