import re

from rest_framework import serializers

from .models import VendorLead


class VendorLeadSerializer(serializers.ModelSerializer):
    instagram_handle = serializers.CharField(max_length=31, required=False, allow_blank=True)

    class Meta:
        model = VendorLead
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def validate_instagram_handle(self, value):
        value = value.strip().removeprefix('@').lower()
        if value and not re.fullmatch(r'[A-Za-z0-9._]{1,30}', value):
            raise serializers.ValidationError('Enter a valid Instagram handle, without a URL.')
        return value

    def validate_application_decision(self, value):
        if value == 'accepted':
            raise serializers.ValidationError('Use the approval invoice action to accept an application.')
        return value

    def validate(self, attrs):
        if not any(attrs.get(field, getattr(self.instance, field, '')) for field in ('instagram_handle', 'email', 'phone_number')):
            raise serializers.ValidationError('Provide an Instagram handle, email, or phone number.')
        return attrs
