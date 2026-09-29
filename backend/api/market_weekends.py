from decimal import Decimal

from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MARKET_WEEKENDS, MarketWeekendBooking


BOOTH_CAPACITY = 40


class MarketWeekendList(APIView):
    def get(self, request):
        weekends = {name: [] for name in MARKET_WEEKENDS}
        bookings = MarketWeekendBooking.objects.select_related('lead', 'invoice').filter(
            lead__application_decision='accepted',
        ).order_by('weekend', 'lead__business_name', 'lead_id')

        for booking in bookings:
            lead = booking.lead
            weekends[booking.weekend].append({
                'vendor_id': lead.pk,
                'business_name': lead.business_name,
                'contact_name': lead.vendor_contact_name or ' '.join(
                    value for value in (lead.first_name, lead.last_name) if value
                ),
                'phone_number': lead.phone_number,
                'email': lead.email,
                'category': lead.vendor_category,
                'amount_paid': str(booking.amount_paid),
                'payment_status': 'Paid' if booking.amount_paid > 0 else 'Unpaid',
            })

        payload = []
        for name, vendors in weekends.items():
            total_paid = sum((Decimal(vendor['amount_paid']) for vendor in vendors), Decimal('0'))
            payload.append({
                'name': name,
                'capacity': BOOTH_CAPACITY,
                'booked': len(vendors),
                'available': max(BOOTH_CAPACITY - len(vendors), 0),
                'total_paid': str(total_paid.quantize(Decimal('0.01'))),
                'vendors': vendors,
            })
        return Response({'weekends': payload})
