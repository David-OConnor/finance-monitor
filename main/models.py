import json
from datetime import date, datetime
from enum import Enum
from json import JSONDecodeError
from typing import Dict, List

from django.db import models
from django.contrib.auth.models import Group, User
from django.core.mail import send_mail
from django.http import HttpRequest
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site

from django.db.models import (
    SET_NULL,
    CASCADE,
    IntegerField,
    DateField,
    DateTimeField,
    FloatField,
    CharField,
    TextField,
    Model,
    BooleanField,
    ForeignKey,
    JSONField,
)

from main.transaction_cats import TransactionCategory


def enum_choices(cls):
    """Required to make Python enums work with Django integer fields"""

    @classmethod
    def choices(cls_):
        return [(key.value, key.name) for key in cls_]

    cls.choices = choices
    return cls


@enum_choices
class RecurringDirection(Enum):
    INFLOW = 0
    OUTFLOW = 1


@enum_choices
class SubAccountType(Enum):
    """These are types as reported by Plaid, with some exception"""

    CHECKING = 0
    SAVINGS = 1
    DEBIT_CARD = 2
    CREDIT_CARD = 3
    T401K = 4
    STUDENT = 5
    MORTGAGE = 6
    CD = 7
    MONEY_MARKET = 8
    IRA = 9
    MUTUAL_FUND = 10
    CRYPTO = 11
    ASSET = 12  # A bit of a catch-all
    BROKERAGE = 13
    ROTH = 14

    @classmethod
    def from_str(cls, s: str) -> "SubAccountType":
        s = s.lower()

        if "check" in s:
            return cls.CHECKING
        if "saving" in s:
            return cls.SAVINGS
        if "debit" in s:
            return cls.DEBIT_CARD
        if "credit" in s:
            return cls.CREDIT_CARD
        if "401" in s:
            return cls.T401K
        if "student" in s:
            return cls.STUDENT
        if "mort" in s:
            return cls.MORTGAGE
        if "cd" in s:
            return cls.CD
        if "money market" in s:
            return cls.MONEY_MARKET
        if "ira" == s:
            return cls.IRA
        if "mutual" in s:
            return cls.MUTUAL_FUND
        if "crypto" in s:
            return cls.CRYPTO
        if "asset" in s:
            return cls.ASSET
        if "broker" in s or "stock" in s:
            return cls.BROKERAGE
        if "roth" in s:
            return cls.ROTH

        print(f"\nFallthrough in parsing sub account type: {s}\n")
        return cls.CHECKING


@enum_choices
class AccountType(Enum):
    """These are types as reported by Plaid"""

    DEPOSITORY = 1
    INVESTMENT = 2
    LOAN = 3
    CREDIT = 4

    @classmethod
    def from_str(cls, s: str) -> "AccountType":
        s = s.lower()

        if "depos" in s:
            return cls.DEPOSITORY
        if "invest" in s:
            return cls.INVESTMENT
        if "loan" in s:
            return cls.LOAN
        if "credit" in s:
            return cls.CREDIT

        print("Fallthrough in parsing account type: ", s)
        return cls.DEPOSITORY

    @classmethod
    def from_sub_type(cls, sub_type: SubAccountType) -> "AccountType":
        if sub_type in [
            SubAccountType.CHECKING,
            SubAccountType.SAVINGS,
            SubAccountType.CRYPTO,
            SubAccountType.ASSET,
        ]:
            return cls.DEPOSITORY
        if sub_type in [SubAccountType.DEBIT_CARD, SubAccountType.CREDIT_CARD]:
            return cls.CREDIT
        if sub_type in [
            SubAccountType.T401K,
            SubAccountType.CD,
            SubAccountType.MONEY_MARKET,
            SubAccountType.IRA,
            SubAccountType.MUTUAL_FUND,
            SubAccountType.BROKERAGE,
            SubAccountType.ROTH,
        ]:
            return cls.INVESTMENT
        if sub_type in [SubAccountType.MORTGAGE, SubAccountType.STUDENT]:
            return cls.LOAN

        print("Fallthrough in account type from sub", sub_type)
        return cls.DEPOSITORY


