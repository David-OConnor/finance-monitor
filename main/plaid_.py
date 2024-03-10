"""
This module contains interacdtions with Plaid's API

Sandbox test credentials: user_good, pass_good, credential_good (pin), mfa_device (pin etc), code: 1234
"""

import json
from typing import Optional, Iterable, List, Tuple

from django.utils import timezone

from plaid import ApiException
from plaid.model.account_base import AccountBase
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest

from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_request import InstitutionsGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest

from plaid.model.products import Products
from plaid.model.transactions_recurring_get_request import TransactionsRecurringGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from django.db import IntegrityError

from . import transaction_cats, util
from .models import (
    FinancialAccount,
    SubAccount,
    AccountType,
    SubAccountType,
    Transaction, Person, RecurringTransaction, RecurringDirection,
)
from .transaction_cats import TransactionCategory
from wallet.settings import PLAID_SECRET, PLAID_CLIENT_ID, PLAID_MODE, PlaidMode

import plaid
from plaid.api import plaid_api

HOUR = 60 * 60

# todo: Settings.py?
# todo: Increase to 12 or so hours.
ACCOUNT_REFRESH_INTERVAL = 4 * HOUR  # seconds.

# We can use a slow update for recurring transactions.
ACCOUNT_REFRESH_INTERVAL_RECURRING = 48 * HOUR  # seconds.

# ACCOUNT_REFRESH_INTERVAL = 1 * 60 * 60  # seconds.  # todo temp
# ACCOUNT_REFRESH_INTERVAL = 1   # seconds.  # todo temp

#  must be one of [
#  "assets",  "auth", "balance", "identity", "identity_match", "investments", "investments_auth", "liabilities", "payment_initiation",
#  "identity_verification", "transactions", "credit_details", "income", "income_verification", "deposit_switch",
#  "standing_orders", "transfer", "employment", "recurring_transactions", "signal", "statements", "processor_payments", "processor_identity",

# Todo: SO confused about this, eg https://dashboard.plaid.com/overview/request-products
# Note: Activating with too many products enabled may cause problems: https://www.youtube.com/watch?v=yPQPPGdBYIs

# "auth",
# "assets",
# "transactions",
# "investments",
# "liabilities",
# "recurring_transactions",  # Not enabled in the Plaid dashboard.

# From experimenting: products= investments only allows access to Vanguard
# products = assets only allows access to novo, Amex

# todo: I still don't understand this.
# Note: We don't use assets! That's used to qualify for a loan. Maybe see if Transactions only works?
# PRODUCTS = [Products(p)for p in ["assets", "transactions"]]
PRODUCTS = [Products(p)for p in ["transactions", "recurring_transactions"]]
# PRODUCTS = [Products(p)for p in ["assets"]]
PRODUCTS_REQUIRED_IF_SUPPORTED = [Products(p)for p in []]
PRODUCTS_OPTIONAL = [Products(p)for p in []]
PRODUCTS_ADDITIONAL_CONSENTED = [Products(p)for p in []]

PLAID_COUNTRY_CODES = ["US"]
PLAID_REDIRECT_URI = "https://financial-monitor-783ae5ca6965.herokuapp.com/dashboard"
# PLAID_REDIRECT_URI = "https://www.financial-monitor.com/dashboard"

# Available environments arefr
# 'Production'
# 'Development'
# 'Sandbox'
if PLAID_MODE == PlaidMode.SANDBOX:
    host = plaid.Environment.Sandbox
elif PLAID_MODE == PlaidMode.DEV:
    host = plaid.Environment.Development
elif PLAID_MODE == PlaidMode.PRODUCTION:
    host = plaid.Environment.Production
else:
    print("Fallthorugh on plaid mode")
    host = plaid.Environment.Sandbox

configuration = plaid.Configuration(
    host=host,
    api_key={
        "clientId": PLAID_CLIENT_ID,
        "secret": PLAID_SECRET,
        # 'plaidVersion': '2020-09-14'
    },
)

