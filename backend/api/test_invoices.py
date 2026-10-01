from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from .test_utils import AuthenticatedAPITestCase

from .models import ApprovalInvoice, MarketWeekendBooking, VendorLead


class ApprovalInvoiceTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.lead = VendorLead.objects.create(
            business_name='Astoria Vintage',
            first_name='Jane',
            vendor_contact_name='Lillian Doe',
            email='vendor@example.com',
            agreed_weekend_dates='October 10 & 11 | October 17 & 18',
        )
        self.url = reverse('vendor-lead-approve-invoice', kwargs={'pk': self.lead.pk})
        self.payload = {
            'amount': '125.00',
            'due_date': (timezone.localdate() + timedelta(days=7)).isoformat(),
            'invoice_link': 'https://payments.example.com/invoices/gf-125',
        }

    @override_settings(INVOICE_EMAIL_READY=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_approval_sends_invoice_and_records_it_once(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.application_decision, 'accepted')
        self.assertEqual(self.lead.funnel_stage, 'vendor')
        invoice = ApprovalInvoice.objects.get(lead=self.lead)
        self.assertEqual(invoice.amount, 125)
        self.assertEqual(invoice.invoice_link, self.payload['invoice_link'])
        self.assertEqual(invoice.weekend_dates, self.lead.agreed_weekend_dates)
        self.assertEqual(
            list(MarketWeekendBooking.objects.filter(lead=self.lead).values_list('weekend', flat=True)),
            ['October 10 & 11', 'October 17 & 18'],
        )
        self.assertEqual(response.data['number'], invoice.number)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.from_email, 'booking@thegoodflea.com')
        self.assertEqual(message.to, ['vendor@example.com'])
        for text in (
            'Hi Jane,',
            "Great news! Your application has been approved for The Good Flea. We loved your submission and can't wait to have you at the upcoming market.",
            'To officially secure your booth space, please complete your payment using the secure invoice link below:',
            self.payload['invoice_link'], invoice.number, 'USD 125.00',
            'October 10 & 11', 'October 17 & 18',
            "Once paid, we'll send over your load-in details and market day schedule.",
            'Welcome to the community!', 'Best,\nThe Good Flea Team',
        ):
            self.assertIn(text, message.body)
        self.assertIn('Due date:', message.body)
        self.assertEqual(self.client.post(self.url, self.payload, format='json').status_code, 409)
        self.assertEqual(len(mail.outbox), 1)
        profile = self.client.get(reverse('vendor-lead-detail', kwargs={'pk': self.lead.pk})).json()
        self.assertEqual(profile['invoice']['number'], invoice.number)
        response = self.client.patch(reverse('vendor-lead-detail', kwargs={'pk': self.lead.pk}), {'application_decision': 'declined'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.application_decision, 'accepted')

    @override_settings(INVOICE_EMAIL_READY=False)
    def test_missing_mail_configuration_cannot_approve(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertFalse(ApprovalInvoice.objects.exists())
        self.assertFalse(MarketWeekendBooking.objects.exists())
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.application_decision, 'pending')


    @override_settings(INVOICE_EMAIL_READY=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_invalid_invoice_or_missing_email_cannot_approve(self):
        for invalid in ({'amount': '-1'}, {'due_date': '2000-01-01'}, {'invoice_link': ''}, {'invoice_link': 'http://payments.example.com/invoice/1'}):
            response = self.client.post(self.url, {**self.payload, **invalid}, format='json')
            self.assertEqual(response.status_code, 400)
        self.lead.email = ''
        self.lead.save(update_fields=['email'])
        self.assertEqual(self.client.post(self.url, self.payload, format='json').status_code, 400)
        self.assertFalse(ApprovalInvoice.objects.exists())

    @override_settings(INVOICE_EMAIL_READY=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_delivery_failure_leaves_application_unapproved(self):
        with patch('api.invoices.EmailMessage.send', side_effect=OSError('smtp unavailable')), patch('api.invoices.logger.exception'):
            response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 502)
        self.assertFalse(ApprovalInvoice.objects.exists())
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.application_decision, 'pending')


class VendorSequenceEmailTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.lead = VendorLead.objects.create(
            business_name='Astoria Vintage',
            first_name='Jane',
            email='vendor@example.com',
        )
        self.url = reverse('vendor-lead-email-sequence', kwargs={'pk': self.lead.pk})
        self.payload = {
            'template_id': 'welcome',
            'subject': 'Welcome to The Good Flea!',
            'body': 'Hi Astoria Vintage, welcome aboard.',
        }

    @override_settings(
        INVOICE_EMAIL_READY=True,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='hello@thegoodflea.com',
    )
    def test_sends_edited_template_to_vendor(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['recipient_email'], self.lead.email)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, self.payload['subject'])
        self.assertEqual(message.body, self.payload['body'])
        self.assertEqual(message.from_email, 'hello@thegoodflea.com')
        self.assertEqual(message.to, [self.lead.email])

    @override_settings(INVOICE_EMAIL_READY=True)
    def test_rejects_unknown_template_and_missing_recipient(self):
        response = self.client.post(self.url, {**self.payload, 'template_id': 'unknown'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.lead.email = ''
        self.lead.save(update_fields=['email'])
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(mail.outbox)

    @override_settings(
        INVOICE_EMAIL_READY=True,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_delivery_failure_returns_gateway_error(self):
        with patch('api.email_sequences.EmailMessage.send', side_effect=OSError('smtp unavailable')):
            response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 502)