class Person(Model):
    """Associated with a user account."""

    # If we don't change on_delete, deleting a user will delete the associated person.
    user = models.OneToOneField(User, related_name="person", on_delete=CASCADE)
    unsuccessful_login_attempts = IntegerField(default=0)
    account_locked = BooleanField(default=False)
    email_verified = BooleanField(default=False)
    subscribed = BooleanField(default=False)
    # verification_token = CharField(max_length=20, blank=True, null=True)
    previous_emails = TextField(default="", blank=True, null=True)  # JSON list
    # We use this token to verify the user's email address. We set it to null once the email is verified.
    email_verification_token = CharField(max_length=60, blank=True, null=True)

    def __str__(self):
        return f"Person. id: {self.id} User: {self.user.username}"

    class Meta:
        # ordering = ["-datetime"]
        pass

    def send_verification_email(self, request: HttpRequest):
        """Send an email asking the user to verify their email address."""
        # Note: I made this up as I went, and in a similar way to password reset token validation. It's
        # surprisingly hard to find information on this topic.

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        verification_url = (
            f"{request.scheme}://{request.get_host()}/verify-email/{uid}/{token}"
        )

        # Disabling click tracking is to stop Sendgrid from intercepting the links.
        email_body = f"""
           <h2>Welcome to Finance Monitor</h2>

           <p>Before using your account, please open <a href="{verification_url} clicktracking=off">this verification link</a>.</p>
           
           <a href="https://www.finance-monitor.com">Finance Monitor home</a>

           <p>If you have questions about Finance Monitor, or would like to contact us for
           any reason, reply to this email: <i>contact@finance-monitor.com</i></p>
           """

        send_mail(
            "Finance Monitor verification",
            "",
            "contact@finance-monitor.com",
            [self.user.email],
            fail_silently=False,
            html_message=email_body,
        )

        self.email_verification_token = token
        self.save()


class Institution(Model):
    # Both of these fields are provided by Plaid
    name = CharField(max_length=50)
    plaid_id = CharField(max_length=30, unique=True)

    def __str__(self):
        return f"Institution. Name: {self.name} Plaid ID: {self.plaid_id}"

    class Meta:
        ordering = ["name"]


# todo: Personal and account-level snapshots over time, eg for generating graphs.


class FinancialAccount(Model):
    """Used by plaid; a Link to a financial institution."""

    person = ForeignKey(Person, related_name="accounts", on_delete=CASCADE)
    institution = ForeignKey(
        Institution,
        on_delete=SET_NULL,
        related_name="institutions",
        blank=True,
        null=True,
    )
    # A user-entered nickname for the account.
    name = CharField(max_length=100, blank=True)
    # todo: nullable if it expires etc.
    # access_token and `item_id` are retrieved from Plaid as part of the token exchange procedure.
    # Lengths we've seen in initial tests are around 40-50.
    access_token = CharField(max_length=100)
    item_id = CharField(max_length=100)
    # todo: Account types associated with this institution/account. Checking, 401k etc.
    # todo: Check the metadata for this A/R.
    last_refreshed = DateTimeField()
    # Recurring can be refreshed at a lower rate.
    last_refreshed_recurring = DateTimeField()
    last_refreshed_successfully = DateTimeField()
    # The cursor is used with the `/transactions/sync` endpoint, to know the latest data loaded.
    # Generally initialized to null, but has a value after. It is encoded in base64, and has a max length of 256 characters.
    # It appears that None fails for the Python Plaid API, eg at init, but an empty string works.
    # plaid_cursor = CharField(max_length=256, null=True, blank=True)
    plaid_cursor = CharField(max_length=256, default="", blank=True)

    # todo: Unique together with person, institution, or can we allow multiples?

    def __str__(self):
        return f"Account. Person: {self.person} Inst: {self.institution.name}"

    class Meta:
        unique_together = ["person", "institution"]
        ordering = ["name"]


