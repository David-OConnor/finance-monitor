import json
from datetime import date
from io import TextIOWrapper

from django.db.models import Q
from django import forms
import time

from . import export

# todo: Plaid institution icon urls??

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
from django.contrib.auth.models import User

from main.models import (
    FinancialAccount,
    Transaction,
    Institution,
    Person,
    SubAccount,
    AccountType,
    SubAccountType, RecurringTransaction,
)

import plaid
from plaid.model.country_code import CountryCode

from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser


from main import plaid_, util
from main.plaid_ import CLIENT, PLAID_COUNTRY_CODES, PLAID_REDIRECT_URI, ACCOUNT_REFRESH_INTERVAL_RECURRING
from .transaction_cats import TransactionCategory

MAX_LOGIN_ATTEMPTS = 5


def landing(request: HttpRequest) -> HttpResponse:
    context = {}

    return render(request, "../templates/index.html", context)


@login_required
def load_transactions(request: HttpRequest) -> HttpResponse:
    """Load transactions. Return them as JSON. This is a POST request."""
    person = request.user.person
    accounts = person.accounts.all()

    data = json.loads(request.body.decode("utf-8"))
    # todo: Use pages or last index A/R.

    print("Loading transactions. Data received: ", data)

    start_i = data["start_i"]
    end_i = data["end_i"]
    search = data.get("search")
    categories = data.get("categories")
    start = data.get("start")
    end = data.get("end")

    if start:
        start = date.fromisoformat(start)
    else:
        start = None  # In case of empty string passed
    if end:
        end = date.fromisoformat(end)
    else:
        end = None

    tran = util.get_transaction_data(start_i, end_i, accounts, person, search, start, end)

    transactions = {
        "transactions": [t.serialize() for t in tran],
    }

    return HttpResponse(json.dumps(transactions), content_type="application/json")


@login_required
def edit_transactions(request: HttpRequest) -> HttpResponse:
    """Edit transactions."""
    data = json.loads(request.body.decode("utf-8"))

    result = {"success": True}

    for tran in data.get("transactions", []):
        # print(tran, "TRAN UP")
        # existing = Transaction.objects.get(id=tran["id"])

        # todo: Do it.
        # if json.loads(existing.categories).contains tran["categories"]:
        #     send_mail(
        #
        #     )

        _, _ = Transaction.objects.update_or_create(
            id=tran["id"],
            defaults={
                "categories": tran["categories"],
                "notes": tran["notes"],
                "amount": tran["amount"],
                "date": tran["date"],
            },
        )

    return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
def edit_accounts(request: HttpRequest) -> HttpResponse:
    """Edit accounts. Notably, account nicknames, and everything about manual accounts."""
    data = json.loads(request.body.decode("utf-8"))
    result = {"success": True}

    for acc in data.get("accounts", []):
        _, _ = SubAccount.objects.update_or_create(
            id=acc["id"],
            defaults={
                "name": acc["name"],
                "nickname": acc["nickname"],
                "iso_currency_code": acc["iso_currency_code"],
                "current": acc["current"],
            },
        )

    return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
def add_account_manual(request: HttpRequest) -> HttpResponse:
    """Add a manual account, with information populated by the user."""
    data = json.loads(request.body.decode("utf-8"))
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

    success = True
    try:
        account.save()
    except IntegrityError:
        print("Integrity error on saving a manual account")
        success = False

    # return HttpResponseRedirect("/dashboard")
    return HttpResponse(
        json.dumps({"success": success, "account": account.serialize()}), content_type="application/json"
    )


@login_required
def delete_accounts(request: HttpRequest) -> HttpResponse:
    """Delete one or more sub accounts."""
    data = json.loads(request.body.decode("utf-8"))
    result = {"success": True}

    # todo: Unlink etc if not manual
    for id_ in data.get("ids", []):
        try:
            SubAccount.objects.get(id=id_).account.delete()
        except SubAccount.DoesNotExist:
            result["success"] = False

    return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
def delete_transactions(request: HttpRequest) -> HttpResponse:
    """Delete one or more transactions."""
    data = json.loads(request.body.decode("utf-8"))
    result = {"success": True}

    for id_ in data.get("ids", []):
        try:
            Transaction.objects.get(id=id_).delete()
        except Transaction.DoesNotExist:
            result["success"] = False

    return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """The main account dashboard."""

    if request.method == "POST":
        uploaded_file = request.FILES["file"]
        file_data = TextIOWrapper(uploaded_file.file, encoding="utf-8")
        export.import_csv_mint(file_data, request.user.person)

        return HttpResponseRedirect("/dashboard")

    person = request.user.person

    spending_highlights = util.setup_spending_highlights(person.accounts.all(), person, 30)

    context = util.load_dash_data(request.user.person)

    context["spending_highlights"] = json.dumps(spending_highlights)

    return render(request, "../templates/dashboard.html", context)


