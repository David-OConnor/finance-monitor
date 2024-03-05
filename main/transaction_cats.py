# A dedicated file for transaction categories, due to its size.
from enum import Enum
from typing import List


# todo: C+P from main.models due ot circular import concern
def enum_choices(cls):
    """Required to make Python enums work with Django integer fields"""

    @classmethod
    def choices(cls_):
        return [(key.value, key.name) for key in cls_]

    cls.choices = choices
    return cls


@enum_choices
class TransactionCategory(Enum):
    """These are types as reported by Plaid"""

    UNCATEGORIZED = -1
    FOOD_AND_DRINK = 0
    RESTAURANTS = 1
    TRAVEL = 3
    AIRLINES_AND_AVIATION_SERVICES = 4
    RECREATION = 5
    GYMS_AND_FITNESS_CENTERS = 6
    TRANSFER = 7
    DEPOSIT = 8
    PAYROLL = 9
    CREDIT_CARD = 10
    FAST_FOOD = 11  # todo: Move up
    DEBIT = 12
    SHOPS = 13
    PAYMENT = 14
    COFFEE_SHOP = 15
    TAXI = 16
    SPORTING_GOODS = 17
    ELECTRONICS = 18
    PETS = 19
    CHILDREN = 20
    MORTGAGE_AND_RENT = 21
    CAR = 22
    HOME_AND_GARDEN = 23
    MEDICAL = 24
    ENTERTAINMENT = 25
    BILLS_AND_UTILITIES = 26
    INVESTMENTS = 27
    FEES = 28
    TAXES = 29
    BUSINESS_SERVICES = 30
    CASH_AND_CHECKS = 31
    GIFT = 32
    EDUCATION = 33

    @classmethod
    def from_str(cls, s: str) -> "TransactionCategory":
        """A little loose. We currently use it for both Plaid, and mint."""
        s = s.lower()

        if "uncategorized" == s:
            return cls.UNCATEGORIZED
        if "food" in s or "grocer" in s:
            return cls.FOOD_AND_DRINK
        if "restau" in s:
            return cls.RESTAURANTS
        if "travel" in s:
            return cls.TRAVEL
        if "airlines" in s:
            return cls.AIRLINES_AND_AVIATION_SERVICES
        if "recrea" in s:
            return cls.RECREATION
        if "gym" in s or "fitness" in s or "health" in s:
            return cls.GYMS_AND_FITNESS_CENTERS
        if "transfer" in s:
            return cls.TRANSFER
        if "deposit" in s:
            return cls.DEPOSIT
        if "payroll" in s or "income" in s:
            return cls.PAYROLL
        if "credit c" in s:
            return cls.CREDIT_CARD
        if "fast food" in s:
            return cls.FAST_FOOD
        if "debit" == s:
            return cls.DEBIT
        if "shop" in s:
            return cls.SHOPS
        if "payment" == s:
            return cls.PAYMENT
        if "coffee shop" == s:
            return cls.COFFEE_SHOP
        if "taxi" == s:
            return cls.TAXI
        if "sporting" == s:
            return cls.SPORTING_GOODS
        if "electron" in s:
            return cls.ELECTRONICS
        if "pet" in s:
            return cls.PETS
        if "child" in s or "kid" in s:
            return cls.CHILDREN
        if "mortgate" in s or "rent" in s:
            return cls.MORTGAGE_AND_RENT
        if "car" in s or "auto" in s:
            return cls.CAR
        if "home" in s or "garden" in s:
            return cls.HOME_AND_GARDEN
        if "medical" in s:
            return cls.MEDICAL
        if "entertainment" in s:
            return cls.ENTERTAINMENT
        if "bill" in s or "utility" in s:
            return cls.BILLS_AND_UTILITIES
        if "invest" in s:
            return cls.INVESTMENTS
        if "fees" in s:
            return cls.FEES
        if "taxes" in s:
            return cls.TAXES
        if "business" in s:
            return cls.BUSINESS_SERVICES
        if "cash" in s or "check" in s:
            return cls.CASH_AND_CHECKS
        if "gift" in s:
            return cls.GIFT
        if "eduation" in s:
            return cls.EDUCATION

        print("Fallthrough in parsing transaction category: ", s)
        return cls.UNCATEGORIZED

    def to_str(self) -> str:
        if self == TransactionCategory.UNCATEGORIZED:
            return "Uncategorized"
        if self == TransactionCategory.FOOD_AND_DRINK:
            return "Food and drink"
        if self == TransactionCategory.RESTAURANTS:
            return "Restaurants"
        if self == TransactionCategory.TRAVEL:
            return "Travel"
        if self == TransactionCategory.AIRLINES_AND_AVIATION_SERVICES:
            return "Airlines"
        if self == TransactionCategory.RECREATION:
            return "Recreation"
        if self == TransactionCategory.GYMS_AND_FITNESS_CENTERS:
            return "Gyms"
        if self == TransactionCategory.TRANSFER:
            return "Transfer"
        if self == TransactionCategory.DEPOSIT:
            return "Deposit"
        if self == TransactionCategory.PAYROLL:
            return "Payroll"
        if self == TransactionCategory.CREDIT_CARD:
            return "Credit card"
        if self == TransactionCategory.FAST_FOOD:
            return "Fast food"
        if self == TransactionCategory.DEBIT:
            return "Debit"
        if self == TransactionCategory.SHOPS:
            return "Shops"
        if self == TransactionCategory.PAYMENT:
            return "Payment"
        if self == TransactionCategory.COFFEE_SHOP:
            return "Coffee shop"
        if self == TransactionCategory.TAXI:
            return "Taxi"
        if self == TransactionCategory.SPORTING_GOODS:
            return "Sporting goods"
        if self == TransactionCategory.ELECTRONICS:
            return "Electronics"
        if self == TransactionCategory.PETS:
            return "Pets"
        if self == TransactionCategory.CHILDREN:
            return "Children"
        if self == TransactionCategory.MORTGAGE_AND_RENT:
            return "Mortgage and rent"
        if self == TransactionCategory.CAR:
            return "Car"
        if self == TransactionCategory.HOME_AND_GARDEN:
            return "Home and garden"
        if self == TransactionCategory.MEDICAL:
            return "Medical"
        if self == TransactionCategory.ENTERTAINMENT:
            return "Entertainment"
        if self == TransactionCategory.BILLS_AND_UTILITIES:
            return "Bills and utilities"
        if self == TransactionCategory.INVESTMENTS:
            return "Investments"
        if self == TransactionCategory.FEES:
            return "Fees"
        if self == TransactionCategory.TAXES:
            return "Taxes"
        if self == TransactionCategory.BUSINESS_SERVICES:
            return "Business services"
        if self == TransactionCategory.CASH_AND_CHECKS:
            return "Cash and checks"
        if self == TransactionCategory.GIFTS:
            return "Gifts"
        if self == TransactionCategory.EDUCATION:
            return "Education"

        print("Fallthrough on cat to string", self)
        return "Fallthrough"

    def to_icon(self) -> str:
        if self == TransactionCategory.UNCATEGORIZED:
            return ""
        if self == TransactionCategory.FOOD_AND_DRINK:
            return "🍎"
        if self == TransactionCategory.RESTAURANTS:
            return "🍴"
        if self == TransactionCategory.TRAVEL:
            return "✈️"
        if self == TransactionCategory.AIRLINES_AND_AVIATION_SERVICES:
            return "✈️"
        if self == TransactionCategory.RECREATION:
            return "⛵"
        if self == TransactionCategory.GYMS_AND_FITNESS_CENTERS:
            return "🏋️"
        if self == TransactionCategory.TRANSFER:
            return "💵 ➡️"
        if self == TransactionCategory.DEPOSIT:
            return "💵 ⬆️"
        if self == TransactionCategory.PAYROLL:
            return "💵 ⬆️"
        if self == TransactionCategory.CREDIT_CARD:
            return "💵 ⬇️"
        if self == TransactionCategory.FAST_FOOD:
            return "🍔"
        if self == TransactionCategory.DEBIT:
            return "💵 ⬇️"
        if self == TransactionCategory.SHOPS:
            return "🛒"
        if self == TransactionCategory.PAYMENT:
            return "💵 "
        if self == TransactionCategory.COFFEE_SHOP:
            return "☕"
        if self == TransactionCategory.TAXI:
            return "🚕"
        if self == TransactionCategory.SPORTING_GOODS:
            return "⚽"
        if self == TransactionCategory.ELECTRONICS:
            return "🔌"
        if self == TransactionCategory.PETS:
            return "🐕"
        if self == TransactionCategory.CHILDREN:
            return "🧒"
        if self == TransactionCategory.MORTGAGE_AND_RENT:
            return "🏠"
        if self == TransactionCategory.CAR:
            return "🚗"
        if self == TransactionCategory.HOME_AND_GARDEN:
            return "🏡"
        if self == TransactionCategory.MEDICAL:
            return "☤"
        if self == TransactionCategory.ENTERTAINMENT:
            return "🎥"
        if self == TransactionCategory.BILLS_AND_UTILITIES:
            return "⚡"
        if self == TransactionCategory.INVESTMENTS:
            return "👨‍📈"
        if self == TransactionCategory.FEES:
            return "💸"
        if self == TransactionCategory.TAXES:
            return "🏛️💵 "
        if self == TransactionCategory.BUSINESS_SERVICES:
            return "📈"
        if self == TransactionCategory.CASH_AND_CHECKS:
            return "💵"
        if self == TransactionCategory.GIFTS:
            return "🎁"
        if self == TransactionCategory.EDUCATION:
            return "🎓"


        print("Fallthrough on cat to icon", self)
        return "Fallthrough"


