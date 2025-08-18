from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from departments.models import Department
from visitors.models import EmployeeProfile


User = get_user_model()


class UniversityAccountAdapter(DefaultAccountAdapter):
	"""Расширение стандартного адаптера при создании/обновлении User."""
	pass


class UniversitySocialAccountAdapter(DefaultSocialAccountAdapter):
	"""Адаптер для обогащения профиля из данных Microsoft (Azure AD)."""

	def populate_user(self, request, sociallogin, data):
		user = super().populate_user(request, sociallogin, data)
		# Мягкое заполнение ФИО/Email, если есть поля
		first_name = data.get('given_name') or data.get('givenName') or data.get('first_name')
		last_name = data.get('family_name') or data.get('surname') or data.get('last_name')
		email = data.get('email') or data.get('mail') or data.get('preferred_username')
		if first_name and not user.first_name:
			user.first_name = first_name
		if last_name and not user.last_name:
			user.last_name = last_name
		if email and not user.email:
			user.email = email
		return user

	def save_user(self, request, sociallogin, form=None):
		user = super().save_user(request, sociallogin, form)
		# После сохранения пользователя обогатим профиль сотрудника
		try:
			social_account = sociallogin.account  # type: SocialAccount
			extra = social_account.extra_data or {}
			department_name = extra.get('department') or extra.get('Department')
			phone = extra.get('telephoneNumber') or extra.get('mobilePhone') or extra.get('phone')
			profile, _ = EmployeeProfile.objects.get_or_create(user=user)
			if phone and not profile.phone_number:
				profile.phone_number = phone
			if department_name and not profile.department:
				try:
					dept = Department.objects.filter(name__iexact=department_name).first()
					if dept:
						profile.department = dept
				except Exception:
					pass
			profile.save()
		except Exception:
			# Не прерываем вход при ошибках маппинга
			pass
		return user


