# Misc / utility functions
import json
from datetime import date
from typing import List, Dict, Iterable

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

    if (
        TransactionCategory.PAYMENT in cats
        and TransactionCategory.CREDIT_CARD in cats
    ):
        cats.remove(TransactionCategory.PAYMENT)

    if (
        TransactionCategory.FOOD_AND_DRINK in cats
        and TransactionCategory.TRANSFER in cats
    ):
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if (
        TransactionCategory.FOOD_AND_DRINK in cats
        and TransactionCategory.SHOPS in cats
    ):
        cats.remove(TransactionCategory.SHOPS)

    if (
        TransactionCategory.FOOD_AND_DRINK in cats
        and TransactionCategory.TRAVEL in cats
    ):
        cats.remove(TransactionCategory.FOOD_AND_DRINK)

    if (
        TransactionCategory.TAXI in cats
        and TransactionCategory.TRAVEL in cats
    ):
        cats.remove(TransactionCategory.TRAVEL)

    if len(cats) > 1:
        print(">1 len categories: \n", cats)

    return cats


def create_transaction_display(accounts: Iterable[FinancialAccount]) -> List[Dict[str, str]]:
    """Create a set of transactions, formatted for display on the Dashboard table. These
    are combined from all sub-accounts."""

    # todo: You really need datetime for result. How do you get it? Take another pass through, and confirm
    # todo you're not missing something.
    result = []

    # todo: Pending? Would have to parse into the DB.

    for acc in accounts:
        for tran in acc.transactions.all():
            cats = [TransactionCategory(cat) for cat in json.loads(tran.categories)]
            cats = cleanup_categories(cats)

            # Only display the year if not the present one.
            if tran.date.year == date.today().year:
                if tran.datetime is not None:
                    date_display = tran.datetime.strftime("%m/%d %H:%M")
                else:
                    date_display = tran.date.strftime("%m/%d")
            else:
                if tran.datetime is not None:
                    date_display = tran.datetime.strftime("%m/%d%y %H:%M")
                else:
                    date_display = tran.date.strftime("%m/%d/%y")


            description = tran.description
            if tran.pending:
                # todo: Separate element so you can make it faded, or otherwise a custom style or cell.
                description += " (pending)"

            result.append(
                {
                    "categories": " | ".join([c.to_icon() for c in cats]),
                    "description": description,
                    # todo: Currency-appropriate symbol.
                    "amount": f"${tran.amount:,.2f}",
                    "amount_class": (
                        "tran_pos" if tran.amount > 0.0 else "tran_neg"
                    ),  # eg to color green or red.
                    "date_display": date_display,
                    "date": tran.date,
                }
            )

    result.sort(key=lambda t: t["date"], reverse=True)
    return result