def category_override(
    descrip: str, categories: List[TransactionCategory]
) -> List[TransactionCategory]:
    """Manual category overrides, based on observation."""
    descrip = descrip.lower()
    # Some category overrides. Separate function A/R
    if "coffee" in descrip:
        categories = [TransactionCategory.COFFEE_SHOP]

    # Prevents a restaurant style logo
    if (
        "trader joe" in descrip
        or "whole foods" in descrip
        or "aldi" in descrip
        or "food lion" in descrip
        or "wegman" in descrip
    ):
        categories = [TransactionCategory.FOOD_AND_DRINK]

    return categories


def cleanup_categories(cats: List[TransactionCategory]) -> List[TransactionCategory]:
    """Simplify a category list if multiple related are listed together by the API.
    Return the result, due to Python's sloppy mutation-in-place."""
    cats = list(set(cats))  # Remove duplicates.

    if (
        TransactionCategory.TRAVEL in cats
        and TransactionCategory.AIRLINES_AND_AVIATION_SERVICES in cats
    ):
        cats.remove(TransactionCategory.TRAVEL)

    if TransactionCategory.TRANSFER in cats and TransactionCategory.DEPOSIT in cats:
        cats.remove(TransactionCategory.TRANSFER)

    if TransactionCategory.TRANSFER in cats and TransactionCategory.DEBIT in cats:
        cats.remove(TransactionCategory.TRANSFER)

    if TransactionCategory.TRANSFER in cats and TransactionCategory.PAYROLL in cats:
        cats.remove(TransactionCategory.PAYROLL)

    if (
        TransactionCategory.RESTAURANTS in cats
        and TransactionCategory.FOOD_AND_DRINK in cats
    ):
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if (
        TransactionCategory.RESTAURANTS in cats
        and TransactionCategory.COFFEE_SHOP in cats
    ):
        cats.remove(TransactionCategory.RESTAURANTS)

    if (
        TransactionCategory.FAST_FOOD in cats
        and TransactionCategory.FOOD_AND_DRINK in cats
    ):
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if (
        TransactionCategory.RESTAURANTS in cats
        and TransactionCategory.FAST_FOOD in cats
    ):
        cats.remove(TransactionCategory.RESTAURANTS)

    if (
        TransactionCategory.GYMS_AND_FITNESS_CENTERS in cats
        and TransactionCategory.RECREATION in cats
    ):
        cats.remove(TransactionCategory.RECREATION)

    # Lots of bogus food+drink cats inserted by Plaid.
    if (
        TransactionCategory.FOOD_AND_DRINK in cats
        and TransactionCategory.CREDIT_CARD in cats
    ):
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if TransactionCategory.PAYMENT in cats and TransactionCategory.CREDIT_CARD in cats:
        cats.remove(TransactionCategory.PAYMENT)

    if (
        TransactionCategory.FOOD_AND_DRINK in cats
        and TransactionCategory.TRANSFER in cats
    ):
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if TransactionCategory.FOOD_AND_DRINK in cats and TransactionCategory.SHOPS in cats:
        cats.remove(TransactionCategory.SHOPS)

    if (
        TransactionCategory.FOOD_AND_DRINK in cats
        and TransactionCategory.TRAVEL in cats
    ):
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if TransactionCategory.TAXI in cats and TransactionCategory.TRAVEL in cats:
        cats.remove(TransactionCategory.TRAVEL)

    if len(cats) > 1:
        print(">1 len categories: \n", cats)

    return cats
