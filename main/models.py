from enum import Enum

from django.db import models

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


class Person(Model):
    # todo: Put this in.
    # user = models.OneToOneField(
    #     User, null=True, blank=True, related_name="person", on_delete=SET_NULL
    # )
    pass

    def __str__(self):
        return f"Person. id: {self.id}"

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
    person = ForeignKey(Person, on_delete=CASCADE, related_name="accounts")
    institution = ForeignKey(Institution, on_delete=CASCADE, related_name="institutions")
    # A user-entered nickname for the account.
    name = CharField(max_length=50)
    # todo: nullable if it expires etc.
    # access_token and `item_id` are retrieved from Plaid as part of the token exchange procedure.
    # Lengths we've seen in initial tests are around 40-50.
    access_token = CharField(max_length=100)
    item_id = CharField(max_length=100)
    # todo: Account types associated with this institution/account. Checking, 401k etc.
    # todo: Check the metadata for this A/R.
    last_refreshed = DateTimeField()

    # todo: Unique together with person, institution, or can we allow multiples?

    def __str__(self):
        return f"Account. Person: {self.person} Inst: {self.institution.name}. Nickname: {self.name}"

    class Meta:
        ordering = ["name"]


class Transaction(Model):
    account = ForeignKey(FinancialAccount, related_name="transactions", on_delete=CASCADE)
    amount = FloatField()
    description = TextField()
    dt = DateTimeField()

    def __str__(self):
        return f"Institution. Name: {self.name} Plaid ID: {self.plaid_id}"

    class Meta:
        ordering = ["dt"]