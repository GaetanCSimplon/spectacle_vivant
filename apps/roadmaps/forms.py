from django import forms

from apps.gigs.models import GigMember

from .models import Lodging, Meal, Roadmap, RoadmapSlot

TIME_FORMAT = "%H:%M"


def _time_widget():
    return forms.TimeInput(attrs={"type": "time"}, format=TIME_FORMAT)


class NotesForm(forms.ModelForm):
    class Meta:
        model = Roadmap
        fields = ["notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}


class SlotForm(forms.ModelForm):
    class Meta:
        model = RoadmapSlot
        fields = ["kind", "time", "label", "note"]
        widgets = {"time": _time_widget(), "note": forms.Textarea(attrs={"rows": 2})}


class LodgingForm(forms.ModelForm):
    class Meta:
        model = Lodging
        fields = ["name", "address", "arrival_time", "notes"]
        widgets = {"arrival_time": _time_widget(), "notes": forms.Textarea(attrs={"rows": 2})}


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ["place", "time", "notes"]
        widgets = {"time": _time_widget(), "notes": forms.Textarea(attrs={"rows": 2})}


class MemberForm(forms.ModelForm):
    class Meta:
        model = GigMember
        fields = ["name", "role", "phone", "email"]
        widgets = {"role": forms.TextInput(attrs={"list": "member-roles"})}
