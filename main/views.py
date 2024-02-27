from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from main.models import Account, Transaction, Institution, Person


# @login_required

# Create your views here.
def home(request: HttpRequest) -> HttpResponse:
    # return HttpResponse(
    #     "Successfully synchronized user accounts with people in your squadron."
    # )

    inst_test = Institution(
        name="My bank"
    )

    person_test = Person(

    )

    account_test = Account(
        name="My account 1",
        institution=inst_test,
        person=person_test,
    )

    context = {
        "accounts": [
            account_test
        ],
        "transactions": [
            Transaction(
                account=account_test,
                amount=-70.50,
                description="Groceries",
            )
        ]
    }

    return render(request, "index.html", context)
