import csv
import io
import re

from django.db import transaction
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CATEGORIES, LEAD_SOURCES, VendorLead
from .serializers import VendorLeadSerializer


MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_CSV_ROWS = 5000

HEADER_ALIASES = {
    'instagram_handle': {'instagram_handle', 'instagram', '@instagram', 'instagram handle'},
    'business_name': {'business_name', 'business name', 'brand name', 'business', 'brand'},
    'first_name': {'first_name', 'first name'},
    'last_name': {'last_name', 'last name'},
    'vendor_contact_name': {'vendor_contact_name', 'vendor contact name', 'contact name'},
    'email': {'email', 'email address'},
    'phone_number': {'phone_number', 'phone number', 'phone'},
    'vendor_category': {'vendor_category', 'vendor category', 'category'},
    'lead_source': {'lead_source', 'lead source', 'source'},
    'notes': {'notes', 'application notes', 'about brand'},
    'agreed_weekend_dates': {'agreed_weekend_dates', 'agreed weekend dates', 'dates booked', 'requested dates'},
}


def normalized_header(value):
    return re.sub(r'\s+', ' ', value.strip().lower().replace('-', ' ').replace('_', ' '))


def row_value(row, field):
    aliases = {normalized_header(value) for value in HEADER_ALIASES[field]}
    for key, value in row.items():
        if key and normalized_header(key) in aliases:
            return (value or '').strip()
    return ''


class ApplicationList(APIView):
    def get(self, request):
        applications = VendorLead.objects.filter(funnel_stage='new_application')
        return Response({'applications': VendorLeadSerializer(applications, many=True).data})


class ApplicationCsvImport(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if not upload:
            return Response({'file': ['Choose a CSV file to upload.']}, status=status.HTTP_400_BAD_REQUEST)
        if not upload.name.lower().endswith('.csv'):
            return Response({'file': ['The uploaded file must be a CSV.']}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > MAX_CSV_BYTES:
            return Response({'file': ['CSV files must be 2 MB or smaller.']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            text = upload.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            return Response({'file': ['Save the CSV as UTF-8 and try again.']}, status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return Response({'file': ['The CSV must include a header row.']}, status=status.HTTP_400_BAD_REQUEST)
        headers = {normalized_header(value) for value in reader.fieldnames if value}
        required = {
            'Instagram': HEADER_ALIASES['instagram_handle'],
            'Business name': HEADER_ALIASES['business_name'],
        }
        missing = [label for label, aliases in required.items() if not headers.intersection({normalized_header(value) for value in aliases})]
        if missing:
            return Response({'file': [f'Missing required column: {", ".join(missing)}.']}, status=status.HTTP_400_BAD_REQUEST)

        seen = set()
        created = []
        skipped = []
        row_errors = []
        rows = list(reader)
        if len(rows) > MAX_CSV_ROWS:
            return Response({'file': [f'CSV files may contain at most {MAX_CSV_ROWS} rows.']}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            existing = {
                value.strip().lstrip('@').lower()
                for value in VendorLead.objects.exclude(instagram_handle='').values_list('instagram_handle', flat=True)
            }
            for number, row in enumerate(rows, start=2):
                handle = row_value(row, 'instagram_handle').lstrip('@').strip().lower()
                business = row_value(row, 'business_name')
                if not handle or not business:
                    row_errors.append({'row': number, 'message': 'Instagram and business name are required.'})
                    continue
                if not re.fullmatch(r'[a-z0-9._]{1,30}', handle):
                    row_errors.append({'row': number, 'message': 'Instagram handle is invalid.'})
                    continue
                if handle in existing or handle in seen:
                    skipped.append({'row': number, 'instagram_handle': f'@{handle}', 'reason': 'Duplicate Instagram handle'})
                    continue

                category = row_value(row, 'vendor_category') or 'Unique Things'
                source = row_value(row, 'lead_source') or 'Google form'
                source_aliases = {
                    'shopify forms': 'Shopify form',
                    'google forms': 'Google form',
                    'google sheet': 'Google Sheets',
                    'google sheets': 'Google Sheets',
                }
                source = source_aliases.get(source.casefold(), source)
                category = next((value for value in CATEGORIES if value.casefold() == category.casefold()), category)
                source = next((value for value in LEAD_SOURCES if value.casefold() == source.casefold()), source)
                payload = {
                    'instagram_handle': handle,
                    'business_name': business,
                    'first_name': row_value(row, 'first_name'),
                    'last_name': row_value(row, 'last_name'),
                    'vendor_contact_name': row_value(row, 'vendor_contact_name'),
                    'email': row_value(row, 'email'),
                    'phone_number': row_value(row, 'phone_number'),
                    'vendor_category': category,
                    'lead_source': source,
                    'interest_level': 'cold',
                    'notes': row_value(row, 'notes'),
                    'agreed_weekend_dates': row_value(row, 'agreed_weekend_dates'),
                    'funnel_stage': 'new_application',
                }
                serializer = VendorLeadSerializer(data=payload)
                if not serializer.is_valid():
                    message = '; '.join(f'{field}: {", ".join(map(str, messages))}' for field, messages in serializer.errors.items())
                    row_errors.append({'row': number, 'message': message})
                    continue
                application = serializer.save()
                created.append({'id': application.pk, 'instagram_handle': f'@{handle}'})
                seen.add(handle)
                existing.add(handle)

        return Response({'created': created, 'skipped': skipped, 'errors': row_errors})