API_CLIENT = plaid.ApiClient(configuration)
CLIENT = plaid_api.PlaidApi(API_CLIENT)


def get_balance_data(access_token: str) -> Optional[AccountBase]:
    """Pull real-time balance information for each account associated
    with the access token. This returns sub-accounts, currently as a dict."""
    request = AccountsBalanceGetRequest(access_token=access_token)

    try:
        response = CLIENT.accounts_balance_get(request)
    except ApiException as e:
        print("API exception; unable to access this account: ", e)
        return None

    return response["accounts"]


def update_accounts(accounts: Iterable[FinancialAccount], person: Person) -> bool:
    """Update all account balances and related information. Return sub accounts, and net worth.
    Returns `True if there is new data. """
    # Update account info, if we are due for a refresh
    new_data = False
    for acc in accounts:
        # todo: We may have a timezone or related error on acct refreshes...
        print(acc, acc.last_refreshed, "ACC")
        print("Time delta seconds, interval", (timezone.now() - acc.last_refreshed).seconds, ACCOUNT_REFRESH_INTERVAL)
        if (timezone.now() - acc.last_refreshed).seconds > ACCOUNT_REFRESH_INTERVAL:
            print("Refreshing account data...")

            refresh_account_balances(acc)
            refresh_transactions(acc)
            acc.last_refreshed = timezone.now()

            new_data = True

        if (timezone.now() - acc.last_refreshed_recurring).seconds > ACCOUNT_REFRESH_INTERVAL_RECURRING:
            refresh_recurring(acc)
            acc.last_refreshed_recurring = timezone.now()

        else:
            print("Not refreshing account data")

    return new_data


def refresh_account_balances(account: FinancialAccount):
    """Update account information in the database."""
    balance_data = get_balance_data(account.access_token)
    if balance_data is None:
        return

    print("\nBalance data loaded: ", balance_data)

    # todo: Icon?

    # todo:  Handle  sub-acct entries in DB that have missing data.
    for sub in balance_data:
        sub_acc_model, _ = SubAccount.objects.update_or_create(
            account=account,
            plaid_id=sub.account_id,
            defaults={
                # "plaid_id_persistent": acc_sub.persistent_account_id,
                "plaid_id_persistent": "",  # todo temp
                "name": sub.name,
                "name_official": sub.official_name,
                "type": AccountType.from_str(str(sub.type)).value,
                "sub_type": SubAccountType.from_str(str(sub.subtype)).value,
                "iso_currency_code": sub.balances.iso_currency_code,
                "available": sub.balances.available,
                "current": sub.balances.current,
                "limit": sub.balances.limit,
            },
        )

    account.last_refreshed = timezone.now()
    account.save()


def refresh_transactions(account: FinancialAccount) -> None:
    """
    Updates the database with transactions for a single account.
    https://plaid.com/docs/api/products/transactions/#transactionssync
    """
    # Provide a cursor from your database if you've previously
    # received one for the Item. Leave null if this is your first sync call for this Item. The first request will
    # return a cursor. (It seems None doesn't work with this API, but an empty string does.)
    cursor = account.plaid_cursor

    # New transaction updates since "cursor"
    added = []
    modified = []
    removed = []  # Removed transaction ids
    has_more = True

    # Iterate through each page of new transaction updates for item
    while has_more:
        request = TransactionsSyncRequest(
            access_token=account.access_token,
            cursor=cursor,
        )
        response = CLIENT.transactions_sync(request)

        print("Transaction resp: ", response)

        # Add this page of results
        added.extend(response["added"])
        modified.extend(response["modified"])
        removed.extend(response["removed"])

        has_more = response["has_more"]

        # Update cursor to the next cursor
        cursor = response["next_cursor"]

        print("Cursor: ", cursor)

    # Persist cursor and updated data
    # database.apply_updates(item_id, added, modified, removed, cursor)

    print("Added: ", added)
    print("Mod: ", modified)
    print("Rem: ", removed)

    for tran in added:
        categories = [TransactionCategory.from_str(cat) for cat in tran.category]
        categories = transaction_cats.category_override(tran.name, categories)

        tran_db = Transaction(
            account=account,
            categories=json.dumps([cat.value for cat in categories]),
            amount=tran.amount,
            # Note: Other fields like "merchange_name" are available, but aren't used on many transactcions.
            description=tran.name,
            date=tran.date,
            datetime=tran.datetime,
            plaid_id=tran.transaction_id,
            currency_code=tran.iso_currency_code,
            pending=tran.pending,
            logo_url=tran.logo_url,
            plaid_category_icon_url="",  # todo: A/R
        )
        try:
            tran_db.save()
        except IntegrityError:
            # todo: Why do we get this, if using cursor?
            print("Integrity error when saving a transaction: ", account)

    for tran in modified:
        # tran_db_, _ = Transaction.objects.update(
        #
        # )
        pass

    for tran in removed:
        # _ = Transaction.objects.filter().delete
        pass

    account.plaid_cursor = cursor
    account.save()


