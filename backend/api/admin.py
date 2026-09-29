from django.contrib import admin
from .models import ApprovalInvoice, MarketWeekendBooking, VendorLead

admin.site.register(VendorLead)

@admin.register(ApprovalInvoice)
class ApprovalInvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'lead', 'amount', 'due_date', 'sent_at')
    search_fields = ('lead__business_name', 'recipient_email')


@admin.register(MarketWeekendBooking)
class MarketWeekendBookingAdmin(admin.ModelAdmin):
    list_display = ('weekend', 'lead', 'amount_paid', 'invoice')
    list_editable = ('amount_paid',)
    list_filter = ('weekend',)
    search_fields = ('lead__business_name', 'lead__email')

# Register your models here.
