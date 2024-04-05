"""
This module contains interacdtions with Plaid's API

Sandbox test credentials: user_good, pass_good, credential_good (pin), mfa_device (pin etc), code: 1234
"""

import json
from typing import Optional, Iterable, List, Tuple

from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from plaid import ApiException
from plaid.model.account_base import AccountBase
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest

from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_request import InstitutionsGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser

from plaid.model.products import Products
from plaid.model.transactions_recurring_get_request import (
    TransactionsRecurringGetRequest,
)
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from django.db import IntegrityError

from wallet import settings
from . import transaction_cats, util
from .models import (
    FinancialAccount,
    SubAccount,
    AccountType,
    SubAccountType,
    Transaction,
    Person,
    RecurringTransaction,
    RecurringDirection,
)
from .transaction_cats import TransactionCategory
from wallet.settings import PLAID_SECRET, PLAID_CLIENT_ID, PLAID_MODE, PlaidMode

import plaid
from plaid.api import plaid_api

HOUR = 60 * 60

# todo: Settings.py?
# todo: Increase to 12 or so hours.
BALANCE_REFRESH_INTERVAL = 4 * HOUR  # seconds.
TRAN_REFRESH_INTERVAL = 4 * HOUR  # seconds.

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

# Note: We don't use assets! That's used to qualify for a loan. Maybe see if Transactions only works?
# PRODUCTS = [Products(p) for p in ["transactions", "recurring_transactions"]]
PRODUCTS = [Products(p) for p in ["transactions"]]
PRODUCTS_REQUIRED_IF_SUPPORTED = [Products(p) for p in []]
PRODUCTS_OPTIONAL = [Products(p) for p in []]
PRODUCTS_ADDITIONAL_CONSENTED = [Products(p) for p in []]

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


def handle_api_exception(e: ApiException):
    """Handles various API exceptions from Plaid; used on all refresh types."""
    error_code = json.loads(e.body)["error_code"].lower()

    # https://plaid.com/docs/link/update-mode/
    if error_code == "item_login_required" or error_code == "pending_expiration":
        msg = f"\nItem login required when refreshing accounts; re-auth may be required: {e}\n"
        print(msg)
        util.send_debug_email(msg)

        # todo: Handle this

    elif error_code == "institution_not_responding":
        # This seems to be periodic; waiting fixes it.

        msg = f"\nInstitution not responding. Error message: {json.loads(e.body)}"
        print(msg)
        # util.send_debug_email(msg)

        # Note that returning None here prevents the `last_refreshed_successfully` DB field from being updated,
        # so we can diagnose an unhealthy account by this being expired, should we keep getting this message.

    else:
        msg = f"\nOther problem refreshing: {e}:\n"
        print(msg)
        util.send_debug_email(msg)

    msg = f"\nProblem refreshing accounts. Error: {e}"
    print(msg)
    util.send_debug_email(msg)


def get_balance_data(access_token: str) -> Optional[AccountBase]:
    """Pull real-time balance information for each account associated
    with the access token. This returns sub-accounts, currently as a dict."""
    request = AccountsBalanceGetRequest(access_token=access_token)

    try:
        response = CLIENT.accounts_balance_get(request)
    except ApiException as e:
        handle_api_exception(e)
        return None

    return response["accounts"]


def update_accounts(accounts: Iterable[FinancialAccount]) -> bool:
    """Update all account balances and related information. Return sub accounts, and net worth.
    Returns `True if there is new data."""
    # Update account info, if we are due for a refresh
    new_data = False
    now = timezone.now()

    for acc in accounts:
        if (
            now - acc.last_balance_refresh_attempt
        ).total_seconds() > BALANCE_REFRESH_INTERVAL:
            print(f"Refreshing balances on acc{acc}...")
            success = refresh_account_balances(acc)

            if success:
                acc.last_balance_refresh_success = now
                new_data = True

            acc.last_balance_refresh_attempt = now
            acc.save()

        if (
            now - acc.last_tran_refresh_attempt
        ).total_seconds() > TRAN_REFRESH_INTERVAL:
            print(f"Refreshing transactions on acc{acc}...")
            success = refresh_transactions(acc)

            if success:
                acc.last_tran_refresh_success = now
                new_data = True

            acc.last_tran_refresh_attempt = now
            acc.save()

        if (
            now - acc.last_refreshed_recurring
        ).total_seconds() > ACCOUNT_REFRESH_INTERVAL_RECURRING:
            print(f"Refreshing recurring on acc{acc}...")
            refresh_recurring(acc)
            acc.last_refreshed_recurring = now
            acc.save()

    return new_data


def refresh_account_balances(account: FinancialAccount) -> bool:
    """Update account information in the database. Returns True if successful."""
    balance_data = get_balance_data(account.access_token)
    if balance_data is None:
        return False

    account.last_balance_refresh_success = timezone.now()

    # todo:  Handle  sub-acct entries in DB that have missing data.
    for sub in balance_data:
        try:
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
        except IntegrityError:
            print(f"This subaccount already exists: {sub}")

    account.save()
    return True


