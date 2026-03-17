from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import MeetingFilterForm, MeetingSubmissionForm
from .models import Meeting


def submit_meeting(request):
	if request.method == "POST":
		form = MeetingSubmissionForm(request.POST, request.FILES)
		if form.is_valid():
			meeting = form.save(commit=False)
			meeting.is_published = True
			meeting.save()
			messages.success(
				request,
				"Meeting details submitted successfully. The meeting is now visible on the View Meetings page.",
			)
			return redirect("meetings:submit")
	else:
		form = MeetingSubmissionForm(initial={"state": "Andhra Pradesh"})

	return render(request, "meetings/submit_meeting.html", {"form": form})


def view_meetings(request):
	queryset = Meeting.objects.filter(is_published=True, end_date__gte=timezone.localdate())
	form = MeetingFilterForm(request.GET or None)

	if form.is_valid():
		meeting_type = form.cleaned_data.get("meeting_type")
		denomination = form.cleaned_data.get("denomination")
		ministry = form.cleaned_data.get("ministry")
		date_value = form.cleaned_data.get("date")
		district = form.cleaned_data.get("district")
		city_area = form.cleaned_data.get("city_area")
		mandal = form.cleaned_data.get("mandal")
		village = form.cleaned_data.get("village")

		if meeting_type:
			queryset = queryset.filter(meeting_type=meeting_type)
		if denomination:
			queryset = queryset.filter(denomination=denomination)
		if ministry:
			queryset = queryset.filter(ministry=ministry)
		if date_value:
			queryset = queryset.filter(start_date__lte=date_value, end_date__gte=date_value)
		if district:
			queryset = queryset.filter(district=district)
		if city_area:
			queryset = queryset.filter(city_area__icontains=city_area)
		if mandal:
			queryset = queryset.filter(mandal__icontains=mandal)
		if village:
			queryset = queryset.filter(village__icontains=village)

		location_term = request.GET.get("location", "").strip()
		if location_term:
			queryset = queryset.filter(
				Q(address__icontains=location_term)
				| Q(city_area__icontains=location_term)
				| Q(mandal__icontains=location_term)
				| Q(village__icontains=location_term)
			)

	meetings = queryset.order_by("start_date", "title")
	return render(request, "meetings/view_meetings.html", {"form": form, "meetings": meetings})


def meeting_detail(request, meeting_id):
	meeting = get_object_or_404(Meeting, id=meeting_id, is_published=True)
	return render(request, "meetings/meeting_detail.html", {"meeting": meeting})