class SubAccount(Model):
    """These are the linked, or manually-added accounts."""

    # This is similar to Transaction: If Account is null, person must have a value. This is for
    # manual transactions.
    account = ForeignKey(
        FinancialAccount,
        related_name="sub_accounts",
        null=True,
        blank=True,
        on_delete=SET_NULL,
    )
    person = ForeignKey(
        Person,
        related_name="subaccounts_manual",
        null=True,
        blank=True,
        on_delete=SET_NULL,
    )
    plaid_id = CharField(max_length=100, blank=True, null=True)
    plaid_id_persistent = CharField(max_length=100, blank=True, null=True)
    name = CharField(max_length=50)
    name_official = CharField(max_length=100, default="", null=True, blank=True)
    nickname = CharField(max_length=30, default="", null=True, blank=True)
    type = IntegerField(choices=AccountType.choices())
    sub_type = IntegerField(choices=SubAccountType.choices())
    iso_currency_code = CharField(max_length=5)
    # unofficial currency code is also available
    available = FloatField(blank=True, null=True)
    current = FloatField(default=0)
    limit = FloatField(blank=True, null=True)
    # Lets the user mark the account as ignored by the program.
    ignored = BooleanField(default=False)
    # todo: Mask?

    def serialize(self) -> Dict[str, str]:
        """For use in the web page."""

        pos_val = self.current > 0.0

        # Invert the value if a negative account type.
        # if AccountType(self.type) in [AccountType.LOAN, AccountType.CREDIT]:
        #     pos_val = not pos_val

        if SubAccountType(self.sub_type) in [
            SubAccountType.DEBIT_CARD,
            SubAccountType.CREDIT_CARD,
            SubAccountType.STUDENT,
            SubAccountType.MORTGAGE,
        ]:
            pos_val = not pos_val

        if self.account is not None:
            institution = self.account.institution.name
        else:
            institution = ""

        return {
            "id": self.id,
            "institution": institution,
            "name": self.name,
            "name_official": self.name_official if self.name_official else "",
            "nickname": self.nickname if self.nickname else "",
            "type": self.type,
            "sub_type": self.sub_type,
            "iso_currency_code": self.iso_currency_code,
            # todo: Consider a "name_display" that is based on if nick, and name_official are avail.
            # "current": f"{self.current:,.0f}",
            "current": self.current if self.current else 0.0,
            "ignored": json.dumps(self.ignored),
            "manual": self.person is not None,
            # Note Use current_val if handling this in JS vice template
            # "current_val": self.current,
            # "current_class": "tran-pos" if pos_val else "tran-neg",
        }

    def __str__(self):
        return f"Sub account. {self.name}, ({self.nickname}), {self.name_official}, {self.type}, Current: {self.current}, {self.iso_currency_code}"

    class Meta:
        ordering = ["name"]
        unique_together = [["account", "plaid_id"], ["account", "name", "name_official"]]


class Transaction(Model):
    # Note that Plaid associates this with a primary account, vice sub account.
    # account can be blank or null, if the transaction is imported, or manual.
    # todo: Allow the user to assign this to an account.
    # todo: Subaccount?
    account = ForeignKey(
        FinancialAccount,
        related_name="transactions",
        null=True,
        blank=True,
        on_delete=SET_NULL,
    )
    # We use Person for imports, and manually-added transactions.
    person = ForeignKey(
        Person,
        related_name="transactions_without_account",
        null=True,
        blank=True,
        on_delete=SET_NULL,
    )
    institution_name = CharField(
        max_length=100
    )  # In case the transaction is disconnected from an account.
    # We generally have 1-2 categories.
    # JSONField here allows for filtering by category

    # todo: Deprecate categories. Ie remove it once you have `category` in everything.
    # categories = JSONField()  # List of category enums, eg [0, 2]
    category = IntegerField(choices=TransactionCategory.choices())
    amount = FloatField()
    description = TextField()
    date = DateField()  # It appears we don't have datetimes available from plaid
    # Datetime seems generally missing from Plaid, despite it being more useful.
    datetime = DateTimeField(null=True, blank=True)
    plaid_id = CharField(max_length=100, null=True, blank=True)
    currency_code = CharField(max_length=5)  # ISO, eg USD
    pending = BooleanField(default=False)
    # Ie, entered by the user.
    notes = CharField(max_length=200, default="", blank=True, null=True)
    # todo: Cache these image URLs somewhere, then use a numeric identifier. Also, host them locally.
    logo_url = CharField(max_length=100, default="", blank=True, null=True)
    plaid_category_icon_url = CharField(
        max_length=100, default="", blank=True, null=True
    )
    # We allow the user to highlight transactions.
    highlighted = BooleanField(default=False)

    def serialize(self) -> Dict[str, str]:
        """For use in the web page."""

        # try:
        #     cats = [TransactionCategory(cat) for cat in self.categories]
        # except JSONDecodeError as e:
        #     print("Problem decoding categories during serialization", self.categories)
        #     cats = [TransactionCategory.UNCATEGORIZED]

        # cats = cleanup_categories(cats)

        # Only display the year if not the present one.
        # todo: Not using DT at all, for now. It seems to vary by merchant if its present
        if self.date.year == date.today().year:
            # if self.datetime is not None:
            #     date_display = self.datetime.strftime("%m/%d %H:%M")
            # else:
            date_display = self.date.strftime("%m/%d")
        else:
            # if self.datetime is not None:
            #     date_display = self.datetime.strftime("%m/%d%y %H:%M")
            # else:
            date_display = self.date.strftime("%m/%d/%y")

        description = self.description

        # todo: Modify to serialize values vice displayl.
        return {
            "id": self.id,  # DB primary key.
            "category": self.category,
            "description": description,
            "notes": self.notes if self.notes else "",
            "amount": self.amount,
            # todo: DO we want this?
            "amount_class": (
                "tran-pos" if self.amount > 0.0 else "tran-neg"
            ),  # eg to color green or red.
            "date": self.date.isoformat(),
            "date_display": date_display,
            "logo_url": self.logo_url if self.logo_url else "",
            "pending": self.pending,
            "highlighted": self.highlighted,
            "institution_name": self.institution_name,
            "currency_code": self.currency_code,
        }

    def __str__(self):
        return (
            f"Transaction. Id: {self.id}, {self.description}, {self.institution_name}, Amount: {self.amount}, date: {self.date}"
        )

    class Meta:
        ordering = ["-date"]
        # Unique together here prevents duplicates, eg from importing a file multiple times.
        # How does unique together work with float?

        # todo: This will falsely prevent multiple transactions on the same day of the same descrip and amount.
        unique_together = [
            ["date", "description", "amount", "account"],
            ["date", "description", "amount", "person"],
        ]


