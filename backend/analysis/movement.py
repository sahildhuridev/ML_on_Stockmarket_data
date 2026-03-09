import pandas as pd
import yfinance as yf
import numpy as np
import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from portfolios.models import Portfolio
from stocks.models import Stock

# We will lazy-load tensorflow to avoid massive memory hit on boot
import os
import sys
sys.path.insert(0, r"C:\Users\Sahil\tf_lib")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

class MovementProbabilityView(APIView):
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

        tickers = list(set(tickers))
        
        # Download ~2 years of data to have enough for LSTM sequences
        data = yf.download(tickers, period="2y", group_by="ticker", auto_adjust=True)
        
        # --- Pre-build LSTM Model to avoid retracing warnings ---
        import tensorflow as tf
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
        
        sequence_length = 20
        # Build lightweight LSTM once out of loop
        lstm_model = Sequential([
            Input(shape=(sequence_length, 1)),
            LSTM(16, activation='relu'),
            Dropout(0.2),
            Dense(1, activation='sigmoid')
        ])
        lstm_model.compile(optimizer='adam', loss='binary_crossentropy')
        initial_lstm_weights = lstm_model.get_weights()
        
        results = []
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    df = data
                else:
                    df = data[ticker]
                
                df_clean = df[['Close']].dropna()
                if len(df_clean) < 100: 
                    continue
                
                df_clean = df_clean.sort_index()
                
                # Create target: 1 if tomorrow's close > today's close, else 0
                df_clean['Return'] = df_clean['Close'].pct_change()
                df_clean['Target'] = (df_clean['Return'].shift(-1) > 0).astype(int)
                
                # Features for Logistic Regression (Past 5 days returns)
                df_clean['Ret_1'] = df_clean['Return'].shift(1)
                df_clean['Ret_2'] = df_clean['Return'].shift(2)
                df_clean['Ret_3'] = df_clean['Return'].shift(3)
                df_clean['Ret_4'] = df_clean['Return'].shift(4)
                df_clean['Ret_5'] = df_clean['Return'].shift(5)
                
                df_lr = df_clean.dropna()
                if len(df_lr) < 50:
                    continue
                    
                X_lr = df_lr[['Return', 'Ret_1', 'Ret_2', 'Ret_3', 'Ret_4', 'Ret_5']].values
                y_lr = df_lr['Target'].values
                
                scaler_lr = StandardScaler()
                X_lr_scaled = scaler_lr.fit_transform(X_lr)
                
                # Train Logistic Regression
                lr_model = LogisticRegression(random_state=42)
                # We train on all except the last row (which doesn't have a valid target yet)
                lr_model.fit(X_lr_scaled[:-1], y_lr[:-1])
                
                # Predict probability for tomorrow (using the last known row features)
                last_features_lr = X_lr_scaled[-1].reshape(1, -1)
                lr_prob_up = lr_model.predict_proba(last_features_lr)[0][1] * 100
                
                # --- LSTM Model Data Prep ---
                returns_data = df_lr['Return'].values.reshape(-1, 1)
                
                scaler_lstm = StandardScaler()
                scaled_returns = scaler_lstm.fit_transform(returns_data)
                
                X_lstm, y_lstm = [], []
                for i in range(len(scaled_returns) - sequence_length):
                    X_lstm.append(scaled_returns[i:(i + sequence_length)])
                    y_lstm.append(y_lr[i + sequence_length - 1])
                    
                X_lstm, y_lstm = np.array(X_lstm), np.array(y_lstm)
                
                # Reset model weights for next ticker
                lstm_model.set_weights(initial_lstm_weights)
                
                # Extremely fast training: 3 epochs
                lstm_model.fit(X_lstm[:-1], y_lstm[:-1], epochs=3, batch_size=32, verbose=0)
                
                # Predict probability for tomorrow
                last_sequence = scaled_returns[-sequence_length:].reshape(1, sequence_length, 1)
                lstm_prob_up = float(lstm_model.predict(last_sequence, verbose=0)[0][0]) * 100
                
                # Expected Return Approx (Average historical return for positive vs negative days)
                avg_up_return = df_clean[df_clean['Return'] > 0]['Return'].mean() * 100
                avg_down_return = df_clean[df_clean['Return'] < 0]['Return'].mean() * 100
                
                # Blended probability of going UP
                combined_prob_up = (lr_prob_up + lstm_prob_up) / 2
                
                if combined_prob_up > 50:
                    expected_return = avg_up_return
                else:
                    expected_return = avg_down_return

                # Calculate specific Price Projections for the graph
                last_price = df_clean['Close'].iloc[-1]
                
                # Logic to convert probabilities to price. 
                # If prob > 50, use avg_up_return, else use avg_down_return
                lr_proj_return = avg_up_return if lr_prob_up > 50 else avg_down_return
                lstm_proj_return = avg_up_return if lstm_prob_up > 50 else avg_down_return

                lr_predicted_price = last_price * (1 + (lr_proj_return / 100))
                lstm_predicted_price = last_price * (1 + (lstm_proj_return / 100))

                # Chart Data for the frontend (Last 30 days of actual prices + 1 prediction day)
                chart_data = []
                recent_df = df_clean.tail(30)
                for date, row_data in recent_df.iterrows():
                    chart_data.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "actual": round(row_data['Close'], 2)
                    })
                
                # Add the Future Day with predicted values
                next_date = (recent_df.index[-1] + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                chart_data.append({
                    "date": next_date,
                    "actual": None,
                    "lr_pred": round(lr_predicted_price, 2),
                    "lstm_pred": round(lstm_predicted_price, 2)
                })

                results.append({
                    "ticker": ticker,
                    "current_price": round(last_price, 2),
                    "lr_prob_up": round(lr_prob_up, 2),
                    "lstm_prob_up": round(lstm_prob_up, 2),
                    "expected_return": round(expected_return, 2),
                    "is_up": combined_prob_up > 50,
                    "chart_data": chart_data
                })

            except Exception as e:
                print(f"Error calculating movement prob for {ticker}: {e}")
                continue
                
        # Sort by those most likely to go up
        results.sort(key=lambda x: x['expected_return'], reverse=True)

        return Response({
            "results": results
        })
