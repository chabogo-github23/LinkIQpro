import requests

CURRENCY_DECIMALS = {
    "USD": 2,  # cents
    "KES": 2,  # kobo
    "NGN": 2,  # kobo
    # Add other currencies as needed
}

def convert_usd_to_currency_for_paystack(amount_usd, target_currency):
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
        data = response.json()
        rates = data.get("rates", {})

        if target_currency not in rates:
            raise ValueError(f"Unsupported currency: {target_currency}")

        # Convert USD to target currency
        converted = amount_usd * rates[target_currency]

        # Convert to lowest currency unit
        decimals = CURRENCY_DECIMALS.get(target_currency, 2)
        amount_in_smallest_unit = int(round(converted * (10 ** decimals)))

        return amount_in_smallest_unit

    except Exception as e:
        print(f"Currency conversion error: {e}")
        return None
