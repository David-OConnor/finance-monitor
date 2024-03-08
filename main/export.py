# This module handles imports and exports from CSV. We use Mint's format.
import csv
import json
from dataclasses import dataclass
import datetime
from io import StringIO, TextIOWrapper
from typing import List, Iterable

from django.db import OperationalError, IntegrityError
from django.http import HttpResponse

from . import transaction_cats
from .models import Transaction, Person
from .transaction_cats import TransactionCategory


def import_csv_mint(csv_data: TextIOWrapper, person: Person) -> None:
    """Parse CSV from mint; update the database accordingly."""
    # lines = csv_data.strip().split('\n')
    reader = csv.reader(csv_data)
    # reader = csv.reader(csv_file, escapechar='\\')

    # Skip the header
    next(reader)

    # categories = JSONField()  # List of category enums, eg [0, 2]
    # amount = FloatField()

    # todo: We currently leave out the labels field, and original description.
    # categoory, tra
    # Iterate over the CSV rows and create Transaction objects
    for row in reader:
        amount = float(row[3])
        # transaction type. Mint always reports positive values, then deliniates as "credit" or "debit".
        if row[4] == "debit":
            amount *= -1

        # todo: Error handlign in this function in general.

        # Convert the date to iso format.
        d = datetime.datetime.strptime(row[0], "%m/%d/%Y")
        date = d.date().isoformat()

        description = row[1]

        categories = [TransactionCategory.from_str(row[5])]
        categories = transaction_cats.category_override(description, categories)

        transaction = Transaction(
            # Associate this transaction directly with the person, vice the account.
            person=person,
            # Exactly one category, including "Uncategorized" is reported by Mint
            categories=json.dumps([c.value for c in categories]),
            amount=amount,
            description=description,
            date=date,
            currency_code="USD",  # todo: Allow the user to select this A/R.
            notes=row[8],
        )
        try:
            transaction.save()
        except OperationalError:
            print("Unable to save this transaction: ", transaction)
        except IntegrityError:
            # Eg a duplicate.
            pass


def export_csv(transactions: Iterable[Transaction], output: HttpResponse) -> str:
    """Export a CSV, using Mint's format."""
    writer = csv.writer(output)

    # writer = csv.writer(response, escapechar='\\')

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

        categories = [
            TransactionCategory(cat).to_str()
            for cat in json.loads(transaction.categories)
        ]
        category = ", ".join(categories)

        # Writing the row according to Mint's CSV format
        # Assuming `transaction.description` maps to both "Description" and "Original Description" as per Mint's format
        writer.writerow(
            [
                transaction.date,
                transaction.description,
                "",  # "Original description"
                amount,
                transaction_type,
                category,
                # todo: Sub-account info?
                transaction.account.institution.name,
                "",  # Labels are skipped as per the provided code snippet
                transaction.notes,
            ]
        )

    # Return the CSV data as a string
    return output.getvalue()
