# Misc / utility functions
from main.models import AccountType, FinancialAccount


def update_net_worth(net_worth: float, account: FinancialAccount) -> None:
    # Update net worth in place, based on this account's sub-accounts.
    for sub_acc_model in account.sub_accounts.all():
        if sub_acc_model.current is not None:
            sign = 1

            if AccountType(sub_acc_model.type) in [
                AccountType.LOAN,
                AccountType.CREDIT,
            ]:
                sign *= -1

            net_worth += sign * sub_acc_model.current

