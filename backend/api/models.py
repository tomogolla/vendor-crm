from django.db import models
from django.utils import timezone

CATEGORIES = [
    'Arts, Prints & Stickers', 'Beauty & Cosmetics', 'Ceramics / Glass',
    'Clothing Brand', 'Crotchet, Sewing, Quilt Goods', 'Cultural Collectibles',
    'Experience', 'Homeware', 'Jewelry', 'Leatherwork', 'Music / Vinyl',
    'NYC Merch', 'Pets Accessories', 'Photography', 'Plants',
    'Soaps / Candles and Perfume', 'Stationery', 'Unique Things',
    'Vintage Clothing', 'Vintage General', 'Vintage Homeware',
    'Vintage Jewelry', 'Vintage Upcycled',
]
LEAD_SOURCES = ['Instagram', 'Email', 'Meta ads', 'Shopify form', 'Google form', 'Google Sheets']
MARKET_WEEKENDS = [
    'October 10 & 11', 'October 17 & 18', 'October 24 & 25',
    'October 31 & November 1', 'November 7 & 8', 'November 14 & 15',
    'November 21 & 22', 'November 28 & 29', 'December 5 & 6',
    'December 12 & 13', 'December 19 & 20', 'December 26 & 27',
]


class VendorLead(models.Model):
    FUNNEL_STAGES = [('new_application', 'New application'), ('vendor', 'Vendor')]

    instagram_handle = models.CharField(max_length=30, blank=True)
    business_name = models.CharField(max_length=200)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=40, blank=True)
    vendor_category = models.CharField(max_length=100, choices=[(v, v) for v in CATEGORIES])
    lead_source = models.CharField(max_length=30, choices=[(v, v) for v in LEAD_SOURCES])
    interest_level = models.CharField(max_length=4, choices=[('hot', 'Hot'), ('warm', 'Warm'), ('cold', 'Cold')])
    next_followup = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, max_length=10000)
    vendor_contact_name = models.CharField(max_length=200, blank=True)
    call_at = models.DateTimeField(null=True, blank=True)
    call_outcome = models.CharField(max_length=30, blank=True, choices=[(v, v) for v in ['Connected', 'Left Voicemail', 'Busy', 'Rescheduled']])
    identity_verified = models.CharField(max_length=3, blank=True, choices=[('Yes', 'Yes'), ('No', 'No')])
    available_to_chat = models.CharField(max_length=30, blank=True, choices=[(v, v) for v in ['Yes', 'Reschedule requested']])
    business_commitment = models.CharField(max_length=20, blank=True, choices=[(v, v) for v in ['Full-time', 'Part-time', 'Hobbyist']])
    currently_does_markets = models.CharField(max_length=3, blank=True, choices=[('Yes', 'Yes'), ('No', 'No')])
    markets_and_frequency = models.TextField(blank=True, max_length=10000)
    team_details = models.TextField(blank=True, max_length=10000)
    primary_goals = models.TextField(blank=True, max_length=10000)
    registration_status = models.CharField(max_length=20, blank=True, choices=[(v, v) for v in ['LLC', 'Sole Prop', 'In Progress', 'None']])
    insurance_status = models.CharField(max_length=30, blank=True, choices=[(v, v) for v in ['Have active policy', 'Need guidance', "Don't have"]])
    application_challenges = models.TextField(blank=True, max_length=10000)
    location_pain_points = models.TextField(blank=True, max_length=10000)
    revenue_consistency = models.TextField(blank=True, max_length=10000)
    offer_interest = models.PositiveSmallIntegerField(null=True, blank=True, choices=[(1, 'Very Hesitant'), (2, 'Hesitant'), (3, 'Neutral'), (4, 'Excited'), (5, 'Extremely Excited')])
    offer_concerns = models.TextField(blank=True, max_length=10000)
    long_term_outlook = models.CharField(max_length=40, blank=True, choices=[(v, v) for v in ['One-off', 'Seasonal', 'Long-term recurring anchor vendor']])
    trial_commitment = models.CharField(max_length=30, blank=True, choices=[(v, v) for v in ['Agreed', 'Under Consideration', 'Declined']])
    agreed_weekend_dates = models.CharField(max_length=500, blank=True)
    onboarding_dates_confirmed = models.BooleanField(default=False)
    trial_term_agreed = models.BooleanField(default=False)
    insurance_setup_walked_through = models.BooleanField(default=False)
    information_packet_sent = models.BooleanField(default=False)
    added_to_market_schedule = models.BooleanField(default=False)
    followup_status = models.CharField(max_length=30, blank=True, choices=[(v, v) for v in ['Closed - Confirmed', 'Follow-up Needed', 'Unqualified', 'Lost']])
    vendor_contract = models.BooleanField(default=False)
    coi = models.BooleanField(default=False)
    info_packet = models.BooleanField(default=False)
    application_decision = models.CharField(max_length=10, default='pending', choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('waitlisted', 'Waitlisted'), ('declined', 'Declined')])
    funnel_stage = models.CharField(max_length=20, choices=FUNNEL_STAGES, default='vendor', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.business_name


class ApprovalInvoice(models.Model):
    lead = models.OneToOneField(VendorLead, on_delete=models.PROTECT, related_name='approval_invoice')
    recipient_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    due_date = models.DateField()
    payment_instructions = models.TextField(max_length=2000)
    invoice_link = models.URLField(max_length=2048, blank=True)
    personal_message = models.TextField(blank=True, max_length=5000)
    weekend_dates = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(default=timezone.now)

    @property
    def number(self):
        return f'GF-{self.sent_at.year}-{self.pk:06d}'

    def __str__(self):
        return self.number


class MarketWeekendBooking(models.Model):
    lead = models.ForeignKey(VendorLead, on_delete=models.PROTECT, related_name='market_bookings')
    invoice = models.ForeignKey(ApprovalInvoice, on_delete=models.PROTECT, related_name='market_bookings')
    weekend = models.CharField(max_length=50, choices=[(value, value) for value in MARKET_WEEKENDS])
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['weekend', 'lead__business_name', 'lead_id']
        constraints = [
            models.UniqueConstraint(fields=['lead', 'weekend'], name='unique_vendor_market_weekend'),
            models.CheckConstraint(condition=models.Q(amount_paid__gte=0), name='market_booking_nonnegative_paid'),
        ]

    def __str__(self):
        return f'{self.lead.business_name} — {self.weekend}'
