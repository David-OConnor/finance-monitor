# Misc / utility functions
import json
from collections import defaultdict
from io import TextIOWrapper
from typing import List, Dict, Iterable, Optional, Tuple
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta

from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
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
    CategoryRule,
)
from wallet import settings
from main.transaction_cats import TransactionCategory


CATS_NON_SPENDING = [
    TransactionCategory.PAYMENT,
    TransactionCategory.INCOME,
    TransactionCategory.TRANSFER,
    TransactionCategory.UNCATEGORIZED,
    TransactionCategory.DEPOSIT,
    TransactionCategory.DEBIT,
    TransactionCategory.CREDIT_CARD,
    TransactionCategory.INVESTMENTS,
]


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


def load_transactions(
    start_i: Optional[int],
    end_i: Optional[int],
    person: Person,
    search_text: Optional[str],
    start: Optional[date],
    end: Optional[date],
    category: Optional[TransactionCategory],
) -> List[Transaction]:
    """Create a set of transactions, serialized for use with the frontend. These
    are combined from all sub-accounts."""
    # todo: Pending? Would have to parse into the DB.

    trans = Transaction.objects.filter(Q(account__person=person) | Q(person=person))

    if search_text:
        trans = trans.filter(
            Q(description__icontains=search_text) | Q(notes__icontains=search_text) | Q(institution_name__icontains=search_text)
        )

    if start is not None:
        trans = trans.filter(date__gte=start)
    if end is not None:
        trans = trans.filter(date__lte=end)

    # This filter takes advantage of `categories` being a JSON Field.
    if category is not None:
        print("\n\n CATEGORY", category, "\n\n)")
        trans = trans.filter(category=category.value)

    if start_i is not None and end_i is not None:
        return trans[start_i:end_i]
    return trans


