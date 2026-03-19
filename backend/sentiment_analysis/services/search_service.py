import requests


class StockSearchService:
    SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

    @staticmethod
    def search(query: str, limit: int = 8) -> list[dict]:
        query = (query or "").strip()
        if not query:
            return []

        response = requests.get(
            StockSearchService.SEARCH_URL,
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        response.raise_for_status()

        quotes = response.json().get("quotes", [])
        results = []
        for quote in quotes[:limit]:
            symbol = quote.get("symbol")
            company_name = quote.get("shortname") or quote.get("longname")
            if not symbol or not company_name:
                continue
            results.append(
                {
                    "ticker": symbol,
                    "company_name": company_name,
                    "exchange": quote.get("exchange") or quote.get("exchDisp"),
                    "type": quote.get("quoteType"),
                }
            )
        return results

