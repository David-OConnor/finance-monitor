from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django import forms


from . import models


@admin.register(models.Person)
class PersonAdmin(ModelAdmin):
    list_display = ("user",)


@admin.register(models.Institution)
class InstitionAdmin(ModelAdmin):
    list_display = ("name", "plaid_id")


@admin.register(models.FinancialAccount)
class FinancialAccountAdmin(ModelAdmin):
    list_display = ("person", "institution", "item_id", "name", "access_token")
    search_fields = ("item_id", "name")


@admin.register(models.SubAccount)
class SubAccountAdmin(ModelAdmin):
    list_display = (
        "account",
        "name",
        "plaid_id",
        "name_official",
        "type",
        "sub_type",
        "available",
        "current",
        "limit",
        "ignored",
    )
    search = ("name", "plaid_id", "name_official")


@admin.register(models.Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ("description", "account", "amount", "category", "plaid_id", "date")
    search_fields = ("description", "notes", "plaid_id")


@admin.register(models.RecurringTransaction)
class RecurringAdmin(ModelAdmin):
    list_display = ("description", "account", "last_date", "average_amount")


@admin.register(models.SnapshotAccount)
class SnapAccountAdmin(ModelAdmin):
    list_display = ("account", "dt", "value")


@admin.register(models.SnapshotPerson)
class SnapPersonAdmin(ModelAdmin):
    list_display = ("person", "dt", "value")
