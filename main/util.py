# Misc / utility functions
from typing import List, Dict, Iterable, Optional
from datetime import date

from django.db.models import Q

from main.models import AccountType, FinancialAccount, Person, SubAccount, Transaction


def unw_helper(net_worth: float, sub_acc: SubAccount) -> float:
    if not sub_acc.ignored and sub_acc.current is not None:
        sign = 1

        if AccountType(sub_acc.type) in [
            AccountType.LOAN,
            AccountType.CREDIT,
        ]:
            sign *= -1

        net_worth += sign * sub_acc.current
    return net_worth


def update_net_worth(net_worth: float, account: FinancialAccount) -> float:
    # Update net worth in place, based on this account's sub-accounts.
    # In Python, this means we must return the new value
    for sub_acc in account.sub_accounts.all():
        net_worth = unw_helper(net_worth, sub_acc)

    return net_worth


def update_net_worth_manual_accs(net_worth: float, person: Person) -> float:
    for sub_acc in person.subaccounts_manual.all():
        net_worth = unw_helper(net_worth, sub_acc)

    return net_worth


def get_transaction_data(
    start_i: int,
    end_i: int,
    accounts: Iterable[FinancialAccount],
    person: Person,
    search_text: Optional[str],
    start: Optional[date],
    end: Optional[date],
) -> List[Dict[str, str]]:
    """Create a set of transactions, serialized for use with the frontend. These
    are combined from all sub-accounts."""
    # todo: Pending? Would have to parse into the DB.

    trans = Transaction.objects.filter(
        Q(account__in=accounts) | Q(person=person)
    )

    if search_text:
        trans = trans.filter(
            #  todo: Categories A/R
            Q(description__icontains=search_text)
            | Q(notes__icontains=search_text)
        )

    if start is not None:
        trans = trans.filter(date__gte=start)
    if end is not None:
        trans = trans.filter(date__lte=end)

    return [tran.serialize() for tran in trans[start_i:end_i]]

