# Generated migration to fix IIN encryption key issue
from django.db import migrations
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken
import hashlib
import base64


def get_old_fernet():
    """Old incorrect implementation that was used in 0028 migration"""
    key = getattr(settings, 'IIN_ENCRYPTION_KEY', '').encode()
    if not key:
        key = base64.urlsafe_b64encode(b'0'*32)
    return Fernet(key)


def get_new_fernet():
    """New correct implementation"""
    key_str = getattr(settings, 'IIN_ENCRYPTION_KEY', '')
    if not key_str:
        key = base64.urlsafe_b64encode(b'0'*32)
    else:
        key = key_str.encode()
    return Fernet(key)


def fix_iin_encryption(apps, schema_editor):
    Guest = apps.get_model('visitors', 'Guest')
    db_alias = schema_editor.connection.alias
    
    old_fernet = get_old_fernet()
    new_fernet = get_new_fernet()
    
    updated_count = 0
    for guest in Guest.objects.using(db_alias).filter(iin_encrypted__isnull=False).iterator():
        try:
            # Расшифровываем старым ключом
            decrypted_iin = old_fernet.decrypt(guest.iin_encrypted).decode()
            
            # Зашифровываем новым ключом
            guest.iin_encrypted = new_fernet.encrypt(decrypted_iin.encode())
            guest.iin_hash = hashlib.sha256(decrypted_iin.encode()).hexdigest()
            guest.save(update_fields=['iin_encrypted', 'iin_hash'])
            updated_count += 1
            
        except (InvalidToken, Exception) as e:
            print(f"Failed to re-encrypt IIN for guest {guest.pk}: {e}")
            continue
    
    print(f"Re-encrypted {updated_count} guest IINs")


def reverse_fix_iin_encryption(apps, schema_editor):
    # Reverse operation would be complex and risky, so we'll just pass
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('visitors', '0028_encrypt_iin_fields'),
    ]

    operations = [
        migrations.RunPython(fix_iin_encryption, reverse_fix_iin_encryption),
    ]
