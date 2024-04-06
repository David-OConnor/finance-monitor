# For automatically updating assets like stocks etc.

from zoneinfo import ZoneInfo
from datetime import datetime
from enum import Enum
import requests
from django.utils import timezone


# We cache remotely-loaded prices for performance reasons; no need to make their HTTP call every time
# we load an asset's value. Cache them in memory.
ASSET_PRICE_CACHE = {}  # { CryptoType: (value, datetime) }

ASSET_TIMEOUT = 60 * 60  # seconds

# todo: DRY with models due to Python's import system
def enum_choices(cls):
    """Required to make Python enums work with Django integer fields"""

    @classmethod
    def choices(cls_):
        return [(key.value, key.name) for key in cls_]

    cls.choices = choices
    return cls


@enum_choices
class CryptoType(Enum):
    Bitcoin = 0
    Ethereum = 1
    Bnb = 2
    Solana = 3
    Xrp = 4

    def abbrev(self) -> str:
        if self == CryptoType.Bitcoin:
            return "btc"
        if self == CryptoType.Ethereum:
            return "eth"
        if self == CryptoType.Bnb:
            return "bnb"
        if self == CryptoType.Solana:
            return "sol"
        if self == CryptoType.Xrp:
            return "xrp"
        else:
            print("\nError: fallthrough on Crypto type")

    def account_value(self, quantity: float) -> float:
        """
        Get an account's value of this cryptocurrency,in USD.
        https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-prices
        """
        cache_details = ASSET_PRICE_CACHE.get(self, [0., timezone.make_aware(datetime.fromisoformat("1999-09-09"))])

        now = timezone.now()
        if (now - cache_details[1]).seconds > ASSET_TIMEOUT:
            print("Updating price on ", self)

            data = requests.get(f"https://api.coinbase.com/v2/prices/{self.abbrev()}-usd/spot").json()
            price = float(data["data"]["amount"]) * quantity

            ASSET_PRICE_CACHE[self] = (price, now)
            return price

        return cache_details[0]