@login_required
def post_dash_load(request: HttpRequest) -> HttpResponse:
    """This performs actions after a dashboard initial  load, such as refreshing
    account data."""
    print("Post dash load...")  # todo temp

    person = request.user.person
    accounts = person.accounts.all()

    data = {
        "sub_accs": [],
        "transactions": [],
    }
    # Get new balance and transaction data from Plaid. This only populates if there is new data available.
    if plaid_.update_accounts(accounts):
        # Send balances and transactions to the UI, if new data is available.
        data = util.load_dash_data(request.user.person, no_preser=True)

        # Save snapshots, for use with charts, etc
        # todo: We need to make sure this is called regularly, even if the user doesn't log into the page.
        util.take_snapshots(accounts, person)

    return HttpResponse(
        json.dumps(data), content_type="application/json"
    )


@login_required
def create_link_token(request: HttpRequest) -> HttpResponse:
    """The first stage of the Plaid workflow. GET request. Passes the client a link token,
    provided by Plaid's API."""
    try:
        request = LinkTokenCreateRequest(
            # `products`: Which products to show.
            products=plaid_.PRODUCTS,
            required_if_supported_products=plaid_.PRODUCTS_REQUIRED_IF_SUPPORTED,
            optional_products=plaid_.PRODUCTS_OPTIONAL,
            additional_consented_products=plaid_.PRODUCTS_ADDITIONAL_CONSENTED,
            client_name="Finance Monitor",
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            redirect_uri=PLAID_REDIRECT_URI,
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=str(request.user.id)),
        )

        # create link token
        response = CLIENT.link_token_create(request)

    except plaid.ApiException as e:
        print(e, "Plaid error")
        return HttpResponse(json.loads(e.body))

    print(f"Link token response: {response}")

    # note: expiration available.
    link_token = response["link_token"]

    return HttpResponse(
        json.dumps({"link_token": link_token}), content_type="application/json"
    )


@login_required
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

    response = CLIENT.item_public_token_exchange(request)

    # These values should be saved to a persistent database and
    # associated with the currently signed-in user
    access_token = response["access_token"]
    item_id = response["item_id"]
    # request_id = response["request_id"]

    print("\n Response when adding acct: ", response)

    sub_accounts = metadata["accounts"]

    print("\n Sub accts: ", sub_accounts)

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

    success = True

    try:
        account_added.save()
    except OperationalError as e:
        print("\nError saving the account: ", e)
        success = False
    else:
        # Add sub-accounts. Note that these are also added when refreshing A/R.
        # for sub in metadata.get("accounts", []):
        #     sub_acc = SubAccount(
        #         account=account_added,
        #         plaid_id=sub["id"],
        #         plaid_id_persistent="",  # todo temp
        #         name=sub.get("name_official", ""),z
        #         name_official=sub.get("name_official", ""),
        #         type=AccountType.from_str(str(sub["type"])).value,
        #         sub_type=AccountType.from_str(str(sub["subtype"])).value,
        #         iso_currency_code=sub.get("iso_currency_code", "USD"),
        #     )
        #     try:
        #         sub_acc.save()
        #     except IntegrityError as e:
        #         print("\nError saving a subaccount during account add", e)
        #         success = False

        # Refresh balances, and send the updated account data to the client to display.
        # (Currently, the client commands a refresh)
        plaid_.refresh_account_balances(account_added)
        plaid_.refresh_transactions(account_added)

    return HttpResponse(
        json.dumps({"success": success}),
        content_type="application/json",
    )


@login_required
def spending(request: HttpRequest) -> HttpResponse:
    """Page for details on spending"""
    return render(request, "spending.html", {})


@login_required
def recurring(request: HttpRequest) -> HttpResponse:
    """Page for recurring transactions"""

    person = request.user.person

    # Note: This is also checked in post_load.
    for acc in person.accounts.all():
    #     if (timezone.now() - acc.last_refreshed_recurring).total_seconds() > ACCOUNT_REFRESH_INTERVAL_RECURRING:
    #         plaid_.refresh_recurring(acc)
    #         acc.last_refreshed_recurring = timezone.now()

        pass
    # todo temp
    #     plaid_.refresh_recurring(acc)

    recur = RecurringTransaction.objects.filter(
            Q(account__person=person) |
            Q(account__account__person=person)
        ).filter(is_active=True)

    context = {
        # "recurring": json.dumps([r.serialize() for r in recur])
        "recurring": recur
    }

    return render(request, "recurring.html", context)


@login_required
def settings(request: HttpRequest) -> HttpResponse:
    """Page for adjusting account settings"""
    return render(request, "settings.html", {})


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
            user.email = user.username
            user.save()

            person = Person()
            person.user = user
            person.save()

            person.send_verification_email()

            login(request, user)  # Log the user in
            messages.success(request, "Registration successful.")
            return redirect("/dashboard")  # Redirect to a desired URL
    else:
        print("Error: Non-post data passed to the register view.")
        # form = UserCreationForm()


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


@login_required
def export_(request: HttpRequest) -> HttpResponse:
    filename = f"transaction_export_{timezone.now().date().isoformat()}.csv"

    response = HttpResponse(
        content_type="text/csv",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    export.export_csv(
        Transaction.objects.filter(
            Q(account__person=request.user.person) | Q(person=request.user.person)
        ),
        response,
    )

    return response
