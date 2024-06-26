# Finance Monitor
## Open-source personal finance aggregator / Mint replacement

### [Official webapp](https://www.finance-monitor.com)

This repository contains the full code to build a web application that aggregates and views personal finance data,
in a similar way to the removed *mint.com*. It aims to be fast and functional, and its open source nature
lends it to being customizable to individual use cases.

Compared to paid alternatives, you can save money, at the cost of having to manage details yourself, as paying for
the aggregator API (eg Plaid) directly is cheaper than paying the $4-$10 a month full services cost. Unlike free
services, your data is private, and not sold.


## Architecture
  - Python backend, using the [Django](https://www.djangoproject.com/) framework.
  - HTML, CSS, and Javascript frontend
  - [PostgreSQL](https://www.postgresql.org/) database, although this can be swapped out easily due to Django's ORM.
You may wish to use SqLite instead if for personal use.
  - [Plaid](https://plaid.com) to connect to financial institutions.
  - [Sendgrid](https://sendgrid.com) as an email provider. (Sends verification and password reset emails, and emails administrators with
errors and debug information.)


## Lines of effort
The webapp is functional in its current state (See our official webapp implementation above), but can be improved in a number
of ways. Here are some examples:

### Support aggregators other than Plaid
This would allow for connecting to a broader range of institutions, and better international support

### Better international support
This is currently only tested in the US; it could use support for mixing different currencies, and aggregators that
work better in other countries

### Budgeting features
Budget support is currently nascent.


### 2 factor authentication (Eg with an authenticator phone app)


### More insightful reports

### Better documentation
Including examples


### Decoupled architecture
Make swapping in and out aggregators easier, through a decoupled API.

### Internal code cleanup
The frontend code is currently repetative and messy in places; there is room for improvement in terms of making it faster


### Smaller plotting libraries
The plotting libraries used on the Spending page (Plotly and plot.js) are currently large and bloated: Especially Plotly.
A more compact, faster alternative would be a better match for this application's otherwise streamlined architecture.


## Configuring for deployed, vice development environments.

If the environment variable `DATABASE_URL` is present, this application is considered to be deployed,
which has several implications for how it operates. (See `settings.py` for details.) If this is present, the 
the following environment variables should be set up (if available):

``````
SECRET_KEY
PLAID_CLIENT_ID
PLAID_SECRET
SENDGRID_KEY
``````

If not deployed (`DATABASE_URL` is not present), create a file called `private.py` in the `main` folder. 

`private.py`
You must create a file `main/private.py` in order to connect to plaid, and the email server. It will include
several variables, provided by Plaid and Sendgrid, through their accounts. Note that you if you
leave these blank, support for Plaid and/or email will be disabled.

Example 
contents:

```python
PLAID_CLIENT_ID = "abc"
PLAID_SECRET_SANDBOX = "abc"
PLAID_SECRET_PRODUCTION = "abc"
SENDGRID_KEY = "abc"

```

## Database setup:
The Database is configured via a URL. In production, this is configured via the `DATABASE_URL` environment
variable. In dev use, it's configured by the `DATABASE_URL` variable in `settings.py`.


### Notes
Currently, the frontend code is written in plain Javascript. This has the distinct advantage of
avoiding a build step and configuration. However: The lack of strict typing and module support,
makes the code fragile: We may change to Typescript in the future.