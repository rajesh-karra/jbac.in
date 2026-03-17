from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import (
	BelieverProfile,
	ChurchProfile,
	OrganizationProfile,
	PastorProfile,
	StudentProfile,
)


class MemberIdPdfTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			mobile_number="9000000004",
			email="believer@example.com",
			password="Secret123!",
			role=User.Role.BELIEVER,
		)
		BelieverProfile.objects.create(
			user=self.user,
			full_name="Rajesh Kumar",
			gender="male",
			is_approved=True,
		)

	def test_member_id_pdf_requires_login(self):
		response = self.client.get(reverse("directory:member-id"))
		self.assertEqual(response.status_code, 302)

	def test_member_id_pdf_download(self):
		self.client.login(mobile_number=self.user.mobile_number, password="Secret123!")
		response = self.client.get(reverse("directory:member-id"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "application/pdf")
		self.assertIn("attachment; filename=\"jbac-member-id.pdf\"", response["Content-Disposition"])
		self.assertTrue(response.content.startswith(b"%PDF"))


class RegistrationFlowTests(TestCase):
	def test_believer_registration(self):
		response = self.client.post(
			reverse("directory:register-category", kwargs={"category": "believer"}),
			{
				"full_name": "Believer One",
				"gender": "male",
				"whatsapp_number": "9110000001",
				"date_of_birth": "1998-01-01",
				"life_goal": "Serve",
				"hobbies": "Music",
				"youtube_channel": "",
				"additional_information": "",
				"mobile_number": "9100001001",
				"email": "believer-flow@example.com",
				"password1": "Secret123!",
				"password2": "Secret123!",
				"consent": "on",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse("core:dashboard"))
		self.assertTrue(User.objects.filter(mobile_number="9100001001", role=User.Role.BELIEVER).exists())
		self.assertTrue(BelieverProfile.objects.filter(user__mobile_number="9100001001").exists())

	def test_pastor_registration(self):
		response = self.client.post(
			reverse("directory:register-category", kwargs={"category": "pastor"}),
			{
				"pastor_name": "Pastor One",
				"gender": "male",
				"church_name": "Grace Church",
				"church_address": "Main Street",
				"district": "Guntur",
				"state": "Andhra Pradesh",
				"latitude": "16.30",
				"longitude": "80.43",
				"years_of_ministry": "12",
				"additional_information": "",
				"mobile_number": "9100001002",
				"email": "pastor-flow@example.com",
				"password1": "Secret123!",
				"password2": "Secret123!",
				"consent": "on",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse("core:dashboard"))
		self.assertTrue(User.objects.filter(mobile_number="9100001002", role=User.Role.PASTOR).exists())
		self.assertTrue(PastorProfile.objects.filter(user__mobile_number="9100001002").exists())

	def test_student_registration(self):
		response = self.client.post(
			reverse("directory:register-category", kwargs={"category": "student"}),
			{
				"student_name": "Student One",
				"gender": "female",
				"college_name": "ABC College",
				"course": "BSc",
				"year_of_study": "2nd",
				"district": "Guntur",
				"state": "Andhra Pradesh",
				"mobile_number": "9100001003",
				"email": "student-flow@example.com",
				"password1": "Secret123!",
				"password2": "Secret123!",
				"consent": "on",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse("core:dashboard"))
		self.assertTrue(User.objects.filter(mobile_number="9100001003", role=User.Role.STUDENT).exists())
		self.assertTrue(StudentProfile.objects.filter(user__mobile_number="9100001003").exists())

	def test_church_registration(self):
		response = self.client.post(
			reverse("directory:register-category", kwargs={"category": "church"}),
			{
				"church_name": "Hope Church",
				"pastor_name": "Pastor Hope",
				"address": "Village Road",
				"village": "Hope Village",
				"district": "Guntur",
				"state": "Andhra Pradesh",
				"latitude": "16.31",
				"longitude": "80.44",
				"year_established": "2000",
				"ministry_details": "Youth ministry",
				"mobile_number": "9100001004",
				"email": "church-flow@example.com",
				"password1": "Secret123!",
				"password2": "Secret123!",
				"consent": "on",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse("core:dashboard"))
		self.assertTrue(User.objects.filter(mobile_number="9100001004", role=User.Role.CHURCH).exists())
		self.assertTrue(ChurchProfile.objects.filter(user__mobile_number="9100001004").exists())

	def test_organization_registration(self):
		response = self.client.post(
			reverse("directory:register-category", kwargs={"category": "organization"}),
			{
				"organization_name": "Service Org",
				"founder_name": "Founder One",
				"address": "Mission Street",
				"district": "Guntur",
				"state": "Andhra Pradesh",
				"website": "",
				"ministry_type": "Training",
				"organization_role": User.Role.ORGANIZATION,
				"mobile_number": "9100001005",
				"email": "organization-flow@example.com",
				"password1": "Secret123!",
				"password2": "Secret123!",
				"consent": "on",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse("core:dashboard"))
		self.assertTrue(
			User.objects.filter(mobile_number="9100001005", role=User.Role.ORGANIZATION).exists()
		)
		self.assertTrue(OrganizationProfile.objects.filter(user__mobile_number="9100001005").exists())
