from django import forms
from .models import Reparatur, TechnicianDocument
from django.db.models import Q



from .models import (
    Device,
    PracticeSettings,
    DeviceDocument,
    DocumentType,
    GeneralDocument,
    Filterwechsel,
    Geraetart,
    HomeInformation,
    HomeImage,

)


class DeviceForm(forms.ModelForm):
    year_built = forms.CharField(
        label="Baujahr",
        required=False,
        widget=forms.TextInput(
            attrs={
                 "placeholder": "z.B. 2024"
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
            "last_stk",
            "last_mtk",
            "last_dguv",
            "status",
            "image",
            "notes",
        ]

        widgets = {

            "name": forms.TextInput(),

            "last_stk": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),

            "last_mtk": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),

            "last_dguv": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):

        geraetart= kwargs.pop("geraetart", None)

        super().__init__(*args, **kwargs)

        if geraetart and geraetart.name!= "Dialyse Maschinen":
             self.fields.pop("operating_hours", None)

  

        if self.instance and self.instance.pk:
            self.initial["last_stk"] = self.instance.last_stk
            self.initial["last_mtk"] = self.instance.last_mtk
            self.initial["last_dguv"] = self.instance.last_dguv

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
            self.fields[field].required = True

        if "next_stk" in self.fields:
           self.fields["next_stk"].required = False

        if "next_mtk" in self.fields:
           self.fields["next_mtk"].required = False

        if "next_dguv" in self.fields:
           self.fields["next_dguv"].required = False

        self.fields["room"].required = False
        if "operating_hours" in self.fields:
            self.fields["operating_hours"].required = False

        

    def clean(self):

        cleaned_data = super().clean()

        geraetart = cleaned_data.get("geraetart")

        room = cleaned_data.get("room")

        last_stk = cleaned_data.get("last_stk")
        last_mtk = cleaned_data.get("last_mtk")
        last_dguv = cleaned_data.get("last_dguv")

        if (
            geraetart
            and geraetart.braucht_pruefung
            and not last_stk
            and not last_mtk
            and not last_dguv
        ):
            raise forms.ValidationError(
                "Bitte mindestens eine Prüfung eingeben: STK, MTK oder DGUV V3."
            )
        if geraetart and geraetart.name == "Dialyse Betten" and not room:
            self.add_error(
                "room",
                "Bei Dialyse Betten muss der Raum angegeben werden."
            )

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
            self.initial["reparatur_datum"] = self.instance.reparatur_datum


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

class GeraetartForm(forms.ModelForm):

    class Meta:
        model = Geraetart

        fields = [
            "name",
            "aktiv",
            "braucht_pruefung",
        ] 

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