from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory
from .models import (
    Device,
    DevicePruefung,
    Pruefart,
    PracticeSettings,
    DeviceDocument,
    DocumentType,
    GeneralDocument,
    Filterwechsel,
    Geraetart,
    HomeInformation,
    HomeImage,
    Reparatur,
    TechnicianDocument,
    DashboardWidget,
)


class DeviceForm(forms.ModelForm):

    year_built = forms.CharField(
        label="Baujahr",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "z.B. 2024",
                "class": "form-control"
            }
        )
    )

    class Meta:

        model = Device

        fields = [
            "geraetart",
            "name",
            "inventory_number",
            "serial_number",
            "ec_number",
            "software_version",
            "operating_hours",
            "manufacturer",
            "year_built",
            "practice",
            "area",
            "room",
            "status",
            "image",
            "notes",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "geraetart": forms.Select(
                attrs={"class": "form-control"}
            ),

            "inventory_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "serial_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "ec_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "software_version": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "operating_hours": forms.NumberInput(
                attrs={"class": "form-control"}
            ),

            "manufacturer": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "practice": forms.Select(
                attrs={"class": "form-control"}
            ),

            "area": forms.Select(
                attrs={"class": "form-control"}
            ),

            "room": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "status": forms.Select(
                attrs={"class": "form-control"}
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        geraetart = kwargs.pop("geraetart", None)

        super().__init__(*args, **kwargs)

        # Betriebsstunden nur bei Dialyse Maschinen
        if geraetart and geraetart.name != "Dialyse Maschinen":
            self.fields.pop("operating_hours", None)

        required_fields = [
            "geraetart",
            "name",
            "inventory_number",
            "serial_number",
            "manufacturer",
            "year_built",
            "practice",
            "area",
        ]

        for field in required_fields:
            if field in self.fields:
                self.fields[field].required = True

        if "room" in self.fields:
            self.fields["room"].required = False

        if "operating_hours" in self.fields:
            self.fields["operating_hours"].required = False

    def clean(self):

        cleaned_data = super().clean()

        geraetart = cleaned_data.get("geraetart")
        room = cleaned_data.get("room")

        # Dialyse Betten brauchen einen Raum
        if (
            geraetart
            and geraetart.name == "Dialyse Betten"
            and not room
        ):
            self.add_error(
                "room",
                "Bei Dialyse Betten muss der Raum angegeben werden."
            )

        # Dialyse Maschinen
        if geraetart and geraetart.name == "Dialyse Maschinen":

            if not cleaned_data.get("ec_number"):
                self.add_error(
                    "ec_number",
                    "Bei Dialyse Maschinen ist die EC-Nummer erforderlich."
                )

            if not cleaned_data.get("software_version"):
                self.add_error(
                    "software_version",
                    "Bei Dialyse Maschinen ist die Software-Version erforderlich."
                )

            if "operating_hours" in self.fields:

                if not cleaned_data.get("operating_hours"):
                    self.add_error(
                        "operating_hours",
                        "Bei Dialyse Maschinen sind die Betriebsstunden erforderlich."
                    )

        return cleaned_data



from django import forms
from .models import Geraetart, DeviceDetailFieldConfig


class DeviceDetailSettingsForm(forms.Form):

    geraetart = forms.ModelChoiceField(
        queryset=Geraetart.objects.all(),
        required=True,
        label="Gerätart"
    )

    fields = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=DeviceDetailFieldConfig.FIELD_CHOICES,
        label="Anzuzeigende Felder"
    )

    
class DevicePruefungForm(forms.ModelForm):

    class Meta:
        model = DevicePruefung

        fields = [
            "pruefart",
            "letztes_datum",
        ]

        widgets = {

            "pruefart": forms.Select(
                attrs={
                    "class": "form-control pruefart-select",
                }
            ),

            "letztes_datum": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "form-control pruefung-date",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["pruefart"].queryset = (
            Pruefart.objects
            .filter(aktiv=True)
            .order_by("order", "name")
        )

        self.fields["letztes_datum"].input_formats = [
            "%Y-%m-%d"
        ]
DevicePruefungFormSet = forms.inlineformset_factory(
    Device,
    DevicePruefung,
    form=DevicePruefungForm,
    extra=0,
    can_delete=True
)

class PruefartForm(forms.ModelForm):

    class Meta:
        model = Pruefart

        fields = [
            "name",
            "intervall_jahre",
            "aktiv",
            "order",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "z.B. STK, MTK, UVV"
                }
            ),

            "intervall_jahre": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "aktiv": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": "form-control"
                }
            ),
        }

