# For automatically updating assets like stocks etc.

from enum import Enum
import requests


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

    # todo: Cache these, loading every 30 mins! For performance.
    def account_value(self, quantity: float) -> float:
        """
        Get an account's value of this cryptocurrency,in USD.
        https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-prices
        """
        data = requests.get(f"https://api.coinbase.com/v2/prices/{self.abbrev()}-usd/spot").json()

        return float(data["data"]["amount"]) * quantity
