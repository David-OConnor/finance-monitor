# Sandbox test credentials: user_good, pass_good, credential_good (pin), mfa_device (pin etc), code: 1234
import csv
import time
import json
from datetime import datetime, date
from io import StringIO, TextIOWrapper

from django.db.models import Q
from django import forms

from . import export

from django.contrib.auth import login, authenticate, logout, user_login_failed
from django.contrib.auth.forms import UserCreationForm
from django.db import OperationalError, IntegrityError
from django.dispatch import receiver
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import requires_csrf_token
from django.contrib.auth.models import Group, User

from main.models import (
    FinancialAccount,
    Transaction,
    Institution,
    Person,
    SubAccount,
    AccountType,
    SubAccountType,
)
from .transaction_cats import TransactionCategory

import plaid
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser


from main import plaid_, util
from main.plaid_ import client, PLAID_PRODUCTS, PLAID_COUNTRY_CODES

ACCOUNT_REFRESH_INTERVAL = 4 * 60 * 60  # seconds.

MAX_LOGIN_ATTEMPTS = 5


def landing(request: HttpRequest) -> HttpResponse:
    context = {}

    return render(request, "../templates/index.html", context)


@login_required
def load_transactions(request: HttpRequest) -> HttpResponse:
    """Load transactions. Return them as JSON. This is a POST request."""
    person = request.user.person
    accounts = person.accounts.all()

    data = json.loads(request.body.decode('utf-8'))
    print("Body of transactions: ", data)
    # todo: Use pages or last index A/R.

    search_text = data.get("search_text")
    categories = data.get("categories")
    start = data.get("start")
    end = data.get("end")

    transactions = {
        "transactions": util.create_transaction_display(accounts, person, search_text)
    }

    return HttpResponse(json.dumps(transactions), content_type="application/json")


@login_required
def edit_transactions(request: HttpRequest) -> HttpResponse:
    """Edit transactions."""
    data = json.loads(request.body.decode('utf-8'))

    result = {"success": True}

    for tran in data.get("transactions", []):
        _, _ = Transaction.objects.update_or_create(
            id=tran["id"],
            defaults={
                "notes": tran["notes"],
                "date": tran["date"],
            }
        )

    return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
def edit_accounts(request: HttpRequest) -> HttpResponse:
    """Edit accounts. Notably, account nicknames, and everything about manual accounts."""
    data = json.loads(request.body.decode('utf-8'))
    print("Body of account edit: ", data)

    result = {"success": True}

    for acc in data.get("accounts", []):
        _, _ = SubAccount.objects.update_or_create(
            id=tran["id"],
            defaults={
                "notes": tran["notes"],
                "date": tran["date"],
            }
        )

    return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
def add_account_manual(request: HttpRequest) -> HttpResponse:
    """Add a manual account, with information populated by the user."""
    data = json.loads(request.body.decode('utf-8'))
    print("Body of adding manual accounts: ", data)
    # todo: Use pages or last index A/R.

    sub_type = SubAccountType(data["sub_type"])

    account_type = AccountType.from_sub_type(sub_type)

    account = SubAccount(
        person=request.user.person,
        name=data["name"],
        type=account_type.value,
        sub_type=sub_type.value,
        iso_currency_code=data["iso_currency_code"].upper(),
        current=data["current"],
    )

    print("Adding account: ", account)

    success = True
    try:
        account.save()
    except IntegrityError:
        print("Integrity error on saving a manual account")
        success = False

    # return HttpResponseRedirect("/dashboard")
    return HttpResponse(json.dumps({"success": success}), content_type="application/json")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    person = request.user.person
    accounts = person.accounts.all()

    net_worth = 0.0

    # Update account info, if we are due for a refresh
    for acc in accounts:
        print("Account: ", acc)
        if (timezone.now() - acc.last_refreshed).seconds > ACCOUNT_REFRESH_INTERVAL:
            print("Refreshing account data...")

            plaid_.refresh_account_balances(acc)
            plaid_.load_transactions(acc)
        else:
            print("Not refreshing account data")

        net_worth = util.update_net_worth(net_worth, acc)
        print(net_worth, "NW")

    net_worth = util.update_net_worth_manual_accs(net_worth, person)

    # todo: Delegate this to a fn A/R
    # Organize balances by sub-account
    # todo: Dict
    cash_accs = []
    investment_accs = []
    crypto_accs = []
    credit_debit_accs = []
    loan_accs = []
    asset_accs = []

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
            cash_accs.append(sub_acc.to_display_dict())
            totals["cash"] += sub_acc.current
        elif t in [SubAccountType.DEBIT_CARD, SubAccountType.CREDIT_CARD]:
            credit_debit_accs.append(sub_acc.to_display_dict())
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
            investment_accs.append(sub_acc.to_display_dict())
            totals["investment"] += sub_acc.current
        elif t in [SubAccountType.STUDENT, SubAccountType.MORTGAGE]:
            loan_accs.append(sub_acc.to_display_dict())
            totals["loans"] -= sub_acc.current
        elif t in [SubAccountType.CRYPTO]:
            crypto_accs.append(sub_acc.to_display_dict())
            totals["crypto"] += sub_acc.current
        elif t in [SubAccountType.ASSET]:
            asset_accs.append(sub_acc.to_display_dict())
            totals["asset"] += sub_acc.current
        else:
            print("Fallthrough in sub account type: ", t)

    # Apply a class for color-coding in the template.

    totals_display = {}  # Avoids adding keys while iterating.

    for (k, v) in totals.items():
        totals_display[k + "_class"] = "tran_pos" if v > 0.0 else "tran_neg"
        # A bit of a hack to keep this value consistent with the sub-account values.
        totals_display[k] = f"{v:,.0f}".replace("-", "")

    #  todo: Move this A/R
    if request.method == 'POST':
        uploaded_file = request.FILES['file']
        file_data = TextIOWrapper(uploaded_file.file, encoding='utf-8')
        export.import_csv_mint(file_data, request.user.person)

        return HttpResponseRedirect("/dashboard")

    context = {
        "accounts": accounts,
        "cash_accs": cash_accs,
        "investment_accs": investment_accs,
        "crypto_accs": crypto_accs,
        "credit_debit_accs": credit_debit_accs,
        "loan_accs": loan_accs,
        "assets": asset_accs,
        # "transactions": transactions,
        "totals": totals_display,
    }

    return render(request, "../templates/dashboard.html", context)


