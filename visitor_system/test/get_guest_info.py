import os
import sys
import django
from pathlib import Path

# Настройка окружения Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')
django.setup()

from visitors.models import Guest, Visit, GuestInvitation
from hikvision_integration.models import HikPersonBinding

def get_guest_info(guest_id):
    try:
        guest = Guest.objects.get(id=guest_id)
        print(f"Guest ID: {guest.id}")
        print(f"Name: {guest.full_name}")
        
        # Получаем все визиты гостя
        visits = Visit.objects.filter(guest=guest)
        print(f"Total visits: {visits.count()}")
        for i, visit in enumerate(visits):
            print(f"  Visit {i+1} - ID: {visit.id}, Date: {getattr(visit, 'entry_time', None)}")
            
            # Получаем приглашения для этого визита
            invitations = GuestInvitation.objects.filter(visit=visit)
            print(f"    Invitations: {invitations.count()}")
            for j, invitation in enumerate(invitations):
                print(f"      Invitation {j+1} - ID: {invitation.id}, Has photo: {bool(invitation.guest_photo)}")
                if invitation.guest_photo:
                    print(f"        Photo path: {invitation.guest_photo.path}")
        
        # Получаем привязки к HikCentral
        bindings = HikPersonBinding.objects.filter(guest_id=guest_id)
        print(f"\nHikCentral bindings: {bindings.count()}")
        for i, binding in enumerate(bindings):
            print(f"  Binding {i+1} - Person ID: {binding.person_id}, Face ID: {binding.face_id or 'None'}")
            print(f"    Created: {binding.created_at}, Updated: {binding.updated_at}")
        
    except Guest.DoesNotExist:
        print(f"Guest with ID {guest_id} not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python get_guest_info.py <guest_id>")
        sys.exit(1)
    
    guest_id = int(sys.argv[1])
    get_guest_info(guest_id)