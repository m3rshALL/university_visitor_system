"""Check HCP version and try to discover available endpoints"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from hikvision_integration.services import HikCentralSession
from hikvision_integration.models import HikCentralServer

def check_hcp_version():
    print("=" * 80)
    print("🔍 Checking HikCentral Professional Version and Capabilities")
    print("=" * 80)
    
    server = HikCentralServer.objects.filter(enabled=True).first()
    if not server:
        print("❌ No enabled HikCentral server found")
        return
    
    session = HikCentralSession(server)
    
    # Test 1: Get version info
    print("\n📋 Test 1: Getting HCP version")
    try:
        resp = session._make_request('GET', '/artemis/api/common/v1/version')
        version_data = resp.json()
        print(f"   ✓ API Response: {version_data}")
        if version_data.get('code') == '0':
            data = version_data.get('data', {})
            print(f"   ✓ Version: {data.get('version', 'Unknown')}")
            print(f"   ✓ Build Time: {data.get('buildTime', 'Unknown')}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 2: Try to get API capabilities/features
    print("\n📋 Test 2: Checking available features")
    test_endpoints = [
        '/artemis/api/common/v1/capabilities',
        '/artemis/api/common/v1/features',
        '/artemis/api/system/v1/version',
        '/artemis/api/system/v1/capabilities',
    ]
    
    for endpoint in test_endpoints:
        try:
            resp = session._make_request('GET', endpoint)
            result = resp.json()
            if result.get('code') in ['0', 0]:
                print(f"   ✓ {endpoint}: Available")
                print(f"      Data: {result.get('data')}")
            else:
                print(f"   ⚠️  {endpoint}: {result.get('msg')}")
        except Exception as e:
            print(f"   ❌ {endpoint}: Not available ({str(e)[:50]})")
    
    # Test 3: Try alternative photo upload endpoints
    print("\n📋 Test 3: Testing alternative photo endpoints")
    alternative_endpoints = [
        ('POST', '/artemis/api/resource/v1/picture/upload'),
        ('POST', '/artemis/api/resource/v1/person/face/update'),
        ('POST', '/artemis/api/resource/v1/person/picture_data'),
        ('PUT', '/artemis/api/resource/v1/person/picture'),
        ('POST', '/artemis/api/acs/v1/faceCheck'),
        ('POST', '/artemis/api/visitor/v1/picture/upload'),
    ]
    
    # Пробуем с минимальным payload чтобы не ломать данные
    test_person_id = '8505'
    
    for method, endpoint in alternative_endpoints:
        try:
            if 'person' in endpoint.lower() and '{' not in endpoint:
                # Пробуем с personId в payload
                resp = session._make_request(method, endpoint, data={'personId': test_person_id})
            else:
                resp = session._make_request(method, endpoint, data={})
            
            result = resp.json()
            code = result.get('code')
            msg = result.get('msg', '')
            
            if code == '0':
                print(f"   🎉 {method} {endpoint}: SUCCESS!")
            elif code == '8':
                print(f"   ❌ {method} {endpoint}: Not supported (code=8)")
            elif 'parameter' in msg.lower():
                print(f"   ⚠️  {method} {endpoint}: Exists but needs correct parameters")
            else:
                print(f"   ⚠️  {method} {endpoint}: {msg}")
        except Exception as e:
            error_msg = str(e)[:60]
            if '404' in error_msg:
                print(f"   ❌ {method} {endpoint}: Not found (404)")
            else:
                print(f"   ❌ {method} {endpoint}: {error_msg}")

    # Test 4: Check Face Library status
    print("\n📋 Test 4: Checking Face Library availability")
    try:
        resp = session._make_request('POST', '/artemis/api/frs/v1/face/group', data={
            'pageNo': 1,
            'pageSize': 10
        })
        result = resp.json()
        if result.get('code') == '0':
            groups = result.get('data', {}).get('list', [])
            print(f"   ✓ Face Library API available!")
            print(f"   ✓ Face Groups: {len(groups)}")
            if groups:
                for group in groups[:3]:
                    print(f"      - {group.get('groupName')} (ID: {group.get('groupId')})")
        else:
            print(f"   ⚠️  Face Library: {result.get('msg')}")
    except Exception as e:
        print(f"   ❌ Face Library: {e}")
    
    # Test 5: Check if we can query person photo directly
    print("\n📋 Test 5: Checking person photo query methods")
    try:
        resp = session._make_request('POST', '/artemis/api/resource/v1/person/personId/personInfo', 
                                     data={'personId': test_person_id})
        result = resp.json()
        if result.get('code') == '0':
            person = result.get('data', {})
            photo_info = person.get('personPhoto', {})
            print(f"   ✓ Person query works")
            print(f"   ✓ Photo fields available: {list(photo_info.keys())}")
            print(f"   ✓ Photo structure: {photo_info}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 Recommendations based on findings above")
    print("=" * 80)
    print("\n1. Check HCP version - if old, update to latest")
    print("2. If any alternative endpoint shows 'needs parameters', focus on that")
    print("3. If Face Library available, request admin to create Face Group")
    print("4. Contact Hikvision support with your HCP version for proper API docs")

if __name__ == '__main__':
    check_hcp_version()
