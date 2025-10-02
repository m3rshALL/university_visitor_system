"""Try uploading photo via external URL or base64 with different structure"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from hikvision_integration.services import HikCentralSession
from hikvision_integration.models import HikCentralServer, HikPersonBinding
import base64

def test_alternative_photo_methods(guest_id=190):
    print("=" * 80)
    print("🔬 Testing Alternative Photo Upload Methods")
    print("=" * 80)
    
    server = HikCentralServer.objects.filter(enabled=True).first()
    binding = HikPersonBinding.objects.filter(guest_id=guest_id).first()
    person_id = binding.person_id
    
    session = HikCentralSession(server)
    
    # Get person info
    resp = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', 
                                 data={'personId': person_id})
    person = resp.json().get('data', {})
    person_name = person.get('personName')
    org_index = person.get('orgIndexCode')
    
    print(f"\n✓ Person: {person_name} (ID={person_id}, org={org_index})")
    
    # Load photo
    photo_path = r"D:\university_visitor_system\visitor_system\media\guest_photos\pavel.jpg"
    with open(photo_path, 'rb') as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    print(f"✓ Photo: {len(image_bytes)} bytes")
    
    # TEST 1: Try with picUri pointing to data URI
    print("\n📤 Test 1: personPhoto with data: URI")
    try:
        payload = {
            'personId': str(person_id),
            'personName': person_name,
            'orgIndexCode': str(org_index),
            'personPhoto': {
                'picUri': f'data:image/jpeg;base64,{image_base64}'
            }
        }
        resp = session._make_request('POST', '/artemis/api/resource/v1/person/single/update', 
                                     data=payload)
        result = resp.json()
        print(f"   Response: code={result.get('code')} msg={result.get('msg')}")
        
        # Verify
        verify = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', 
                                      data={'personId': person_id})
        pic_uri = verify.json().get('data', {}).get('personPhoto', {}).get('picUri', '')
        if pic_uri:
            print(f"   🎉 SUCCESS! picUri: {pic_uri[:50]}...")
            return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # TEST 2: Try with picData field instead of picUri
    print("\n📤 Test 2: personPhoto with picData instead of picUri")
    try:
        payload = {
            'personId': str(person_id),
            'personName': person_name,
            'orgIndexCode': str(org_index),
            'personPhoto': {
                'picData': image_base64
            }
        }
        resp = session._make_request('POST', '/artemis/api/resource/v1/person/single/update', 
                                     data=payload)
        result = resp.json()
        print(f"   Response: code={result.get('code')} msg={result.get('msg')}")
        
        verify = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', 
                                      data={'personId': person_id})
        pic_uri = verify.json().get('data', {}).get('personPhoto', {}).get('picUri', '')
        if pic_uri:
            print(f"   🎉 SUCCESS! picUri: {pic_uri[:50]}...")
            return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # TEST 3: Try visitor API instead of resource API
    print("\n📤 Test 3: Using visitor API for photo update")
    try:
        payload = {
            'personId': str(person_id),
            'personName': person_name,
            'personPhoto': image_base64
        }
        resp = session._make_request('POST', '/artemis/api/visitor/v1/registerment/update', 
                                     data=payload)
        result = resp.json()
        print(f"   Response: code={result.get('code')} msg={result.get('msg')}")
        
        if result.get('code') == '0':
            verify = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', 
                                          data={'personId': person_id})
            pic_uri = verify.json().get('data', {}).get('personPhoto', {}).get('picUri', '')
            if pic_uri:
                print(f"   🎉 SUCCESS! picUri: {pic_uri[:50]}...")
                return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # TEST 4: Check if we can add photo during person creation (not update)
    print("\n📤 Test 4: Testing if photo works during person creation")
    print("   ℹ️  This would require creating a NEW test person")
    print("   ℹ️  Skipping to avoid creating test data")
    
    # TEST 5: Check person card photo upload (some versions use card photos)
    print("\n📤 Test 5: Try person card photo endpoint")
    try:
        payload = {
            'personId': str(person_id),
            'cardNo': str(person_id),
            'photo': image_base64
        }
        resp = session._make_request('POST', '/artemis/api/resource/v1/card/personPhoto', 
                                     data=payload)
        result = resp.json()
        print(f"   Response: code={result.get('code')} msg={result.get('msg')}")
        
        if result.get('code') == '0':
            verify = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', 
                                          data={'personId': person_id})
            pic_uri = verify.json().get('data', {}).get('personPhoto', {}).get('picUri', '')
            if pic_uri:
                print(f"   🎉 SUCCESS! picUri: {pic_uri[:50]}...")
                return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n" + "=" * 80)
    print("❌ All alternative methods failed")
    print("=" * 80)
    print("\n💡 FINAL CONCLUSION:")
    print("   Your HCP version does NOT support photo upload via API")
    print("   All tested methods (multipart, JSON, alternative endpoints) failed")
    print("   ")
    print("   ✅ SOLUTION: Manual photo upload via HCP UI")
    print("   OR")
    print("   ✅ SOLUTION: Update HCP to newer version with API support")
    return False

if __name__ == '__main__':
    test_alternative_photo_methods(190)
