"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.urls import path
from api.views import VendorLeadListCreate, VendorLeadDetail
from api.invoices import ApproveAndSendInvoice
from api.email_sequences import SendSequenceEmail
from api.market_weekends import MarketWeekendList
from api.applications import ApplicationCsvImport, ApplicationList
from api.authentication import LoginView, LogoutView, CurrentUserView

urlpatterns = [
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/auth/me/', CurrentUserView.as_view(), name='auth-me'),
    path('api/applications/', ApplicationList.as_view(), name='applications'),
    path('api/applications/import-csv/', ApplicationCsvImport.as_view(), name='application-csv-import'),
    path('api/vendor-leads/', VendorLeadListCreate.as_view(), name='vendor-leads'),
    path('api/vendor-leads/<int:pk>/', VendorLeadDetail.as_view(), name='vendor-lead-detail'),
    path('api/vendor-leads/<int:pk>/approve-invoice/', ApproveAndSendInvoice.as_view(), name='vendor-lead-approve-invoice'),
    path('api/vendor-leads/<int:pk>/email-sequence/', SendSequenceEmail.as_view(), name='vendor-lead-email-sequence'),
    path('api/market-weekends/', MarketWeekendList.as_view(), name='market-weekends'),
    path('admin/', admin.site.urls),
]
