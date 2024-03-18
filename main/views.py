import json
from datetime import date, timedelta
from io import TextIOWrapper

from django.db.models import Q
from django import forms

from . import export

from django.contrib.auth import login, authenticate, logout, user_login_failed
from django.contrib.auth.forms import UserCreationForm
from django.db import OperationalError, IntegrityError
from django.dispatch import receiver
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import SetPasswordForm

from main.models import (
    FinancialAccount,
    Transaction,
    Institution,
    Person,
    SubAccount,
    AccountType,
    SubAccountType,
    RecurringTransaction,
    CategoryRule,
    CategoryCustom,
)

import plaid
from plaid.model.country_code import CountryCode

from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser


from main import plaid_, util
from main.plaid_ import (
    CLIENT,
    PLAID_COUNTRY_CODES,
    PLAID_REDIRECT_URI,
    ACCOUNT_REFRESH_INTERVAL_RECURRING,
)
from .transaction_cats import TransactionCategory

MAX_LOGIN_ATTEMPTS = 5


def load_body(request: HttpRequest) -> dict:
    """Helper function"""
    return json.loads(request.body.decode("utf-8"))


def landing(request: HttpRequest) -> HttpResponse:
    context = {}

    return render(request, "../templates/index.html", context)


@login_required
def load_transactions(request: HttpRequest) -> HttpResponse:
    """Load transactions. Return them as JSON. This is a POST request."""
    person = request.user.person

    data = load_body(request)
    # todo: Use pages or last index A/R.

    print("Loading transactions. Data received: ", data)

    start_i = data["start_i"]
    end_i = data["end_i"]
    search = data.get("search")
    category = data.get("category")
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

    if category is not None:
        category = TransactionCategory(category)

    tran = util.load_transactions(start_i, end_i, person, search, start, end, category)

    transactions = {
        "transactions": [t.serialize() for t in tran],
    }

    return JsonResponse(transactions)


@login_required
def load_spending_data(request: HttpRequest) -> HttpResponse:
    """Load data for the spending page."""
    person = request.user.person

    data = load_body(request)

    start = data["start"]
    end = data["end"]

    data = util.setup_spending_data(person, start, end)

    return JsonResponse(data)


@login_required
def edit_transactions(request: HttpRequest) -> HttpResponse:
    """Edit transactions."""
    data = load_body(request)

    # todo: This is being spammed, along with "Refreshing transactions" on the frontend!!!

    result = {"success": True}
    person = request.user.person

    for tran in data.get("transactions", []):

        # todo: Do it.
        # if json.loads(existing.categories).contains tran["categories"]:
        #     send_mail(
        #
        #     )

        tran_db = Transaction.objects.filter(id=tran["id"])
        tran_db = tran_db.filter(
            Q(account__person=request.user.person) | Q(person=request.user.person)
        ).first()  # Prevent exploits
        # todo: Don't override the original description for a linked transaction; use a separate field.

        tran_db.category= tran["category"]
        tran_db.description = tran["description"]
        tran_db.notes = tran["notes"]
        tran_db.amount = tran["amount"]
        tran_db.date = tran["date"]
        tran_db.save()

        if data.get("create_rule", False):
            rule_db, _ = CategoryRule.objects.update_or_create(
                person=person,
                description=tran_db.description,
                defaults={"category": tran["category"]},
            )

            util.change_tran_cats_from_rule(rule_db, person)

    return JsonResponse(result)


@login_required
def add_transactions(request: HttpRequest) -> HttpResponse:
    """Add one or more transactions, eg manually added by the user on the UI."""
    data = load_body(request)

    for tran in data.get("transactions", []):
        print("Tran adding: ", tran)
        # todo: Do it.

        tran_db = Transaction(
            account=None,
            person=request.user.person,
            institution_name=tran["institution_name"],
            category=tran["category"],
            amount=tran["amount"],
            description=tran["description"],
            date=tran["date"],
            currency_code=tran["currency_code"],
            pending=False,
        )

        try:
            tran_db.save()

            # todo: This id setup is not set up to handle multiple. Fine for now.
            result = {"success": True, "ids": [tran_db.id]}

        except IntegrityError:
            print("Integrity error saving new transaction manually added")
            result = {
                "success": False,
            }

    return JsonResponse(result)


@login_required
def edit_accounts(request: HttpRequest) -> HttpResponse:
    """Edit accounts. Notably, account nicknames, and everything about manual accounts."""
    data = load_body(request)
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

    return JsonResponse(result)


@login_required
def add_account_manual(request: HttpRequest) -> HttpResponse:
    """Add a manual account, with information populated by the user."""
    data = load_body(request)
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

    return JsonResponse({"success": success, "account": account.serialize()})


