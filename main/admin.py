from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django import forms


from . import models


@admin.register(models.Person)
class PersonAdmin(ModelAdmin):
    # list_display = (""pause_orders", "restock_messag"e")
    pass


@admin.register(models.Institution)
class InstitionAdmin(ModelAdmin):
    list_display = ("name", "plaid_id")


@admin.register(models.FinancialAccount)
class FinancialAccountAdmin(ModelAdmin):
    list_display = ("name", "item_id", "access_token")


@admin.register(models.SubAccount)
class SubAccountAdmin(ModelAdmin):
    list_display = ("name", "plaid_id", "name_official", "type", "sub_type", "available", "current", "limit")


@admin.register(models.Transaction)
class TransactionAdmin(ModelAdmin):
    # list_display = ("account__name", "amount", "description", "dt")
    list_display = ("amount", "description", "dt")
