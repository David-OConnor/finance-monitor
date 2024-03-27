# A dedicated file for transaction categories, due to its size.
from enum import Enum
from typing import List, Iterable

from django.core.mail import send_mail

from wallet import settings


# todo: C+P from main.models due ot circular import concern
def enum_choices(cls):
    """Required to make Python enums work with Django integer fields"""

    @classmethod
    def choices(cls_):
        return [(key.value, key.name) for key in cls_]

    cls.choices = choices
    return cls


class TransactionCategoryDiscret(Enum):
    """Our broadest grouping"""

    DISCRETIONARY = 0
    # Housing, bills etc
    NON_DISCRETIONARY = 1


class TransactionCategoryGeneral(Enum):
    """We group each category into one of these more general categories"""

    UNCATEGORIZED = -1
    TRAVEL = 0
    CONSUMER_PRODUCTS = 1
    BUSINESS = 2
    FOOD_AND_DRINK = 3

    @classmethod
    def from_cat(cls, cat: "TransactionCategory") -> "TransactionCategoryGeneral":
        if cat == TransactionCategory.UNCATEGORIZED:
            return cls.UNCATEGORIZED
        if cat in [
            TransactionCategory.TRAVEL,
            TransactionCategory.AIRLINES_AND_AVIATION_SERVICES,
        ]:
            return cls.TRAVEL
        if cat in [CONSUMER_PRODUCTS]:
            return cls.CONSUMER_PRODUCTS
        if cat in [CONSUMER_PRODUCTS]:
            return cls.BUSINESS
        if cat in [
            TransactionCategory.GROCERIES,
            TransactionCategory.ALCOHOL,
            TransactionCategory.RESTAURANTS,
            TransactionCategory.COFFEE_SHOP,
        ]:
            return cls.FOOD_AND_DRINK


