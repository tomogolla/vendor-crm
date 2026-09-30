import logging
import smtplib
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MARKET_WEEKENDS, ApprovalInvoice, MarketWeekendBooking, VendorLead


logger = logging.getLogger(__name__)


class ApprovalInvoiceInput(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.00'))
    due_date = serializers.DateField()
    invoice_link = serializers.URLField(max_length=2048)

    def validate_due_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError('Choose today or a future date.')
        return value

    def validate_invoice_link(self, value):
        if not value.startswith('https://'):
            raise serializers.ValidationError('Enter a secure HTTPS invoice link.')
        return value


def invoice_data(invoice):
    return {
        'number': invoice.number,
        'recipient_email': invoice.recipient_email,
        'amount': str(invoice.amount),
        'currency': invoice.currency,
        'due_date': invoice.due_date.isoformat(),
        'invoice_link': invoice.invoice_link,
        'weekend_dates': invoice.weekend_dates,
        'sent_at': invoice.sent_at.isoformat(),
    }


def invoice_message(lead, invoice):
    first_name = lead.first_name or (lead.vendor_contact_name.split()[0] if lead.vendor_contact_name.strip() else lead.business_name)
    return '\n'.join([
        f'Hi {first_name},',
        '',
        "Great news! Your application has been approved for The Good Flea. We loved your submission and can't wait to have you at the upcoming market.",
        '',
        'To officially secure your booth space, please complete your payment using the secure invoice link below:',
        invoice.invoice_link,
        '',
        f'Invoice: {invoice.number}',
        f'Amount due: {invoice.currency} {invoice.amount:.2f}',
        f'Due date: {invoice.due_date:%B %d, %Y}',
        f'Selected market dates: {invoice.weekend_dates.replace(" | ", ", ") or "To be confirmed"}',
        '',
        "Once paid, we'll send over your load-in details and market day schedule.",
        '',
        'Welcome to the community!',
        '',
        'Best,',
        'The Good Flea Team',
    ])


class ApproveAndSendInvoice(APIView):
    def post(self, request, pk):
        serializer = ApprovalInvoiceInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not settings.INVOICE_EMAIL_READY:
            return Response({'non_field_errors': ['Invoice email is not configured. Set SMTP_HOST on the Django server.']}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        with transaction.atomic():
            lead = get_object_or_404(VendorLead.objects.select_for_update(), pk=pk)
            if ApprovalInvoice.objects.filter(lead=lead).exists():
                return Response({'non_field_errors': ['An approval invoice has already been sent for this vendor.']}, status=status.HTTP_409_CONFLICT)
            try:
                validate_email(lead.email)
            except ValidationError:
                return Response({'non_field_errors': ['Add a valid vendor email before sending an invoice.']}, status=status.HTTP_400_BAD_REQUEST)

            invoice = ApprovalInvoice.objects.create(
                lead=lead,
                recipient_email=lead.email,
                amount=serializer.validated_data['amount'],
                due_date=serializer.validated_data['due_date'],
                payment_instructions='',
                invoice_link=serializer.validated_data['invoice_link'],
                weekend_dates=lead.agreed_weekend_dates,
            )
            try:
                sent = EmailMessage(
                    subject=f'The Good Flea vendor approval and invoice {invoice.number}',
                    body=invoice_message(lead, invoice),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[invoice.recipient_email],
                ).send()
                if sent != 1:
                    raise RuntimeError('Mail backend did not send the invoice.')
            except (smtplib.SMTPException, OSError, RuntimeError):
                logger.exception('Could not send approval invoice for vendor lead %s', lead.pk)
                transaction.set_rollback(True)
                return Response({'non_field_errors': ['The invoice email could not be sent. The application was not approved. Please try again.']}, status=status.HTTP_502_BAD_GATEWAY)

            lead.application_decision = 'accepted'
            lead.funnel_stage = 'vendor'
            lead.save(update_fields=['application_decision', 'funnel_stage'])
            selected_weekends = {
                value.strip() for value in invoice.weekend_dates.split(' | ') if value.strip()
            }
            MarketWeekendBooking.objects.bulk_create([
                MarketWeekendBooking(lead=lead, invoice=invoice, weekend=weekend)
                for weekend in MARKET_WEEKENDS if weekend in selected_weekends
            ])
            return Response(invoice_data(invoice), status=status.HTTP_201_CREATED)