def create_link_token(request_: HttpRequest) -> HttpResponse:
    """The first stage of the Plaid workflow. GET request. Passes the client a link token,
    provided by Plaid's API."""
    user_id = 100

    try:
        request = LinkTokenCreateRequest(
            products=PLAID_PRODUCTS,
            client_name="Finance Monitor",
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
    an access token, which is stored in the database, along with its associated item id.
    """
    person = request.user.person

    data = json.loads(request.body.decode("utf-8"))

    public_token = data["public_token"]
    metadata = data["metadata"]

    # Example metadata: {
    # 'status': None,
    # 'link_session_id': '973847c4-be0b-4619-b241-f48fbcf16949',
    # 'institution': {
    #   'name': 'Interactive Brokers - US',
    #   'institution_id': 'ins_116530'
    # },
    # 'accounts': [
        # {
        # 'id': 'prvM1kM78eH1Ejw5OyDzI4k01joBm8H3Nyn7Q',
        # 'name': "David A O'Connor",
        # 'mask': '4029',
        # 'type': 'investment',
        # 'subtype': 'brokerage',
        # 'verification_status': None,
        # 'class_type': None
        # }
    # ],
    # 'account': {
    #   'id': 'prvM1kM78eH1Ejw5OyDzI4k01joBm8H3Nyn7Q',
    #   'name': "David A O'Connor",
    #   'mask': '4029',
    #   'type': 'investment',
    #   'subtype': 'brokerage',
    #   'verification_status': None,
    #   'class_type': None
    # },
    # 'account_id': 'prvM1kM78eH1Ejw5OyDzI4k01joBm8H3Nyn7Q',
    # 'transfer_status': None,
    # 'wallet': None,
    # 'public_token': 'public-development-0cce98fd-c5e1-424b-ae33-b9ea92332522'
    # }

    print("\nMetadata received during token exchange (account link): ", metadata)

    request = ItemPublicTokenExchangeRequest(public_token=public_token)

    response = client.item_public_token_exchange(request)

    # These values should be saved to a persistent database and
    # associated with the currently signed-in user
    access_token = response["access_token"]
    item_id = response["item_id"]
    # request_id = response["request_id"]

    # sub_accounts = metadata["accounts"]

    inst, _ = Institution.objects.get_or_create(
        plaid_id=metadata["institution"]["institution_id"],
        defaults={"name": metadata["institution"]["name"]},
    )

    account_added = FinancialAccount(
        person=person,
        institution=inst,
        name="",
        access_token=access_token,
        item_id=item_id,
        last_refreshed=timezone.now(),
    )
    # todo: We can add subaccounts here if we wish, using metadata["accounts"].
    # todo: Sub-keys

    try:
        account_added.save()
    except OperationalError as e:
        print("\nError saving the account: ", e)
    else:
        print(f"\nSuccessfully saved an account: {account_added}")
        plaid_.refresh_account_balances(account_added)

    return HttpResponse(
        json.dumps({"success": True}),
        content_type="application/json",
    )


def about(request: HttpRequest) -> HttpResponse:
    return render(request, "about.html", {})


def privacy(request: HttpRequest) -> HttpResponse:
    return render(request, "privacy.html", {})


def terms(request: HttpRequest) -> HttpResponse:
    return render(request, "terms.html", {})


@receiver(user_login_failed)
def login_failed_handler(sender, credentials, request, **kwargs):
    attempted_username = credentials["username"]
    attempted_password = credentials["password"]

    # todo: The relevant DB fields should be tied to a user, not Person, ideally.

    try:
        user = User.objects.get(username=attempted_username)
    except User.DoesNotExist:
        print("User doesn't exist on failed login attempt")
        return

    try:
        person = user.person
    except Person.DoesNotExist:
        # No action required; their login will be blocked in `user_login()`.
        print("Person doesn't exist on failed login attempt")
        return
        # todo: Do something else sus?

    person.unsuccessful_login_attempts += 1

    if person.unsuccessful_login_attempts >= MAX_LOGIN_ATTEMPTS:
        person.account_locked = True

    person.save()


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            person = Person()
            person.user = user
            person.save()

            login(request, user)  # Log the user in
            messages.success(request, "Registration successful.")
            return redirect("/dashboard")  # Redirect to a desired URL
    else:
        form = UserCreationForm()
    return render(request, "register.html", {})


@requires_csrf_token
def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        unsuccessful_msg = (
            "Unable to log you on. ☹️ If you've incorrectly entered your password several times "
            "in a row, your account may have been temporarily locked. Click here to unlock it."
        )

        user = authenticate(request, username=username.lower(), password=password)
        if user is not None:
            login(request, user)

            # todo: How do we log unsuccessful attempts?

            # Once authenticated, make sure the user's password isn't expired. We perform this check to make
            # 4FW Comm and IG happier; agreed on a 180-day expiration for now. (2021-09-27).
            try:
                person = user.person
            except Person.DoesNotExist:
                return HttpResponse(
                    "No person associated with your account; please "
                    "contact a training or scheduling shop member."
                )

            if person.account_locked:
                return HttpResponse(unsuccessful_msg)
            else:
                if person.unsuccessful_login_attempts > 0:
                    person.unsuccessful_login_attempts = 0
                    person.save()

            # # if (dt.date.today() - person.last_changed_password).days > 180:
            # # This is the default date; so, require a PW change if this is the first login.
            # # Note that this is skippable in its current form...
            # if person.last_changed_password == "2021-09-30":
            #     # Send to the default password change form instead of the page requested.
            #     # return auth_views.PasswordChangeView
            #     return HttpResponseRedirect("/password_change/")

            # Redirect to a success page.
            return HttpResponseRedirect("/dashboard")
        else:
            # Return an 'invalid login' error message.
            return HttpResponse(unsuccessful_msg)

    else:
        return render(request, "login.html")


@requires_csrf_token
def password_change_done(request):
    """Thin wrapper around the Django default PasswordChangeDone"""
    # return auth_views.PasswordChangeDoneView.as_view(),
    # return auth_views.PasswordChangeDoneView,
    # try:
    #     person = request.user.person
    # except Person.DoesNotExist:
    #     return HttpResponse(
    #         "No person associated with your account; please "
    #         "contact a training or scheduling shop member."
    #     )

    # person.last_changed_password = date.today()
    # person.save()

    return HttpResponseRedirect("/dashboard")


# Use the login_required() decorator to ensure only those logged in can access the view.
@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)
    # Take the user back to the homepage.
    return HttpResponseRedirect("/")


class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50)
    file = forms.FileField()


# @login_required
# def import_(request: HttpRequest) -> HttpResponse:
#     # todo: A/R
#
#
#     # body_unicode = request.body.decode('utf-8')
#     # csv_file = StringIO(body_unicode)
#     #
#     # export.import_csv_mint(csv_file, request.user.person)
#
#     print("IMPORT")
#     # todo?
#     # return HttpResponse({"success": True})
#     return HttpResponseRedirect("/dashboard")


@login_required
def export_(request: HttpRequest) -> HttpResponse:
    filename = f"transaction_export_{timezone.now().date().isoformat()}.csv"

    response = HttpResponse(
        content_type="text/csv",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    export.export_csv(Transaction.objects.filter(
        Q(account__person=request.user.person) | Q(person=request.user.person)
    ), response)

    return response


def refresh_balances(request: HttpRequest) -> HttpResponse:
    pass


def refresh_transactions(request: HttpRequest) -> HttpResponse:
    pass
