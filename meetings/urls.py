from django.urls import path
from django.views.generic import RedirectView

from .views import meeting_detail, submit_meeting, view_meetings

app_name = "meetings"

urlpatterns = [
	path("", RedirectView.as_view(pattern_name="meetings:view", permanent=False)),
	path("submit/", submit_meeting, name="submit"),
	path("view/", view_meetings, name="view"),
	path("view/<int:meeting_id>/", meeting_detail, name="detail"),
]
