# Misc / utility functions
from typing import List

from main.models import AccountType, FinancialAccount, TransactionCategory


def update_net_worth(net_worth: float, account: FinancialAccount) -> float:
    # Update net worth in place, based on this account's sub-accounts.
    # In Python, this means we must return the new value
    for sub_acc_model in account.sub_accounts.all():
        if not sub_acc_model.ignored and sub_acc_model.current is not None:
            sign = 1

            if AccountType(sub_acc_model.type) in [
                AccountType.LOAN,
                AccountType.CREDIT,
            ]:
                sign *= -1

            net_worth += sign * sub_acc_model.current
    return net_worth


def cleanup_categories(cats: List[TransactionCategory]) -> List[TransactionCategory]:
    """Simplify a category list if multiple related are listed together by the API.
    Return the result, due to Python's sloppy mutation-in-place."""
    cats = list(set(cats))  # Remove duplicates.

    if TransactionCategory.TRAVEL in cats and TransactionCategory.AIRLINES_AND_AVIATION_SERVICES in cats:
        cats.remove(TransactionCategory.TRAVEL)

    if TransactionCategory.TRANSFER in cats and TransactionCategory.DEPOSIT in cats:
        cats.remove(TransactionCategory.TRANSFER)

    if TransactionCategory.TRANSFER in cats and TransactionCategory.PAYROLL in cats:
        cats.remove(TransactionCategory.PAYROLL)

    if TransactionCategory.RESTAURANTS in cats and TransactionCategory.FOOD_AND_DRINK in cats:
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if TransactionCategory.FAST_FOOD in cats and TransactionCategory.FOOD_AND_DRINK in cats:
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if TransactionCategory.RESTAURANTS in cats and TransactionCategory.FAST_FOOD in cats:
        cats.remove(TransactionCategory.RESTAURANTS)

    if TransactionCategory.GYMS_AND_FITNESS_CENTERS in cats and TransactionCategory.RECREATION in cats:
        cats.remove(TransactionCategory.RECREATION)

    # Lots of bogus food+drink cats inserted by Plaid.
    if TransactionCategory.FOOD_AND_DRINK in cats and TransactionCategory.CREDIT_CARD in cats:
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if TransactionCategory.FOOD_AND_DRINK in cats and TransactionCategory.TRANSFER in cats:
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if TransactionCategory.FOOD_AND_DRINK in cats and TransactionCategory.TRAVEL in cats:
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    return cats

