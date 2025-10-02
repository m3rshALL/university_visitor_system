"""Test multipart photo upload implementation"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from hikvision_integration.services import HikCentralSession, upload_face_hikcentral_multipart
from hikvision_integration.models import HikCentralServer, HikPersonBinding

def test_multipart_implementation(guest_id=190):
    print("=" * 80)
    print("🚀 Testing NEW Multipart Upload Implementation")
    print("=" * 80)
    
    # Get server and binding
    server = HikCentralServer.objects.filter(enabled=True).first()
    if not server:
        print("❌ No enabled HikCentral server found")
        return False
        
    binding = HikPersonBinding.objects.filter(guest_id=guest_id).first()
    if not binding:
        print(f"❌ No HikPersonBinding found for guest {guest_id}")
        return False
        
    person_id = binding.person_id
    print(f"\n✓ Guest ID: {guest_id}")
    print(f"✓ Person ID: {person_id}")
    
    # Load photo
    photo_path = r"D:\university_visitor_system\visitor_system\media\guest_photos\pavel.jpg"
    if not os.path.exists(photo_path):
        print(f"❌ Photo not found: {photo_path}")
        return False
        
    with open(photo_path, 'rb') as f:
        image_bytes = f.read()
    
    print(f"✓ Photo loaded: {len(image_bytes)} bytes")
    
    # Create session
    session = HikCentralSession(server)
    
    # Test multipart upload
    print("\n" + "=" * 80)
    print("📤 Uploading via Multipart with AK/SK signature...")
    print("=" * 80)
    
    try:
        result = upload_face_hikcentral_multipart(
            session=session,
            face_lib_id='',
            image_bytes=image_bytes,
            person_id=person_id
        )
        
        print(f"\n✓ Upload completed!")
        print(f"✓ Result: {result}")
        
        # Verify in HCP
        print("\n" + "=" * 80)
        print("🔍 Verifying photo in HCP...")
        print("=" * 80)
        
        verify_resp = session._make_request(
            'POST',
            '/artemis/api/resource/v1/person/personId/personInfo',
            data={'personId': person_id}
        )
        verify_json = verify_resp.json()
        photo_data = verify_json.get('data', {}).get('personPhoto', {})
        photo_uri = photo_data.get('picUri', '')
        
        print(f"\n📷 Photo Status:")
        print(f"   picUri: '{photo_uri}'")
        print(f"   Has photo: {bool(photo_uri)}")
        
        if photo_uri:
            print(f"\n🎉🎉🎉 SUCCESS! Photo is NOW visible in HCP!")
            print(f"   URI: {photo_uri}")
            return True
        else:
            print(f"\n⚠️  Upload completed but photo not visible yet")
            print(f"   (May need time to sync or fallback was used)")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_multipart_implementation(190)
    print("\n" + "=" * 80)
    if success:
        print("✅ MULTIPART UPLOAD TEST: PASSED")
    else:
        print("❌ MULTIPART UPLOAD TEST: FAILED (check logs above)")
    print("=" * 80)
