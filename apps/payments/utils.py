"""
Payment Utilities
Helper functions for payment processing
"""
import requests
from decimal import Decimal
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Currency decimal places (for converting to smallest unit)
CURRENCY_DECIMALS = {
    "USD": 2,
    "KES": 2,
    "NGN": 2,
    "GHS": 2,
    "ZAR": 2,
    "GBP": 2,
    "EUR": 2,
}

# Supported currencies for Paystack
SUPPORTED_CURRENCIES = ['USD', 'KES', 'NGN', 'GHS', 'ZAR', 'GBP', 'EUR']


def get_exchange_rates() -> Optional[dict]:
    """
    Fetch current exchange rates from USD to other currencies.
    Returns dict of rates or None on failure.
    """
    try:
        response = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("rates", {})
    except requests.RequestException as e:
        logger.error(f"Failed to fetch exchange rates: {e}")
        return None
    except Exception as e:
        logger.error(f"Exchange rate parsing error: {e}")
        return None


def convert_usd_to_currency(amount_usd: float, target_currency: str) -> Tuple[Optional[int], Optional[float], Optional[str]]:
    """
    Convert USD amount to target currency for Paystack.
    
    Args:
        amount_usd: Amount in USD (e.g., 100.00)
        target_currency: Target currency code (e.g., 'KES', 'NGN')
    
    Returns:
        Tuple of (amount_in_smallest_unit, converted_amount, error_message)
        - amount_in_smallest_unit: Integer amount for Paystack API (e.g., 10000 for $100 or KES equivalent)
        - converted_amount: Float of the converted amount for display
        - error_message: Error string if conversion failed, None otherwise
    """
    # Validate currency
    if target_currency not in SUPPORTED_CURRENCIES:
        return None, None, f"Unsupported currency: {target_currency}. Supported: {', '.join(SUPPORTED_CURRENCIES)}"
    
    # If target is USD, no conversion needed
    if target_currency == 'USD':
        decimals = CURRENCY_DECIMALS.get(target_currency, 2)
        amount_in_smallest = int(round(amount_usd * (10 ** decimals)))
        return amount_in_smallest, amount_usd, None
    
    # Fetch exchange rates
    rates = get_exchange_rates()
    if not rates:
        return None, None, "Failed to fetch exchange rates. Please try again."
    
    # Check if currency is in rates
    if target_currency not in rates:
        return None, None, f"Exchange rate not available for {target_currency}"
    
    try:
        # Convert USD to target currency
        exchange_rate = rates[target_currency]
        converted_amount = amount_usd * exchange_rate
        
        # Convert to smallest currency unit
        decimals = CURRENCY_DECIMALS.get(target_currency, 2)
        amount_in_smallest = int(round(converted_amount * (10 ** decimals)))
        
        logger.info(
            f"Currency conversion: ${amount_usd} USD -> {converted_amount:.2f} {target_currency} "
            f"(rate: {exchange_rate}, smallest unit: {amount_in_smallest})"
        )
        
        return amount_in_smallest, converted_amount, None
        
    except Exception as e:
        logger.error(f"Currency conversion calculation error: {e}")
        return None, None, f"Currency conversion failed: {str(e)}"


def get_exchange_rate(target_currency: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Get the current exchange rate from USD to target currency.
    
    Args:
        target_currency: Target currency code
        
    Returns:
        Tuple of (exchange_rate, error_message)
    """
    if target_currency == 'USD':
        return 1.0, None
    
    rates = get_exchange_rates()
    if not rates:
        return None, "Failed to fetch exchange rates"
    
    if target_currency not in rates:
        return None, f"Exchange rate not available for {target_currency}"
    
    return rates[target_currency], None


def format_currency_amount(amount: float, currency: str) -> str:
    """
    Format amount with currency symbol for display.
    """
    symbols = {
        'USD': '$',
        'KES': 'KES ',
        'NGN': '₦',
        'GHS': 'GH₵',
        'ZAR': 'R',
        'GBP': '£',
        'EUR': '€',
    }
    symbol = symbols.get(currency, currency + ' ')
    return f"{symbol}{amount:,.2f}"
