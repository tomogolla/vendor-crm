from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ApprovalInvoice, CATEGORIES, LEAD_SOURCES, VendorLead
from .invoices import invoice_data
from .serializers import VendorLeadSerializer


class VendorLeadListCreate(APIView):
    def get(self, request):
        leads = VendorLead.objects.filter(funnel_stage='vendor')
        return Response({
            'leads': VendorLeadSerializer(leads, many=True).data,
            'categories': CATEGORIES,
            'sources': LEAD_SOURCES,
        })

    def post(self, request):
        serializer = VendorLeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)


class VendorLeadDetail(APIView):
    def get(self, request, pk):
        lead = get_object_or_404(VendorLead, pk=pk)
        invoice = getattr(lead, 'approval_invoice', None)
        return Response({'lead': VendorLeadSerializer(lead).data, 'invoice': invoice_data(invoice) if invoice else None, 'categories': CATEGORIES, 'sources': LEAD_SOURCES})

    def patch(self, request, pk):
        lead = get_object_or_404(VendorLead, pk=pk)
        if 'application_decision' in request.data and ApprovalInvoice.objects.filter(lead=lead).exists():
            return Response({'application_decision': ['The approval invoice has already been sent. This decision cannot be changed here.']}, status=409)
        serializer = VendorLeadSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
