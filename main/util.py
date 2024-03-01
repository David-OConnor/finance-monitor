# Misc / utility functions

from main.models import AccountType, FinancialAccount


def update_net_worth(net_worth: float, account: FinancialAccount) -> float:
    # Update net worth in place, based on this account's sub-accounts.
    # In Python, this means we must return the new value
    for sub_acc_model in account.sub_accounts.all():
        if not sub_acc_model.ignored and sub_acc_model.current is not None:
            sign = 1

            if AccountType(sub_acc_model.type) in [
                AccountType.LOAN,
                AccountType.CREDIT,
            ]:
                sign *= -1

            net_worth += sign * sub_acc_model.current
    return net_worth

