"""
URL configuration for wallet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from main import views

urlpatterns = [
    # path("accounts/", include("django.contrib.auth.urls")),
    # path('password_reset/',
    #      auth_views.PasswordResetView.as_view(
    #          template_name='password_reset.html'
    #      ),
    #      name='password_reset'
    #      ),
    path("admin/", admin.site.urls),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("register/", views.register, name="register"),
    path("password-reset/", views.password_reset_request),
    # path("password-reset-confirm/", views.password_reset_confirm),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("send-verification", views.send_verification),
    path("", views.landing),
    path("dashboard", views.dashboard),
    # path("about", views.about),
    path("spending", views.spending),
    path("recurring", views.recurring),
    path("settings", views.settings),
    path("budget", views.budget),
    path("privacy", views.privacy),
    path("terms", views.terms),
    # path("refresh-balances", views.refresh_balances),
    # path("refresh-transactions", views.refresh_transactions),
    path("export", views.export_),
    # path("import", views.import_),
    path("create-link-token", views.create_link_token),
    path("exchange-public-token", views.exchange_public_token),
    path("load-transactions", views.load_transactions),
    path("load-spending-data", views.load_spending_data),
    path("add-account-manual", views.add_account_manual),
    path("edit-transactions", views.edit_transactions),
    path("add-transactions", views.add_transactions),
    path("edit-accounts", views.edit_accounts),
    path("delete-transactions", views.delete_transactions),
    path("edit-rules", views.edit_rules),
    path("edit-categories", views.edit_categories),
    path("edit-budget-items", views.edit_budget_items),
    path("delete-accounts", views.delete_accounts),
    path("post-dash-load", views.post_dash_load),
    path("toggle-highlight", views.toggle_highlight),
    path("toggle-ignore", views.toggle_ignore),
    path("delete-user-account", views.delete_user_account),
]
