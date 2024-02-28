"""
This module contains interacdtions with Plaid's API
"""

import json

import requests
import pydantic

import plaid
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_request import InstitutionsGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from .keys import PLAID_SECRET, PLAID_CLIENT_ID

import plaid
from plaid.api import plaid_api

BASE_URL = "https://www.plaid.com/api"

PLAID_PRODUCTS = [
    "assets",
    # "balance",
    "transactions",
    "investments",
    # "recurring_transactions",
]

# Available environments arefr
# 'Production'
# 'Development'
# 'Sandbox'
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        "clientId": PLAID_CLIENT_ID,
        "secret": PLAID_SECRET,
        # 'plaidVersion': '2020-09-14'
    },
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)


def link(access_token: str) -> str:
    # the public token is received from Plaid Link
    exchange_request = ItemPublicTokenExchangeRequest(
        public_token=pt_response["public_token"]
    )
    exchange_response = client.item_public_token_exchange(exchange_request)

    print("Exchange resp: {:?}", exchange_response)
    return exchange_response["access_token"]


def get_institutions(access_token: str) -> dict:
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


def get_balance(access_token: str) -> dict:
    # Pull real-time balance information for each account associated
    # with the Item
    request = AccountsBalanceGetRequest(access_token=access_token)
    response = client.accounts_balance_get(request)

    print(response, "RESP")

    accounts = response["accounts"]



    return accounts


def get_investment_holdings(access_token: str) -> (dict, dict):
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


def load_transactions(access_token: str):
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


def load_accounts(access_token: str):
    url = BASE_URL + "accounts/get"

    access_token = "asdf"

    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    accounts = response["accounts"]

    print("ACCOUNTS", accounts)

    resp = requests.get(
        url,
        params={
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            "access_token": access_token,
            # "options": {},
            # "account_ids": [],
        },
    )
