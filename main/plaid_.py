"""
This module contains interacdtions with Plaid's API
"""

import json
from enum import Enum, auto
from typing import Optional

import requests
import pydantic

from django.utils import timezone

import plaid
from plaid import ApiException
from plaid.model.account_base import AccountBase
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_request import InstitutionsGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from . import transaction_cats
from .models import (
    FinancialAccount,
    SubAccount,
    AccountType,
    SubAccountType,
    Transaction,
)
from .transaction_cats import TransactionCategory
from wallet.settings import PLAID_SECRET, PLAID_CLIENT_ID, PLAID_MODE, PlaidMode

import plaid
from plaid.api import plaid_api

#  must be one of [
#  "assets",  "auth", "balance", "identity", "identity_match", "investments", "investments_auth", "liabilities", "payment_initiation",
#  "identity_verification", "transactions", "credit_details", "income", "income_verification", "deposit_switch",
#  "standing_orders", "transfer", "employment", "recurring_transactions", "signal", "statements", "processor_payments", "processor_identity",

# Todo: SO confused about this, eg https://dashboard.plaid.com/overview/request-products
PLAID_PRODUCTS = [
    Products(p)
    for p in [
        "auth",
        "assets",
        # "balance",
        "transactions",
        "investments",
        "liabilities",
        # "recurring_transactions",
    ]
]


PLAID_COUNTRY_CODES = ["US"]
PLAID_REDIRECT_URI = "http://finance-monitor.com/"  # todo

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

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)


def get_balance_data(access_token: str) -> Optional[AccountBase]:
    """Pull real-time balance information for each account associated
    with the access token. This returns sub-accounts, currently as a dict."""
    request = AccountsBalanceGetRequest(access_token=access_token)

    try:
        response = client.accounts_balance_get(request)
    except ApiException as e:
        print("API exception; unable to access this account: ", e)
        return None

    return response["accounts"]


def refresh_account_balances(account: FinancialAccount):
    """Update account information in the database."""
    balance_data = get_balance_data(account.access_token)
    if balance_data is None:
        return

    print("Balance data loaded: ", balance_data)

    # todo:  Handle  sub-acct entries in DB that have missing data.
    for sub_loaded in balance_data:
        sub_acc_model, _ = SubAccount.objects.update_or_create(
            account=account,
            plaid_id=sub_loaded.account_id,
            defaults={
                # "plaid_id_persistent": acc_sub.persistent_account_id,
                "plaid_id_persistent": "",  # todo temp
                "name": sub_loaded.name,
                "name_official": sub_loaded.official_name,
                "type": AccountType.from_str(str(sub_loaded.type)).value,
                "sub_type": SubAccountType.from_str(str(sub_loaded.subtype)).value,
                "iso_currency_code": sub_loaded.balances.iso_currency_code,
                "available": sub_loaded.balances.available,
                "current": sub_loaded.balances.current,
                "limit": sub_loaded.balances.limit,
            },
        )

    account.last_refreshed = timezone.now()
    account.save()


def load_transactions(account: FinancialAccount) -> None:
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
        response = client.transactions_sync(request)

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
        categories = [TransactionCategory.from_str(cat).value for cat in tran.category]

        categories = transaction_cats.category_override(tran.name, categories)

        tran_db = Transaction(
            account=account,
            categories=json.dumps(categories),
            amount=tran.amount,
            # Note: Other fields like "merchange_name" are available, but aren't used on many transactcions.
            description=tran.name,
            date=tran.date,
            datetime=tran.datetime,
            plaid_id=tran.transaction_id,
            currency_code=tran.iso_currency_code,
            pending=tran.pending,
        )
        tran_db.save()

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


def load_transactions2(access_token: str):
    """Note:  /transactions/sync replaces /transactions/get."""
    request = TransactionsSyncRequest(
        access_token=access_token,
    )
    response = client.transactions_sync(request)
    transactions = response["added"]

    # the transactions in the response are paginated, so make multiple calls while incrementing the cursor to
    # retrieve all transactions
    while response["has_more"]:
        request = TransactionsSyncRequest(
            access_token=access_token, cursor=response["next_cursor"]
        )
        response = client.transactions_sync(request)

        json_string = json.dumps(response.to_dict(), default=str)

        transactions += response["added"]


# todo: Do we need this? Handled in get_balance_data
def _get_institutions(access_token: str) -> dict:
    count = 3
    offset = 0

    request = InstitutionsGetRequest(
        country_codes=[CountryCode("US")], count=count, offset=offset
    )
    response = client.institutions_get(request)

    print("Inst resp", response)

    institutions = response["institutions"]

    print(institutions, "INSTS")

    return institutions


def _get_investment_holdings(access_token: str) -> (dict, dict):
    # Pull Holdings for an Item
    request = InvestmentsHoldingsGetRequest(access_token=access_token)
    response = client.investments_holdings_get(request)

    # Handle Holdings response
    holdings = response["holdings"]

    # Handle Securities response
    securities = response["securities"]

    print("holdings", holdings)
    print(f"security: {securities}")

    return holdings, securities