@enum_choices
class TransactionCategory(Enum):
    """These are types as reported by Plaid"""

    UNCATEGORIZED = -1
    SOFTWARE_SUBSCRIPTIONS = 2
    GROCERIES = 0
    RESTAURANTS = 1
    TRAVEL = 3
    AIRLINES_AND_AVIATION_SERVICES = 4
    RECREATION = 5
    GYMS_AND_FITNESS_CENTERS = 6
    TRANSFER = 7
    DEPOSIT = 8
    INCOME = 9
    CREDIT_CARD = 10
    FAST_FOOD = 11  # todo: Move up
    DEBIT = 12
    SHOPS = 13
    PAYMENT = 14
    COFFEE_SHOP = 15
    TAXI = 16
    SPORTING_GOODS = 17
    ELECTRONICS = 18
    PETS = 19
    CHILDREN = 20
    MORTGAGE_AND_RENT = 21
    CAR = 22
    HOME_AND_GARDEN = 23
    MEDICAL = 24
    ENTERTAINMENT = 25
    BILLS_AND_UTILITIES = 26
    INVESTMENTS = 27
    FEES = 28
    TAXES = 29
    BUSINESS_SERVICES = 30
    CASH_AND_CHECKS = 31
    GIFTS = 32
    EDUCATION = 33
    ALCOHOL = 34
    HEALTH_AND_PERSONAL_CARE = 35

    @classmethod
    def from_str(cls, s: str) -> "TransactionCategory":
        """A little loose. We currently use it for both Plaid, and mint."""
        s = s.lower()

        if "uncategorized" == s or "misc expenses" in s:
            return cls.UNCATEGORIZED
        if "food" in s or "grocer" in s:
            return cls.GROCERIES
        if "software subscription" in s or "digital purchase" in s:
            return cls.SOFTWARE_SUBSCRIPTIONS
        if "restau" in s:
            return cls.RESTAURANTS
        if "travel" in s or "lodging" in s:
            return cls.TRAVEL
        if "airlines" in s:
            return cls.AIRLINES_AND_AVIATION_SERVICES
        if "recrea" in s:
            return cls.RECREATION
        if "gym" in s or "fitness" in s or "health" in s:
            return cls.GYMS_AND_FITNESS_CENTERS
        if "transfer" in s:
            return cls.TRANSFER
        if "deposit" in s:
            return cls.DEPOSIT
        if "payroll" in s or "income" in s:
            return cls.INCOME
        if "credit" in s:
            return cls.CREDIT_CARD
        if "fast food" in s:
            return cls.FAST_FOOD
        if "debit" in s:
            return cls.DEBIT
        if (
            "shop" in s
            or "bookstore" in s
            or "hardware" in s
            or "clothing" in s
            or "merchandise" in s
        ):
            return cls.SHOPS
        if "payment" == s:
            return cls.PAYMENT
        if "coffee shop" == s:
            return cls.COFFEE_SHOP
        if "taxi" in s:
            return cls.TAXI
        if "sporting" in s:
            return cls.SPORTING_GOODS
        if "electron" in s or "video games" in s or "computer" in s or "software" in s:
            return cls.ELECTRONICS
        if "pet" in s:
            return cls.PETS
        if "child" in s or "kid" in s:
            return cls.CHILDREN
        if "mortgate" in s or "rent" in s:
            return cls.MORTGAGE_AND_RENT
        if "car" in s or "auto" in s or "gas station" in s:
            return cls.CAR
        if "home" in s or "garden" in s:
            return cls.HOME_AND_GARDEN
        if "medical" in s:
            return cls.MEDICAL
        if "entertainment" in s or "dance" in s or "music" in s:
            return cls.ENTERTAINMENT
        if "bill" in s or "utility" in s or "telecommunication serv" in s:
            return cls.BILLS_AND_UTILITIES
        if "invest" in s:
            return cls.INVESTMENTS
        if "fees" in s or "interest charge" in s:
            return cls.FEES
        if "taxes" in s:
            return cls.TAXES
        # todo: Sort out "service"
        if "business" in s or "shipping" in s or "service" in s:
            return cls.BUSINESS_SERVICES
        if "cash" in s or "check" in s:
            return cls.CASH_AND_CHECKS
        if "gift" in s or "donation" in s:
            return cls.GIFTS
        if "education" in s:
            return cls.EDUCATION
        if "alcohol" in s or "bar" in s:
            return cls.ALCOHOL
        if "health" in s or "personal care" in s:
            return cls.HEALTH_AND_PERSONAL_CARE
        if "interest" in s:
            return cls.FEES
        if "third party" in s:
            return cls.UNCATEGORIZED  # todo
        if "paypal" in s:
            return cls.SHOPS  # todo?
        if "insurance" in s:
            return cls.BILLS_AND_UTILITIES
        if "office supplies" in s:
            return cls.BUSINESS_SERVICES  # todo: Eh...
        if "hotels" in s:
            return cls.TRAVEL
        if "government departments" in s:
            return cls.BUSINESS_SERVICES  # todo Eh...
        if "community" in s:
            return cls.UNCATEGORIZED  # todo...

        print("Fallthrough in parsing transaction category: ", s)

        # Send an email, so we know and can add it.

        if settings.DEPLOYED:
            send_mail(
                "Finance Monitor error",
                "Fallthrough in parsing transaction category: " + s,
                "contact@finance-monitor.com",
                # todo: contact @FM, and my person emails are temp
                ["contact@finance-monitor.com"],
                fail_silently=False,
                html_message="",
            )

        return cls.UNCATEGORIZED

    def to_str(self) -> str:
        if self == TransactionCategory.UNCATEGORIZED:
            return "Uncategorized"
        if self == TransactionCategory.GROCERIES:
            return "Groceries"
        if self == TransactionCategory.SOFTWARE_SUBSCRIPTIONS:
            return "Software subscriptions"
        if self == TransactionCategory.RESTAURANTS:
            return "Restaurants"
        if self == TransactionCategory.TRAVEL:
            return "Travel"
        if self == TransactionCategory.AIRLINES_AND_AVIATION_SERVICES:
            return "Airlines"
        if self == TransactionCategory.RECREATION:
            return "Recreation"
        if self == TransactionCategory.GYMS_AND_FITNESS_CENTERS:
            return "Gyms"
        if self == TransactionCategory.TRANSFER:
            return "Transfer"
        if self == TransactionCategory.DEPOSIT:
            return "Deposit"
        if self == TransactionCategory.INCOME:
            return "Income"
        if self == TransactionCategory.CREDIT_CARD:
            return "Credit card"
        if self == TransactionCategory.FAST_FOOD:
            return "Fast food"
        if self == TransactionCategory.DEBIT:
            return "Debit"
        if self == TransactionCategory.SHOPS:
            return "Shops"
        if self == TransactionCategory.PAYMENT:
            return "Payment"
        if self == TransactionCategory.COFFEE_SHOP:
            return "Coffee shop"
        if self == TransactionCategory.TAXI:
            return "Taxi"
        if self == TransactionCategory.SPORTING_GOODS:
            return "Sporting goods"
        if self == TransactionCategory.ELECTRONICS:  # todo: Separate software cat?
            return "Electronics and software"
        if self == TransactionCategory.PETS:
            return "Pets"
        if self == TransactionCategory.CHILDREN:
            return "Children"
        if self == TransactionCategory.MORTGAGE_AND_RENT:
            return "Mortgage and rent"
        if self == TransactionCategory.CAR:
            return "Car"
        if self == TransactionCategory.HOME_AND_GARDEN:
            return "Home and garden"
        if self == TransactionCategory.MEDICAL:
            return "Medical"
        if self == TransactionCategory.ENTERTAINMENT:
            return "Entertainment"
        if self == TransactionCategory.BILLS_AND_UTILITIES:
            return "Bills and utilities"
        if self == TransactionCategory.INVESTMENTS:
            return "Investments"
        if self == TransactionCategory.FEES:
            return "Fees"
        if self == TransactionCategory.TAXES:
            return "Taxes"
        if self == TransactionCategory.BUSINESS_SERVICES:
            return "Business services"
        if self == TransactionCategory.CASH_AND_CHECKS:
            return "Cash and checks"
        if self == TransactionCategory.GIFTS:
            return "Gifts and donations"
        if self == TransactionCategory.EDUCATION:
            return "Education"
        if self == TransactionCategory.ALCOHOL:
            return "Alcohol and bars"
        if self == TransactionCategory.HEALTH_AND_PERSONAL_CARE:
            return "Health and personal care"

        print("Fallthrough on cat to string", self)
        return "Fallthrough"

    def to_icon(self) -> str:
        if self == TransactionCategory.UNCATEGORIZED:
            return "❓"
        if self == TransactionCategory.GROCERIES:
            return "🍎"
        if self == TransactionCategory.SOFTWARE_SUBSCRIPTIONS:
            return "📅"
        if self == TransactionCategory.RESTAURANTS:
            return "🍴"
        if self == TransactionCategory.TRAVEL:
            return "✈️"
        if self == TransactionCategory.AIRLINES_AND_AVIATION_SERVICES:
            return "✈️"
        if self == TransactionCategory.RECREATION:
            return "⛵"
        if self == TransactionCategory.GYMS_AND_FITNESS_CENTERS:
            return "🏋️"
        if self == TransactionCategory.TRANSFER:
            # return "💵 ➡️"
            return "💵"
        if self == TransactionCategory.DEPOSIT:
            # return "💵 ⬆️"
            return "💵"
        if self == TransactionCategory.INCOME:
            # return "💵 ⬆️"
            return "💵"
        if self == TransactionCategory.CREDIT_CARD:
            # return "💵 ⬇️"
            return "💵"
        if self == TransactionCategory.FAST_FOOD:
            return "🍔"
        if self == TransactionCategory.DEBIT:
            return "💵"
            # return "💵 ⬇️"
        if self == TransactionCategory.SHOPS:
            return "🛒"
        if self == TransactionCategory.PAYMENT:
            return "💵"
        if self == TransactionCategory.COFFEE_SHOP:
            return "☕"
        if self == TransactionCategory.TAXI:
            return "🚕"
        if self == TransactionCategory.SPORTING_GOODS:
            return "⚽"
        if self == TransactionCategory.ELECTRONICS:
            return "🔌"
        if self == TransactionCategory.PETS:
            return "🐕"
        if self == TransactionCategory.CHILDREN:
            return "🧒"
        if self == TransactionCategory.MORTGAGE_AND_RENT:
            return "🏠"
        if self == TransactionCategory.CAR:
            return "🚗"
        if self == TransactionCategory.HOME_AND_GARDEN:
            return "🏡"
        if self == TransactionCategory.MEDICAL:
            return "⚕️"
        if self == TransactionCategory.ENTERTAINMENT:
            return "🎥"
        if self == TransactionCategory.BILLS_AND_UTILITIES:
            return "⚡"
        if self == TransactionCategory.INVESTMENTS:
            return "📈"
        if self == TransactionCategory.FEES:
            return "💸"
        if self == TransactionCategory.TAXES:
            return "🏛️"
        if self == TransactionCategory.BUSINESS_SERVICES:
            return "📈"
        if self == TransactionCategory.CASH_AND_CHECKS:
            return "💵"
        if self == TransactionCategory.GIFTS:
            return "🎁"
        if self == TransactionCategory.EDUCATION:
            return "🎓"
        if self == TransactionCategory.ALCOHOL:
            return "🍺"
        if self == TransactionCategory.HEALTH_AND_PERSONAL_CARE:
            return "🛁"

        print("Fallthrough on cat to icon", self)
        return "Fallthrough"

    @classmethod
    def from_plaid(cls, cats_raw: List[str], descrip: str, rules: Iterable["CategoryRule"]) -> "TransactionCategory":
        if len(cats_raw):
            category = cleanup_categories(TransactionCategory.from_str(c) for c in cats_raw)[0]
        else:
            category = TransactionCategory.UNCATEGORIZED

        return category_override(
            descrip, category, rules
        )


