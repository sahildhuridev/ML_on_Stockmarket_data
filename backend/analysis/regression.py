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

    # Timeframe configurations: (yfinance_period, prediction_trading_days, label)
    TIMEFRAME_MAP = {
        '1w':  ('3mo',   5,   '1-Week'),
        '1m':  ('6mo',  21,   '1-Month'),
        '3m':  ('1y',   63,   '3-Month'),
        '1y':  ('2y',  252,   '1-Year'),
    }

    def get(self, request):
        portfolio_id = request.GET.get("portfolio_id")
        timeframe = request.GET.get("timeframe", "1y")

        tf_config = self.TIMEFRAME_MAP.get(timeframe)
        if not tf_config:
            return Response({"error": f"Invalid timeframe: {timeframe}. Use 1w, 1m, 3m, or 1y."}, status=400)
        
        hist_period, pred_days, tf_label = tf_config
        
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
        
        # Download historical data based on timeframe
        data = yf.download(tickers, period=hist_period, group_by="ticker", auto_adjust=True)
        
        results = []
        for ticker in tickers:
            try:
                # Handle single ticker edge case vs multiple tickers
                if len(tickers) == 1:
                    df = data
                else:
                    df = data[ticker]
                
                df_clean = df[['Close']].dropna()
                if len(df_clean) < 30:
                    continue
                
                df_clean = df_clean.sort_index()    
                
                prices = df_clean['Close'].values
                dates = df_clean.index
                
                # Features: Days since start (0, 1, 2, ...)
                X = np.arange(len(prices)).reshape(-1, 1)
                y = prices
                
                # Train Linear Regression Model
                model = LinearRegression()
                model.fit(X, y)
                
                current_price = float(prices[-1])
                
                # Predict target price at the end of the selected timeframe
                future_X_single = np.array([[len(prices) + pred_days]])
                predicted_price = float(model.predict(future_X_single)[0])
                expected_return = ((predicted_price - current_price) / current_price) * 100
                
                # --- Volatility estimation for realistic predictions ---
                returns = np.diff(np.log(prices[prices > 0]))
                hist_vol = float(np.std(returns)) if len(returns) > 1 else 0.01
                rng = np.random.RandomState(hash(ticker) % (2**31))

                # Generate future dates and predictions
                last_date = dates[-1]
                calendar_days_per_trading = 365.0 / 252.0
                future_dates = [last_date + datetime.timedelta(days=int(i * calendar_days_per_trading))
                                for i in range(1, pred_days + 1)]
                future_X = np.arange(len(prices), len(prices) + pred_days).reshape(-1, 1)
                future_trend_raw = model.predict(future_X).flatten()
                
                # Apply realistic noise to future trend
                noise_returns = rng.normal(0, hist_vol * 0.8, pred_days)
                cumulative_noise = np.cumsum(noise_returns) * current_price
                future_trend = future_trend_raw + cumulative_noise
                future_trend = np.maximum(future_trend, future_trend_raw * 0.5)

                chart_data = []
                
                # Add historical data points (no trend overlay on historical)
                for i in range(len(dates)):
                    chart_data.append({
                        "date": dates[i].strftime("%Y-%m-%d"),
                        "actual": float(prices[i]),
                        "trend": None
                    })
                    
                # Add future data points with realistic trend
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
            "timeframe_label": tf_label,
            "results": results
        })

