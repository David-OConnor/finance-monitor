# Sandbox test credentials: user_good, pass_good, credential_good (pin), mfa_device (pin etc), code: 1234

import time
import json
from datetime import datetime

from django.db import OperationalError
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from main.models import FinancialAccount, Transaction, Institution, Person, SubAccount, AccountType, SubAccountType

import plaid
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser


from main import plaid_
from main.plaid_ import client, PLAID_PRODUCTS

products = []
for product in PLAID_PRODUCTS:
    products.append(Products(product))

PLAID_COUNTRY_CODES = ["US"]
PLAID_REDIRECT_URI = "http://localhost:8080/"  # todo

ACCOUNT_REFRESH_INTERVAL = 30 * 60  # seconds. Todo: Increase this.


def landing(request: HttpRequest) -> HttpResponse:
    context = {}

    return render(request, "../templates/index.html", context)


def dashboard(request: HttpRequest) -> HttpResponse:
    # todo: Set up a login system, then change this.
    person = Person.objects.first()

    accounts = person.accounts.all()

    # todo
    transactions = []

    net_worth = 0.

    # Update account info, if we are due for a refresh
    for acc in accounts:
        now = timezone.now()
        print("TIME", (acc.last_refreshed - now).seconds)
        if (now - acc.last_refreshed).seconds > ACCOUNT_REFRESH_INTERVAL:
            acc.last_refreshed = now
            acc.save()

            print("Refreshing account data...")
            # todo: Function?
            balance_data = plaid_.get_balance(acc.access_token)

            # todo:  Handle  sub-acct entries in DB that have missing data.
            for sub_loaded in balance_data:
                # print("\n\nSub acc: ", sub_loaded, type(sub_loaded))

                sub_acc_model, _ = SubAccount.objects.update_or_create(
                    account=acc,
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
                    }
                )

        else:
            print("Not refreshing account data")

        for sub_acc_model in acc.sub_accounts.all():
            if sub_acc_model.current is not None:
                sign = 1

                if AccountType(sub_acc_model.type) in [AccountType.LOAN, AccountType.CREDIT]:
                    sign *= -1
                    print("Debit")

                net_worth += sign * sub_acc_model.current

    context = {
        "accounts": accounts,
        # "sub_accounts": sub_accounts,
        "transactions": transactions,
        "net_worth": net_worth,
    }

    return render(request, "../templates/dashboard.html", context)


def create_link_token(request_: HttpRequest) -> HttpResponse:
    """The first stage of the Plaid workflow. GET request. Passes the client a link token,
    provided by Plaid's API."""
    user_id = 100

    try:
        request = LinkTokenCreateRequest(
            products=products,
            client_name="Plaid Quickstart",
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            # redirect_uri=PLAID_REDIRECT_URI,
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),
        )

        # create link token
        response = client.link_token_create(request)

    except plaid.ApiException as e:
        print(e, "Plaid error")
        return HttpResponse(json.loads(e.body))

    print(f"Link token response: {response}")

    # note: expiration available.
    link_token = response["link_token"]

    return HttpResponse(
        json.dumps({"link_token": link_token}), content_type="application/json"
    )


def exchange_public_token(request: HttpRequest) -> HttpResponse:
    """Part of the Plaid workflow. POST request. Exchanges the public token retrieved by
    the client, after it successfullya uthenticates with an institution. Exchanges this for
    an access token, which is stored in the database, along with its associated item id."""
    data = json.loads(request.body.decode('utf-8'))

    public_token = data["public_token"]
    metadata = data["metadata"]

    print("\nMetadata received: ", metadata)

    request = ItemPublicTokenExchangeRequest(public_token=public_token)

    response = client.item_public_token_exchange(request)

    print(f"Token exchange response: {response}")

    # These values should be saved to a persistent database and
    # associated with the currently signed-in user
    access_token = response["access_token"]
    item_id = response["item_id"]
    # request_id = response["request_id"]

    person = Person.objects.first()  # todo temp

    sub_accounts = metadata["accounts"]

    inst, _ = Institution.objects.get_or_create(
        plaid_id=metadata["institution"]["institution_id"],
        defaults={"name": metadata["institution"]["name"]},
    )

    account_added = FinancialAccount(
        person=person,
        institution=inst,
        name="",  # todo: Pull from response, and/or metadata
        access_token=access_token,
        item_id=item_id,
        last_refreshed=timezone.now(),
    )

    try:
        account_added.save()
    except OperationalError as e:
        print("\nError saving the account: ", e)
    else:
        print(f"\nSuccessfully saved an account: {account_added}")

    return HttpResponse(
        json.dumps({"success": True}),
        content_type="application/json",
    )

