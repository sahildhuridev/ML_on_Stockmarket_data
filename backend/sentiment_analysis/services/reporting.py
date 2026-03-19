from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from .storage import get_job_root


class SentimentReportBuilder:
    @staticmethod
    def build(job, result) -> str:
        report_dir = get_job_root(job) / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{job.ticker.lower()}_sentiment_report.pdf"

        with PdfPages(report_path) as pdf:
            fig = plt.figure(figsize=(8.27, 11.69))
            plt.axis("off")
            plt.text(0.05, 0.95, f"Sentiment Analysis Report: {job.ticker}", fontsize=20, weight="bold")
            plt.text(0.05, 0.90, f"Company: {job.company_name or job.ticker}", fontsize=12)
            plt.text(0.05, 0.85, f"Overall Sentiment: {result.overall_label}", fontsize=12)
            plt.text(0.05, 0.81, f"Confidence: {result.overall_confidence:.2f}", fontsize=12)
            plt.text(0.05, 0.77, f"Score: {result.overall_score:.2f}/10", fontsize=12)
            plt.text(0.05, 0.73, f"Momentum: {result.momentum}", fontsize=12)
            plt.text(0.05, 0.69, f"Risk Indicator: {result.risk_indicator}", fontsize=12)
            plt.text(0.05, 0.63, "Summary Payload", fontsize=14, weight="bold")
            plt.text(0.05, 0.59, str(result.summary_json or {}), fontsize=10, wrap=True)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

            if result.distribution_json:
                fig, ax = plt.subplots(figsize=(8.27, 6))
                ax.pie([item["value"] for item in result.distribution_json], labels=[item["label"] for item in result.distribution_json], autopct="%1.1f%%")
                ax.set_title("Sentiment Distribution")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

            if result.daily_trend_json:
                fig, ax = plt.subplots(figsize=(8.27, 6))
                ax.plot([item["date"] for item in result.daily_trend_json], [item["avg_score"] for item in result.daily_trend_json], marker="o")
                ax.set_title("Daily Sentiment Trend")
                ax.tick_params(axis="x", rotation=45)
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

        return str(report_path)

