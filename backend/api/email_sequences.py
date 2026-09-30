import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VendorLead


logger = logging.getLogger(__name__)
SEQUENCE_IDS = (
    'welcome',
    'vendor-fit',
    'application-process',
    'upcoming-weekends',
)


class SequenceEmailInput(serializers.Serializer):
    template_id = serializers.ChoiceField(choices=SEQUENCE_IDS)
    subject = serializers.CharField(max_length=255, trim_whitespace=True)
    body = serializers.CharField(max_length=10000, trim_whitespace=True)

    def validate_subject(self, value):
        if not value:
            raise serializers.ValidationError('Enter an email subject.')
        return value

    def validate_body(self, value):
        if not value:
            raise serializers.ValidationError('Enter an email message.')
        return value


class SendSequenceEmail(APIView):
    def post(self, request, pk):
        serializer = SequenceEmailInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not settings.INVOICE_EMAIL_READY:
            return Response(
                {'non_field_errors': ['Email is not configured. Set SMTP_HOST on the Django server.']},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        lead = get_object_or_404(VendorLead, pk=pk)
        try:
            validate_email(lead.email)
        except ValidationError:
            return Response(
                {'email': ['Add a valid vendor email before sending.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sent = EmailMessage(
                subject=serializer.validated_data['subject'],
                body=serializer.validated_data['body'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[lead.email],
            ).send()
            if sent != 1:
                raise RuntimeError('Mail backend did not send the sequence email.')
        except (smtplib.SMTPException, OSError, RuntimeError):
            logger.exception('Could not send sequence email %s for vendor lead %s', serializer.validated_data['template_id'], lead.pk)
            return Response(
                {'non_field_errors': ['The email could not be sent. Please try again.']},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'success': True, 'recipient_email': lead.email}, status=status.HTTP_200_OK)