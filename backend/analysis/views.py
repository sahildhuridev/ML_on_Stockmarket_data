from django.shortcuts import render

# Create your views here.
import matplotlib
matplotlib.use("Agg")

import yfinance as yf
import uuid
import numpy as np

import matplotlib.pyplot as plt
import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from portfolios.models import Portfolio


def _to_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _save_plot_and_get_url(request, filename_prefix):
    unique_filename = f"{filename_prefix}_{uuid.uuid4().hex}.png"
    file_path = os.path.join(settings.MEDIA_ROOT, unique_filename)
    plt.savefig(file_path)
    plt.close()
    return request.build_absolute_uri(settings.MEDIA_URL + unique_filename)


class PriceGraphView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ticker = request.GET.get('ticker')
        data = yf.download(ticker, period="6mo")

        plt.figure()
        data['Close'].plot(title=f"{ticker} Price Chart")

        file_path = os.path.join(settings.MEDIA_ROOT, f"{ticker}.png")
        plt.savefig(file_path)
        plt.close()

        image_url = request.build_absolute_uri(settings.MEDIA_URL + f"{ticker}.png")

        return Response({
            "ticker": ticker,
            "image_url": image_url
        })


class PERatioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio_id = request.GET.get("portfolio_id")

        if not portfolio_id:
            return Response({"error": "portfolio_id required"}, status=400)

        try:
            portfolio = Portfolio.objects.get(
                id=portfolio_id,
                user=request.user
            )
        except Portfolio.DoesNotExist:
            return Response({"error": "Invalid portfolio"}, status=404)

        stocks = portfolio.stocks.all()

        pe_data = []
        tickers = []

        for stock in stocks:
            try:
                ticker_obj = yf.Ticker(stock.ticker)
                info = ticker_obj.info
                pe = info.get("trailingPE")

                if pe and isinstance(pe, (int, float)) and pe > 0:
                    pe_data.append(pe)
                    tickers.append(stock.ticker)

            except Exception:
                continue

        if not pe_data:
            return Response({"error": "No PE data available"}, status=400)

        pe_array = np.array(pe_data)

        # Valuation Lines
        q1 = float(np.nanpercentile(pe_array, 25))
        q3 = float(np.nanpercentile(pe_array, 75))
        median = float(np.nanmedian(pe_array))

        # Plot Scatter
        plt.figure(figsize=(12, 8), dpi=130)

        x = np.arange(len(pe_array))

        plt.scatter(
            x,
            pe_array,
            s=90,
            c="#1f77b4",
            edgecolors="black",
            linewidths=0.7,
            zorder=3,
        )

        # Add ticker labels below dots
        for i, pe in enumerate(pe_array):
            plt.text(
                i,
                pe - 0.5,
                tickers[i],
                ha="center",
                va="top",
                fontsize=9,
            )

            # Add valuation lines
            plt.axhline(q1, color="#2ca02c", linestyle="--",
                        linewidth=1.5, label=f"Undervalued (Q1 ≈ {q1:.1f})")

            plt.axhline(q3, color="#d62728", linestyle="--",
                        linewidth=1.5, label=f"Overvalued (Q3 ≈ {q3:.1f})")

            plt.axhline(median, color="#ff7f0e", linestyle=":",
                        linewidth=1.5, label=f"Median PE ≈ {median:.1f}")

            plt.title(f"PE Ratio Scatter – {portfolio.name}")
            plt.xlabel("Companies")
            plt.ylabel("Trailing PE")
            plt.grid(True, linestyle="--", alpha=0.35)
            plt.xticks(x, tickers, rotation=35, ha="right", fontsize=8)
            plt.legend(loc="best")
            plt.tight_layout()

            # Save unique file
            unique_filename = f"pe_scatter_{uuid.uuid4().hex}.png"
            file_path = os.path.join(settings.MEDIA_ROOT, unique_filename)

            plt.savefig(file_path)
            plt.close()

            image_url = request.build_absolute_uri(
                settings.MEDIA_URL + unique_filename
            )

            return Response({
                "portfolio": portfolio.name,
                "undervalued_line": round(q1, 2),
                "overvalued_line": round(q3, 2),
                "median_pe": round(median, 2),
                "image_url": image_url
            })


class VolumePortfolioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio_id = request.GET.get("portfolio_id")

        if not portfolio_id:
            return Response({"error": "portfolio_id required"}, status=400)

        try:
            portfolio = Portfolio.objects.get(
                id=portfolio_id,
                user=request.user
            )
        except Portfolio.DoesNotExist:
            return Response({"error": "Invalid portfolio"}, status=404)

        stocks = portfolio.stocks.all()

        tickers = []
        avg_volumes = []

        for stock in stocks:
            ticker = stock.ticker
            try:
                data = yf.download(ticker, period="3mo")
                if data is None or data.empty or "Volume" not in data.columns:
                    continue
                vol_series = data["Volume"].dropna()
                if vol_series.empty:
                    continue
                tickers.append(ticker)
                avg_volumes.append(float(vol_series.mean()))
            except Exception:
                continue

        if not avg_volumes:
            return Response({"error": "No volume data available"}, status=400)

        plt.figure(figsize=(12, 6), dpi=130)
        x = np.arange(len(tickers))

        plt.bar(x, avg_volumes, color="#6366f1", edgecolor="black", linewidth=0.6)
        plt.title(f"Average Daily Volume (3mo) – {portfolio.name}")
        plt.xlabel("Tickers")
        plt.ylabel("Avg Volume")
        plt.grid(True, axis="y", linestyle="--", alpha=0.35)
        plt.xticks(x, tickers, rotation=35, ha="right", fontsize=9)
        plt.tight_layout()

        image_url = _save_plot_and_get_url(request, "volume_portfolio")

        return Response({
            "portfolio": portfolio.name,
            "metric": "avg_daily_volume_3mo",
            "image_url": image_url,
        })


class VolumeChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ticker = request.GET.get("ticker")

        if not ticker:
            return Response({"error": "ticker required"}, status=400)

        try:
            data = yf.download(ticker, period="6mo")
            if data is None or data.empty or "Volume" not in data.columns:
                return Response({"error": "No volume data available"}, status=400)

            vol = data["Volume"].dropna()
            if vol.empty:
                return Response({"error": "No volume data available"}, status=400)

            plt.figure(figsize=(12, 6), dpi=130)
            plt.plot(vol.index, vol.values, color="#0ea5e9", linewidth=1.4)
            plt.fill_between(vol.index, vol.values, color="#0ea5e9", alpha=0.15)
            plt.title(f"{ticker} Volume (6mo)")
            plt.xlabel("Date")
            plt.ylabel("Volume")
            plt.grid(True, linestyle="--", alpha=0.35)
            plt.tight_layout()

            image_url = _save_plot_and_get_url(request, f"volume_{ticker}")
            return Response({"ticker": ticker, "image_url": image_url})
        except Exception as e:
            print(f"Error generating volume chart for {ticker}: {e}")
            return Response({"error": "Error generating volume chart", "details": str(e)}, status=500)


class DiscountedValueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio_id = request.GET.get("portfolio_id")

        if not portfolio_id:
            return Response({"error": "portfolio_id required"}, status=400)

        try:
            portfolio = Portfolio.objects.get(
                id=portfolio_id,
                user=request.user
            )
        except Portfolio.DoesNotExist:
            return Response({"error": "Invalid portfolio"}, status=404)

        stocks = portfolio.stocks.all()

        tickers = []
        positions = []
        lows = []
        highs = []
        discount_values = []
        rows = []

        for stock in stocks:
            ticker = stock.ticker
            try:
                info = yf.Ticker(ticker).info
                high = _to_float(info.get("fiftyTwoWeekHigh"))
                low = _to_float(info.get("fiftyTwoWeekLow"))
                price = _to_float(info.get("regularMarketPrice"))
                
                if price is None:
                    price = _to_float(info.get("currentPrice"))

                if high is None or low is None or price is None:
                    continue
                if high <= low:
                    continue
                if price <= 0:
                    continue

                position_in_range = (price - low) / (high - low)
                position_in_range = float(np.clip(position_in_range, 0.0, 1.0))
                
                discount_val = high - price

                tickers.append(ticker)
                positions.append(position_in_range)
                lows.append(low)
                highs.append(high)
                discount_values.append(discount_val)
                
                rows.append({
                    "ticker": ticker,
                    "price": round(price, 2),
                    "52w_high": round(high, 2),
                    "52w_low": round(low, 2),
                    "position_in_range": round(position_in_range, 4),
                    "discount_value": round(discount_val, 2),
                })
            except Exception:
                continue

        if not positions:
            return Response({"error": "No 52-week high/low data available"}, status=400)

        x = np.arange(len(tickers))
        
        # Plot 2: 52-Week Low
        plt.figure(figsize=(12, 6), dpi=130)
        plt.bar(x, lows, color="#3b82f6", edgecolor="black", linewidth=0.6)
        plt.title(f"52-Week Low – {portfolio.name}")
        plt.xlabel("Tickers")
        plt.ylabel("52w Low Price")
        plt.grid(True, axis="y", linestyle="--", alpha=0.35)
        plt.xticks(x, tickers, rotation=35, ha="right", fontsize=9)
        max_low = max(lows) if lows else 1
        for i, v in enumerate(lows):
            plt.text(i, v + (max_low * 0.01), f"{v:.1f}", ha="center", va="bottom", fontsize=8)
        plt.tight_layout()
        image_url_low = _save_plot_and_get_url(request, "52w_low")
        
        # Plot 3: 52-Week High
        plt.figure(figsize=(12, 6), dpi=130)
        plt.bar(x, highs, color="#ef4444", edgecolor="black", linewidth=0.6)
        plt.title(f"52-Week High – {portfolio.name}")
        plt.xlabel("Tickers")
        plt.ylabel("52w High Price")
        plt.grid(True, axis="y", linestyle="--", alpha=0.35)
        plt.xticks(x, tickers, rotation=35, ha="right", fontsize=9)
        max_high = max(highs) if highs else 1
        for i, v in enumerate(highs):
            plt.text(i, v + (max_high * 0.01), f"{v:.1f}", ha="center", va="bottom", fontsize=8)
        plt.tight_layout()
        image_url_high = _save_plot_and_get_url(request, "52w_high")
        
        # Plot 4: Discounted Value (52W High - Price)
        plt.figure(figsize=(12, 6), dpi=130)
        max_discount_idx = np.argmax(discount_values) if discount_values else -1
        colors = ["#f59e0b" if i == max_discount_idx else "#9ca3af" for i in range(len(discount_values))]
        
        plt.bar(x, discount_values, color=colors, edgecolor="black", linewidth=0.6)
        plt.title(f"Discounted Value (52W High - Current Price) – {portfolio.name}")
        plt.xlabel("Tickers")
        plt.ylabel("Discount Amount")
        plt.grid(True, axis="y", linestyle="--", alpha=0.35)
        plt.xticks(x, tickers, rotation=35, ha="right", fontsize=9)
        max_discount = max(discount_values) if discount_values else 1
        for i, v in enumerate(discount_values):
            plt.text(i, v + (max_discount * 0.01), f"{v:.1f}", ha="center", va="bottom", fontsize=8,
                     fontweight='bold' if i == max_discount_idx else 'normal')
        plt.tight_layout()
        image_url_discount = _save_plot_and_get_url(request, "discount_amount")

        return Response({
            "portfolio": portfolio.name,
            "image_url_low": image_url_low,
            "image_url_high": image_url_high,
            "image_url_discount": image_url_discount,
            "rows": rows,
        })


class ModelAccuracyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        portfolio_id = request.data.get("portfolio_id")
        target_date = request.data.get("target_date")
        target_hour = request.data.get("target_hour")

        if not portfolio_id or not target_date or not target_hour:
            return Response(
                {"error": "portfolio_id, target_date, and target_hour are required"},
                status=400,
            )

        try:
            portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
        except Portfolio.DoesNotExist:
            return Response({"error": "Invalid portfolio"}, status=404)

        stocks = portfolio.stocks.all()
        if not stocks.exists():
            return Response(
                {"error": "No stocks in this portfolio"}, status=400
            )

        from .model_accuracy import analyze_portfolio_stocks

        try:
            result = analyze_portfolio_stocks(stocks, target_date, target_hour)
            return Response(result, status=200)
        except Exception as e:
            return Response(
                {"error": "Analysis failed", "details": str(e)}, status=500
            )