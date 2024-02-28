# Sandbox test credentials: user_good, pass_good, credential_good (pin), mfa_device (pin etc), code: 1234

import time
import json

from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from main.models import FinancialAccount, Transaction, Institution, Person

import plaid
from plaid.model.payment_amount import PaymentAmount
from plaid.model.payment_amount_currency import PaymentAmountCurrency
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.recipient_bacs_nullable import RecipientBACSNullable
from plaid.model.payment_initiation_address import PaymentInitiationAddress
from plaid.model.payment_initiation_recipient_create_request import PaymentInitiationRecipientCreateRequest
from plaid.model.payment_initiation_payment_create_request import PaymentInitiationPaymentCreateRequest
from plaid.model.payment_initiation_payment_get_request import PaymentInitiationPaymentGetRequest
from plaid.model.link_token_create_request_payment_initiation import LinkTokenCreateRequestPaymentInitiation
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.asset_report_create_request import AssetReportCreateRequest
from plaid.model.asset_report_create_request_options import AssetReportCreateRequestOptions
from plaid.model.asset_report_user import AssetReportUser
from plaid.model.asset_report_get_request import AssetReportGetRequest
from plaid.model.asset_report_pdf_get_request import AssetReportPDFGetRequest
from plaid.model.auth_get_request import AuthGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.identity_get_request import IdentityGetRequest
from plaid.model.investments_transactions_get_request_options import InvestmentsTransactionsGetRequestOptions
from plaid.model.investments_transactions_get_request import InvestmentsTransactionsGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.transfer_authorization_create_request import TransferAuthorizationCreateRequest
from plaid.model.transfer_create_request import TransferCreateRequest
from plaid.model.transfer_get_request import TransferGetRequest
from plaid.model.transfer_network import TransferNetwork
from plaid.model.transfer_type import TransferType
from plaid.model.transfer_authorization_user_in_request import TransferAuthorizationUserInRequest
from plaid.model.ach_class import ACHClass
from plaid.model.transfer_create_idempotency_key import TransferCreateIdempotencyKey
from plaid.model.transfer_user_address_in_request import TransferUserAddressInRequest
from plaid.api import plaid_api

PLAID_REDIRECT_URI = 'http://localhost:3000/'

from main import plaid_
from main.plaid_ import client, PLAID_PRODUCTS

products = []
for product in PLAID_PRODUCTS:
    products.append(Products(product))

PLAID_COUNTRY_CODES = ["US"]

# todo temp
LINK_TOKEN = "link-sandbox-19fd5aee-b3ff-46cd-9e14-0f45e7a5ffaa"

# @login_required


# Create your views here.
def home(request: HttpRequest) -> HttpResponse:
    # return HttpResponse(
    #     "Successfully synchronized user accounts with people in your squadron."
    # )

    # institutions = plaid_.get_institutions("asdf")

    # plaid_.get_balance(LINK_TOKEN)

    # plaid_.get_investment_holdings(LINK_TOKEN)

    inst_test = Institution(
        name="My bank"
    )

    person_test = Person(

    )

    account_test = FinancialAccount(
        name="My account 1",
        institution=inst_test,
        person=person_test,
    )

    context = {
        "accounts": [
            account_test
        ],
        "transactions": [
            Transaction(
                account=account_test,
                amount=-70.50,
                description="Groceries",
            )
        ]
    }

    return render(request, "../templates/index.html", context)


def create_link_token(request: HttpRequest) -> HttpResponse:
    """The first stage of the Plaid workflow."""
    user_id = 100

    try:
        request = LinkTokenCreateRequest(
            products=products,
            client_name="Plaid Quickstart",
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            # redirect_uri=PLAID_REDIRECT_URI,
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(user_id)
            )
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
        json.dumps({
            "link_token": link_token
        }),
        content_type="application/json"
    )


def exchange_public_token(request: HttpRequest) -> HttpResponse:
    """Part of the Plaid workflow."""
    global access_token

    print(f"Request for public token exchange: {request}")

    public_token = request.body['public_token']

    request = ItemPublicTokenExchangeRequest(
        public_token=public_token
    )

    response = client.item_public_token_exchange(request)

    # These values should be saved to a persistent database and
    # associated with the currently signed-in user
    access_token = response['access_token']
    item_id = response['item_id']

    # person = Person ()
    # person.access_token = access_token
    # person.save()

    print(f"Token exchange response: {response}")

    return HttpResponse(
        json.dumps({'public_token_exchange': 'complete'}),
        content_type="application/json"
    )


# @app.route('/api/create_link_token_for_payment', methods=['POST'])
def create_link_token2(request: HttpRequest):
    # todo: DRF?
    global payment_id

    try:
        request = PaymentInitiationRecipientCreateRequest(
            name='John Doe',
            bacs=RecipientBACSNullable(account='26207729', sort_code='560029'),
            address=PaymentInitiationAddress(
                street=['street name 999'],
                city='city',
                postal_code='99999',
                country='GB'
            )
        )


        response = client.payment_initiation_recipient_create(
            request)
        recipient_id = response['recipient_id']

        request = PaymentInitiationPaymentCreateRequest(
            recipient_id=recipient_id,
            reference='TestPayment',
            amount=PaymentAmount(
                PaymentAmountCurrency('GBP'),
                value=100.00
            )
        )
        response = client.payment_initiation_payment_create(
            request
        )
        print(response.to_dict())

        # We store the payment_id in memory for demo purposes - in production, store it in a secure
        # persistent data store along with the Payment metadata, such as userId.
        payment_id = response['payment_id']

        linkRequest = LinkTokenCreateRequest(
            # The 'payment_initiation' product has to be the only element in the 'products' list.
            products=[Products('payment_initiation')],
            client_name='Plaid Test',
            # Institutions from all listed countries will be shown.
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            language='en',
            user=LinkTokenCreateRequestUser(
                # This should correspond to a unique id for the current user.
                # Typically, this will be a user ID number from your application.
                # Personally identifiable information, such as an email address or phone number, should not be used here.
                client_user_id=str(time.time())
            ),
            payment_initiation=LinkTokenCreateRequestPaymentInitiation(
                payment_id=payment_id
            )
        )

        if PLAID_REDIRECT_URI != None:
            linkRequest['redirect_uri'] = PLAID_REDIRECT_URI
        linkResponse = client.link_token_create(linkRequest)
        print(linkResponse.to_dict())
        return jsonify(linkResponse.to_dict())
    except plaid.ApiException as e:
        return json.loads(e.body)
