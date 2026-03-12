from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Portfolio
from stocks.models import Stock
from .serializers import PortfolioSerializer
import yfinance as yf

class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PortfolioSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio_id = request.query_params.get('portfolio_id')
        
        if portfolio_id:
            try:
                portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
                stocks = portfolio.stocks.all()
            except Portfolio.DoesNotExist:
                return Response({"error": "Portfolio not found"}, status=404)
        else:
            stocks = Stock.objects.filter(portfolio__user=request.user)

        total_invested = 0.0
        total_current_value = 0.0
        number_of_stocks = stocks.count()

        if number_of_stocks > 0:
            tickers = [stock.ticker for stock in stocks]
            try:
                # Optimized yfinance call for multiple tickers
                data = yf.download(tickers, period="1d", interval="1m", progress=False)
                
                prices = {}
                if len(tickers) == 1:
                    close = data['Close']
                    prices[tickers[0]] = float(close.iloc[-1].item() if hasattr(close.iloc[-1], 'item') else close.iloc[-1])
                else:
                    for ticker in tickers:
                        try:
                            prices[ticker] = float(data['Close'][ticker].dropna().iloc[-1])
                        except Exception:
                            prices[ticker] = 0.0 # fallback if no data
                            
            except Exception as e:
                # Fallback to individual fetches or zero if yfinance fails
                prices = {}
                
            for stock in stocks:
                invested = stock.buy_price * stock.quantity
                total_invested += invested
                
                current_price = prices.get(stock.ticker, 0.0)
                if current_price == 0.0:
                    # Attempt individual fetch if bulk failed for this ticker
                    try:
                        d = yf.download(stock.ticker, period="1d", interval="1m", progress=False)
                        if not d.empty:
                            close = d['Close']
                            current_price = float(close.iloc[-1].item() if hasattr(close.iloc[-1], 'item') else close.iloc[-1])
                    except:
                        pass
                
                total_current_value += current_price * stock.quantity

        total_profit_loss = total_current_value - total_invested

        return Response({
            "number_of_stocks": number_of_stocks,
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current_value, 2),
            "total_profit_loss": round(total_profit_loss, 2)
        })