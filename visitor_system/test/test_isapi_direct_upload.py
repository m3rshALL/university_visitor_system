#!/usr/bin/env python
"""Test direct ISAPI photo upload to devices (bypassing HCP)"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from hikvision_integration.models import HikDevice, HikCentralServer
from hikvision_integration.services import HikSession, upload_face_isapi
from visitors.models import Guest

print("=" * 80)
print("🔬 Testing Direct ISAPI Photo Upload (Bypassing HCP)")
print("=" * 80)

# Check if we have any devices configured
devices = HikDevice.objects.all()
print(f"\n📋 Found {devices.count()} Hikvision devices in database:")

if devices.count() == 0:
    print("\n❌ No Hikvision devices configured!")
    print("\n💡 To test ISAPI direct upload, you need to:")
    print("   1. Add HikDevice in Django admin")
    print("   2. Configure device IP, username, password")
    print("   3. Ensure device has Face Library enabled")
    print("\n⚠️  This method works ONLY if:")
    print("   • Devices have direct IP access (not only via HCP)")
    print("   • Devices support ISAPI")
    print("   • Devices are not locked by HCP management")
    sys.exit(0)

for device in devices:
    print(f"\n   Device: {device.name}")
    print(f"   Host: {device.host}:{device.port}")
    print(f"   Enabled: {device.enabled}")
    print(f"   Primary: {device.is_primary}")

# Use test photo directly
test_photo_path = r"D:\university_visitor_system\visitor_system\media\guest_photos\pavel.jpg"

print(f"\n✓ Using test photo: {test_photo_path}")

if not os.path.exists(test_photo_path):
    print(f"❌ Photo file not found!")
    print(f"   Please ensure test photo exists at: {test_photo_path}")
    sys.exit(1)
    
with open(test_photo_path, 'rb') as f:
    image_bytes = f.read()
print(f"✓ Photo size: {len(image_bytes)} bytes")

# Get test person ID
test_person_id = "190"  # Guest ID as person ID
print(f"✓ Test person ID: {test_person_id}")

print("\n" + "=" * 80)
print("🧪 Testing ISAPI Upload to Each Device")
print("=" * 80)

for device in devices:
    if not device.enabled:
        print(f"\n⏭️  Skipping disabled device: {device.name}")
        continue
        
    print(f"\n📡 Testing device: {device.name} ({device.host}:{device.port})")
    
    try:
        # Create ISAPI session
        session = HikSession(device)
        print(f"   ✓ Session created")
        
        # Test if device is accessible
        try:
            test_response = session.get('/ISAPI/System/deviceInfo')
            if test_response.status_code == 200:
                print(f"   ✓ Device accessible via ISAPI")
            else:
                print(f"   ⚠️  Device returned status {test_response.status_code}")
                continue
        except Exception as e:
            print(f"   ❌ Cannot connect to device: {e}")
            continue
        
        # Try to upload photo
        print(f"\n   🔄 Attempting photo upload via ISAPI...")
        
        # upload_face_isapi(device, person_code, image_bytes) -> bool
        result = upload_face_isapi(device, test_person_id, image_bytes)
        print(f"   📊 Upload result: {result}")
        
        if "error" not in result.lower() and "status" not in result.lower():
            print(f"   ✅ Photo uploaded successfully to {device.name}!")
            print(f"\n💡 ISAPI direct upload WORKS for this device!")
            print(f"   This can be used as alternative to HCP API")
        else:
            print(f"   ⚠️  Upload returned: {result}")
            
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("📝 Summary and Recommendations")
print("=" * 80)

print("""
If ISAPI direct upload works:
✅ You can use direct device integration (bypass HCP API)
   Pros:
   • No HCP version limitation
   • Direct control over devices
   • Faster response
   
   Cons:
   • Need to manage each device separately
   • No centralized management via HCP
   • May conflict with HCP if both try to manage same device
   
If ISAPI direct upload fails:
❌ Options:
   1. Update HCP to newer version (RECOMMENDED)
   2. Manual photo upload via HCP UI
   3. Contact Hikvision support

Current setup analysis:
• HCP API: ❌ Not working (old version)
• ISAPI Direct: ⚠️  Test results above
• Manual Upload: ✅ Always works
""")

print("\n" + "=" * 80)
print("🎯 Final Answer to 'Нужна лицензия покупать?'")
print("=" * 80)
print("""
НЕТ, лицензию покупать НЕ нужно!

Проблема НЕ в лицензии, а в версии HikCentral Professional.

Решения (в порядке приоритета):

1. 🔄 ОБНОВИТЬ HCP (Best option)
   • Бесплатное обновление ПО
   • Получите современные API
   • Полная автоматизация

2. 🔧 ISAPI Direct (If devices accessible)
   • Результаты теста выше
   • Работает в обход HCP
   • Требует настройки устройств

3. 👤 Manual Upload (Current)
   • Работает всегда
   • Требует ручной работы
   • Временное решение

❌ Лицензия НЕ решит проблему - у вас уже есть все необходимые права!
✅ Нужно только обновление ПО HCP или использование ISAPI напрямую
""")