@login_required
def delete_accounts(request: HttpRequest) -> HttpResponse:
    """Delete one or more sub accounts."""
    data = load_body(request)
    result = {"success": True}

    person = request.user.person

    # todo: Unlink etc if not manual
    for id_ in data.get("ids", []):
        try:
            # person and account checks prevent abuse.
            acc = SubAccount.objects.filter(
                Q(id=id_, person=person) | Q(id=id_, account__person=person)
            ).account
        except SubAccount.DoesNotExist:
            result["success"] = False
        else:
            # Associate the transactions with the person, so it will still be loaded.
            for tran in acc.transactions.all():
                tran.person = person
                tran.save()

            acc.delete()

    return JsonResponse(result)


@login_required
def delete_transactions(request: HttpRequest) -> HttpResponse:
    """Delete one or more transactions."""
    data = load_body(request)
    result = {"success": True}

    for id_ in data.get("ids", []):
        try:
            # The person check prevents abuse

            tran = Transaction.objects.filter(id=id_)
            tran = tran.filter(
                Q(account__person=request.user.person) | Q(person=request.user.person)
            ).first()  # Prevent exploits
            tran.delete()
        except Transaction.DoesNotExist:
            result["success"] = False

    return JsonResponse(result)


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """The main account dashboard."""
    person = request.user.person

    account_status = util.check_account_status(request)
    if account_status is not None:
        return account_status

    if request.method == "POST":
        uploaded_file = request.FILES["file"]
        file_data = TextIOWrapper(uploaded_file.file, encoding="utf-8")
        export.import_csv_mint(file_data, request.user.person)

        return HttpResponseRedirect("/dashboard")

    spending_highlights = util.setup_spending_highlights(person, 30, 0, False)

    context = util.load_dash_data(request.user.person)

    context["spending_highlights"] = json.dumps(spending_highlights)

    return render(request, "dashboard.html", context)


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

    return JsonResponse(data)


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

    return JsonResponse({"link_token": link_token})


@login_required
def exchange_public_token(request: HttpRequest) -> HttpResponse:
    """Part of the Plaid workflow. POST request. Exchanges the public token retrieved by
    the client, after it successfullya uthenticates with an institution. Exchanges this for
    an access token, which is stored in the database, along with its associated item id.
    """
    person = request.user.person

    data = load_body(request)

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
        last_refreshed_recurring=timezone.now(),
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

    return JsonResponse({"success": success})


@login_required
def spending(request: HttpRequest) -> HttpResponse:
    """Page for details on spending, and related trends"""
    person = request.user.person

    account_status = util.check_account_status(request)
    if account_status is not None:
        return account_status

    # context = util.setup_spending_data(person, 30, 0)
    context = {}

    return render(request, "spending.html", context)


@login_required
def recurring(request: HttpRequest) -> HttpResponse:
    """Page for recurring transactions"""

    account_status = util.check_account_status(request)
    if account_status is not None:
        return account_status

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
        Q(account__person=person) | Q(account__account__person=person)
    ).filter(is_active=True)

    context = {
        # "recurring": json.dumps([r.serialize() for r in recur])
        "recurring": recur
    }

    return render(request, "recurring.html", context)


@login_required
def settings(request: HttpRequest) -> HttpResponse:
    """Page for adjusting account settings"""

    if request.method == "POST":
        form = SetPasswordForm(request.user, request.POST)

        if form.is_valid():
            form.save()
            return render(
                request,
                "settings.html",
                {"password_change": True, "password_change_success": True},
            )
        else:
            return render(
                request,
                "settings.html",
                {"password_change": True, "password_change_success": False},
            )

    account_status = util.check_account_status(request)
    if account_status is not None:
        return account_status

    context = {
        "rules": CategoryRule.objects.filter(person=request.user.person),
        "custom_categories": CategoryCustom.objects.filter(person=request.user.person),
        "password_change": False,
    }

    return render(request, "settings.html", context)


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

            person.send_verification_email(request)

            login(request, user)  # Log the user in
            messages.success(request, "Registration successful.")
            return redirect("/dashboard")  # Redirect to a desired URL
    else:
        print("Error: Non-post data passed to the register view.")
        # form = UserCreationForm()

    return render(request, "register.html", {})


# def password_reset(request):
#     if request.method == "POST":
#         pass
#         # form = UserCreationForm(request.POST)
#         # if form.is_valid():
#         #     user = form.save()
#         #     user.email = user.username
#         #     user.save()
#         #
#         #     person = Person()
#         #     person.user = user
#         #     person.save()
#         #
#         #     person.send_verification_email()
#         #
#         #     login(request, user)  # Log the user in
#         #     messages.success(request, "Registration successful.")
#         #     return redirect("/dashboard")  # Redirect to a desired URL
#
#     return render(request, "password_reset.html", {})


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        unsuccessful_msg = (
            "Unable to log you on. ☹️ If you've incorrectly entered your password several times "
            "in a row, your account may have been temporarily locked. Click here to unlock it."
        )

        print("A", request.POST)
        user = authenticate(request, username=username.lower(), password=password)
        print("B", user)

        # Try authenticating using the email address; ie if email changed.
        # if user is None:
        #     print("\nTrying email....")
        #     user = authenticate(request, email=username.lower(), password=password)

        if user is not None:
            login(request, user)

            # todo: How do we log unsuccessful attempts?

            person = user.person

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
            # return HttpResponse(unsuccessful_msg)
            return render(request, "login_fail.html")

    else:
        return render(request, "login.html")


