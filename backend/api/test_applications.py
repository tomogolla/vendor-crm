import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from .models import VendorLead
from .test_utils import AuthenticatedAPITestCase


class ApplicationPipelineTests(AuthenticatedAPITestCase):
    def upload(self, content, name='applications.csv'):
        file = SimpleUploadedFile(name, content.encode('utf-8'), content_type='text/csv')
        return self.client.post(reverse('application-csv-import'), {'file': file}, format='multipart')

    def test_csv_import_creates_new_applications_and_skips_instagram_duplicates(self):
        VendorLead.objects.create(
            instagram_handle='@Existing.Shop', business_name='Existing',
            email='existing@example.com', funnel_stage='vendor',
        )
        response = self.upload(
            'Business Name,Instagram,Email,Phone,Category,Source,First Name,Last Name,Requested Dates\n'
            'New Brand,@New.Shop,new@example.com,555-0101,Jewelry,Shopify form,Jamie,Lee,"October 10 & 11 | October 17 & 18"\n'
            'Duplicate Existing,@EXISTING.SHOP,duplicate@example.com,555-0102,Jewelry,Google form,A,B,\n'
            'Duplicate File,@new.shop,another@example.com,555-0103,Jewelry,Google form,C,D,\n'
            'Missing Handle,,missing@example.com,555-0104,Jewelry,Google form,E,F,\n'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data['created']), 1)
        self.assertEqual(len(response.data['skipped']), 2)
        self.assertEqual(len(response.data['errors']), 1)
        application = VendorLead.objects.get(instagram_handle='new.shop')
        self.assertEqual(application.funnel_stage, 'new_application')
        self.assertEqual(application.business_name, 'New Brand')
        self.assertEqual(application.lead_source, 'Shopify form')
        self.assertEqual(application.agreed_weekend_dates, 'October 10 & 11 | October 17 & 18')

        applications = self.client.get(reverse('applications')).json()['applications']
        self.assertEqual([item['id'] for item in applications], [application.pk])
        vendors = self.client.get(reverse('vendor-leads')).json()['leads']
        self.assertEqual([item['business_name'] for item in vendors], ['Existing'])

    def test_csv_validation_rejects_bad_file_and_headers(self):
        wrong_type = SimpleUploadedFile('applications.txt', b'Business Name,Instagram\nBrand,@brand', content_type='text/plain')
        self.assertEqual(self.client.post(reverse('application-csv-import'), {'file': wrong_type}, format='multipart').status_code, 400)
        self.assertEqual(self.upload('Email,Phone\na@example.com,555').status_code, 400)
        self.assertEqual(self.upload('Business Name,Instagram\nBrand,@bad handle').status_code, 200)
        self.assertFalse(VendorLead.objects.exists())

    @override_settings(INVOICE_EMAIL_READY=True, MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}})
    def test_approval_moves_application_to_vendor_list(self):
        application = VendorLead.objects.create(
            instagram_handle='approved.shop', business_name='Approved Shop',
            first_name='Ari', email='ari@example.com', funnel_stage='new_application',
            agreed_weekend_dates='October 10 & 11',
        )
        response = self.client.post(reverse('vendor-lead-approve-invoice', kwargs={'pk': application.pk}), {
            'amount': '100.00',
            'due_date': timezone.localdate().isoformat(),
            'invoice_link': 'https://payments.example.com/approved-shop',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        application.refresh_from_db()
        self.assertEqual(application.funnel_stage, 'vendor')
        self.assertFalse(any(item['id'] == application.pk for item in self.client.get(reverse('applications')).json()['applications']))
        self.assertTrue(any(item['id'] == application.pk for item in self.client.get(reverse('vendor-leads')).json()['leads']))