def refresh_recurring(account: FinancialAccount) -> List[RecurringTransaction]:
    # Run this on all sub-accounts that have recent transactions.\
    # The docs have some interesting notes; I'm not yet sure how to impl them.
    # https://plaid.com/docs/api/products/transactions/#transactionsrecurringget

    # todo: Use your own logic instead of paying Plaid for this API.

    sub_accs = account.sub_accounts.all()  # todo: Filter A/R based on which have transactions
    account_ids = [s.plaid_id for s in sub_accs]

    request = TransactionsRecurringGetRequest(
        access_token=account.access_token,
        account_ids=account_ids
    )

    response = CLIENT.transactions_recurring_get(request)

    inflow_streams = response.inflow_streams
    outflow_streams = response.outflow_streams

    # Example response:
    # Recur resp:  {'inflow_streams': [{'account_id': 'GMBMxzPRkLfkKxL5RDD4cGlaGjZMaqI6oKX8n',
    #                      'average_amount': {'amount': -4.22},
    #                      'category': ['Transfer', 'Payroll'],
    #                      'category_id': '21009000',
    #                      'description': 'INTRST PYMNT',
    #                      'first_date': datetime.date(2023, 12, 21),
    #                      'frequency': 'MONTHLY',
    #                      'is_active': True,
    #                      'is_user_modified': False,
    #                      'last_amount': {'amount': -4.22},
    #                      'last_date': datetime.date(2024, 2, 19),
    #                      'last_user_modified_datetime': datetime.datetime(1, 1, 1, 0, 0, tzinfo=tzutc()),
    #                      'merchant_name': '',
    #                      'personal_finance_category': {'confidence_level': 'UNKNOWN',
    #                                                    'detailed': 'INCOME_WAGES',
    #                                                    'primary': 'INCOME'},
    #                      'status': 'MATURE',
    #                      'stream_id': 'Z4D4yMVpjlHJkNdKxjjXUNVoQEXgWAFgZXBJN',
    #                      'transaction_ids': ['mKZKXDVa91T5EDRqKPPJil7ZWE8ZZ5cgw77mV',
    #                                          'nr1rQDVbJLUBG6lKrnnaIXAqpb9qqBfAp88ep',
    #                                          'LkykNaZQbECRbqk5prrzIeB5npQ4aVikEEae5']}],
    #  'outflow_streams': [{'account_id': 'bMQMzXVwjdfMG3K47wwNFoBZoAgeZVum7n1zE',
    #                       'average_amount': {'amount': 2078.5},
    #                       'category': ['Payment'],
    #                       'category_id': '16000000',
    #                       'description': 'AUTOMATIC PAYMENT - THANK',
    #                       'first_date': datetime.date(2024, 1, 4),
    #                       'frequency': 'MONTHLY',
    #                       'is_active': True,
    #                       'is_user_modified': False,
    #                       'last_amount': {'amount': 2078.5},
    #                       'last_date': datetime.date(2024, 3, 4),
    #                       'last_user_modified_datetime': datetime.datetime(1, 1, 1, 0, 0, tzinfo=tzutc()),
    #                       'merchant_name': '',
    #                       'personal_finance_category': {'confidence_level': 'UNKNOWN',
    #                                                     'detailed': 'TRANSFER_OUT_ACCOUNT_TRANSFER',
    #                                                     'primary': 'TRANSFER_OUT'},
    #                       'status': 'MATURE',
    #                       'stream_id': 'bMQMzXVwjdfMG3K47wwrUq1LyvDzWViVAZeo4',
    #                       'transaction_ids': ['3RwRXbgLvlhZNrkR6vvACke1EBo11duZKwwJ1',
    #                                           'lk5kQDVJ1MC5GmPlkooaiNA31DB33rFpGLLWB',
    #                                           'EQEQBK4nrMuZknD5wWW1ClnND9Rba6c4mmlgX']},
    #                      {'account_id': 'bMQMzXVwjdfMG3K47wwNFoBZoAgeZVum7n1zE',
    #                       'average_amount': {'amount': 500.0},
    #                       'category': ['Travel', 'Airlines and Aviation Services'],
    #                       'category_id': '22001000',
    #                       'description': 'United Airlines',
    #                       'first_date': datetime.date(2023, 12, 11),
    #                       'frequency': 'MONTHLY',
    #                       'is_active': True,
    #                       'is_user_modified': False,
    #                       'last_amount': {'amount': 500.0},
    #                       'last_date': datetime.date(2024, 2, 9),
    #                       'last_user_modified_datetime': datetime.datetime(1, 1, 1, 0, 0, tzinfo=tzutc()),
    #                       'merchant_name': 'United Airlines',
    #                       'personal_finance_category': {'confidence_level': 'UNKNOWN',
    #                                                     'detailed': 'TRAVEL_FLIGHTS',
    #                                                     'primary': 'TRAVEL'},
    #                       'status': 'MATURE',
    #                       'stream_id': 'WxgxyMGp46TekEo5KjjbTpW46QD1XdCle1VPZ',
    #                       'transaction_ids': ['dLaL3XVNJ4HpkwzW733ZtBZQPx6QQaiJ5PPNk',
    #                                           'Ko9oNdQyV8UnpLD5AJJgcE7ZxeGZZWsRW668p',
    #                                           'APbPkV3497TgKnNZQookfXJm35nRQqt955P44']},

    for recur in inflow_streams:
        categories = [TransactionCategory.from_str(cat) for cat in recur.category]
        categories = transaction_cats.category_override(recur.description, categories)

        sub_acc = SubAccount.objects.get(plaid_id=recur.account_id)

        recur_db = RecurringTransaction(
            account=sub_acc,
            direction=RecurringDirection.INFLOW,
            average_amount=recur.average_amount.amount,
            last_amount=recur.last_amount.amount,
            first_date=recur.first_date,
            last_date=recur.last_date,
            description=recur.description,
            merchant_name=recur.merchant_name,
            is_active=recur.is_active,
            status=recur.status,
            categories=json.dumps([cat.value for cat in categories]),
        )
        try:
            recur_db.save()
        except IntegrityError as e:
            print("Integrity error saving recuring transaction", e)

    # todo: DRY!
    for recur in outflow_streams:
        categories = [TransactionCategory.from_str(cat) for cat in recur.category]
        categories = transaction_cats.category_override(recur.description, categories)

        sub_acc = SubAccount.objects.get(plaid_id=recur.account_id)

        recur_db = RecurringTransaction(
            account=sub_acc,
            direction=RecurringDirection.OUTFLOW,
            average_amount=recur.average_amount.amount,
            last_amount=recur.last_amount.amount,
            first_date=recur.first_date,
            last_date=recur.last_date,
            description=recur.description,
            merchant_name=recur.merchant_name,
            is_active=recur.is_active,
            status=recur.status,
            categories=json.dumps([cat.value for cat in categories]),
        )
        try:
            recur_db.save()
        except IntegrityError as e:
            print("Integrity error saving recuring transaction", e)

    # print("\nRecur resp: ", response)