def refresh_transactions(account: FinancialAccount) -> bool:
    """
    Updates the database with transactions for a single account.
    https://plaid.com/docs/api/products/transactions/#transactionssync

    Returns success status
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

        try:
            response = CLIENT.transactions_sync(request)
        except ApiException as e:
            handle_api_exception(e)
            return False

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
    rules = account.person.category_rules.all()

    for tran in added:
        print("\n\n Adding transaction: ", tran, "\n\n")
        cat_detailed = tran.personal_finance_category.detailed
        cat_primary = tran.personal_finance_category.primary

        print(
            f"\n Description: {tran.name}, Cat prim: {cat_primary}, Cat detailed: {cat_detailed} Cat isolated: {tran.category}\n"
        )

        tran_db = Transaction(
            account=account,
            institution_name=account.institution.name,
            category=TransactionCategory.from_plaid(
                tran.category, tran.name, rules
            ).value,
            # todo: Sort out what pos vs negative transactions mean, here and import
            amount=-tran.amount,
            # Note: Other fields like "merchant_name" are available, but aren't used on many transactcions.
            description=tran.name,
            merchant=tran.merchant_name,  # Not always present.
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

    # On Pending: https://plaid.com/docs/transactions/transactions-data/
    # Pending transactions will be in the remove category once completed, and the
    # final transaction wil be added; so, they are not modifications.
    for tran in modified:
        print("\n\n Modifing transaction:\n", tran, "\n\n")
        tran_db = Transaction.objects.filter(
            # account=account,
            Q(plaid_id=tran.transaction_id)
            | Q(plaid_id=tran.pending_transaction_id) & Q(account=account),
        )

        try:
            tran_db = tran_db[0]
        except IndexError as e:
            print(
                f"\n Error: Unable to find the transaction requested to modify: \n\n{tran}"
            )
            util.send_debug_email(f"Tran modification error: \n{tran}: \n\n: {e}")
        else:
            tran_db.amount = tran.amount
            tran_db.description = tran.name
            tran_db.date = tran.date
            tran_db.datetime = tran.datetime
            tran_db.currency_code = tran.iso_currency_code
            tran_db.pending = tran.pending
            tran_db.logo_url = tran.logo_url
            tran_db.plaid_category_icon_url = ""

            try:
                tran_db.save()
            except IntegrityError as e:
                print(f"\n\nIntegrity error saving message\n\n: {tran_db}: \n: {e}")
                util.send_debug_email(
                    f"Integrity error saving message\n\n: {tran_db}: \n: {e}"
                )

    for tran in removed:
        print("\n\n Deleting transaction:\n", tran, "\n\n")
        _ = Transaction.objects.filter(
            # account=account,
            # Q(plaid_id=tran.transaction_id) | Q(plaid_id=tran.pending_transaction_id) & Q(account=account),
            plaid_id=tran.transaction_id,
            account=account,
        ).delete()

    account.plaid_cursor = cursor
    account.save()

    return True


def refresh_recurring(account: FinancialAccount):
    # Run this on all sub-accounts that have recent transactions.\
    # The docs have some interesting notes; I'm not yet sure how to impl them.
    # https://plaid.com/docs/api/products/transactions/#transactionsrecurringget

    # todo: Use your own logic instead of paying Plaid for this API.

    sub_accs = (
        account.sub_accounts.all()
    )  # todo: Filter A/R based on which have transactions
    account_ids = [s.plaid_id for s in sub_accs]

    request = TransactionsRecurringGetRequest(
        access_token=account.access_token, account_ids=account_ids
    )

    try:
        response = CLIENT.transactions_recurring_get(request)
    except ApiException as e:
        handle_api_exception(e)
        return

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
    rules = account.person.category_rules.all()

    for recur in inflow_streams:
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
            category=TransactionCategory.from_plaid(
                recur.category, recur.description, rules
            ).value,
        )
        try:
            recur_db.save()
        except IntegrityError as e:
            print("Integrity error saving recuring transaction", e)

    # todo: DRY!

    # Delete all previous recurring transactions, replacing them with the latest.
    RecurringTransaction.objects.filter(account__account=account).delete()

    for recur in outflow_streams:
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
            category=TransactionCategory.from_plaid(
                recur.category, recur.description, rules
            ).value,
        )
        try:
            recur_db.save()
        except IntegrityError as e:
            print("Integrity error saving recuring transaction", e)

    # print("\nRecur resp: ", response)


def link_token_helper(
    user_id: int, update_mode: bool, access_token: Optional[str] = None
) -> LinkTokenCreateRequest:
    if update_mode:
        return LinkTokenCreateRequest(
            access_token=access_token,
            client_name="Finance Monitor",
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            redirect_uri=PLAID_REDIRECT_URI,
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),
        )

    else:
        return LinkTokenCreateRequest(
            # `products`: Which products to show.
            products=PRODUCTS,
            required_if_supported_products=PRODUCTS_REQUIRED_IF_SUPPORTED,
            optional_products=PRODUCTS_OPTIONAL,
            additional_consented_products=PRODUCTS_ADDITIONAL_CONSENTED,
            client_name="Finance Monitor",
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            redirect_uri=PLAID_REDIRECT_URI,
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),
        )
