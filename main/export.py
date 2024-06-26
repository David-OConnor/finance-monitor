# This module handles imports and exports from CSV. We use Mint's format.
import csv
import json
from dataclasses import dataclass
import datetime
from io import StringIO, TextIOWrapper
from typing import List, Iterable

from django.db import OperationalError, IntegrityError
from django.db.utils import DataError
from django.http import HttpResponse

from . import transaction_cats
from .models import Transaction, Person
from .transaction_cats import TransactionCategory
from .util import send_debug_email


def import_csv_mint(csv_data: TextIOWrapper, person: Person) -> None:
    """Parse CSV from mint; update the database accordingly."""
    reader = csv.reader(csv_data)

    # Skip the header
    try:
        next(reader)
    except UnicodeDecodeError:
        msg = f"UTF-8 import failed; trying ISO."
        print(msg)
        send_debug_email(msg)

        reader = csv.reader(csv_data, encoding="ISO-8859-1")
        try:
            next(reader)
        except UnicodeDecodeError:
            msg = f"Error decoding CSV; both UTF-8 and ISO. \n{csv_data}"
            print(msg)
            send_debug_email(msg)
            return None

    # categories = JSONField()  # List of category enums, eg [0, 2]
    # amount = FloatField()

    # todo: We currently leave out the labels field, and original description.
    # categoory, tra
    # Iterate over the CSV rows and create Transaction objects

    rules = person.category_rules.all()

    for row in reader:
        try:
            amount = float(row[3])
        except ValueError:
            print("Error: Invalid amount. Probably wrong spreadsheet format.")
            amount = 0.0

        # transaction type. Mint always reports positive values, then deliniates as "credit" or "debit".
        if row[4] == "debit":
            amount *= -1

        # todo: Error handlign in this function in general.

        # Convert the date to iso format.
        d = datetime.datetime.strptime(row[0], "%m/%d/%Y")
        date = d.date().isoformat()

        description = row[1]

        category = TransactionCategory.from_str(row[5])
        category = transaction_cats.category_override(description, category, rules)

        transaction = Transaction(
            # Associate this transaction directly with the person, vice the account.
            person=person,
            # Exactly one category, including "Uncategorized" is reported by Mint
            category=category.value,
            amount=amount,
            description=description,
            date=date,
            currency_code="USD",  # todo: Allow the user to select this A/R.
            notes=row[8],
            institution_name=row[6],
            # todo: Merchant?
        )
        try:
            transaction.save()
        except OperationalError as e:
            print(
                "Unable to save this transaction (Operational error): ", e, transaction
            )
        except DataError as e:
            print("Unable to save this transaction (Data error): ", e, transaction)
        except IntegrityError:
            # Eg a duplicate.
            pass


def export_csv(transactions: Iterable[Transaction], output: HttpResponse) -> str:
    """Export a CSV, using Mint's format, augmented with extra fields as required."""
    writer = csv.writer(output)

    # Write the header
    writer.writerow(
        [
            "Date",
            "Description",
            "Original Description",
            "Amount",
            "Transaction Type",
            "Category",
            "Account Name",
            "Labels",
            "Notes",
            "Merchant",
        ]
    )

    for transaction in transactions:
        # Convert the amount to a positive number and determine the transaction type
        if transaction.amount < 0:
            amount = -transaction.amount
            transaction_type = "debit"
        else:
            amount = transaction.amount
            transaction_type = "credit"

        # Writing the row according to Mint's CSV format
        # Assuming `transaction.description` maps to both "Description" and "Original Description" as per Mint's format

        writer.writerow(
            [
                transaction.date,
                transaction.description,
                "",  # "Original description"
                amount,
                transaction_type,
                TransactionCategory(transaction.category).to_str(),
                # todo: Sub-account info?
                transaction.institution_name,
                "",  # Labels are skipped as per the provided code snippet
                transaction.notes,
                transaction.merchant,
            ]
        )

    # Return the CSV data as a string
    return output.getvalue()
