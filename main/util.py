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
from main.transaction_cats import TransactionCategory, TransactionCategoryDiscret

# Show an account as unhealthy if the last successful refresh was older than this.
ACCOUNT_UNHEALTHY_REFRESH_HOURS = 18


def unw_helper(net_worth: float, sub_acc: SubAccount) -> float:
    if not sub_acc.ignored and sub_acc.get_value() is not None:
        sign = 1

        if AccountType(sub_acc.type) in [
            AccountType.LOAN,
            AccountType.CREDIT,
        ]:
            sign *= -1

        net_worth += sign * sub_acc.get_value()
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
        search_text = search_text.lower()

        cat_vals = [c[0] for c in transaction_cats.CAT_NAMES if search_text in c[1]]
        print(cat_vals, "CAT_VALS", "SEARCH TEXT: ", search_text)
        trans = trans.filter(
            Q(description__icontains=search_text)
            | Q(notes__icontains=search_text)
            | Q(institution_name__icontains=search_text)
            | Q(category__in=cat_vals)
            | Q(merchant__icontains=search_text)
        )

    if start is not None:
        trans = trans.filter(date__gte=start)
    if end is not None:
        trans = trans.filter(date__lte=end)

    # Note: this hard-set category filter is independent from filtering transaction category by search text.
    if category is not None:
        trans = trans.filter(category=category.value)

    # Make sure this index filter is last; it's related to selectingly loading only what's needed at a time
    # on the frontend.
    if start_i is not None and end_i is not None:
        return trans[start_i:end_i]
    return trans


