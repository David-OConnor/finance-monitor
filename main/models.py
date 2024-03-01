from enum import Enum

from django.db import models
from django.contrib.auth.models import Group, User

from django.db.models import (
    SET_NULL,
    CASCADE,
    JSONField,
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

        print("Fallthrough in parsing sub account type: ", s)
        return cls.CHECKING


@enum_choices
class TransactionCategory(Enum):
    """These are types as reported by Plaid"""

    FOOD_AND_DRINK = 0
    RESTAURANTS = 1
    TRAVEL = 3
    AIRLINES_AND_AVIATION_SERVICES = 4
    RECREATION = 5
    GYMS_AND_FITNESS_CENTERS = 6
    TRANSFER = 7
    DEPOSIT = 8
    PAYROLL = 9
    CREDIT_CARD = 10
    FAST_FOOD = 11  # todo: Move up

    @classmethod
    def from_str(cls, s: str) -> "TransactionCategory":
        s = s.lower()

        if "food and" in s:
            return cls.FOOD_AND_DRINK
        if "restau" in s:
            return cls.RESTAURANTS
        if "travel" in s:
            return cls.TRAVEL
        if "airlines" in s:
            return cls.AIRLINES_AND_AVIATION_SERVICES
        if "recrea" in s:
            return cls.RECREATION
        if "gyms" in s:
            return cls.GYMS_AND_FITNESS_CENTERS
        if "transfer" in s:
            return cls.TRANSFER
        if "deposit" in s:
            return cls.DEPOSIT
        if "payroll" in s:
            return cls.PAYROLL
        if "credit c" in s:
            return cls.CREDIT_CARD
        if "fast food" in s:
            return cls.FAST_FOOD

        print("Fallthrough in parsing transaction category: ", s)
        return cls.FOOD_AND_DRINK


class Person(Model):
    # If we don't change on_delete, deleting a user will delete the associated person.
    user = models.OneToOneField(
        User, related_name="person", on_delete=CASCADE
    )
    unsuccessful_login_attempts = IntegerField(default=0)
    account_locked = BooleanField(default=False)

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
    # todo: Mask?

    def __str__(self):
        return f"Sub account. {self.name}, {self.name_official}, {self.type}, Current: {self.current}"

    class Meta:
        ordering = ["name"]


class Transaction(Model):
    # todo: SubAccout as required, but I'm not sure how using Plaid's API atm.
    # account = ForeignKey(SubAccount, related_name="transactions", on_delete=CASCADE)
    account = ForeignKey(FinancialAccount, related_name="transactions", on_delete=CASCADE)
    # We generally have 1-2 categories.
    categories = JSONField()  # List of category enums, eg [0, 2]
    amount = FloatField()
    description = TextField()
    date = DateField()  # It appears we don't have datetimes available from plaid
    plaid_id = CharField(max_length=100)

    def __str__(self):
        return f"Transaction. {self.description} Amount: {self.amount}, date: {self.date}"

    class Meta:
        ordering = ["date"]
