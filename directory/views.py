from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .forms import (
	BelieverRegistrationForm,
	ChurchRegistrationForm,
	OrganizationRegistrationForm,
	PastorRegistrationForm,
	StudentRegistrationForm,
)
from .models import DISTRICT_CHOICES, STATE_CHOICES, ChurchProfile, PastorProfile, get_profile_for_user


DISTRICT_CENTER_POINTS = {
	"Visakhapatnam": [17.6868, 83.2185],
	"Guntur": [16.3067, 80.4365],
	"Krishna": [16.4419, 80.6226],
	"Nellore": [14.4426, 79.9865],
	"Kurnool": [15.8281, 78.0373],
	"Srikakulam": [18.2949, 83.8938],
	"Chittoor": [13.2172, 79.1003],
}


def _float_or_none(value):
	if value is None:
		return None
	return float(value)


REGISTRATION_CONFIG = {
	"believer": {
		"title": "Believer Registration",
		"title_te": "విశ్వాసుల నమోదు",
		"form_class": BelieverRegistrationForm,
		"description": "Create a confidential believer profile for JBAC services and updates.",
	},
	"pastor": {
		"title": "Pastor Registration",
		"title_te": "పాస్టర్ నమోదు",
		"form_class": PastorRegistrationForm,
		"description": "Register a pastor profile for the searchable ministry directory.",
	},
	"student": {
		"title": "Student Registration",
		"title_te": "విద్యార్థుల నమోదు",
		"form_class": StudentRegistrationForm,
		"description": "Connect students with scholarships, mentorship, and council programs.",
	},
	"church": {
		"title": "Church Registration",
		"title_te": "చర్చి నమోదు",
		"form_class": ChurchRegistrationForm,
		"description": "List a church with ministry details, service location, and pastoral contact.",
	},
	"organization": {
		"title": "Organization Registration",
		"title_te": "సంస్థ నమోదు",
		"form_class": OrganizationRegistrationForm,
		"description": "Register associations, ministries, and Christian organizations in one flow.",
	},
}


def registration_landing(request):
	registrations = [
		{"slug": slug, **config}
		for slug, config in REGISTRATION_CONFIG.items()
	]
	return render(request, "directory/register_landing.html", {"registrations": registrations})


def register_category(request, category):
	config = REGISTRATION_CONFIG.get(category)
	if config is None:
		return redirect("directory:register")

	form_class = config["form_class"]
	if request.method == "POST":
		form = form_class(request.POST)
		if form.is_valid():
			profile = form.save()
			login(request, profile.user, backend=settings.AUTHENTICATION_BACKENDS[0])
			messages.success(request, "Registration submitted. An admin can approve directory visibility after review.")
			return redirect("core:dashboard")
	else:
		form = form_class()

	return render(
		request,
		"directory/registration_form.html",
		{
			"form": form,
			"category": category,
			"config": config,
		},
	)


def search_directory(request):
	directory_type = request.GET.get("type", "all")
	query = request.GET.get("query", "").strip()
	district = request.GET.get("district", "").strip()
	state = request.GET.get("state", "").strip()

	pastors = PastorProfile.objects.filter(is_approved=True, is_public=True).select_related("user")
	churches = ChurchProfile.objects.filter(is_approved=True, is_public=True).select_related("user")

	if query:
		pastors = pastors.filter(
			Q(pastor_name__icontains=query)
			| Q(church_name__icontains=query)
			| Q(user__mobile_number__icontains=query)
		)
		churches = churches.filter(
			Q(church_name__icontains=query)
			| Q(pastor_name__icontains=query)
			| Q(village__icontains=query)
			| Q(user__mobile_number__icontains=query)
		)

	if district:
		pastors = pastors.filter(district=district)
		churches = churches.filter(district=district)

	if state:
		pastors = pastors.filter(state=state)
		churches = churches.filter(state=state)

	if directory_type == "pastor":
		churches = churches.none()
	elif directory_type == "church":
		pastors = pastors.none()

	return render(
		request,
		"directory/search.html",
		{
			"directory_type": directory_type,
			"query": query,
			"district": district,
			"state": state,
			"district_choices": DISTRICT_CHOICES,
			"state_choices": STATE_CHOICES,
			"pastors": pastors[:24],
			"churches": churches[:24],
		},
	)


def map_search(request):
	district = request.GET.get("district", "").strip()
	state = request.GET.get("state", "Andhra Pradesh").strip() or "Andhra Pradesh"

	churches = ChurchProfile.objects.filter(
		is_approved=True,
		is_public=True,
		latitude__isnull=False,
		longitude__isnull=False,
	)

	if district:
		churches = churches.filter(district=district)
	if state:
		churches = churches.filter(state=state)

	markers = []
	for church in churches[:200]:
		markers.append(
			{
				"name": church.church_name,
				"pastor": church.pastor_name,
				"district": church.district,
				"state": church.state,
				"lat": _float_or_none(church.latitude),
				"lng": _float_or_none(church.longitude),
			}
		)

	district_center = DISTRICT_CENTER_POINTS.get(district, [15.9129, 79.74])
	return render(
		request,
		"directory/map_search.html",
		{
			"district": district,
			"state": state,
			"district_choices": DISTRICT_CHOICES,
			"state_choices": STATE_CHOICES,
			"markers": markers,
			"district_center": district_center,
		},
	)


@login_required
def member_id_pdf(request):
	profile = get_profile_for_user(request.user)
	buffer = BytesIO()
	pdf = canvas.Canvas(buffer, pagesize=A6)

	pdf.setFillColor(colors.HexColor("#163126"))
	pdf.rect(0, 0, A6[0], A6[1], stroke=0, fill=1)

	pdf.setFillColor(colors.white)
	pdf.setFont("Helvetica-Bold", 16)
	pdf.drawString(12 * mm, 94 * mm, "JBAC Member ID")

	pdf.setFont("Helvetica", 10)
	pdf.drawString(12 * mm, 86 * mm, "Jesus Believers Association Council")
	pdf.drawString(12 * mm, 80 * mm, "Andhra Pradesh")

	pdf.setFillColor(colors.HexColor("#f6efe4"))
	pdf.roundRect(10 * mm, 32 * mm, 85 * mm, 42 * mm, 4 * mm, stroke=0, fill=1)

	pdf.setFillColor(colors.HexColor("#1b1b17"))
	pdf.setFont("Helvetica-Bold", 11)
	pdf.drawString(14 * mm, 68 * mm, f"Name: {request.user.display_name[:30]}")
	pdf.drawString(14 * mm, 62 * mm, f"Member ID: {request.user.member_id or 'NA'}")
	pdf.drawString(14 * mm, 56 * mm, f"Category: {request.user.get_role_display()[:28]}")
	pdf.setFont("Helvetica", 10)
	pdf.drawString(14 * mm, 50 * mm, f"Mobile: {request.user.mobile_number}")

	if profile and getattr(profile, "is_approved", False):
		status_line = "Status: Approved"
	else:
		status_line = "Status: Pending approval"
	pdf.drawString(14 * mm, 44 * mm, status_line)

	pdf.setFont("Helvetica-Oblique", 8)
	pdf.drawString(12 * mm, 20 * mm, "This card is generated from jbac.in")

	pdf.showPage()
	pdf.save()
	buffer.seek(0)

	response = HttpResponse(buffer.read(), content_type="application/pdf")
	response["Content-Disposition"] = 'attachment; filename="jbac-member-id.pdf"'
	return response