class SnapshotAccount(Model):
    account = ForeignKey(
        SubAccount, related_name="snapshots", on_delete=SET_NULL, blank=True, null=True
    )
    # Used if the account gets deleted etc.
    account_name = CharField(max_length=30)
    dt = DateTimeField()
    value = FloatField()

    def __str__(self):
        return f"Value snapshot. {self.account}, {self.dt}: {self.value}"


class SnapshotPerson(Model):
    person = ForeignKey(Person, related_name="snapshots", on_delete=CASCADE)
    dt = DateTimeField()
    value = FloatField()

    def __str__(self):
        return f"Value snapshot. {self.person}, {self.dt}: {self.value}"


class CategoryCustom(Model):
    person = ForeignKey(Person, related_name="custom_cats", on_delete=CASCADE)
    name = CharField(max_length=30)

    def __str__(self):
        return f"Custom cat. {self.person}, {self.name}"

    def serialize(self) -> Dict[str, str]:
        return {
            "id": self.id,  # DB primary key.
            "name": self.name,
        }


class RecurringTransaction(Model):
    account = ForeignKey(SubAccount, related_name="recurring", on_delete=CASCADE)
    direction = CharField(choices=RecurringDirection.choices())
    average_amount = FloatField()
    last_amount = FloatField()
    first_date = DateField()
    last_date = DateField()
    description = CharField(max_length=50)
    merchant_name = CharField(max_length=50)
    is_active = BooleanField(default=True)
    status = CharField(max_length=15)  # Plaid string. Use an enum or remove A/R
    # todo: JSONField A/R, like Transaction.
    # categories = TextField()  # List of category enums, eg [0, 2]
    category = IntegerField(choices=TransactionCategory.choices())
    # User notes
    notes = TextField()

    class Meta:
        ordering = ["-last_date"]
        # unique_together = ["account", "description", ""]

    def __str__(self):
        return f"Recurring {self.account}, {self.average_amount}, Last: {self.last_date}, {self.description}"

    def serialize(self) -> Dict[str, str]:
        # todo: DRY with tran serializer

        #
        # # Only display the year if not the present one.
        # if self.date.year == date.today().year:
        #     if self.datetime is not None:
        #         date_display = self.datetime.strftime("%m/%d %H:%M")
        #     else:
        #         date_display = self.date.strftime("%m/%d")
        # else:
        #     if self.datetime is not None:
        #         date_display = self.datetime.strftime("%m/%d%y %H:%M")
        #     else:
        #         date_display = self.date.strftime("%m/%d/%y")

        # todo: Modify to serialize values vice displayl.
        cat = TransactionCategory(self.category)

        return {
            "id": self.id,  # DB primary key.
            "institution": self.account.account.institution.name,
            "direction": self.direction,
            "average_amount": self.average_amount,
            "last_amount": self.last_amount,
            "first_date": self.first_date.isoformat(),
            "last_date": self.last_date.isoformat(),
            "description": self.description,
            "merchant_name": self.merchant_name,
            "is_active": json.dumps(self.is_active),
            "status": self.status,
            "categories": self.category,
            "category_icon": cat.to_icon(),
            "categories_text": cat.to_str(),
            "notes": self.notes,
        }

    def cat_display(self) -> str:
        """Since we don't apply the serializer as we do with transactions on the dash, apply the
        post-processing category code here. (DRY from serialize)"""
        cat = TransactionCategory(self.category)
        return cat.to_icon() + cat.to_str()


class CategoryRule(Model):
    """Map transaction descriptions to categories automatically, by user selection."""

    person = ForeignKey(Person, related_name="category_rules", on_delete=CASCADE)
    description = CharField(max_length=100)
    category = IntegerField(choices=TransactionCategory.choices())

    class Meta:
        ordering = ["description"]
        unique_together = ["person", "description"]

    def __str__(self):
        return f"Category rule. Person: {self.person}, {self.description} => {self.category}"
