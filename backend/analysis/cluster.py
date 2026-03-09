from django.shortcuts import render
import pandas as pd
import yfinance as yf
import numpy as np
import uuid
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from portfolios.models import Portfolio
from stocks.models import Stock

def calculate_rsi(data, window=14):
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=window - 1, adjust=False).mean()
    ema_down = down.ewm(com=window - 1, adjust=False).mean()
    rs = ema_up / ema_down
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 0

class ClusterAnalysisView(APIView):
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
        data = yf.download(tickers, period="1y", group_by="ticker", auto_adjust=True)
        
        metrics = []
        for ticker in tickers:
            try:
                # Handle single ticker edge case vs multiple tickers
                if len(tickers) == 1:
                    df = data
                else:
                    df = data[ticker]
                
                prices = df['Close'].dropna()
                if len(prices) < 30: # Need enough data
                    continue
                    
                # Calculate daily returns
                returns = prices.pct_change().dropna()
                
                # Annualized Metrics
                avg_return = returns.mean() * 252 * 100 # Annualized percentage
                volatility = returns.std() * np.sqrt(252) * 100 # Annualized percentage
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
                rsi = calculate_rsi(prices)
                
                metrics.append({
                    "ticker": ticker,
                    "avg_return": float(avg_return),
                    "volatility": float(volatility),
                    "sharpe": float(sharpe),
                    "rsi": float(rsi)
                })
            except Exception as e:
                print(f"Error calculating metrics for {ticker}: {e}")
                continue
                
        if len(metrics) < 3:
            return Response({"error": "Not enough data points to create 3 clusters. Minimum 3 stocks with valid data required."}, status=400)
            
        # Prepare data for clustering
        df_metrics = pd.DataFrame(metrics)
        
        # Feature matrix: Average Return, Volatility, Sharpe Ratio, RSI
        features = df_metrics[['avg_return', 'volatility', 'sharpe', 'rsi']]
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)
        
        # KMeans
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(scaled_features)
        df_metrics['cluster'] = clusters
        
        # Map clusters to labels: High return-High risk, Moderate return-Low risk, Low return-High risk
        cluster_summary = df_metrics.groupby('cluster')[['avg_return', 'volatility']].mean()
        
        labels = {}
        # Find lowest volatility
        low_risk_idx = cluster_summary['volatility'].idxmin()
        labels[low_risk_idx] = {"name": "Moderate return – Low risk", "color": "#3b82f6", "emoji": "🔵"}
        
        remaining = [c for c in cluster_summary.index if c != low_risk_idx]
        if cluster_summary.loc[remaining[0], 'avg_return'] > cluster_summary.loc[remaining[1], 'avg_return']:
            high_ret_idx = remaining[0]
            low_ret_idx = remaining[1]
        else:
            high_ret_idx = remaining[1]
            low_ret_idx = remaining[0]
            
        labels[high_ret_idx] = {"name": "High return – High risk", "color": "#22c55e", "emoji": "🟢"}
        labels[low_ret_idx] = {"name": "Low return – High risk", "color": "#ef4444", "emoji": "🔴"}
        
        df_metrics['cluster_name'] = df_metrics['cluster'].map(lambda c: labels[c]['name'])
        df_metrics['cluster_color'] = df_metrics['cluster'].map(lambda c: labels[c]['color'])
        df_metrics['cluster_emoji'] = df_metrics['cluster'].map(lambda c: labels[c]['emoji'])
        
        from scipy.spatial import ConvexHull
        
        draw_outline = request.GET.get("draw_outline") == "true"
        
        # Generation of Plotly/Matplotlib image
        plt.figure(figsize=(10, 6), dpi=130)
        
        for c in range(3):
            cluster_data = df_metrics[df_metrics['cluster'] == c]
            points = cluster_data[['volatility', 'avg_return']].values
            
            plt.scatter(
                cluster_data['volatility'], 
                cluster_data['avg_return'], 
                s=100, 
                c=labels[c]['color'], 
                label=labels[c]['name'],
                edgecolors='black',
                alpha=0.8
            )
            
            if draw_outline and len(points) >= 3:
                try:
                    hull = ConvexHull(points)
                    
                    # Fill the polygon
                    hull_points = points[hull.vertices]
                    plt.fill(hull_points[:,0], hull_points[:,1], alpha=0.15, color=labels[c]['color'])
                    
                    # Draw the boundary
                    for simplex in hull.simplices:
                        plt.plot(points[simplex, 0], points[simplex, 1], color=labels[c]['color'], linewidth=2)
                except Exception as e:
                    print(f"Could not draw hull for cluster {c}: {e}")
            
            # Annotate tickers
            for _, row in cluster_data.iterrows():
                # Avoid overlapping exactly
                plt.text(row['volatility'], row['avg_return'] + (df_metrics['avg_return'].max() * 0.02), row['ticker'], fontsize=9, ha='center')
                
        plt.title(f"Stock Clustering (Return vs Volatility)")
        plt.xlabel("Volatility (Annualized %)")
        plt.ylabel("Average Return (Annualized %)")
        plt.grid(True, linestyle="--", alpha=0.3)
        plt.legend()
        plt.tight_layout()
        
        unique_filename = f"clustering_{uuid.uuid4().hex}.png"
        file_path = os.path.join(settings.MEDIA_ROOT, unique_filename)
        plt.savefig(file_path)
        plt.close()
        
        image_url = request.build_absolute_uri(settings.MEDIA_URL + unique_filename)
        
        # Format response data
        table_data = []
        for _, row in df_metrics.iterrows():
            table_data.append({
                "ticker": row['ticker'],
                "avg_return": round(row['avg_return'], 2),
                "volatility": round(row['volatility'], 2),
                "sharpe": round(row['sharpe'], 2),
                "rsi": round(row['rsi'], 2),
                "cluster_name": row['cluster_name'],
                "cluster_emoji": row['cluster_emoji']
            })
            
        # Sort table by ticker
        table_data.sort(key=lambda x: x['ticker'])
            
        return Response({
            "image_url": image_url,
            "table_data": table_data
        })
