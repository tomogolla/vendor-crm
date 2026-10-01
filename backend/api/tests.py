from django.urls import reverse
from .models import CATEGORIES, LEAD_SOURCES, VendorLead
from .test_utils import AuthenticatedAPITestCase


class VendorLeadTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('vendor-leads')
        self.payload = {
            'instagram_handle': '@goodflea', 'business_name': 'Good Flea',
            'first_name': 'Jane', 'last_name': 'Doe', 'email': 'jane@example.com',
            'phone_number': '+254 700 000 000', 'vendor_category': CATEGORIES[0],
            'lead_source': 'Instagram', 'interest_level': 'hot',
            'next_followup': '2026-10-01T12:30:00+03:00',
            'notes': 'Interested in the next market weekend.',
        }

    def test_create_persists_all_fields_and_list_returns_lead(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 201)
        lead = VendorLead.objects.get()
        for field, value in self.payload.items():
            if field not in ('instagram_handle', 'next_followup'):
                self.assertEqual(getattr(lead, field), value)
        self.assertEqual(lead.instagram_handle, 'goodflea')
        self.assertEqual(lead.next_followup.isoformat(), '2026-10-01T09:30:00+00:00')
        data = self.client.get(self.url).json()
        self.assertEqual(data['leads'][0]['id'], lead.id)
        self.assertEqual(data['categories'], CATEGORIES)
        self.assertEqual(data['sources'], LEAD_SOURCES)

    def test_invalid_fields_do_not_create_a_lead(self):
        for field, value in [
            ('business_name', '  '), ('email', 'invalid'),
            ('instagram_handle', 'https://instagram.com/foo'),
            ('vendor_category', 'invalid'), ('lead_source', 'invalid'),
            ('interest_level', 'invalid'), ('next_followup', 'not a date'),
        ]:
            with self.subTest(field=field):
                response = self.client.post(self.url, {**self.payload, field: value}, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.assertFalse(VendorLead.objects.exists())

    def test_requires_at_least_one_contact_method(self):
        payload = {**self.payload, 'instagram_handle': '', 'email': '', 'phone_number': ''}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(VendorLead.objects.exists())

    def test_optional_fields_and_full_length_handle(self):
        payload = {key: self.payload[key] for key in ('business_name', 'vendor_category', 'lead_source', 'interest_level')}
        payload['instagram_handle'] = '@' + 'a' * 30
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(VendorLead.objects.get().next_followup)

    def test_questionnaire_answers_persist_and_roundtrip(self):
        answers = {
            'vendor_contact_name': 'Jane Doe',
            'call_at': '2026-10-01T12:30:00+03:00',
            'call_outcome': 'Connected', 'identity_verified': 'Yes',
            'available_to_chat': 'Yes', 'business_commitment': 'Full-time',
            'currently_does_markets': 'Yes', 'markets_and_frequency': 'Local market, weekly',
            'team_details': 'Solo, with occasional help', 'primary_goals': 'Build repeat customers',
            'registration_status': 'LLC', 'insurance_status': 'Need guidance',
            'application_challenges': 'Unsure about insurance',
            'location_pain_points': 'Low foot traffic', 'revenue_consistency': 'Wants predictable weekly revenue',
            'offer_interest': 5, 'offer_concerns': 'Needs setup time',
            'long_term_outlook': 'Long-term recurring anchor vendor',
            'trial_commitment': 'Agreed', 'agreed_weekend_dates': 'October 3–4 and 10–11, 2026',
            'onboarding_dates_confirmed': True, 'trial_term_agreed': True,
            'insurance_setup_walked_through': False, 'information_packet_sent': True,
            'added_to_market_schedule': False, 'followup_status': 'Closed - Confirmed',
        }
        response = self.client.post(self.url, {**self.payload, **answers}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        lead = VendorLead.objects.get()
        saved = self.client.get(self.url).json()['leads'][0]
        for field, value in answers.items():
            if field == 'call_at':
                self.assertEqual(lead.call_at.isoformat(), '2026-10-01T09:30:00+00:00')
            else:
                self.assertEqual(getattr(lead, field), value)
                self.assertEqual(saved[field], value)

    def test_invalid_questionnaire_answers_are_rejected(self):
        for field, value in [
            ('call_at', 'bad-date'), ('call_outcome', 'Unknown'),
            ('identity_verified', 'Maybe'), ('available_to_chat', 'No'),
            ('business_commitment', 'Unknown'), ('currently_does_markets', 'Maybe'),
            ('registration_status', 'Unknown'), ('insurance_status', 'Unknown'),
            ('offer_interest', 0), ('offer_interest', 6), ('offer_interest', 2.5),
            ('long_term_outlook', 'Unknown'), ('trial_commitment', 'Unknown'),
            ('followup_status', 'Unknown'), ('onboarding_dates_confirmed', 'Unknown'),
        ]:
            with self.subTest(field=field, value=value):
                response = self.client.post(self.url, {**self.payload, field: value}, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)
        self.assertFalse(VendorLead.objects.exists())

    def test_incomplete_call_can_be_saved(self):
        response = self.client.post(self.url, {
            **self.payload, 'call_outcome': 'Left Voicemail',
            'call_at': None, 'offer_interest': None,
            'followup_status': 'Follow-up Needed',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        lead = VendorLead.objects.get()
        self.assertIsNone(lead.offer_interest)
        self.assertEqual(lead.identity_verified, '')
        self.assertFalse(lead.trial_term_agreed)

    def test_profile_read_update_and_review_actions_preserve_lead(self):
        created = self.client.post(self.url, self.payload, format='json').json()
        url = reverse('vendor-lead-detail', kwargs={'pk': created['id']})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['lead']['business_name'], self.payload['business_name'])
        self.assertEqual(response.json()['lead']['application_decision'], 'pending')
        for decision in ['waitlisted', 'declined']:
            response = self.client.patch(url, {'application_decision': decision}, format='json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(VendorLead.objects.get().application_decision, decision)
        response = self.client.patch(url, {'vendor_contract': True, 'coi': True, 'info_packet': False}, format='json')
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(url, {'business_name': 'Updated brand', 'offer_interest': 4}, format='json')
        self.assertEqual(response.status_code, 200)
        lead = VendorLead.objects.get()
        self.assertTrue(lead.vendor_contract)
        self.assertTrue(lead.coi)
        self.assertFalse(lead.info_packet)
        self.assertEqual(lead.business_name, 'Updated brand')
        self.assertEqual(lead.offer_interest, 4)
        self.assertEqual(lead.email, self.payload['email'])
        self.assertEqual(lead.application_decision, 'declined')
        self.assertEqual(VendorLead.objects.count(), 1)

    def test_direct_approval_without_invoice_is_rejected(self):
        created = self.client.post(self.url, self.payload, format='json').json()
        url = reverse('vendor-lead-detail', kwargs={'pk': created['id']})
        response = self.client.patch(url, {'application_decision': 'accepted'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(VendorLead.objects.get().application_decision, 'pending')

    def test_profile_validation_and_missing_lead(self):
        lead = VendorLead.objects.create(business_name='Brand', email='hello@example.com')
        url = reverse('vendor-lead-detail', kwargs={'pk': lead.pk})
        for payload in [{'application_decision': 'invalid'}, {'coi': 'invalid'}, {'email': ''}]:
            response = self.client.patch(url, payload, format='json')
            self.assertEqual(response.status_code, 400)
        lead.refresh_from_db()
        self.assertEqual(lead.application_decision, 'pending')
        self.assertEqual(lead.email, 'hello@example.com')
        missing = reverse('vendor-lead-detail', kwargs={'pk': 999999})
        self.assertEqual(self.client.get(missing).status_code, 404)
        self.assertEqual(self.client.patch(missing, {}, format='json').status_code, 404)
