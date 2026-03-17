from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Meeting


class MeetingViewsTests(TestCase):
	def test_meetings_index_redirects_to_view(self):
		response = self.client.get("/meetings/")
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse("meetings:view"))

	def test_submit_meeting_creates_published_record(self):
		payload = {
			"title": "Youth Prayer Summit",
			"description": "Prayer and worship gathering.",
			"start_date": "2030-01-10",
			"end_date": "2030-01-11",
			"organizer_name": "Pastor Samuel",
			"estimated_attendance": 300,
			"organizer_phone": "9000011111",
			"address": "Main Road, Guntur",
			"district": "guntur",
			"state": "Andhra Pradesh",
			"meeting_type": "youth",
		}
		response = self.client.post(reverse("meetings:submit"), payload)
		self.assertEqual(response.status_code, 302)
		meeting = Meeting.objects.get(title="Youth Prayer Summit")
		self.assertTrue(meeting.is_published)

	def test_view_meetings_shows_only_published_upcoming(self):
		today = timezone.localdate()
		Meeting.objects.create(
			title="Visible Meeting",
			description="Public",
			start_date=today,
			end_date=today + timedelta(days=1),
			organizer_name="Organizer",
			estimated_attendance=100,
			organizer_phone="9000011111",
			address="Vizag",
			district="visakhapatnam",
			state="Andhra Pradesh",
			meeting_type="gospel",
			is_published=True,
		)
		Meeting.objects.create(
			title="Hidden Draft Meeting",
			description="Draft",
			start_date=today,
			end_date=today + timedelta(days=1),
			organizer_name="Draft Organizer",
			estimated_attendance=120,
			organizer_phone="9000011112",
			address="Vizag",
			district="visakhapatnam",
			state="Andhra Pradesh",
			meeting_type="gospel",
			is_published=False,
		)

		response = self.client.get(reverse("meetings:view"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Visible Meeting")
		self.assertNotContains(response, "Hidden Draft Meeting")

	def test_view_meetings_filters_by_district(self):
		today = timezone.localdate()
		Meeting.objects.create(
			title="Guntur Meeting",
			description="Public",
			start_date=today,
			end_date=today + timedelta(days=1),
			organizer_name="Organizer",
			estimated_attendance=100,
			organizer_phone="9000011111",
			address="Guntur",
			district="guntur",
			state="Andhra Pradesh",
			meeting_type="vbs",
			is_published=True,
		)
		Meeting.objects.create(
			title="Kurnool Meeting",
			description="Public",
			start_date=today,
			end_date=today + timedelta(days=1),
			organizer_name="Organizer",
			estimated_attendance=100,
			organizer_phone="9000011113",
			address="Kurnool",
			district="kurnool",
			state="Andhra Pradesh",
			meeting_type="vbs",
			is_published=True,
		)

		response = self.client.get(reverse("meetings:view"), {"district": "guntur"})
		self.assertContains(response, "Guntur Meeting")
		self.assertNotContains(response, "Kurnool Meeting")

	def test_meeting_detail_shows_published_meeting(self):
		today = timezone.localdate()
		meeting = Meeting.objects.create(
			title="Detail Meeting",
			description="Full event description",
			start_date=today,
			end_date=today + timedelta(days=1),
			organizer_name="Organizer",
			estimated_attendance=200,
			organizer_phone="9000011119",
			address="Guntur",
			district="guntur",
			state="Andhra Pradesh",
			meeting_type="vbs",
			is_published=True,
		)

		response = self.client.get(reverse("meetings:detail", kwargs={"meeting_id": meeting.id}))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Detail Meeting")
		self.assertContains(response, "Full event description")

	def test_meeting_detail_hides_unpublished_meeting(self):
		today = timezone.localdate()
		meeting = Meeting.objects.create(
			title="Hidden Detail Meeting",
			description="Should not be visible",
			start_date=today,
			end_date=today + timedelta(days=1),
			organizer_name="Organizer",
			estimated_attendance=200,
			organizer_phone="9000011120",
			address="Guntur",
			district="guntur",
			state="Andhra Pradesh",
			meeting_type="vbs",
			is_published=False,
		)

		response = self.client.get(reverse("meetings:detail", kwargs={"meeting_id": meeting.id}))
		self.assertEqual(response.status_code, 404)
