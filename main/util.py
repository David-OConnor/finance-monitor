# Misc / utility functions
from typing import List, Dict, Iterable

from main.models import AccountType, FinancialAccount, Person


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


def create_transaction_display(accounts: Iterable[FinancialAccount], person: Person) -> List[Dict[str, str]]:
    """Create a set of transactions, formatted for display on the Dashboard table. These
    are combined from all sub-accounts."""

    # todo: You really need datetime for result. How do you get it? Take another pass through, and confirm
    # todo you're not missing something.
    result = []

    # todo: Pending? Would have to parse into the DB.

    # todo: Sort out amounts/pagination etc

    for tran in person.transactions_without_account.all()[:30]:
        result.append(tran.to_display_dict())

    for acc in accounts:
        for tran in acc.transactions.all()[:30]:
            result.append(tran.to_display_dict())

    result.sort(key=lambda t: t["date"], reverse=True)

    for tran in result:
        tran.pop("date")  # Remove the non-display date after sorting.

    return result
