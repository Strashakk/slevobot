import requests

class ExchangeRateAPI:
    url = "https://api.cnb.cz/cnbapi/exrates/daily"

    def __init__(self, timeout=15):
        self.timeout = timeout

    def fetch_rates(self):
        response = requests.get(self.url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        rates = payload.get("rates", [])
        if not isinstance(rates, list):
            raise ValueError("Invalid response format: expected 'rates' list")
        return rates

    def find_currency(self, target_code):
        code = target_code.strip().upper()
        if not code:
            return []
        return [
            rate for rate in self.fetch_rates()
            if rate.get("currencyCode", "").upper() == code
        ]

    def get_currency_rate(self, target_code):
        matches = self.find_currency(target_code)
        if not matches:
            return None
        return matches[0]


if __name__ == "__main__":
    api = ExchangeRateAPI()
    
    target_code = "TRY"
    """Placeholder for testing, intended as /dluhy argument in the future"""
    
    found = api.find_currency(target_code)
    for item in found:
        # print(item.get("currencyCode"), item.get("rate"), item.get("country"))
        normalized_rate = item.get("rate", 0) / item.get("amount", 1)
        print(f"Normalized rate: {normalized_rate}")