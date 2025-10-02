#!/usr/bin/env python
"""Test /person/face/update with correct parameters according to API docs"""
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

print("=" * 80)
print("🧪 Testing /person/face/update with CORRECT parameters")
print("=" * 80)
print("\n📖 API Documentation says:")
print("   POST /artemis/api/resource/v1/person/face/update")
print("   Edit the information of face linked with the person.")
print("\n   Parameters:")
print("   • userId - User ID")
print("   • personId - Person ID")
print("   • faceData - Face image data (base64)")
print("\n" + "=" * 80)

# Get HCP server
server = HikCentralServer.objects.first()
if not server:
    print("❌ No HikCentral server configured")
    sys.exit(1)

session = HikCentralSession(server)

# Test data
test_person_id = "8505"  # Павел Дуров
test_photo_path = r"D:\university_visitor_system\visitor_system\media\guest_photos\pavel.jpg"

print(f"\n📋 Test person ID: {test_person_id}")
print(f"📋 Photo path: {test_photo_path}")

# Load and encode image
if not os.path.exists(test_photo_path):
    print(f"❌ Photo file not found!")
    sys.exit(1)

with open(test_photo_path, 'rb') as f:
    image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

print(f"✓ Photo loaded: {len(image_bytes)} bytes")
print(f"✓ Base64 encoded: {len(image_base64)} characters")

# Get person info first to get userId
print("\n📡 Step 1: Getting person info to find userId...")
person_info_resp = session._make_request(
    'POST',
    '/artemis/api/resource/v1/person/personId/personInfo',
    data={'personId': test_person_id}
)
person_info = person_info_resp.json()

print(f"   Response code: {person_info.get('code')}")
print(f"   Response msg: {person_info.get('msg')}")

if person_info.get('code') != '0':
    print(f"❌ Failed to get person info")
    print(json.dumps(person_info, indent=2, ensure_ascii=False))
    sys.exit(1)

person_data = person_info.get('data', {})
user_id = person_data.get('userId')
person_name = person_data.get('personName')
person_code = person_data.get('personCode')

print(f"✓ Person found:")
print(f"   userId: {user_id}")
print(f"   personId: {test_person_id}")
print(f"   personName: {person_name}")
print(f"   personCode: {person_code}")

print("\n" + "=" * 80)
print("🧪 TEST 1: Using ALL three parameters (userId, personId, faceData)")
print("=" * 80)

payload_1 = {
    'userId': str(user_id) if user_id else '',
    'personId': test_person_id,
    'faceData': image_base64
}

print(f"\n📤 Payload structure:")
print(f"   userId: {payload_1['userId']}")
print(f"   personId: {payload_1['personId']}")
print(f"   faceData: <{len(payload_1['faceData'])} chars base64>")

response_1 = session._make_request(
    'POST',
    '/artemis/api/resource/v1/person/face/update',
    data=payload_1
)
result_1 = response_1.json()

print(f"\n📊 Response:")
print(f"   code: {result_1.get('code')}")
print(f"   msg: {result_1.get('msg')}")

if result_1.get('data'):
    print(f"   data: {result_1.get('data')}")

if result_1.get('code') == '0':
    print(f"\n✅ SUCCESS! Request accepted!")
    print(f"\n🔍 Verifying if photo was saved...")
    
    # Verify
    verify_resp = session._make_request(
        'POST',
        '/artemis/api/resource/v1/person/personId/personInfo',
        data={'personId': test_person_id}
    )
    verify_data = verify_resp.json().get('data', {})
    pic_uri = verify_data.get('personPhoto', {}).get('picUri', '')
    
    print(f"   picUri after update: '{pic_uri}'")
    
    if pic_uri:
        print(f"\n🎉 PHOTO UPLOADED SUCCESSFULLY!")
        print(f"   Photo URI: {pic_uri}")
    else:
        print(f"\n⚠️ Request succeeded but picUri still empty")
else:
    print(f"\n❌ Request failed")

print("\n" + "=" * 80)
print("🧪 TEST 2: Only userId and faceData (without personId)")
print("=" * 80)

if user_id:
    payload_2 = {
        'userId': str(user_id),
        'faceData': image_base64
    }
    
    print(f"\n📤 Payload structure:")
    print(f"   userId: {payload_2['userId']}")
    print(f"   faceData: <{len(payload_2['faceData'])} chars base64>")
    
    response_2 = session._make_request(
        'POST',
        '/artemis/api/resource/v1/person/face/update',
        data=payload_2
    )
    result_2 = response_2.json()
    
    print(f"\n📊 Response:")
    print(f"   code: {result_2.get('code')}")
    print(f"   msg: {result_2.get('msg')}")
    
    if result_2.get('code') == '0':
        print(f"\n✅ SUCCESS with userId only!")
        
        # Verify
        verify_resp = session._make_request(
            'POST',
            '/artemis/api/resource/v1/person/personId/personInfo',
            data={'personId': test_person_id}
        )
        verify_data = verify_resp.json().get('data', {})
        pic_uri = verify_data.get('personPhoto', {}).get('picUri', '')
        
        print(f"   picUri after update: '{pic_uri}'")
        
        if pic_uri:
            print(f"\n🎉 PHOTO UPLOADED SUCCESSFULLY!")
        else:
            print(f"\n⚠️ Request succeeded but picUri still empty")
else:
    print("⏭️  Skipping (no userId found)")

print("\n" + "=" * 80)
print("🧪 TEST 3: Only personId and faceData (without userId)")
print("=" * 80)

payload_3 = {
    'personId': test_person_id,
    'faceData': image_base64
}

print(f"\n📤 Payload structure:")
print(f"   personId: {payload_3['personId']}")
print(f"   faceData: <{len(payload_3['faceData'])} chars base64>")

response_3 = session._make_request(
    'POST',
    '/artemis/api/resource/v1/person/face/update',
    data=payload_3
)
result_3 = response_3.json()

print(f"\n📊 Response:")
print(f"   code: {result_3.get('code')}")
print(f"   msg: {result_3.get('msg')}")

if result_3.get('code') == '0':
    print(f"\n✅ SUCCESS with personId only!")
    
    # Verify
    verify_resp = session._make_request(
        'POST',
        '/artemis/api/resource/v1/person/personId/personInfo',
        data={'personId': test_person_id}
    )
    verify_data = verify_resp.json().get('data', {})
    pic_uri = verify_data.get('personPhoto', {}).get('picUri', '')
    
    print(f"   picUri after update: '{pic_uri}'")
    
    if pic_uri:
        print(f"\n🎉 PHOTO UPLOADED SUCCESSFULLY!")
    else:
        print(f"\n⚠️ Request succeeded but picUri still empty")

print("\n" + "=" * 80)
print("📝 SUMMARY")
print("=" * 80)
print(f"""
Test 1 (userId + personId + faceData): {result_1.get('code')} - {result_1.get('msg')}
""")

if user_id:
    print(f"Test 2 (userId + faceData): {result_2.get('code')} - {result_2.get('msg')}")
else:
    print(f"Test 2 (userId + faceData): Skipped (no userId)")

print(f"Test 3 (personId + faceData): {result_3.get('code')} - {result_3.get('msg')}")

print("\n" + "=" * 80)
print("💡 CONCLUSIONS")
print("=" * 80)
print("""
If ANY test shows code=0 AND picUri is not empty:
✅ This method WORKS! We just had wrong parameter combination!

If ALL tests show code=0 BUT picUri stays empty:
❌ API accepts request but HCP version still doesn't save photos

If tests show code=2 or other error:
❌ Parameters still incorrect or endpoint not supported
""")