def load_dash_data(person: Person, no_preser: bool = False) -> Dict:
    """Load account balances, transactions, and totals."""

    # todo: Rethink totals.

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
        totals_display[k + "_class"] = "tran-pos" if v > 0.0 else "tran-neg"
        # A bit of a hack to keep this value consistent with the sub-account values.
        # totals_display[k] = f"{v:,.0f}".replace("-", "")
        totals_display[k] = f"{v:,.0f}"

    count = 60  # todo: Set this elsewhere
    transactions = load_transactions(0, count, person, None, None, None, None)
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

    month_picker_items = []
    # todo: This month setup  DRY from setup_spending_data.
    for months_back in range(12, -1, -1):
        now = timezone.now()
        month_start = (now - relativedelta(months=months_back)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + relativedelta(months=1) - timedelta(seconds=1))

        if month_start.year == now.year:
            month_name = month_start.strftime("%b")
        else:
            month_name = month_start.strftime("%b %y")

        month_picker_items.append((
            month_name,
            month_start.date().isoformat(),
            month_end.date().isoformat()
        ))

    return {
        "totals": totals_display,
        "sub_accs": accs,
        "transactions": tran,
        "month_picker_items": month_picker_items
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


def filter_trans_spending(trans) -> List[Transaction]:
    """Filter transactions to only include spending categories."""
    result = []

    for tran in trans:
        # For now, assume all custom categories are considered to be spending.
        if tran.category > 1_000:
            result.append(tran)
            continue

        cat = TransactionCategory(tran.category)

        if cat not in CATS_NON_SPENDING:
            result.append(tran)

    return result


# def setup_spending_highlights(accounts: Iterable[FinancialAccount], person: Person, num_days: int) -> List[Tuple[TransactionCategory, List[int, float, Dict[str, str]]]]:
def setup_spending_highlights(
    person: Person, start_days_back: int, end_days_back: int, is_lookback: bool
):
    """Find the biggest recent spending highlights."""
    now = timezone.now()
    start = now - timedelta(days=start_days_back)
    end = now - timedelta(days=end_days_back)

    # todo: We likely have already loaded these transactions. Optimize later.
    # todo: Maybe cache, this and run it once in a while? Or always load 30 days of trans?
    trans = load_transactions(None, None, person, "", start, end, None)

    by_cat = {}
    large_transactions = []

    total = 0.0

    # # This can be low; large purchases will be rank-limited.
    LARGE_PURCHASE_THRESH = 150.0

    trans_spending = filter_trans_spending(trans)
    # print(trans_spending, "TS")

    for tran in trans_spending:
        # cat = TransactionCategory(tran.category)
        cat = tran.category

        if cat not in by_cat.keys():
            by_cat[cat] = [1, tran.amount]  # count, total, transactions serialized
        else:
            by_cat[cat][0] += 1
            by_cat[cat][1] += tran.amount

        if abs(tran.amount) >= LARGE_PURCHASE_THRESH:
            large_transactions.append(
                {"description": tran.description, "amount": tran.amount}
            )

        total += tran.amount

    # Sort by value
    by_cat = sorted(by_cat.items(), key=lambda x: x[1][1])
    large_transactions = sorted(large_transactions, key=lambda x: x["amount"])

    total_change = None
    # This check prevents an infinite recursion.
    if not is_lookback:
        # todo: We don't need to compute the entire data set for the previous period.; just the relevant parts.
        data_prev_month = setup_spending_highlights(
            person, start_days_back * 2, start_days_back, True
        )
        total_change = total - data_prev_month["total"]

        cat_changes = []
        for c in by_cat:
            prev = [d for d in data_prev_month["by_cat"] if d[0] == c[0]]
            if len(prev):
                prev_amt = prev[0][1][1]
            else:
                prev_amt = 0.0

            diff = c[1][1] - prev_amt

            cat_changes.append([c[0], diff])

        cat_changes.sort(key=lambda c: abs(c[1]), reverse=True)
        # todo: Take into account cats missing this month that  were prsent the prev.
    else:
        cat_changes = []

    return {
        "by_cat": by_cat,
        "total": total,
        "total_change": total_change,
        "cat_changes": cat_changes,
        "large_purchases": large_transactions,
    }


def setup_spending_data(
    person: Person, start_days_back: int, end_days_back: int
) -> dict:
    # todo: DRY/C+P! This is bad because it repeats the same transaction query. Fix it for performance reasons.
    now = timezone.now()
    start = now - timedelta(days=start_days_back)
    end = now - timedelta(days=end_days_back)

    # todo: We likely have already loaded these transactions. Optimize later.
    # todo: Maybe cache, this and run it once in a while? Or always load 30 days of trans?
    trans = load_transactions(None, None, person, "", start, end, None)

    # todo: Other cats?
    income_transactions = [
        t for t in trans if TransactionCategory.INCOME.value == t.category
    ]

    income_total = 0.0
    for t in income_transactions:
        income_total += t.amount

    expense_transactions = filter_trans_spending(trans)
    expenses_total = 0.0
    for t in expense_transactions:
        expenses_total += t.amount

    # TODO. no! Doubles the query.
    spending_highlights = setup_spending_highlights(person, start_days_back, end_days_back, False)

    spending_over_time = []
    income_over_time = []
    # for months_back in range(0, 12):
    for months_back in range(12, 0, -1):
        now = timezone.now()
        start = (now - relativedelta(months=months_back)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (start + relativedelta(months=1) - timedelta(seconds=1))

        # todo: DRY with above.
        trans_in_month = load_transactions(None, None, person, "", start, end, None)

        expenses_in_month = 0.0
        expense_transactions = filter_trans_spending(trans_in_month)
        for t in expense_transactions:
            expenses_in_month += t.amount
        spending_over_time.append((start.date().strftime("%b %y"), expenses_in_month))

        income_in_month = 0.0
        income_transactions = [
            t for t in trans_in_month if TransactionCategory.INCOME.value == t.category
        ]
        for t in income_transactions:
            income_in_month += t.amount
        income_over_time.append((start.date().strftime("%b %y"), income_in_month))

    return {
        "highlights": spending_highlights,
        "income_total": income_total,
        "expenses_total": expenses_total,
        "spending_over_time": spending_over_time,
        "income_over_time": income_over_time,
    }


def check_account_status(request: HttpRequest) -> Optional[HttpResponse]:
    """Checks that the account is verified, and that it isn't locked, before viewing account-related pages."""
    person = request.user.person

    if not person.email_verified:
        return render(request, "not_verified.html", {})

    if person.account_locked:
        # todo
        return HttpResponse(
            "This account is locked due to suspicious activity. Please contact us: contact@finance-monitor.com"
        )


def change_tran_cats_from_rule(rule: CategoryRule, person: Person):
    """This is a bit of a forward decision, but retroactively re-categorize transactions matching
    a given description, based on a new or updated rule."""
    for tran in Transaction.objects.filter(
        Q(person=person) | Q(account__person=person),
        description__iexact=rule.description,
    ):
        tran.category = rule.category
        tran.save()


def send_debug_email(message: str):
    if not settings.DEPLOYED:
        return

    send_mail(
        "Finance Monitor error",
        "",
        "contact@finance-monitor.com",
        ["contact@finance-monitor.com"],
        fail_silently=False,
        html_message=message,
    )
