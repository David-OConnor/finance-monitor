# Misc / utility functions
import json
from collections import defaultdict
from io import TextIOWrapper
from typing import List, Dict, Iterable, Optional, Tuple
from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from main import transaction_cats
from main.models import (
    AccountType,
    FinancialAccount,
    Person,
    SubAccount,
    Transaction,
    SubAccountType,
    SnapshotAccount,
    SnapshotPerson,
)
from main.transaction_cats import TransactionCategory


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


def get_transaction_data(
    start_i: Optional[int],
    end_i: Optional[int],
    accounts: Iterable[FinancialAccount],
    person: Person,
    search_text: Optional[str],
    start: Optional[date],
    end: Optional[date],
) -> List[Transaction]:
    """Create a set of transactions, serialized for use with the frontend. These
    are combined from all sub-accounts."""
    # todo: Pending? Would have to parse into the DB.

    trans = Transaction.objects.filter(Q(account__in=accounts) | Q(person=person))

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

    if start_i is not None and end_i is not None:
        return trans[start_i:end_i]
    return trans


def load_dash_data(person: Person, no_preser: bool = False) -> Dict:
    """Load account balances, transactions, and totals."""

    # todo: Rethink totals.
    accounts = person.accounts.all()

    sub_accounts = SubAccount.objects.filter(
        Q(account__person=person) | Q(person=person)
    )

    net_worth = 0.0
    for acc in sub_accounts:
        net_worth = unw_helper(net_worth, acc)

    totals = {
        "cash": 0,
        "investment": 0,
        "crypto": 0,
        "credit_debit": 0,
        "loans": 0,
        "assets": 0,
        # net_worth: f"{net_worth:,.0f}"
        "net_worth": net_worth,
    }

    for sub_acc in SubAccount.objects.filter(
        Q(account__person=person) | Q(person=person)
    ):
        if sub_acc.ignored:
            continue

        t = SubAccountType(sub_acc.sub_type)

        # todo: Integer math and DB storage; not floating point.

        # todo: Consistency with use of minus signs on debgs. Currently reverse behavior on cat
        # total and per-accoutn for loads, CC+Debit

        if t in [SubAccountType.CHECKING, SubAccountType.SAVINGS]:
            totals["cash"] += sub_acc.current
        elif t in [SubAccountType.DEBIT_CARD, SubAccountType.CREDIT_CARD]:
            totals["credit_debit"] -= sub_acc.current
        elif t in [
            SubAccountType.T401K,
            SubAccountType.CD,
            SubAccountType.MONEY_MARKET,
            SubAccountType.IRA,
            SubAccountType.MUTUAL_FUND,
            SubAccountType.BROKERAGE,
            SubAccountType.ROTH,
        ]:
            totals["investment"] += sub_acc.current
        elif t in [SubAccountType.STUDENT, SubAccountType.MORTGAGE]:
            totals["loans"] -= sub_acc.current
        elif t in [SubAccountType.CRYPTO]:
            totals["crypto"] += sub_acc.current
        elif t in [SubAccountType.ASSET]:
            totals["asset"] += sub_acc.current
        else:
            print("Fallthrough in sub account type: ", t)

    # Apply a class for color-coding in the template.

    totals_display = {}  # Avoids adding keys while iterating.

    for k, v in totals.items():
        totals_display[k + "_class"] = "tran_pos" if v > 0.0 else "tran_neg"
        # A bit of a hack to keep this value consistent with the sub-account values.
        # totals_display[k] = f"{v:,.0f}".replace("-", "")
        totals_display[k] = f"{v:,.0f}"

    count = 60  # todo: Set this elsewhere
    transactions = get_transaction_data(0, count, accounts, person, None, None, None)
    #
    # print("Returning: ",{
    #     "totals": totals_display,
    #     # "sub_accs": json.dumps([s.serialize() for s in sub_accounts]),
    #     "sub_accs": [s.serialize() for s in sub_accounts],
    #     "transactions": transactions,
    # })

    # We're getting different results in template vs JSON responses.
    # Preserialize for the template; don't preserialize for JSON responses.
    accs = [s.serialize() for s in sub_accounts]
    tran = [t.serialize() for t in transactions]

    if not no_preser:
        accs = json.dumps(accs)
        tran = json.dumps(tran)

    return {
        "totals": totals_display,
        "sub_accs": accs,
        "transactions": tran,
    }


def take_snapshots(accounts: Iterable[FinancialAccount], person: Person):
    now = timezone.now()
    net_worth = 0.0

    for account in accounts:
        for sub in account.sub_accounts.all():
            snap = SnapshotAccount(
                account=sub, account_name=sub.name, dt=now, value=sub.current
            )
            snap.save()

            print("Snap saved acct: ", snap)

            net_worth = unw_helper(net_worth, sub)

    snap_person = SnapshotPerson(
        person=person,
        dt=now,
        value=net_worth,
    )

    print("Snap saved person: ", snap_person)

    snap_person.save()


# def setup_spending_highlights(accounts: Iterable[FinancialAccount], person: Person, num_days: int) -> List[Tuple[TransactionCategory, List[int, float, Dict[str, str]]]]:
def setup_spending_highlights(
    accounts: Iterable[FinancialAccount], person: Person, num_days: int
):
    """Find the biggest recent spending highlights."""
    end = timezone.now().date()
    start = end - timedelta(days=num_days)

    # todo: We likely have already loaded these transactions. Optimize later.
    # todo: Maybe cache, this and run it once in a while? Or always load 30 days of trans?
    trans = get_transaction_data(None, None, accounts, person, "", start, end)

    # print(trans, "TRANS")

    result = {}

    total = 0.0

    for tran in trans:
        total += tran.amount

        cats = [TransactionCategory(c) for c in json.loads(tran.categories)]
        cats = transaction_cats.cleanup_categories(cats)

        for cat in cats:
            c = cat  # We serialize anyway, so no need to convert to a TransactionCategory.

            # Remove categories that don't categorize spending well.
            if c in [
                TransactionCategory.PAYMENT,
                TransactionCategory.INCOME,
                TransactionCategory.TRANSFER,
                TransactionCategory.UNCATEGORIZED,
                TransactionCategory.DEPOSIT,
                TransactionCategory.DEBIT,
                TransactionCategory.CREDIT_CARD,
            ]:
                continue

            if c.value not in result.keys():
                result[c.value] = [0, 0.0, []]  # count, total, transactions serialized

            result[c.value][0] += 1
            result[c.value][1] += tran.amount
            result[c.value][2].append(tran.serialize())

    # Sort by value
    result = sorted(result.items(), key=lambda x: x[1][1], reverse=True)

    # print("\nTran cats: ", result)

    #

    # by_cat = trans.sort(key=lambda t: t.)

    return {
        "by_cat": result,
        "total": total,
    }