# Statically set up all cat names, for use in filtering.
CAT_NAMES = []
for cat_val in range(-1, 35):
    CAT_NAMES.append(
        (cat_val, TransactionCategory(cat_val).to_str().lower())
    )

# A mapping of keywords to manual transactions
replacements = [
    ("coffee", TransactionCategory.COFFEE_SHOP),
    ("starbucks", TransactionCategory.COFFEE_SHOP),
    #
    ("jlcpcb", TransactionCategory.BUSINESS_SERVICES),
    ("squarespace", TransactionCategory.BUSINESS_SERVICES),
    ("github", TransactionCategory.BUSINESS_SERVICES),
    ("heroku", TransactionCategory.BUSINESS_SERVICES),
    ("domains", TransactionCategory.BUSINESS_SERVICES),
    ("gsuite", TransactionCategory.BUSINESS_SERVICES),
    ("pirate ship", TransactionCategory.BUSINESS_SERVICES),
    ("polycase", TransactionCategory.BUSINESS_SERVICES),
    #
    ("trader joe", TransactionCategory.GROCERIES),
    ("whole foods", TransactionCategory.GROCERIES),
    ("aldi", TransactionCategory.GROCERIES),
    ("food lion", TransactionCategory.GROCERIES),
    ("wegman", TransactionCategory.GROCERIES),
    ("hello fresh", TransactionCategory.GROCERIES),
    ("7-eleven", TransactionCategory.GROCERIES),
    ("stater bros", TransactionCategory.GROCERIES),
    ("grocer", TransactionCategory.GROCERIES),
    ("winco", TransactionCategory.GROCERIES),
    ("foods", TransactionCategory.GROCERIES),
    ("meijer", TransactionCategory.GROCERIES),  # Can also be shops
    ("wholesale", TransactionCategory.GROCERIES),  # Can also be shops
    ("publix", TransactionCategory.GROCERIES),  # Can also be shops
    #
    ("panda express", TransactionCategory.FAST_FOOD),
    ("jersey mike", TransactionCategory.FAST_FOOD),
    ("aunt anne", TransactionCategory.FAST_FOOD),
    ("quizno", TransactionCategory.FAST_FOOD),
    ("golden corral", TransactionCategory.RESTAURANTS),
    ("hard rock cafe", TransactionCategory.RESTAURANTS),
    ("buffalo wild wings", TransactionCategory.RESTAURANTS),
    ("chipotle", TransactionCategory.FAST_FOOD),
    ("nathan's famous", TransactionCategory.FAST_FOOD),
    ("little caesar", TransactionCategory.FAST_FOOD),
    ("tgi friday", TransactionCategory.RESTAURANTS),
    ("papa john", TransactionCategory.FAST_FOOD),
    ("chilis", TransactionCategory.RESTAURANTS),
    ("boston market", TransactionCategory.RESTAURANTS),
    ("white castle", TransactionCategory.FAST_FOOD),
    ("long horn steak", TransactionCategory.RESTAURANTS),
    ("five guys", TransactionCategory.FAST_FOOD),
    ("a&w", TransactionCategory.RESTAURANTS),
    ("mrs. fields", TransactionCategory.FAST_FOOD),
    ("red robin", TransactionCategory.RESTAURANTS),
    ("waffle house", TransactionCategory.RESTAURANTS),
    ("marie callender", TransactionCategory.RESTAURANTS),
    ("dennys", TransactionCategory.RESTAURANTS),
    ("cold stone", TransactionCategory.FAST_FOOD),
    ("red lobster", TransactionCategory.RESTAURANTS),
    ("mcdonalds", TransactionCategory.FAST_FOOD),
    ("outback steak", TransactionCategory.RESTAURANTS),
    ("cracker barrel", TransactionCategory.RESTAURANTS),
    ("popeyes", TransactionCategory.FAST_FOOD),
    ("taco bell", TransactionCategory.FAST_FOOD),
    ("texas roadhouse", TransactionCategory.RESTAURANTS),
    ("kfc", TransactionCategory.FAST_FOOD),
    ("olive garden", TransactionCategory.RESTAURANTS),
    ("applebee", TransactionCategory.RESTAURANTS),
    ("burger king", TransactionCategory.FAST_FOOD),
    ("chick-fil-a", TransactionCategory.FAST_FOOD),
    ("sonic", TransactionCategory.FAST_FOOD),
    ("subway", TransactionCategory.FAST_FOOD),
    ("panera", TransactionCategory.FAST_FOOD),
    ("dominos", TransactionCategory.FAST_FOOD),
    ("cheesecake factory", TransactionCategory.RESTAURANTS),
    ("ihop", TransactionCategory.RESTAURANTS),
    ("cinnabon", TransactionCategory.FAST_FOOD),
    ("pizza hut", TransactionCategory.FAST_FOOD),
    ("dunkin", TransactionCategory.FAST_FOOD),
    ("kirspy kreme", TransactionCategory.FAST_FOOD),
    ("wendys", TransactionCategory.FAST_FOOD),
    ("dairy queen", TransactionCategory.FAST_FOOD),
    ("baskin-robbins", TransactionCategory.FAST_FOOD),
    #
    ("at&t", TransactionCategory.BILLS_AND_UTILITIES),
    ("cox cable", TransactionCategory.BILLS_AND_UTILITIES),
    ("comcast", TransactionCategory.BILLS_AND_UTILITIES),
    ("comcast", TransactionCategory.BILLS_AND_UTILITIES),
    ("google fi", TransactionCategory.BILLS_AND_UTILITIES),
    ("verizon", TransactionCategory.BILLS_AND_UTILITIES),
    ("pacific gas", TransactionCategory.BILLS_AND_UTILITIES),
    ("edison", TransactionCategory.BILLS_AND_UTILITIES),
    ("power", TransactionCategory.BILLS_AND_UTILITIES),
    ("energy", TransactionCategory.BILLS_AND_UTILITIES),
    ("electric", TransactionCategory.BILLS_AND_UTILITIES),
    ("elec & gas", TransactionCategory.BILLS_AND_UTILITIES),
    ("gas & elec", TransactionCategory.BILLS_AND_UTILITIES),
    ("exelon", TransactionCategory.BILLS_AND_UTILITIES),
    # ("duke energy", TransactionCategory.BILLS_AND_UTILITIES),
    # ("dte energy", TransactionCategory.BILLS_AND_UTILITIES),
    # ("consumers energy", TransactionCategory.BILLS_AND_UTILITIES),
    #
    ("bumble", TransactionCategory.SOFTWARE_SUBSCRIPTIONS),
    ("hinge", TransactionCategory.SOFTWARE_SUBSCRIPTIONS),
    # todo: Could be a restaurant too
    ("audible", TransactionCategory.SOFTWARE_SUBSCRIPTIONS),
    ("midjourney", TransactionCategory.SOFTWARE_SUBSCRIPTIONS),
    ("openai", TransactionCategory.SOFTWARE_SUBSCRIPTIONS),
    ("youtubeprem", TransactionCategory.SOFTWARE_SUBSCRIPTIONS),
    ("spotify", TransactionCategory.SOFTWARE_SUBSCRIPTIONS),
    ("kagi inc", TransactionCategory.SOFTWARE_SUBSCRIPTIONS),
    ("google stor", TransactionCategory.SOFTWARE_SUBSCRIPTIONS),
    #
    ("sparkfun", TransactionCategory.ELECTRONICS),
    ("digikey", TransactionCategory.ELECTRONICS),
    ("mouser", TransactionCategory.ELECTRONICS),
    #
    ("mcdonald's", TransactionCategory.FAST_FOOD),
    ("kfc", TransactionCategory.FAST_FOOD),
    #
    ("bar", TransactionCategory.ALCOHOL),
    ("beer garden", TransactionCategory.ALCOHOL),
    ("total wine", TransactionCategory.ALCOHOL),
    #
    ("bp products", TransactionCategory.CAR),
    ("exxon", TransactionCategory.CAR),
    ("shell", TransactionCategory.CAR),
    ("o'reilly", TransactionCategory.CAR),
    ("oreilly", TransactionCategory.CAR),
    ("autozone", TransactionCategory.CAR),
    ("advance auto", TransactionCategory.CAR),
    ("tire", TransactionCategory.CAR),
    #
    ("pharmacy", TransactionCategory.MEDICAL),
    #
    ("cvs", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("walgreen", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("beauty", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("cosmetic", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("sephora", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("dermstore", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("detox", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("fragrance", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("bluemercury", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("credo", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("perfumania", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("ulta", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("fsastore", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    ("avon", TransactionCategory.HEALTH_AND_PERSONAL_CARE),
    #
    ("best buy", TransactionCategory.ELECTRONICS),
    ("newegg", TransactionCategory.ELECTRONICS),
    ("apple", TransactionCategory.ELECTRONICS),
    ("dell", TransactionCategory.ELECTRONICS),
    ("hewlett", TransactionCategory.ELECTRONICS),
    # ("ibm", TransactionCategory.ELECTRONICS),
    ("microsoft", TransactionCategory.ELECTRONICS),
    #
    ("costco", TransactionCategory.SHOPS),
    ("kroger", TransactionCategory.SHOPS),
    ("home depot", TransactionCategory.SHOPS),
    ("target", TransactionCategory.SHOPS),
    ("lowes", TransactionCategory.SHOPS),
    ("lowe's", TransactionCategory.SHOPS),
    ("dollar tree", TransactionCategory.SHOPS),
    ("dollar general", TransactionCategory.SHOPS),
    ("macys", TransactionCategory.SHOPS),
    ("macy's", TransactionCategory.SHOPS),
    ("kohls", TransactionCategory.SHOPS),
    ("kohl's", TransactionCategory.SHOPS),
    ("nordstrom", TransactionCategory.SHOPS),
    ("wayfair", TransactionCategory.SHOPS),
    ("jc penney", TransactionCategory.SHOPS),
    ("bass pro", TransactionCategory.SHOPS),
    ("foot locker", TransactionCategory.SHOPS),
    ("lululemon", TransactionCategory.SHOPS),
    ("american eagle", TransactionCategory.SHOPS),
    ("barnes and noble", TransactionCategory.SHOPS),
    ("staples", TransactionCategory.SHOPS),
    ("office depot", TransactionCategory.SHOPS),
    ("petco", TransactionCategory.SHOPS),
    ("petstmart", TransactionCategory.SHOPS),
    ("hobby lobby", TransactionCategory.SHOPS),
    ("jeweler", TransactionCategory.SHOPS),
    ("amway", TransactionCategory.SHOPS),
    ("ultra beauty", TransactionCategory.SHOPS),
    ("menards", TransactionCategory.SHOPS),
    ("amazon", TransactionCategory.SHOPS),
    #
    ("interest", TransactionCategory.FEES),
    ("online payment", TransactionCategory.TRANSFER),
    ("cash reward", TransactionCategory.INCOME),
    ("deposit-ach", TransactionCategory.INCOME),
    ("gusto", TransactionCategory.INCOME),
]


def category_override(
    # Avoid a circular import by not importing CategoryRule
    descrip: str,
    category: TransactionCategory,
    rules: Iterable["CategoryRule"],
) -> TransactionCategory:
    """Manual category overrides, based on observation. Note: This is currently handled prior to adding to the DB."""
    descrip = descrip.lower()
    # Some category overrides. Separate function A/R

    for keyword, cat in replacements:
        if keyword in descrip:
            category = cat

    for rule in rules:
        if descrip.strip() == rule.description.strip():
            return TransactionCategory(rule.category)

    return category


def cleanup_categories(cats: List[TransactionCategory]) -> List[TransactionCategory]:
    """Simplify a category list if multiple related are listed together by Plaid's API.
    In general, we return the more specific of the categories.
    Return the result, due to Python's sloppy mutation-in-place.

    Note that this is set up for """
    cats = list(set(cats))  # Remove duplicates.

    if (
        TransactionCategory.TRAVEL in cats
        and TransactionCategory.AIRLINES_AND_AVIATION_SERVICES in cats
    ):
        cats.remove(TransactionCategory.TRAVEL)

    if TransactionCategory.TRANSFER in cats and TransactionCategory.DEPOSIT in cats:
        cats.remove(TransactionCategory.TRANSFER)

    if TransactionCategory.TRANSFER in cats and TransactionCategory.DEBIT in cats:
        cats.remove(TransactionCategory.TRANSFER)

    if TransactionCategory.TRANSFER in cats and TransactionCategory.INCOME in cats:
        cats.remove(TransactionCategory.INCOME)

    if (
        TransactionCategory.RESTAURANTS in cats
        and TransactionCategory.GROCERIES in cats
    ):
        cats.remove(TransactionCategory.GROCERIES)

    if (
        TransactionCategory.RESTAURANTS in cats
        and TransactionCategory.COFFEE_SHOP in cats
    ):
        cats.remove(TransactionCategory.RESTAURANTS)

    if TransactionCategory.FAST_FOOD in cats and TransactionCategory.GROCERIES in cats:
        cats.remove(TransactionCategory.GROCERIES)

    if (
        TransactionCategory.RESTAURANTS in cats
        and TransactionCategory.FAST_FOOD in cats
    ):
        cats.remove(TransactionCategory.RESTAURANTS)

    if (
        TransactionCategory.GYMS_AND_FITNESS_CENTERS in cats
        and TransactionCategory.RECREATION in cats
    ):
        cats.remove(TransactionCategory.RECREATION)

    # Lots of bogus food+drink cats inserted by Plaid.
    if (
        TransactionCategory.GROCERIES in cats
        and TransactionCategory.CREDIT_CARD in cats
    ):
        cats.remove(TransactionCategory.GROCERIES)

    if TransactionCategory.PAYMENT in cats and TransactionCategory.CREDIT_CARD in cats:
        cats.remove(TransactionCategory.PAYMENT)

    if TransactionCategory.GROCERIES in cats and TransactionCategory.TRANSFER in cats:
        cats.remove(TransactionCategory.GROCERIES)

    if TransactionCategory.GROCERIES in cats and TransactionCategory.SHOPS in cats:
        cats.remove(TransactionCategory.SHOPS)

    if (
        TransactionCategory.SOFTWARE_SUBSCRIPTIONS in cats
        and TransactionCategory.SHOPS in cats
    ):
        cats.remove(TransactionCategory.SHOPS)

    if TransactionCategory.SPORTING_GOODS in cats and TransactionCategory.SHOPS in cats:
        cats.remove(TransactionCategory.SHOPS)

    if TransactionCategory.ELECTRONICS in cats and TransactionCategory.SHOPS in cats:
        cats.remove(TransactionCategory.SHOPS)

    if TransactionCategory.RESTAURANTS in cats and TransactionCategory.SHOPS in cats:
        cats.remove(TransactionCategory.RESTAURANTS)

    if TransactionCategory.GROCERIES in cats and TransactionCategory.TRAVEL in cats:
        cats.remove(TransactionCategory.GROCERIES)

    if TransactionCategory.TAXI in cats and TransactionCategory.TRAVEL in cats:
        cats.remove(TransactionCategory.TRAVEL)

    if TransactionCategory.CAR in cats and TransactionCategory.TRAVEL in cats:
        cats.remove(TransactionCategory.TRAVEL)

    if TransactionCategory.BILLS_AND_UTILITIES in cats and TransactionCategory.BUSINESS_SERVICES in cats:
        cats.remove(TransactionCategory.BUSINESS_SERVICES)

    if TransactionCategory.UNCATEGORIZED in cats and len(cats) > 1:
        cats.remove(TransactionCategory.UNCATEGORIZED)

    if len(cats) > 1:
        print(">1 len categories: \n", cats)

    return cats
