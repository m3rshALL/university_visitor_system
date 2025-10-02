#!/usr/bin/env python
"""Test face/update with different parameter formats"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from hikvision_integration.services import HikCentralSession
from hikvision_integration.models import HikCentralServer
import base64
import json
from PIL import Image
import io

print("=" * 80)
print("🧪 Testing /person/face/update with VARIOUS parameter formats")
print("=" * 80)

# Get HCP server
server = HikCentralServer.objects.first()
if not server:
    print("❌ No HikCentral server configured")
    sys.exit(1)

session = HikCentralSession(server)

# Test data
test_person_id = "8505"
test_photo_path = r"D:\university_visitor_system\visitor_system\media\guest_photos\pavel.jpg"

# Load image
with open(test_photo_path, 'rb') as f:
    image_bytes = f.read()

print(f"\n✓ Photo loaded: {len(image_bytes)} bytes")

# Get person info
person_info_resp = session._make_request(
    'POST',
    '/artemis/api/resource/v1/person/personId/personInfo',
    data={'personId': test_person_id}
)
person_data = person_info_resp.json().get('data', {})
print(f"✓ Person: {person_data.get('personName')}")
print(f"  personId: {test_person_id}")
print(f"  personCode: {person_data.get('personCode')}")
print(f"  userId: {person_data.get('userId')}")

print("\n" + "=" * 80)
print("🧪 TEST 1: faceData as plain base64 string")
print("=" * 80)

payload = {
    'personId': test_person_id,
    'faceData': base64.b64encode(image_bytes).decode('utf-8')
}

resp = session._make_request('POST', '/artemis/api/resource/v1/person/face/update', data=payload)
result = resp.json()
print(f"Result: code={result.get('code')} msg={result.get('msg')}")

print("\n" + "=" * 80)
print("🧪 TEST 2: faceData as object with base64")
print("=" * 80)

payload = {
    'personId': test_person_id,
    'faceData': {
        'data': base64.b64encode(image_bytes).decode('utf-8')
    }
}

resp = session._make_request('POST', '/artemis/api/resource/v1/person/face/update', data=payload)
result = resp.json()
print(f"Result: code={result.get('code')} msg={result.get('msg')}")

print("\n" + "=" * 80)
print("🧪 TEST 3: Optimized smaller image (500x500)")
print("=" * 80)

# Optimize image
img = Image.open(test_photo_path)
img = img.convert('RGB')
img.thumbnail((500, 500), Image.Resampling.LANCZOS)

# Save to bytes
img_bytes_io = io.BytesIO()
img.save(img_bytes_io, format='JPEG', quality=80)
optimized_bytes = img_bytes_io.getvalue()

print(f"Original: {len(image_bytes)} bytes")
print(f"Optimized: {len(optimized_bytes)} bytes")

payload = {
    'personId': test_person_id,
    'faceData': base64.b64encode(optimized_bytes).decode('utf-8')
}

resp = session._make_request('POST', '/artemis/api/resource/v1/person/face/update', data=payload)
result = resp.json()
print(f"Result: code={result.get('code')} msg={result.get('msg')}")

print("\n" + "=" * 80)
print("🧪 TEST 4: Using personCode instead of personId")
print("=" * 80)

payload = {
    'personCode': person_data.get('personCode'),
    'faceData': base64.b64encode(image_bytes).decode('utf-8')
}

resp = session._make_request('POST', '/artemis/api/resource/v1/person/face/update', data=payload)
result = resp.json()
print(f"Result: code={result.get('code')} msg={result.get('msg')}")

print("\n" + "=" * 80)
print("🧪 TEST 5: Try creating faceId first, then update")
print("=" * 80)

# Try to get existing faceId or create one
print("Checking if person has existing face...")

# Check current personPhoto
current_photo = person_data.get('personPhoto', {})
print(f"Current personPhoto: {current_photo}")

# Try alternative endpoint - face addition
print("\nTrying /person/face/addition endpoint...")
payload = {
    'personId': test_person_id,
    'faceData': base64.b64encode(image_bytes).decode('utf-8')
}

resp = session._make_request('POST', '/artemis/api/resource/v1/person/face/addition', data=payload)
result = resp.json()
print(f"Result: code={result.get('code')} msg={result.get('msg')}")

if result.get('code') == '0':
    print("✅ Face addition succeeded!")
    
    # Now verify
    verify_resp = session._make_request(
        'POST',
        '/artemis/api/resource/v1/person/personId/personInfo',
        data={'personId': test_person_id}
    )
    verify_data = verify_resp.json().get('data', {})
    pic_uri = verify_data.get('personPhoto', {}).get('picUri', '')
    
    if pic_uri:
        print(f"🎉 PHOTO SAVED! picUri: {pic_uri}")
    else:
        print(f"⚠️ Response OK but picUri still empty")

print("\n" + "=" * 80)
print("🧪 TEST 6: Check if endpoint even exists (404 vs other error)")
print("=" * 80)

# Try with obviously wrong data to see error type
payload = {
    'personId': '999999999',
    'faceData': 'test'
}

resp = session._make_request('POST', '/artemis/api/resource/v1/person/face/update', data=payload)
result = resp.json()
print(f"Result with wrong personId: code={result.get('code')} msg={result.get('msg')}")

print("\n" + "=" * 80)
print("📝 ANALYSIS")
print("=" * 80)
print("""
Key findings:
1. Person has NO userId (userId: None)
2. Endpoint returns code=128 "person data is invalid"
3. This suggests the person record is missing required fields for face linking

Possible reasons:
• Person was created without all required fields for face management
• HCP version doesn't support face linking for this person type
• Person needs to be in specific organization or have specific attributes

Next steps to try:
1. Check if person needs to be recreated with additional fields
2. Check HCP documentation for person creation requirements for face support
3. Try updating person record with missing fields first
""")