class PracticeSettingsForm(forms.ModelForm):

    class Meta:

        model = PracticeSettings

        fields = [
            "practice_name",
            "contact_person",
            "email",
            "phone",
            "address",
        ]


class DeviceDocumentForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["document_type"].queryset = DocumentType.objects.all().order_by("order")

    class Meta:

        model = DeviceDocument

        fields = [
            "document_type",
            "file",
            "display_name",
            "notes",
        ]

        widgets = {

            "document_type": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "display_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Neuer Dokumentname (optional)"
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }

class GeneralDocumentForm(forms.ModelForm):

    class Meta:

        model = GeneralDocument

        fields = [
            "file",
        ]

        widgets = {

            "file": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            )

        }


class ReparaturForm(forms.ModelForm):

    class Meta:
        model = Reparatur

        fields = [
            "geraet",
            "beschreibung",
            "melder",
           
        ]

        widgets = {

            "geraet": forms.HiddenInput(),

            "beschreibung": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Problembeschreibung"
                }
            ),

            
        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["geraet"].required = True
        self.fields["beschreibung"].required = True
        self.fields["melder"].required = True

class ReparaturBearbeitenForm(forms.ModelForm):

    class Meta:

        model = Reparatur

        fields = [
            "geraet",
            "beschreibung",
            "melder",
            "status",
            "techniker",
            "reparatur_datum",
            "ausfuehrung",
            "reparaturbericht",
            "reparaturbild"
        ]

        widgets = {

            "geraet": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_geraet"
                }
            ),

            "beschreibung": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5
                }
            ),

            "melder": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "status-select"
                }
            ),

            "techniker": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "id_techniker"
                }
            ),

            "reparatur_datum": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "id": "id_reparatur_datum"
                }
            ),

            "ausfuehrung": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "id": "id_ausfuehrung"
                }
            ),
        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:

            self.initial["reparatur_datum"] = (
                self.instance.reparatur_datum
            )

from django import forms
from .models import Filterwechsel

class FilterwechselForm(forms.ModelForm):

    geraet = forms.ModelChoiceField(
        queryset=Device.objects.all(),
        label="Gerät",
        empty_label="Gerät auswählen"
    )

    class Meta:
        model = Filterwechsel

        fields = [
            "geraet",
            "anzahl_filter",
            "filtercode",
            "datum",
            "durchgeführt_von",
            "bemerkung",
        ]

        widgets = {

            "datum": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                }
            ),

            "bemerkung": forms.Textarea(
                attrs={
                    "rows": 4
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["datum"].input_formats = [
            "%Y-%m-%d"
        ]

        # Filtercode wird über filtercode_1, filtercode_2 ...
        # dynamisch im HTML eingegeben
        self.fields["filtercode"].required = False

class GeraetartForm(forms.ModelForm):

    class Meta:
        model = Geraetart

        fields = [
            "name",
            "aktiv",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Geräteart"
                }
            ),

            "aktiv": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),
        }

class TechnicianDocumentForm(forms.ModelForm):

    class Meta:
        model = TechnicianDocument

        fields = [
            "title",
            "category",
            "file",
            "notes",
        ]


class HomeInformationForm(forms.ModelForm):

    title = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Titel eingeben..."
            }
        )
    )

    class Meta:
        model = HomeInformation
        fields = ["title"]

        
from django import forms
from .models import DashboardWidget


class DashboardWidgetForm(forms.ModelForm):

    class Meta:
        model = DashboardWidget
        fields = [
            "widget_type",
            "title",
            "standort",
            "geraetart",
            "color",
            "order",
            "visible",
        ]

        widgets = {
            "widget_type": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "standort": forms.Select(attrs={"class": "form-control"}),
            "geraetart": forms.Select(attrs={"class": "form-control"}),
            "color": forms.Select(attrs={"class": "form-control"}),
            "icon": forms.Select(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "visible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }