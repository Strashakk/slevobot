from cogs.exchangerate_api import ExchangeRateAPI

api = ExchangeRateAPI()
normalized_rate = api.get_normalized_rate("EUR")
print(f"Normalized rate: {normalized_rate}")