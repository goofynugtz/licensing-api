from .utils import validate_signature, generate_license, new_rsa, mail_license_keys
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.transaction import atomic, non_atomic_requests
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils import timezone
from accounts.models import Employee
from prometheus_client import Counter, generate_latest
from decouple import config
from .models import License, Policy
from .serializers import LicenseSerializer
import jwt

counter = {
  'success': Counter('total_successful_validations', 'Total no. of successful validation requests'),
  'failed': Counter('total_failed_validations', 'Total no. of failed validation requests'),
  'issued': Counter('total_licenses_issued', 'Total no. of license keys issued'),
  'suspended': Counter('total_licenses_suspended', 'Total no. of license keys suspended'),
  'revoked': Counter('total_licenses_revoked', 'Total no. of license keys revoked')
}

# Body { "email", "key" }
@api_view(['GET'])
@permission_classes([AllowAny])
@non_atomic_requests
def validate(request):
  email = request.data["email"].lower()
  key = request.data['key']
  try:
    user = Employee.objects.get(email=email)
    try:
      license_record = License.objects.get(user=user)
      if (validate_signature(email=email, license_key=key, public_key=license_record.public_key)):
        if (license_record.validUpto < timezone.now()):
          record_status = { "status": License.EXP, }
          license_serializer = LicenseSerializer(instance=license_record, data=record_status, partial=True)
          if (license_serializer.is_valid()):
            license_serializer.save()
          counter['failed'].inc()
          return Response(license_record.status, status=status.HTTP_406_NOT_ACCEPTABLE)
        else: 
          counter['success'].inc()
          return Response(license_record.status, status=status.HTTP_200_OK)
      else:
        counter['failed'].inc()
        return Response("INVALID", status=status.HTTP_406_NOT_ACCEPTABLE)
    except ObjectDoesNotExist:
      counter['failed'].inc()
      return Response("NOT_FOUND", status=status.HTTP_404_NOT_FOUND)
  except ObjectDoesNotExist:
    counter['failed'].inc()
    return Response("USER_SCOPE_MISMATCH", status=status.HTTP_403_FORBIDDEN)

# Header { "Authorization": "Bearer JWT" } 
# Body   { "name", "policy"}
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@atomic
def issue(request):
  access_token = request.headers['Authorization'].split(' ')[-1]
  name = request.data["name"]
  policy_name = request.data["policy"]
  try: 
    policy = Policy.objects.get(name=policy_name)
    data = jwt.decode(access_token, algorithms=['HS256'], key=config('SECRET_KEY'))
    email = data['email']
    try:
      user = Employee.objects.get(email=email)
      previous_license = License.objects.filter(user=user)
      if (len(previous_license) > 0):
          previous_license.delete()
      validUpto = timezone.now() + policy.validity
      public_key, private_key = new_rsa()
      key = generate_license(email, private_key)
      License.objects.create(
        name = name,
        key = key,
        public_key = public_key,
        private_key = private_key,
        user = user,
        policy = policy,
        validUpto = validUpto,
      )
      mail_license_keys(key, email)
      counter['issued'].inc()
      return Response("Success", status=status.HTTP_201_CREATED)
      # return Response(key, status=status.HTTP_201_CREATED)
    except ObjectDoesNotExist:
      return Response("Employee/Email does not exist.", status=status.HTTP_400_BAD_REQUEST)
  except ObjectDoesNotExist:
    return Response("Invalid policy.", status=status.HTTP_404_NOT_FOUND)

# Header { "Authorization": "Bearer JWT" } 
# Body   { "email" }
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@non_atomic_requests
def suspend(request):
  email = request.data['email']
  try:
    user = Employee.objects.get(email=email)
    license_record = License.objects.get(user=user)
    record_status = { "status": License.SUS, }
    license_serializer = LicenseSerializer(instance=license_record, data=record_status, partial=True)
    if license_serializer.is_valid():
      license_serializer.save()
      counter['suspended'].inc()
      return Response("License Suspended", status=status.HTTP_202_ACCEPTED)
    else:
      return Response("Something went wrong. Please contact your administrator.", status=status.HTTP_304_NOT_MODIFIED)
  except ObjectDoesNotExist:
    return Response("Employee/License does not exists.", status=status.HTTP_401_UNAUTHORIZED)

# Header { "Authorization": "Bearer JWT" } 
# Body   { "email" }
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@non_atomic_requests
def resume(request):
  email = request.data['email']
  try:
    user = Employee.objects.get(email=email)
    license_record = License.objects.get(user=user)
    record_status = { "status": License.VAL, }
    license_serializer = LicenseSerializer(instance=license_record, data=record_status, partial=True)
    if license_serializer.is_valid():
      license_serializer.save()
      return Response("License status Continued", status=status.HTTP_202_ACCEPTED)
    else:
      return Response("Something went wrong. Please contact your administrator.", status=status.HTTP_304_NOT_MODIFIED)
  except ObjectDoesNotExist:
    return Response("Employee/License does not exists.", status=status.HTTP_401_UNAUTHORIZED)

# Header { "Authorization": "Bearer JWT" } 
# Body   { "email" }
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@non_atomic_requests
def revoke(request):
  email = request.data['email']
  try:
    user = Employee.objects.get(email=email)
    license_record = License.objects.get(user=user)
    license_record.delete()
    counter['revoked'].inc()
    return Response("Deleted", status=status.HTTP_200_OK)
  except:
    return Response("Employee/License does not exists.", status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([AllowAny])
@non_atomic_requests
def compute_metrics(request):
  res = []
  for _, value in counter.items():
    res.append(generate_latest(value))
  return HttpResponse(res, content_type="text/plain")
