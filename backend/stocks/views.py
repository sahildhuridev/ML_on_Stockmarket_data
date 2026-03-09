from django.shortcuts import render
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# Create your views here.
from rest_framework import viewsets
from .models import Stock
from .serializers import StockSerializer

class StockViewSet(viewsets.ModelViewSet):
    serializer_class = StockSerializer

    def get_queryset(self):
        return Stock.objects.filter(portfolio__user=self.request.user)

class StockSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.GET.get('q', '')
        if not query:
            return Response([])

        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            data = response.json()
            quotes = data.get('quotes', [])
            
            results = []
            for quote in quotes[:5]:
                if 'symbol' in quote and 'shortname' in quote:
                    results.append({
                        'ticker': quote['symbol'],
                        'company_name': quote['shortname']
                    })
            
            return Response(results)
        except Exception as e:
            return Response({"error": "Failed to fetch data", "details": str(e)}, status=500)