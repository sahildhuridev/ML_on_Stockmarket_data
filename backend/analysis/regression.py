import pandas as pd
import yfinance as yf
import numpy as np
import datetime
from sklearn.linear_model import LinearRegression
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from portfolios.models import Portfolio
from stocks.models import Stock

class StockPotentialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio_id = request.GET.get("portfolio_id")
        
        tickers = []
        if portfolio_id == "all":
            stocks = Stock.objects.filter(portfolio__user=request.user)
            tickers = [s.ticker for s in stocks]
        elif portfolio_id:
            try:
                portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
                stocks = portfolio.stocks.all()
                tickers = [s.ticker for s in stocks]
            except Portfolio.DoesNotExist:
                return Response({"error": "Invalid portfolio"}, status=404)
        else:
            return Response({"error": "portfolio_id required"}, status=400)
            
        if not tickers:
            return Response({"error": "No stocks found for analysis"}, status=400)

        # Remove duplicates
        tickers = list(set(tickers))
        
        # Download 1-year data
        # auto_adjust=True handles splits and dividends
        data = yf.download(tickers, period="1y", group_by="ticker", auto_adjust=True)
        
        results = []
        for ticker in tickers:
            try:
                # Handle single ticker edge case vs multiple tickers
                if len(tickers) == 1:
                    df = data
                else:
                    df = data[ticker]
                
                # We need the 'Close' price and drop any NaN values
                df_clean = df[['Close']].dropna()
                if len(df_clean) < 30: # Need enough data for a basic linear regression
                    continue
                
                # Sort by date just to be safe
                df_clean = df_clean.sort_index()    
                
                prices = df_clean['Close'].values
                dates = df_clean.index
                
                # Features: Days since start (0, 1, 2, ...)
                X = np.arange(len(prices)).reshape(-1, 1)
                y = prices
                
                # Train Linear Regression Model
                model = LinearRegression()
                model.fit(X, y)
                
                # Current Price is the last actual price
                current_price = float(prices[-1])
                
                # Future Prediction: Predict 252 trading days (~1 year) into the future
                future_X_single = np.array([[len(prices) + 252]])
                predicted_price = float(model.predict(future_X_single)[0])
                
                # Calculate Expected Return (%)
                expected_return = ((predicted_price - current_price) / current_price) * 100
                
                # Generate Chart Data (Historical + Future Trendline)
                # 1. We create the trendline for the *historical* part
                historical_trend = model.predict(X)
                
                # 2. We generate the *future* dates and predict their trend
                last_date = dates[-1]
                future_dates = [last_date + datetime.timedelta(days=int(i * (365/252))) for i in range(1, 253)]
                future_X = np.arange(len(prices), len(prices) + 252).reshape(-1, 1)
                future_trend = model.predict(future_X)
                
                chart_data = []
                
                # Add historical data points
                for i in range(len(dates)):
                    chart_data.append({
                        "date": dates[i].strftime("%Y-%m-%d"),
                        "actual": float(prices[i]),
                        "trend": float(historical_trend[i])
                    })
                    
                # Add future data points (actual is null)
                for i in range(len(future_dates)):
                    chart_data.append({
                        "date": future_dates[i].strftime("%Y-%m-%d"),
                        "actual": None,
                        "trend": float(future_trend[i])
                    })
                
                results.append({
                    "ticker": ticker,
                    "current_price": round(current_price, 2),
                    "predicted_price": round(predicted_price, 2),
                    "expected_return": round(expected_return, 2),
                    "chart_data": chart_data
                })
                
            except Exception as e:
                print(f"Error calculating regression for {ticker}: {e}")
                continue
                
        # Sort results by highest expected return descending
        results.sort(key=lambda x: x['expected_return'], reverse=True)
            
        return Response({
            "results": results
        })
