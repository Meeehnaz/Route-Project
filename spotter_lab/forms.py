from django import forms

class RouteForm(forms.Form):
    origin = forms.CharField(label='Origin', max_length=255)
    destination = forms.CharField(label='Destination', max_length=255)