# @requires_csrf_token
# def password_change_done(request):
#     """Thin wrapper around the Django default PasswordChangeDone"""
#     # return auth_views.PasswordChangeDoneView.as_view(),
#     # return auth_views.PasswordChangeDoneView,
#     # try:
#     #     person = request.user.person
#     # except Person.DoesNotExist:
#     #     return HttpResponse(
#     #         "No person associated with your account; please "
#     #         "contact a training or scheduling shop member."
#     #     )
#
#     # person.last_changed_password = date.today()
#     # person.save()
#
#     return HttpResponseRedirect("/dashboard")


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


@login_required
def edit_rules(request: HttpRequest) -> HttpResponse:
    """We use this to edit rules, eg from the settings page. Note that
    when editing the transactions table, we use the `edit_transactions` endpoint instead.
    """

    success = True

    data = load_body(request)
    person = request.user.person

    for rule in data["edited"]:
        rule_db, _ = CategoryRule.objects.update_or_create(
            person=person,
            id=rule["id"],
            defaults={
                "description": rule["description"],
                "category": rule["category"],
            },
        )
        util.change_tran_cats_from_rule(rule_db, person)

    for rule in data["added"]:
        # The person check here prevents abuse by the frontend.
        rule_db = CategoryRule(
            person=person,
            description=rule["description"],
            category=rule["category"],
        )
        # todo: Pass added IDs to the UI.
        try:
            rule_db.save()
        except IntegrityError:
            success = False
        else:
            util.change_tran_cats_from_rule(rule_db, person)

    for id_ in data["deleted"]:
        # The person check here prevents abuse by the frontend.
        CategoryRule.objects.get(id=id_, person=person).delete()

    return JsonResponse({"success": success})


# class CustomPasswordResetView(PasswordResetView):
#     print("\nCustom PW view")
#     template_name = 'password_reset.html'
#     email_template_name = 'registration/custom_password_reset_email.html'
#     subject_template_name = 'registration/custom_password_reset_subject.txt'
#     success_url = reverse_lazy('password_reset_done')
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # Add custom context data here
#         context['custom_data'] = 'This is custom data'
#         return context


def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email", "")
        user = User.objects.filter(email=email).first()

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{request.scheme}://{request.get_host()}/password-reset-confirm/{uid}/{token}"

            # Disabling click tracking is to stop Sendgrid from intercepting the links.
            email_body = f"""
               <h2>Reset your Finance Monitor password by clicking <a href="{reset_url}" clicktracking=off>this link</a>.</h2>
               
               If you did not request this reset, please contact us immediately by replying to this email.

               <p>If you have questions about Finance Monitor, or would like to contact us for
               any reason, reply to this email: <i>contact@finance-monitor.com</i></p>
               """

            # email = render_to_string(email_template_name, c)
            try:

                send_mail(
                    "Password reset: Finance Monitor",
                    "",
                    "contact@finance-monitor.com",
                    [user.email],
                    fail_silently=False,
                    html_message=email_body,
                )

            except Exception as e:
                print("Error sending email")
                return HttpResponse("Invalid header found.")

            print("Success on reset; redirecting")
            return HttpResponseRedirect("/login")

    print("\nRendering PW request form")

    # return render(request, template_name="registration/password_reset_form.html")
    return render(request, "password_reset.html")


def password_reset_confirm(request, uidb64=None, token=None):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = SetPasswordForm(user, request.POST)

            if form.is_valid():
                form.save()
                return HttpResponseRedirect("/login")
            else:
                print("Pw is not valid!")
                pass  # todo?
        else:
            form = SetPasswordForm(user)

        return render(request, "password_reset_confirm.html", {"form": form})
    else:
        return render(request, "password_reset_invalid.html")


def verify_email(request: HttpRequest, uidb64=None, token=None):
    print(f"In verify email. UId: {uidb64}, token: {token}")

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # todo: Do you need/want this token_generator check?
    if (
        user is not None
        and default_token_generator.check_token(user, token)
        and token == user.person.email_verification_token
    ):
        print("\nSuccessfully verified email")
        user.person.email_verification_token = None
        user.person.email_verified = True
        user.person.save()

        return HttpResponseRedirect("/dashboard")
    else:
        return HttpResponse("Problem verifying your email address. :(")


def send_verification(request: HttpRequest) -> HttpResponse:
    """We use this if the user requests to re-send the verification email."""

    person = request.user.person
    person.send_verification_email(request)

    print("\nRe-sending verification email")
    return HttpResponseRedirect("/dashboard")


def toggle_highlight(request: HttpRequest) -> HttpResponse:
    """Toggle a transactions highlight status."""
    data = load_body(request)

    tran = Transaction.objects.filter(id=data["id"])
    tran = tran.filter(
        Q(account__person=request.user.person) | Q(person=request.user.person)
    ).first()  # Prevent exploits

    tran.highlighted = not tran.highlighted
    tran.save()

    return JsonResponse({"success": True})
