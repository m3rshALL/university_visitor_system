from django.db import migrations, models
from django.conf import settings
from cryptography.fernet import Fernet
import hashlib
import base64


def get_fernet():
    key = getattr(settings, 'IIN_ENCRYPTION_KEY', '').encode()
    if not key:
        key = base64.urlsafe_b64encode(b'0'*32)
    return Fernet(key)


def forwards_encrypt_iin(apps, schema_editor):
    Guest = apps.get_model('visitors', 'Guest')
    db_alias = schema_editor.connection.alias
    f = get_fernet()
    for guest in Guest.objects.using(db_alias).all().iterator():
        # Миграция старого поля guest.iin (если было) в iin_encrypted/iin_hash
        raw_iin = getattr(guest, 'iin', None)
        if raw_iin and isinstance(raw_iin, str) and raw_iin.isdigit() and len(raw_iin) == 12:
            try:
                enc = f.encrypt(raw_iin.encode())
                setattr(guest, 'iin_encrypted', enc)
                setattr(guest, 'iin_hash', hashlib.sha256(raw_iin.encode()).hexdigest())
                guest.save(update_fields=['iin_encrypted', 'iin_hash'])
            except Exception:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('visitors', '0027_studentvisit_student_visit_status_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='guest',
            name='iin_encrypted',
            field=models.BinaryField(blank=True, null=True, editable=False, verbose_name='Зашифрованный ИИН'),
        ),
        migrations.AddField(
            model_name='guest',
            name='iin_hash',
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=64, null=True, verbose_name='Хэш ИИН (поиск)'),
        ),
        migrations.AddField(
            model_name='guestinvitation',
            name='guest_iin_last4',
            field=models.CharField(blank=True, editable=False, max_length=4, null=True),
        ),
        migrations.AddField(
            model_name='groupguest',
            name='iin_last4',
            field=models.CharField(blank=True, editable=False, max_length=4, null=True),
        ),
        migrations.RunPython(forwards_encrypt_iin, migrations.RunPython.noop),
    ]


