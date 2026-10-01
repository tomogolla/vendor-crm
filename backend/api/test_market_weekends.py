from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from .models import MARKET_WEEKENDS, ApprovalInvoice, MarketWeekendBooking, VendorLead
from .test_utils import AuthenticatedAPITestCase


class MarketWeekendTests(AuthenticatedAPITestCase):
    def create_booking(self, name, dates, amount='100.00', paid='0.00', decision='accepted'):
        lead = VendorLead.objects.create(
            business_name=name,
            vendor_contact_name=f'{name} Contact',
            email=f'{name.lower().replace(" ", "-")}@example.com',
            phone_number='555-0100',
            vendor_category='Jewelry',
            application_decision=decision,
            agreed_weekend_dates=dates,
        )
        invoice = ApprovalInvoice.objects.create(
            lead=lead,
            recipient_email=lead.email,
            amount=amount,
            due_date=timezone.localdate(),
            weekend_dates=dates,
        )
        for weekend in dates.split(' | '):
            if weekend in MARKET_WEEKENDS:
                MarketWeekendBooking.objects.create(
                    lead=lead, invoice=invoice, weekend=weekend, amount_paid=paid,
                )
        return lead

    def test_returns_all_weekends_with_capacity_and_bookings(self):
        self.create_booking('Alpha', 'October 10 & 11 | October 17 & 18', paid='75.00')
        self.create_booking('Beta', 'October 10 & 11', amount='50.00', paid='50.00')
        self.create_booking('Declined', 'October 10 & 11', paid='100.00', decision='declined')
        response = self.client.get(reverse('market-weekends'))
        self.assertEqual(response.status_code, 200)
        weekends = response.json()['weekends']
        self.assertEqual([weekend['name'] for weekend in weekends], MARKET_WEEKENDS)
        october_10 = weekends[0]
        self.assertEqual(october_10['capacity'], 40)
        self.assertEqual(october_10['booked'], 2)
        self.assertEqual(october_10['available'], 38)
        self.assertEqual(october_10['total_paid'], '125.00')
        self.assertEqual([vendor['business_name'] for vendor in october_10['vendors']], ['Alpha', 'Beta'])
        self.assertEqual(october_10['vendors'][0]['payment_status'], 'Paid')
        self.assertEqual(october_10['vendors'][1]['payment_status'], 'Paid')
        self.assertEqual(weekends[-1]['booked'], 0)
        self.assertEqual(weekends[-1]['available'], 40)
        self.assertEqual(weekends[-1]['total_paid'], '0.00')

    def test_unknown_legacy_dates_are_not_added_to_schedule(self):
        self.create_booking('Legacy', 'October 3–4 and 10–11, 2026', paid='20.00')
        weekends = self.client.get(reverse('market-weekends')).json()['weekends']
        self.assertTrue(all(weekend['booked'] == 0 for weekend in weekends))
