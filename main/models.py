from enum import Enum

from django.db import models
from django.contrib.auth.models import Group, User

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
)


def enum_choices(cls):
    """Required to make Python enums work with Django integer fields"""

    @classmethod
    def choices(cls_):
        return [(key.value, key.name) for key in cls_]

    cls.choices = choices
    return cls


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

        print("Fallthrough in parsing account type: ", s)
        return cls.DEPOSITORY


@enum_choices
class SubAccountType(Enum):
    """These are types as reported by Plaid"""

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
        if "ira" == s :
            return cls.IRA

        print("Fallthrough in parsing sub account type: ", s)
        return cls.CHECKING


class Person(Model):
    # If we don't change on_delete, deleting a user will delete the associated person.
    user = models.OneToOneField(User, related_name="person", on_delete=CASCADE)
    unsuccessful_login_attempts = IntegerField(default=0)
    account_locked = BooleanField(default=False)
    email_verified = BooleanField(default=False)

    def __str__(self):
        return f"Person. id: {self.id} User: {self.user.username}"

    class Meta:
        # ordering = ["-datetime"]
        pass


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
    person = ForeignKey(Person, related_name="accounts", on_delete=CASCADE)
    institution = ForeignKey(
        Institution, on_delete=CASCADE, related_name="institutions"
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
    # The cursor is used with the `/transactions/sync` endpoint, to know the latest data loaded.
    # Generally initialized to null, but has a value after. It is encoded in base64, and has a max length of 256 characters.
    # It appears that None fails for the Python Plaid API, eg at init, but an empty string works.
    # plaid_cursor = CharField(max_length=256, null=True, blank=True)
    plaid_cursor = CharField(max_length=256, default="", blank=True)

    # todo: Unique together with person, institution, or can we allow multiples?

    def __str__(self):
        return f"Account. Person: {self.person} Inst: {self.institution.name}. Nickname: {self.name}"

    class Meta:
        ordering = ["name"]


class SubAccount(Model):
    account = ForeignKey(
        FinancialAccount, related_name="sub_accounts", on_delete=CASCADE
    )
    plaid_id = CharField(max_length=100)
    plaid_id_persistent = CharField(max_length=100, blank=True, null=True)
    name = CharField(max_length=50)
    name_official = CharField(max_length=100, null=True, blank=True)
    type = IntegerField(choices=AccountType.choices())
    sub_type = IntegerField(choices=SubAccountType.choices())
    iso_currency_code = CharField(max_length=5)
    # unofficial currency code is also available
    available = FloatField(blank=True, null=True)
    current = FloatField(blank=True, null=True)
    limit = FloatField(blank=True, null=True)
    # Lets the user mark the account as ignored by the program.
    ignored = BooleanField(default=False)
    # todo: Mask?

    def __str__(self):
        return f"Sub account. {self.name}, {self.name_official}, {self.type}, Current: {self.current}"

    class Meta:
        ordering = ["name"]


class Transaction(Model):
    # Note that Plaid associates this with a primary account, vice sub account.
    # account can be blank or null, if the transaction is imported, or manual.
    # todo: Allow the user to assign this to an account.
    account = ForeignKey(
        FinancialAccount, related_name="transactions", null=True, blank=True, on_delete=SET_NULL
    )
    # We use Person for imports, and manually-added transactions.
    person = ForeignKey(
        Person, related_name="transactions_without_account", null=True, blank=True, on_delete=SET_NULL
    )
    # We generally have 1-2 categories.
    # todo: Consider just u sing a Textfield here; you're not using the wrapping json object
    categories = TextField()  # List of category enums, eg [0, 2]
    amount = FloatField()
    description = TextField()
    date = DateField()  # It appears we don't have datetimes available from plaid
    # Datetime seems generally missing from Plaid, despite it being more useful.
    datetime = DateTimeField(null=True, blank=True)
    plaid_id = CharField(max_length=100)
    currency_code = CharField(max_length=5)  # ISO, eg USD
    pending = BooleanField(default=False)
    # Ie, entered by the user.
    notes = CharField(max_length=200, default="")

    def __str__(self):
        return (
            f"Transaction. {self.description} Amount: {self.amount}, date: {self.date}"
        )

    class Meta:
        ordering = ["-date"]
        # Unique together here prevents duplicates, eg from importing a file multiple times.
        # How does unique together work with float?
        unique_together = ["date", "description", "amount"]

# todo: More refined snapshot, including all accounts.

class NetWorthSnapshot(Model):
    person = ForeignKey(Person, related_name="net_worth_snapshots", on_delete=CASCADE)
    datetime = DateTimeField()
    value = FloatField()