def setup_month_picker() -> List[Tuple[str, str, str]]:
    """Creates items, for use in a template, to create buttons that select date ranges for each month going backwards."""
    result = []

    # todo: This month setup  DRY from setup_spending_data.
    for months_back in range(12, -1, -1):
        now = timezone.now()
        month_start = (now - relativedelta(months=months_back)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        month_end = month_start + relativedelta(months=1) - timedelta(seconds=1)

        if month_start.year == now.year:
            month_name = month_start.strftime("%b")
        else:
            month_name = month_start.strftime("%b %y")

        result.append(
            (month_name, month_start.date().isoformat(), month_end.date().isoformat())
        )

    return result


def load_dash_data(person: Person, no_preser: bool = False) -> Dict:
    """Load account balances, transactions, and totals."""

    # todo: Rethink totals.

    sub_accounts = SubAccount.objects.filter(
        Q(account__person=person) | Q(person=person)
    )

    totals = {
        "cash": 0.0,
        "investment": 0.0,
        "crypto": 0.0,
        "credit_debit": 0.0,
        "loans": 0.0,
        "assets": 0.0,
        "net_worth": 0.0,
    }

    no_accs = sub_accounts.count() == 0

    for sub_acc in sub_accounts:
        if sub_acc.ignored:
            continue

        totals["net_worth"] = unw_helper(totals["net_worth"], sub_acc)

        t = SubAccountType(sub_acc.sub_type)

        # todo: Integer math and DB storage; not floating point.

        # todo: Consistency with use of minus signs on debgs. Currently reverse behavior on cat
        # total and per-accoutn for loads, CC+Debit

        if t in [SubAccountType.CHECKING, SubAccountType.SAVINGS]:
            totals["cash"] += sub_acc.get_value()
        elif t in [SubAccountType.DEBIT_CARD, SubAccountType.CREDIT_CARD]:
            totals["credit_debit"] -= sub_acc.get_value()
        elif t in [
            SubAccountType.T401K,
            SubAccountType.CD,
            SubAccountType.MONEY_MARKET,
            SubAccountType.IRA,
            SubAccountType.MUTUAL_FUND,
            SubAccountType.BROKERAGE,
            SubAccountType.ROTH,
        ]:
            totals["investment"] += sub_acc.get_value()
        elif t in [SubAccountType.STUDENT, SubAccountType.MORTGAGE]:
            totals["loans"] -= sub_acc.get_value()
        elif t in [SubAccountType.CRYPTO]:
            totals["crypto"] += sub_acc.get_value()
        elif t in [SubAccountType.ASSET]:
            totals["asset"] += sub_acc.get_value()
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

    # We're getting different results in template vs JSON responses.
    # Preserialize for the template; don't preserialize for JSON responses.
    accs = [s.serialize() for s in sub_accounts]
    tran = [t.serialize() for t in transactions]

    if not no_preser:
        accs = json.dumps(accs)
        tran = json.dumps(tran)

    # return health status, by (institution-level) account.
    acc_health = []
    now = timezone.now()
    for acc in person.accounts.all():
        if (
            now - acc.last_balance_refresh_success
        ).total_seconds() > ACCOUNT_UNHEALTHY_REFRESH_HOURS * 3600:
            for sub_acc in acc.sub_accounts.all():
                acc_health.append([sub_acc.id, False])
        else:
            for sub_acc in acc.sub_accounts.all():
                acc_health.append([sub_acc.id, True])

    if not no_preser:
        acc_health = json.dumps(acc_health)

    return {
        "totals": totals_display,
        "sub_accs": accs,
        "transactions": tran,
        "month_picker_items": setup_month_picker(),
        "acc_health": acc_health,
        "no_accs": no_accs,
    }


def take_snapshots(accounts: Iterable[FinancialAccount], person: Person):
    now = timezone.now()
    net_worth = 0.0

    for account in accounts:
        for sub in account.sub_accounts.all():
            snap = SnapshotAccount(
                account=sub, account_name=sub.name, dt=now, value=sub.get_value()
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
        if tran.ignored:
            continue

        # For now, assume all custom categories are considered to be spending.
        if tran.category > 1_000:
            result.append(tran)
            continue

        cat = TransactionCategory(tran.category)

        if cat not in transaction_cats.CATS_NON_SPENDING:
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
        t
        for t in trans
        if TransactionCategory.INCOME.value == t.category and not t.ignored
    ]

    income_total = 0.0
    for t in income_transactions:
        income_total += t.amount

    expense_transactions = filter_trans_spending(trans)

    expenses_total = 0.0
    expenses_discretionary = 0.0
    expenses_nondiscret = 0.0

    for t in expense_transactions:
        expenses_total += t.amount

        discret = TransactionCategoryDiscret.from_cat(TransactionCategory(t.category))
        if discret == TransactionCategoryDiscret.DISCRETIONARY:
            expenses_discretionary += t.amount
        elif discret == TransactionCategoryDiscret.NON_DISCRETIONARY:
            expenses_nondiscret += t.amount
        # The third option here is a non-spending expense (transfer, fee etc)

    # TODO. no! Doubles the query.
    spending_highlights = setup_spending_highlights(
        person, start_days_back, end_days_back, False
    )

    spending_over_time = []
    income_over_time = []
    # for months_back in range(0, 12):
    for months_back in range(12, 0, -1):
        start_ = (now - relativedelta(months=months_back)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end_ = start_ + relativedelta(months=1) - timedelta(seconds=1)

        # todo: DRY with above.
        trans_in_month = load_transactions(None, None, person, "", start_, end_, None)

        expenses_in_month = 0.0
        expense_transactions = filter_trans_spending(trans_in_month)
        for t in expense_transactions:
            expenses_in_month += t.amount
        spending_over_time.append((start_.date().strftime("%b %y"), expenses_in_month))

        income_in_month = 0.0
        income_transactions = [
            t for t in trans_in_month if TransactionCategory.INCOME.value == t.category
        ]
        for t in income_transactions:
            income_in_month += t.amount
        income_over_time.append((start_.date().strftime("%b %y"), income_in_month))

    # todo: QC this merchant check
    start_new_merchant_check = start - timedelta(days=360)
    merchants_new = find_new_merchants(
        person, (start, end), (start_new_merchant_check, start)
    )

    return {
        "highlights": spending_highlights,
        "income_total": income_total,
        "expenses_total": expenses_total,
        "expenses_discretionary": expenses_discretionary,
        "expenses_nondiscret": expenses_nondiscret,
        "spending_over_time": spending_over_time,
        "income_over_time": income_over_time,
        "merchants_new": merchants_new,
    }


def check_account_status(request: HttpRequest) -> Optional[HttpResponse]:
    """Checks that the account is verified, and that it isn't locked, before viewing account-related pages."""
    person = request.user.person

    if not person.email_verified:
        return render(request, "not_verified.html", {"email": person.user.email})

    if person.account_locked:
        # todo
        return HttpResponse(
            "This account is locked due to suspicious activity. Please contact us: contact@finance-monitor.com"
        )


def change_tran_cats_from_rule(rule: CategoryRule, person: Person):
    """This is a bit of a forward decision, but retroactively re-categorize transactions matching
    a given description, based on a new or updated rule."""

    # todo: Make this mor egeneral, like when you recategorize new transactions based on rules. stripping whitespace,
    # todo, chars like ', & etc.
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
        "Finance Monitor debug",
        "",
        "contact@finance-monitor.com",
        ["contact@finance-monitor.com"],
        fail_silently=False,
        html_message=message,
    )


def find_new_merchants(
    person: Person,
    range_new: (datetime, datetime),
    range_baseline: (datetime, datetime),
) -> List[Tuple[str, str]]:
    """Find merchants that appear in a given time period that were not present in another period."""

    # todo: You could have a more optimized query by doing this more carefully; later.
    tran_new = load_transactions(
        None, None, person, None, range_new[0], range_new[1], None
    )
    tran_baseline = load_transactions(
        None, None, person, None, range_baseline[0], range_baseline[1], None
    )

    merchants_base = list(set([t.merchant.lower() for t in tran_baseline]))
    return list(
        set(
            [
                (t.merchant.lower(), t.logo_url)
                for t in tran_new
                if t.merchant.lower() not in merchants_base
            ]
        )
    )


def spending_this_month(cat: TransactionCategory, person: Person) -> float:
    """For use in Budget: Find the spending amount in the current calendar month, in this transaction category"""
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = month_start + relativedelta(months=1) - timedelta(seconds=1)

    trans = load_transactions(None, None, person, None, month_start, month_end, cat)

    total = 0.0
    for t in trans:
        total += t.amount

    return total
