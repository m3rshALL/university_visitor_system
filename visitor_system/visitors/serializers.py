from rest_framework import serializers
from .models import Visit, StudentVisit


class VisitListSerializer(serializers.ModelSerializer):
    guest_name = serializers.CharField(source='guest.full_name')
    department = serializers.CharField(source='department.name')
    employee = serializers.SerializerMethodField()

    class Meta:
        model = Visit
        fields = (
            'id', 'status', 'entry_time', 'exit_time', 'purpose',
            'guest_name', 'department', 'employee'
        )

    def get_employee(self, obj):
        try:
            full = obj.employee.get_full_name()
            return full or obj.employee.username
        except Exception:
            return None


class StudentVisitListSerializer(serializers.ModelSerializer):
    guest_name = serializers.CharField(source='guest.full_name')
    department = serializers.CharField(source='department.name')

    class Meta:
        model = StudentVisit
        fields = (
            'id', 'status', 'entry_time', 'exit_time', 'purpose',
            'guest_name', 'department'
        )


