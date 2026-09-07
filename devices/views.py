from pathlib import Path
from django.urls import reverse
import os
import re
import json
import shutil
import subprocess
from devices.services.git_service import GitService
from devices.services.update_service import UpdateService
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import update_session_auth_hash
from django.db.models import (
    Count,
    Q,
    Sum,
    Case,
    When,
    Value,
    IntegerField,
)

from django.http import (
    FileResponse,
    Http404,
    JsonResponse,
)

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


from .models import (
    Device,
    DeviceDetailFieldConfig,
    DevicePruefung,
    Pruefart,
    Reparatur,
    Messmittel,
    PracticeSettings,
    DeviceDocument,
    GeneralDocument,
    Rechnung,
    RechnungKategorie,
    UserProfile,
    UserPermission,
    HomeInformation,
    HomeImage,
    Standort,
    Filterwechsel,
    Geraetart,
    TechnicianDocument,
    DocumentType,
    DashboardSettings,
    CompanyInformation,
    AuditLog,
    ContactInformation,
    ContactImage,
    DashboardWidget,
)


from .forms import (
    DeviceForm,
    DevicePruefungForm,
    DevicePruefungFormSet,
    PruefartForm,
    PracticeSettingsForm,
    DeviceDocumentForm,
    GeneralDocumentForm,
    FilterwechselForm,
    GeraetartForm,
    TechnicianDocumentForm,
    HomeInformationForm,
    ReparaturForm,
    ReparaturBearbeitenForm,
)

def rechnung_permission_required(view_func):

    @login_required
    def wrapper(request, *args, **kwargs):

        # Superuser darf immer auf Rechnung zugreifen
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Benutzer mit Rechnung-Berechtigung
        if request.user.has_perm(
            "devices.access_rechnung"
        ):
            return view_func(request, *args, **kwargs)

        # Keine Berechtigung
        return render(
            request,
            "403.html",
            status=403
        )

    return wrapper

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("home")

        else:
            return render(
                request,
                "registration/login.html",
                {"error": "Benutzername oder Passwort falsch"}
            )

    return render(
        request,
        "registration/login.html"
    )
@login_required
def home(request):

    create_daily_backup()

    home, created = HomeInformation.objects.get_or_create(
        user=request.user
    )

    return render(
        request,
        "devices/home.html",
        {
            "home": home,
        },
    )

@login_required
def home_edit(request):

    home, created = HomeInformation.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        form = HomeInformationForm(
            request.POST,
            instance=home
        )

        if form.is_valid():

            home = form.save()

            # =====================================================
            # حذف الصور المحددة
            # =====================================================

            if "delete_selected" in request.POST:

                delete_ids = request.POST.getlist(
                    "delete_images"
                )

                HomeImage.objects.filter(
                    id__in=delete_ids,
                    home=home
                ).delete()

            # =====================================================
            # إضافة الصور الجديدة
            # =====================================================

            images = request.FILES.getlist("images")

            for image in images:

                HomeImage.objects.create(
                    home=home,
                    image=image
                )

            messages.success(
                request,
                "Startseite erfolgreich aktualisiert."
            )

            return redirect("home_edit")

    else:

        form = HomeInformationForm(
            instance=home
        )

    return render(
        request,
        "devices/home_edit.html",
        {
            "form": form,
            "home": home,
        },
    )

def natural_key(value):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r'(\d+)', value or "")
    ]

@login_required
def device_list(request):

    search = request.GET.get("search", "")
    practice = request.GET.get("practice", "")
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "")
    geraetart = request.GET.get("geraetart", "")

    # =========================================================
    # ALLE GERÄTE
    # =========================================================
    devices = (
        Device.objects
        .prefetch_related(
            "pruefungen__pruefart"
        )
        .all()
    )

    # =========================================================
    # SUCHE
    # =========================================================
    if search:
        devices = devices.filter(
            Q(name__icontains=search)
            | Q(
                inventory_number__icontains=search
            )
            | Q(
                serial_number__icontains=search
            )
            | Q(
                practice__name__icontains=search
            )
            | Q(
                geraetart__name__icontains=search
            )
        )

    # =========================================================
    # STANDORT FILTER
    # =========================================================
    if practice:
        devices = devices.filter(
            practice_id=practice
        )

    # =========================================================
    # GERÄTEART FILTER
    # =========================================================
    if geraetart:
        devices = devices.filter(
            geraetart_id=geraetart
        )

    # =========================================================
    # STATUS FILTER
    # =========================================================
    if status:
        devices = devices.filter(
            status=status
        )

    # =========================================================
    # SORTIERUNG
    # =========================================================

    # =========================================================
    # BETRIEBSSTUNDEN – WENIGER
    # Nur vorhandene Werte
    # =========================================================
    if sort == "operating_hours":

        devices = (
            devices
            .filter(
                operating_hours__isnull=False
            )
            .order_by(
                "operating_hours"
            )
        )

    # =========================================================
    # BETRIEBSSTUNDEN – MEHR
    # Nur vorhandene Werte
    # =========================================================
    elif sort == "-operating_hours":

        devices = (
            devices
            .filter(
                operating_hours__isnull=False
            )
            .order_by(
                "-operating_hours"
            )
        )

    # =========================================================
    # NÄCHSTE PRÜFUNG – FRÜHESTE
    # Nur aktive Prüfungen mit Datum
    # =========================================================
    elif sort == "next_pruefung":

        devices = (
            devices
            .filter(
                pruefungen__aktiv=True,
                pruefungen__naechstes_datum__isnull=False
            )
            .order_by(
                "pruefungen__naechstes_datum"
            )
            .distinct()
        )

    # =========================================================
    # NÄCHSTE PRÜFUNG – SPÄTESTE
    # Nur aktive Prüfungen mit Datum
    # =========================================================
    elif sort == "-next_pruefung":

        devices = (
            devices
            .filter(
                pruefungen__aktiv=True,
                pruefungen__naechstes_datum__isnull=False
            )
            .order_by(
                "-pruefungen__naechstes_datum"
            )
            .distinct()
        )

    # =========================================================
    # STK – FRÜHESTE
    # Nur vorhandene STK-Werte
    # =========================================================
    elif sort == "next_stk":

        devices = (
            devices
            .filter(
                next_stk__isnull=False
            )
            .order_by(
                "next_stk"
            )
        )

    # =========================================================
    # STK – SPÄTESTE
    # Nur vorhandene STK-Werte
    # =========================================================
    elif sort == "-next_stk":

        devices = (
            devices
            .filter(
                next_stk__isnull=False
            )
            .order_by(
                "-next_stk"
            )
        )

    # =========================================================
    # STANDORT SORTIERUNG
    # =========================================================
    elif sort == "practice":

        devices = devices.order_by(
            "practice__name"
        )

    elif sort == "-practice":

        devices = devices.order_by(
            "-practice__name"
        )

    # =========================================================
    # STANDARD-REIHENFOLGE
    #
    # 1. Dialyse Maschinen – Lübeck
    # 2. Dialyse Maschinen – Ratzeburg
    # 3. Dialyse Betten – Lübeck
    # 4. Dialyse Betten – Ratzeburg
    #
    # Danach Inventarnummer
    # =========================================================
    else:

        def device_group_priority(device):

            # -------------------------------------------------
            # GERÄTEART
            # -------------------------------------------------
            geraetart_name = (
                device.geraetart.name.strip()
                if device.geraetart
                else ""
            )

            # -------------------------------------------------
            # STANDORT
            # -------------------------------------------------
            standort_name = (
                device.practice.name.strip()
                if device.practice
                else ""
            )

            # -------------------------------------------------
            # 1. Dialyse Maschinen – Lübeck
            # -------------------------------------------------
            if (
                geraetart_name == "Dialyse Maschinen"
                and
                standort_name == "Lübeck"
            ):
                return 1

            # -------------------------------------------------
            # 2. Dialyse Maschinen – Ratzeburg
            # -------------------------------------------------
            if (
                geraetart_name == "Dialyse Maschinen"
                and
                standort_name == "Ratzeburg"
            ):
                return 2

            # -------------------------------------------------
            # 3. Dialyse Betten – Lübeck
            # -------------------------------------------------
            if (
                geraetart_name == "Dialyse Betten"
                and
                standort_name == "Lübeck"
            ):
                return 3

            # -------------------------------------------------
            # 4. Dialyse Betten – Ratzeburg
            # -------------------------------------------------
            if (
                geraetart_name == "Dialyse Betten"
                and
                standort_name == "Ratzeburg"
            ):
                return 4

            # -------------------------------------------------
            # ALLE ANDEREN GERÄTE
            # -------------------------------------------------
            return 99

        # =====================================================
        # SORTIEREN
        # =====================================================
        devices = sorted(
            devices,
            key=lambda d: (
                device_group_priority(d),
                natural_key(
                    d.inventory_number
                ),
            ),
        )

    # =========================================================
    # DROPDOWN – STANDORTE
    # =========================================================
    standorte = (
        Standort.objects
        .filter(
            active=True
        )
        .order_by(
            "name"
        )
    )

    # =========================================================
    # DROPDOWN – GERÄTEARTEN
    # =========================================================
    geraetarten = (
        Geraetart.objects
        .filter(
            aktiv=True
        )
        .order_by(
            "name"
        )
    )

    # =========================================================
    # RENDER
    # =========================================================
    return render(
        request,
        "devices/device_list.html",
        {
            "devices": devices,
            "search": search,
            "practice": practice,
            "status": status,
            "geraetart": geraetart,
            "standorte": standorte,
            "geraetarten": geraetarten,
        },
    )
@login_required
def device_detail(request, device_id):

    device = get_object_or_404(
        Device,
        id=device_id
    )

    document_types = DocumentType.objects.all().order_by("order")

    documents = (
        DeviceDocument.objects
        .filter(device=device)
        .select_related("document_type")
        .order_by(
            "document_type__name",
            "-upload_date"
        )
    )

    pruefungen = (
        device.pruefungen
        .filter(aktiv=True)
        .select_related("pruefart")
        .order_by(
            "pruefart__order",
            "pruefart__name"
        )
    )
    # =========================================================
    # GERÄTEDETAILS - SICHTBARE FELDER
    # =========================================================

    detail_fields = []

    if device.geraetart:

        detail_fields = list(
            DeviceDetailFieldConfig.objects
            .filter(
                geraetart=device.geraetart,
                is_visible=True
            )
            .order_by("position")
        )

    return render(
        request,
        "devices/device_detail.html",
        {
            "device": device,
            "document_types": document_types,
            "documents": documents,
            "filterwechsel": (
                device.filterwechsel
                .all()
                .order_by("-datum")
            ),
            "detail_fields": detail_fields,
            "pruefungen": pruefungen,
        }
    )

@login_required
def device_create(request):

    if request.method == "POST":

        form = DeviceForm(
            request.POST,
            request.FILES
        )

        pruefung_formset = DevicePruefungFormSet(
            request.POST,
            prefix="pruefungen"
        )

        print("DEVICE FORM:", form.is_valid())
        print("PRUEFUNG FORMSET:", pruefung_formset.is_valid())

        if form.is_valid() and pruefung_formset.is_valid():

            device = form.save()

            pruefung_formset.instance = device
            pruefung_formset.save()

            AuditLog.objects.create(
                user=request.user,
                action="CREATE",
                model_name="Gerät",
                object_id=device.id,
                description=(
                    f"Gerät {device.name} "
                    f"({device.inventory_number}) "
                    "hinzugefügt."
                )
            )

            messages.success(
                request,
                "Gerät erfolgreich hinzugefügt."
            )

            return redirect("device_list")

    else:

        form = DeviceForm()

        pruefung_formset = DevicePruefungFormSet(prefix="pruefungen")

    return render(
        request,
        "devices/device_form.html",
        {
            "form": form,
            "pruefung_formset": pruefung_formset,
            "geraetarten": Geraetart.objects.all(),
            "pruefarten": Pruefart.objects.filter(
                aktiv=True
            ).order_by("order", "name"),
        }
    )

@login_required
def device_create_geraetart(request, geraetart_id):

    geraetart = get_object_or_404(
        Geraetart,
        id=geraetart_id
    )

    if request.method == "POST":

        form = DeviceForm(
            request.POST,
            request.FILES,
            geraetart=geraetart
        )

        pruefung_formset = DevicePruefungFormSet(
            request.POST
        )

        if form.is_valid() and pruefung_formset.is_valid():

            device = form.save(commit=False)

            device.geraetart = geraetart
            device.name = geraetart.name

            device.save()

            pruefung_formset.instance = device
            pruefung_formset.save()

            AuditLog.objects.create(
                user=request.user,
                action="CREATE",
                model_name="Gerät",
                object_id=device.id,
                description=(
                    f"Gerät {device.name} "
                    f"({device.inventory_number}) "
                    "hinzugefügt."
                )
            )

            messages.success(
                request,
                "Gerät erfolgreich hinzugefügt."
            )

            return redirect(
                "device_geraetart",
                geraetart_id=geraetart.id
            )

    else:

        form = DeviceForm(
            geraetart=geraetart
        )

        pruefung_formset = DevicePruefungFormSet()

    return render(
        request,
        "devices/device_form.html",
        {
            "form": form,
            "pruefung_formset": pruefung_formset,
            "geraetart": geraetart,
        }
    )

@login_required       
def device_geraetart(request, geraetart):

    
    search = request.GET.get("search", "")
    practice = request.GET.get("practice", "")


    devices = Device.objects.filter(
            geraetart=geraetart
    )


    if search:
        devices = devices.filter(
            Q(name__icontains=search) |
            Q(inventory_number__icontains=search) |
            Q(serial_number__icontains=search)
        )


    if practice:
        devices = devices.filter(
            practice=practice
        )


    devices = devices.order_by("inventory_number")


    return render(
        request,
        "devices/device_category.html",
        {
            "devices": devices,
            "geraetart": geraetart,
            "search": search,
            "practice": practice,
        }
    )

@login_required
def pruefarten(request):

    pruefarten = Pruefart.objects.all().order_by(
        "order",
        "name"
    )

    return render(
        request,
        "devices/pruefarten.html",
        {
            "pruefarten": pruefarten,
        }
    ) 

@login_required
def pruefart_create(request):
    if not request.user.is_superuser:
            return redirect("permission_denied")
    if request.method == "POST":

        form = PruefartForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Prüfart erfolgreich hinzugefügt."
            )

            return redirect("pruefarten")

    else:

        form = PruefartForm()

    return render(
        request,
        "devices/pruefart_form.html",
        {
            "form": form,
            "title": "Neue Prüfart hinzufügen",
        }
    )


@login_required
def pruefart_edit(request, id):
    if not request.user.is_superuser:
            return redirect("permission_denied")
    pruefart = get_object_or_404(
        Pruefart,
        id=id
    )

    if request.method == "POST":

        form = PruefartForm(
            request.POST,
            instance=pruefart
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Prüfart erfolgreich geändert."
            )

            return redirect("pruefarten")

    else:

        form = PruefartForm(
            instance=pruefart
        )

    return render(
        request,
        "devices/pruefart_form.html",
        {
            "form": form,
            "title": "Prüfart bearbeiten",
            "pruefart": pruefart,
        }
    )

@login_required
def pruefart_delete(request, id):

    # =========================================================
    # NUR ADMIN
    # =========================================================

    if not request.user.is_superuser:
        return redirect("permission_denied")


    # =========================================================
    # PRÜFART LADEN
    # =========================================================

    pruefart = get_object_or_404(
        Pruefart,
        id=id
    )


    # =========================================================
    # LÖSCHEN
    # =========================================================

    if request.method == "POST":

        name = pruefart.name

        pruefart.delete()

        messages.success(
            request,
            f'✅ Prüfart "{name}" wurde erfolgreich gelöscht.'
        )

        return redirect(
            "pruefarten"
        )


    # =========================================================
    # BESTÄTIGUNG
    # =========================================================

    return render(
        request,
        "devices/pruefart_delete.html",
        {
            "pruefart": pruefart,
        }
    )

@login_required
def contact(request):

    settings = PracticeSettings.objects.first()

    kontakt = ContactInformation.objects.first()


    return render(
        request,
        "devices/contact.html",
        {
            "settings": settings,
            "kontakt": kontakt,
        }
    )

@login_required
def faellige_pruefung(request, pruefart_id):

    heute = date.today()
    grenze = heute + timedelta(days=30)

    # =========================================================
    # PRÜFUNGSART
    # =========================================================

    pruefart = get_object_or_404(
        Pruefart,
        id=pruefart_id
    )

    # =========================================================
    # ALLE GERÄTEARTEN AUS EINSTELLUNGEN
    # =========================================================

    geraetearten = (
        Geraetart.objects
        .all()
        .order_by("name")
    )

    # =========================================================
    # ALLE STANDORTE AUS EINSTELLUNGEN
    # =========================================================

    standorte = (
        Standort.objects
        .all()
        .order_by("name")
    )

    # =========================================================
    # STATUS AUS DASHBOARD
    # =========================================================

    pruef_status = request.GET.get(
        "status",
        ""
    ).strip()

    # =========================================================
    # PRÜFUNGEN
    # =========================================================

    pruefungen = (
        DevicePruefung.objects
        .filter(
            pruefart=pruefart,
            aktiv=True,
            device__status="Aktiv",
            naechstes_datum__isnull=False,
        )
        .select_related(
            "device",
            "pruefart",
            "device__geraetart",
            "device__practice",
        )
    )

    # =========================================================
    # STATUS FILTER
    # =========================================================

    if pruef_status == "gueltig":

        pruefungen = pruefungen.filter(
            naechstes_datum__gt=grenze
        )

    elif pruef_status == "faellig":

        pruefungen = pruefungen.filter(
            naechstes_datum__gte=heute,
            naechstes_datum__lte=grenze
        )

    elif pruef_status == "ueberfaellig":

        pruefungen = pruefungen.filter(
            naechstes_datum__lt=heute
        )

    # =========================================================
    # SORTIERUNG
    # =========================================================

    pruefungen = pruefungen.order_by(
        "naechstes_datum"
    )

    # =========================================================
    # TEMPLATE
    # =========================================================

    return render(
        request,
        "devices/faellige_pruefung.html",
        {
            "pruefart": pruefart,

            "pruefungen": pruefungen,

            "heute": heute,

            "grenze": grenze,

            "geraetearten": geraetearten,

            "standorte": standorte,

            # Wichtig für das Template
            "pruef_status": pruef_status,
        }
    )
@login_required
def messmittel_list(request):

    messmittel = Messmittel.objects.all().order_by(
        "name"
    )

    return render(
        request,
        "devices/messmittel.html",
        {
            "messmittel": messmittel,
        }
    )

@login_required
def messmittel_create(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()

        if name:

            Messmittel.objects.create(
                name=name
            )

            messages.success(
                request,
                "Messmittel erfolgreich hinzugefügt."
            )

            return redirect(
                "messmittel_list"
            )

        messages.error(
            request,
            "Bitte Messmittel eingeben."
        )

    return render(
        request,
        "devices/messmittel_form.html"
    )

@login_required
def messmittel_update(request, pk):

    messmittel = get_object_or_404(
        Messmittel,
        pk=pk
    )

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        if name:

            messmittel.name = name

            messmittel.save()

            messages.success(
                request,
                "Messmittel erfolgreich geändert."
            )

            return redirect(
                "messmittel_list"
            )

        messages.error(
            request,
            "Bitte Messmittel eingeben."
        )

    return render(
        request,
        "devices/messmittel_form.html",
        {
            "messmittel": messmittel,
            "edit": True,
        }
    )

@login_required
def messmittel_delete(request, pk):

    messmittel = get_object_or_404(
        Messmittel,
        pk=pk
    )

    if request.method == "POST":

        messmittel.delete()

        messages.success(
            request,
            "Messmittel erfolgreich gelöscht."
        )

    return redirect(
        "messmittel_list"
    )


@login_required
def reparatur(request):

    reparaturen = Reparatur.objects.filter(
        status__in=["Offen", "In Bearbeitung"]
    ).order_by("-datum")

    return render(
        request,
        "devices/reparatur.html",
        {
            "reparaturen": reparaturen
        }
    )



@login_required
def search_reparatur_device(request):

    query = request.GET.get("q", "")

    devices = Device.objects.filter(
        Q(inventory_number__icontains=query) |
        Q(serial_number__icontains=query) |
        Q(name__icontains=query)
    ).order_by("inventory_number")[:10]

    data = []

    for device in devices:

        data.append({
            "id": device.id,
            "inventory": device.inventory_number,
            "name": device.name,
            "serial": device.serial_number,
            "standort": device.practice.name,
        })

    return JsonResponse(data, safe=False)

@login_required
def reparatur_create(request):

    if request.method == "POST":

        form = ReparaturForm(request.POST)


        if form.is_valid():


            reparatur = form.save(commit=False)


            # Gerät aus Formular übernehmen
            device = form.cleaned_data.get("geraet")


            reparatur.geraet = device


            # Standard Status
            reparatur.status = "Offen"


            reparatur.save()



            AuditLog.objects.create(

                user=request.user,

                action="CREATE",

                model_name="Reparatur",

                object_id=reparatur.id,

                description=(

                    f"Reparatur für Gerät "
                    f"{device.name} "
                    f"(Inventarnummer: {device.inventory_number}) "
                    "erstellt."

                )

            )



            messages.success(

                request,

                "Reparatur erfolgreich erstellt."

            )



            return redirect(
                "reparatur"
            )


    else:


        form = ReparaturForm()



    return render(

        request,

        "devices/reparatur_form.html",

        {
            "form": form,
        },

    )


@login_required
def reparatur_detail(request, pk):

    reparatur = get_object_or_404(
        Reparatur,
        pk=pk
    )

    # =====================================================
    # READONLY
    # =====================================================

    readonly = request.GET.get("readonly") == "1"

    if readonly:

        form = ReparaturBearbeitenForm(
            instance=reparatur
        )

        return render(
            request,
            "devices/reparatur_detail.html",
            {
                "reparatur": reparatur,
                "form": form,
                "readonly": True,
                "elektrische_daten":
                    reparatur.elektrische_pruefung_daten or {},
            }
        )

    # =====================================================
    # POST
    # =====================================================

    if request.method == "POST":

        # =================================================
        # DELETE
        # =================================================

        if request.POST.get("delete") == "1":

            AuditLog.objects.create(

                user=request.user,

                action="DELETE",

                model_name="Reparatur",

                object_id=reparatur.id,

                description=(
                    f"Reparatur für Gerät "
                    f"{reparatur.geraet.name} "
                    f"(Inventarnummer: "
                    f"{reparatur.geraet.inventory_number}) "
                    "gelöscht."
                )
            )

            reparatur.delete()

            messages.success(
                request,
                "Reparatur gelöscht."
            )

            return redirect("reparatur")

        # =================================================
        # FORM
        # =================================================

        form = ReparaturBearbeitenForm(
            request.POST,
            request.FILES,
            instance=reparatur
        )

        if form.is_valid():

            # -------------------------------------------------
            # Reparatur speichern
            # -------------------------------------------------

            reparatur = form.save()

            # -------------------------------------------------
            # Falls Messmittel ManyToMany ist:
            # Form.save() übernimmt die Auswahl automatisch.
            # -------------------------------------------------

            # =================================================
            # ELEKTRISCHE PRÜFUNG
            # =================================================

            if reparatur.elektrische_pruefung:

                # =============================================
                # BETTEN
                # =============================================

                if reparatur.elektrische_pruefung_art == "Betten":

                    reparatur.elektrische_pruefung_daten = {

                        "betten": {

                            # ---------------------------------
                            # Potentialausgleichswiderstand
                            # ---------------------------------

                            "potentialausgleichswiderstand": {

                                "1": {
                                    "messwert":
                                        request.POST.get(
                                            "potentialausgleichswiderstand_1",
                                            ""
                                        ),
                                    "ok":
                                        request.POST.get(
                                            "potentialausgleichswiderstand_1_ok"
                                        ) == "on",
                                },

                                "2": {
                                    "messwert":
                                        request.POST.get(
                                            "potentialausgleichswiderstand_2",
                                            ""
                                        ),
                                    "ok":
                                        request.POST.get(
                                            "potentialausgleichswiderstand_2_ok"
                                        ) == "on",
                                },

                                "3": {
                                    "messwert":
                                        request.POST.get(
                                            "potentialausgleichswiderstand_3",
                                            ""
                                        ),
                                    "ok":
                                        request.POST.get(
                                            "potentialausgleichswiderstand_3_ok"
                                        ) == "on",
                                },
                            },

                            # ---------------------------------
                            # Gerätableitstrom Ersatzmessung
                            # ---------------------------------

                            "geraeteableitstrom_ersatzmessung": {

                                "intrakardiale_anwendung": {

                                    "messwert":
                                        request.POST.get(
                                            "intrakardiale_anwendung",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "intrakardiale_anwendung_ok"
                                        ) == "on",
                                },

                                "typ_b": {

                                    "messwert":
                                        request.POST.get(
                                            "typ_b_messwert",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "typ_b_ok"
                                        ) == "on",
                                },

                                "laserlampe": {

                                    "messwert":
                                        request.POST.get(
                                            "laserlampe_messwert",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "laserlampe_ok"
                                        ) == "on",
                                },

                                "netzspannung": {

                                    "messwert":
                                        request.POST.get(
                                            "netzspannung_messwert",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "netzspannung_ok"
                                        ) == "on",
                                },
                            },
                        }
                    }

                # =============================================
                # MASCHINEN
                # =============================================

                elif reparatur.elektrische_pruefung_art == "Maschinen":

                    reparatur.elektrische_pruefung_daten = {

                        "maschinen": {

                            # ---------------------------------
                            # Schutzleiterwiderstand
                            # ---------------------------------

                            "schutzleiterwiderstand": {

                                "messwert":
                                    request.POST.get(
                                        "maschinen_schutzleiterwiderstand",
                                        ""
                                    ),

                                "ok":
                                    request.POST.get(
                                        "maschinen_schutzleiterwiderstand_ok"
                                    ) == "on",
                            },

                            # ---------------------------------
                            # Typ B
                            # ---------------------------------

                            "typ_b": {

                                "ok":
                                    request.POST.get(
                                        "maschinen_typ_b_ok"
                                    ) == "on",
                            },

                            # ---------------------------------
                            # Differenzstrommessung
                            # ---------------------------------

                            "differenzstrommessung": {

                                "ok":
                                    request.POST.get(
                                        "maschinen_differenz_ok"
                                    ) == "on",
                            },

                            # ---------------------------------
                            # Direktmessung
                            # ---------------------------------

                            "direktmessung": {

                                "ok":
                                    request.POST.get(
                                        "maschinen_direkt_ok"
                                    ) == "on",
                            },

                            # ---------------------------------
                            # Nennspannung
                            # ---------------------------------

                            "nennspannung": {

                                "messwert":
                                    request.POST.get(
                                        "maschinen_nennspannung",
                                        ""
                                    ),

                                "ok":
                                    request.POST.get(
                                        "maschinen_nennspannung_ok"
                                    ) == "on",
                            },

                            # ---------------------------------
                            # Polarität L - N
                            # ---------------------------------

                            "polaritaet_l_n": {

                                "ibmax": {

                                    "messwert":
                                        request.POST.get(
                                            "maschinen_ln_ibmax",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "maschinen_ln_ibmax_ok"
                                        ) == "on",
                                },

                                "ubmax": {

                                    "messwert":
                                        request.POST.get(
                                            "maschinen_ln_ubmax",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "maschinen_ln_ubmax_ok"
                                        ) == "on",
                                },

                                "in": {

                                    "messwert":
                                        request.POST.get(
                                            "maschinen_ln_in",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "maschinen_ln_in_ok"
                                        ) == "on",
                                },
                            },

                            # ---------------------------------
                            # Polarität N - L
                            # ---------------------------------

                            "polaritaet_n_l": {

                                "ibmax": {

                                    "messwert":
                                        request.POST.get(
                                            "maschinen_nl_ibmax",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "maschinen_nl_ibmax_ok"
                                        ) == "on",
                                },

                                "ubmax": {

                                    "messwert":
                                        request.POST.get(
                                            "maschinen_nl_ubmax",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "maschinen_nl_ubmax_ok"
                                        ) == "on",
                                },

                                "in": {

                                    "messwert":
                                        request.POST.get(
                                            "maschinen_nl_in",
                                            ""
                                        ),

                                    "ok":
                                        request.POST.get(
                                            "maschinen_nl_in_ok"
                                        ) == "on",
                                },
                            },
                        }
                    }

                # =============================================
                # DIALYSE MASCHINE
                # =============================================

                elif (
                    reparatur.elektrische_pruefung_art
                    == "Dialyse Maschinen"
                ):

                    reparatur.elektrische_pruefung_daten = {

                        "dialyse": {

                            # ---------------------------------
                            # Schutzleiterwiderstand
                            # ---------------------------------

                            "schutzleiterwiderstand": {

                                "messwert":
                                    request.POST.get(
                                        "dialyse_schutzleiterwiderstand",
                                        ""
                                    ),

                                "ok":
                                    request.POST.get(
                                        "dialyse_schutzleiterwiderstand_ok"
                                    ) == "on",
                            },

                            # ---------------------------------
                            # Typ B
                            # ---------------------------------

                            "typ_b": {

                                "ok":
                                    request.POST.get(
                                        "dialyse_typ_b_ok"
                                    ) == "on",
                            },

                            # ---------------------------------
                            # Differenzstrommessung
                            # ---------------------------------

                            "differenzstrommessung": {

                                "ok":
                                    request.POST.get(
                                        "dialyse_differenzstrommessung"
                                    ) == "on",
                            },

                            # ---------------------------------
                            # Direktmessung
                            # ---------------------------------

                            "direktmessung": {

                                "ok":
                                    request.POST.get(
                                        "dialyse_direktmessung"
                                    ) == "on",
                            },

                            # ---------------------------------
                            # Nennspannung U0
                            # ---------------------------------

                            "nennspannung_u0": {

                                "messwert":
                                    request.POST.get(
                                        "dialyse_nennspannung_u0",
                                        ""
                                    ),
                            },

                            # ---------------------------------
                            # Polarität L - N
                            # ---------------------------------

                            "polaritaet_l_n": {

                                "ebmax": {

                                    "messwert":
                                        request.POST.get(
                                            "dialyse_ebmax",
                                            ""
                                        ),
                                },

                                "ubmax": {

                                    "messwert":
                                        request.POST.get(
                                            "dialyse_ubmax",
                                            ""
                                        ),
                                },

                                "in": {

                                    "messwert":
                                        request.POST.get(
                                            "dialyse_in_ln",
                                            ""
                                        ),
                                },
                            },

                            # ---------------------------------
                            # Polarität N - L
                            # ---------------------------------

                            "polaritaet_n_l": {

                                "ibmax": {

                                    "messwert":
                                        request.POST.get(
                                            "dialyse_ibmax",
                                            ""
                                        ),
                                },

                                "ubmax": {

                                    "messwert":
                                        request.POST.get(
                                            "dialyse_ubmax_nl",
                                            ""
                                        ),
                                },

                                "in": {

                                    "messwert":
                                        request.POST.get(
                                            "dialyse_in_nl",
                                            ""
                                        ),
                                },
                            },
                        }
                    }

                # =================================================
                # SPEICHERN ELEKTRISCHE DATEN
                # =================================================

                reparatur.save(
                    update_fields=[
                        "elektrische_pruefung_daten"
                    ]
                )

            else:

                reparatur.elektrische_pruefung_daten = {}

                reparatur.save(
                    update_fields=[
                        "elektrische_pruefung_daten"
                    ]
                )

            # =================================================
            # VOM TECHNIKER GELESEN
            # Nur Admin
            # =================================================

            if request.user.is_superuser:

                reparatur.techniker_gelesen = (
                    request.POST.get(
                        "techniker_gelesen"
                    ) == "on"
                )

                reparatur.save(
                    update_fields=[
                        "techniker_gelesen"
                    ]
                )

            # =================================================
            # AUDIT LOG
            # =================================================

            AuditLog.objects.create(

                user=request.user,

                action="UPDATE",

                model_name="Reparatur",

                object_id=reparatur.id,

                description=(
                    f"Reparatur für Gerät "
                    f"{reparatur.geraet.name} "
                    f"(Inventarnummer: "
                    f"{reparatur.geraet.inventory_number}) "
                    "geändert."
                )
            )

            messages.success(
                request,
                "Reparatur erfolgreich gespeichert."
            )

            return redirect("reparatur")

    # =====================================================
    # GET
    # =====================================================

    else:

        form = ReparaturBearbeitenForm(
            instance=reparatur
        )

    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "devices/reparatur_detail.html",
        {
            "reparatur": reparatur,
            "form": form,
            "readonly": False,
            "elektrische_daten":
                reparatur.elektrische_pruefung_daten or {},
        }
    )

@login_required
def reparatur_uebersicht(request):

    reparaturen = Reparatur.objects.filter(
        status__in=["Offen", "In Bearbeitung"]
    )

    status = request.GET.get("status")

    if status:
        reparaturen = reparaturen.filter(status=status)

    reparaturen = reparaturen.order_by("-datum")

    return render(
        request,
        "devices/reparatur.html",
        {
            "reparaturen": reparaturen,
            "title": "Reparaturübersicht",
            "count": reparaturen.count(),
        },
    )
@login_required
def reparatur_historie(request):

    # =========================================================
    # REPARATUREN
    # =========================================================

    reparaturen = (
        Reparatur.objects
        .select_related(
            "geraet",
            "geraet__geraetart",
            "geraet__practice"
        )
        .filter(
            status="Erledigt"
        )
        .order_by(
            "geraet__practice_id",
            "-datum"
        )
    )


    # =========================================================
    # SUCHE
    # =========================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()


    if search:

        reparaturen = reparaturen.filter(

            Q(
                geraet__inventory_number__icontains=search
            )
            |
            Q(
                geraet__serial_number__icontains=search
            )
            |
            Q(
                beschreibung__icontains=search
            )
            |
            Q(
                ausfuehrung__icontains=search
            )

        )


    # =========================================================
    # GERÄTEART FILTER
    # =========================================================

    geraetart = request.GET.get(
        "geraetart",
        ""
    ).strip()


    if geraetart:

        reparaturen = reparaturen.filter(
            geraet__geraetart_id=geraetart
        )


    # =========================================================
    # GERÄTEARTEN
    # =========================================================

    geraetearten = (
        Geraetart.objects
        .all()
        .order_by(
            "name"
        )
    )


    # =========================================================
    # STANDORT FILTER
    # =========================================================

    practice = request.GET.get(
        "practice",
        ""
    ).strip()


    if practice:

        reparaturen = reparaturen.filter(
            geraet__practice_id=practice
        )


    # =========================================================
    # STANDORTE
    # =========================================================

    standorte = (
        Standort.objects
        .all()
        .order_by(
            "id"
        )
    )


    # =========================================================
    # AUSGEWÄHLTE LÖSCHEN
    # NUR SUPERUSER
    # =========================================================

    if request.method == "POST":

        if not request.user.is_superuser:

            messages.error(
                request,
                "Keine Berechtigung."
            )

            return redirect(
                "reparatur_historie"
            )


        ids = request.POST.getlist(
            "selected_repairs"
        )


        for repair_id in ids:

            reparatur = (
                Reparatur.objects
                .select_related(
                    "geraet"
                )
                .filter(
                    id=repair_id
                )
                .first()
            )


            if reparatur:

                AuditLog.objects.create(

                    user=request.user,

                    action="DELETE",

                    model_name="Reparatur",

                    object_id=reparatur.id,

                    description=(

                        f"Reparatur gelöscht: "
                        f"{reparatur.geraet.name} "
                        f"(Inventarnummer: "
                        f"{reparatur.geraet.inventory_number})"

                    )

                )

                reparatur.delete()


        messages.success(
            request,
            "Ausgewählte Reparaturen gelöscht."
        )


        return redirect(
            "reparatur_historie"
        )


    # =========================================================
    # RENDER
    # =========================================================

    return render(

        request,

        "devices/reparatur_historie.html",

        {
            "reparaturen": reparaturen,
            "search": search,
            "practice": practice,
            "geraetart": geraetart,
            "geraetearten": geraetearten,
            "standorte": standorte,
        }

    )

@login_required
def reparatur_historie_detail(request, pk):

    reparatur = get_object_or_404(
        Reparatur,
        pk=pk
    )

    form = ReparaturBearbeitenForm(instance=reparatur)

    return render(
        request,
        "devices/reparatur_detail.html",
        {
            "reparatur": reparatur,
            "form": form,
            "readonly": True,
        }
    )
@login_required
def repair_delete(request, repair_id):

    reparatur = get_object_or_404(
        Reparatur,
        id=repair_id
    )


    if request.method == "POST":


        AuditLog.objects.create(

            user=request.user,

            action="DELETE",

            model_name="Reparatur",

            object_id=reparatur.id,

            description=(

                f"Reparatur für Gerät "
                f"{reparatur.geraet.name} "
                f"(Inventarnummer: {reparatur.geraet.inventory_number}) "
                "gelöscht."

            )

        )


        reparatur.delete()


        messages.success(

            request,

            "Reparatur gelöscht."

        )


    return redirect(
        "reparatur"
    )

@login_required
def reparatur_delete(request, pk):

    reparatur = get_object_or_404(
        Reparatur,
        pk=pk
    )

    if request.method == "POST":

        AuditLog.objects.create(

            user=request.user,

            action="DELETE",

            model_name="Reparatur",

            object_id=reparatur.id,

            description=(

                f"Reparatur für Gerät "
                f"{reparatur.geraet.name} "
                f"(Inventarnummer: "
                f"{reparatur.geraet.inventory_number}) "
                "gelöscht."

            )

        )

        reparatur.delete()

        messages.success(
            request,
            "Reparatur erfolgreich gelöscht."
        )

    return redirect(
        "reparatur"
    )

@login_required
def device_search(request):

    query = request.GET.get("q", "")

    devices = Device.objects.none()

    if query:
        devices = Device.objects.filter(
            Q(name__icontains=query) |
            Q(inventory_number__icontains=query) |
            Q(serial_number__icontains=query)
        ).order_by("name")

    return render(
        request,
        "devices/device_search.html",
        {
            "devices": devices,
            "query": query,
        }
    )

@login_required
def settings_view(request):

    permission, created = UserPermission.objects.get_or_create(
        user=request.user
    )

    return render(
        request,
        "devices/settings.html",
        {
            "permissions": permission,
            "is_admin": request.user.is_superuser,
        }
    )


@login_required
def practice_settings_edit(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    settings = PracticeSettings.objects.first()

    if request.method == "POST":

        form = PracticeSettingsForm(
            request.POST,
            instance=settings
        )

        if form.is_valid():
            form.save()

            return render(
                request,
                "devices/settings.html"
            )

    else:

        form = PracticeSettingsForm(
            instance=settings
        )


    return render(
        request,
        "devices/practice_settings_edit.html",
        {
            "form": form
        }
    )
@login_required
def dashboard(request):

    heute = date.today()
    grenze = heute + timedelta(days=30)

    # =====================================================
    # GERÄTE
    # =====================================================

    devices = Device.objects.all()

    dashboard_settings, created = (
        DashboardSettings.objects.get_or_create(id=1)
    )

    # =====================================================
    # SUCHE
    # =====================================================

    search = request.GET.get("search", "").strip()

    if search:

        devices = devices.filter(
            Q(name__icontains=search)
            | Q(inventory_number__icontains=search)
            | Q(serial_number__icontains=search)
            | Q(practice__name__icontains=search)
            | Q(geraetart__name__icontains=search)
        )

    # =====================================================
    # STATUS FILTER
    # =====================================================

    status = request.GET.get("status", "").strip()

    if status:

        devices = devices.filter(
            status=status
        )

    # =====================================================
    # SORTIERUNG
    # =====================================================

    sort = request.GET.get("sort", "").strip()

    if sort == "inventory_number":

        devices = devices.order_by(
            "inventory_number"
        )

    elif sort == "-inventory_number":

        devices = devices.order_by(
            "-inventory_number"
        )

    elif sort == "operating_hours":

        devices = (
            devices
            .filter(
                operating_hours__isnull=False
            )
            .order_by(
                "operating_hours"
            )
        )

    elif sort == "-operating_hours":

        devices = (
            devices
            .filter(
                operating_hours__isnull=False
            )
            .order_by(
                "-operating_hours"
            )
        )

    elif sort == "practice":

        devices = devices.order_by(
            "practice__name"
        )

    elif sort == "-practice":

        devices = devices.order_by(
            "-practice__name"
        )

    elif sort == "next_pruefung":

        devices = (
            devices
            .filter(
                pruefungen__aktiv=True,
                pruefungen__naechstes_datum__isnull=False
            )
            .order_by(
                "pruefungen__naechstes_datum"
            )
            .distinct()
        )

    elif sort == "-next_pruefung":

        devices = (
            devices
            .filter(
                pruefungen__aktiv=True,
                pruefungen__naechstes_datum__isnull=False
            )
            .order_by(
                "-pruefungen__naechstes_datum"
            )
            .distinct()
        )

    # =====================================================
    # STANDORTE
    # =====================================================

    luebeck_total = Device.objects.filter(
        practice__name="Lübeck"
    ).count()

    ratzeburg_total = Device.objects.filter(
        practice__name="Ratzeburg"
    ).count()

    # =====================================================
    # REPARATUREN
    # =====================================================

    offene_reparaturen = Reparatur.objects.filter(
        status="Offen"
    ).count()

    reparaturen_bearbeitung = Reparatur.objects.filter(
        status="In Bearbeitung"
    ).count()

    reparaturen_erledigt = Reparatur.objects.filter(
        status="Erledigt"
    ).count()

    # =====================================================
    # PRÜFUNGEN
    #
    # Neues System:
    # Nur "Prüfungsart"
    # Keine STK / MTK / DGUV mehr
    # =====================================================

    pruefungen = (
        DevicePruefung.objects
        .filter(
            aktiv=True,
            device__status="Aktiv",
            naechstes_datum__isnull=False
        )
    )

    # =====================================================
    # GERÄTEÜBERSICHT
    # =====================================================

    geraete_uebersicht = (
        Device.objects
        .values(
            "geraetart__name",
            "practice__name"
        )
        .annotate(
            anzahl=Count("id")
        )
        .order_by(
            "geraetart__name",
            "practice__name"
        )
    )

    # =====================================================
    # DASHBOARD WIDGETS
    # Jeder Benutzer sieht nur seine eigenen Widgets
    # =====================================================

    dashboard_widgets = (
        DashboardWidget.objects
        .filter(
            user=request.user,
            visible=True
        )
        .select_related(
            
            "standort",
            "geraetart",
            "pruefart"
        )
        .order_by(
            "order"
        )
    )

    # =====================================================
    # WIDGET WERTE + LINKS
    # =====================================================

    for widget in dashboard_widgets:

        # =================================================
        # STANDARD
        # =================================================

        widget.value = 0
        widget.url = None

        # =================================================
        # GERÄTE
        # =================================================

        if widget.widget_type == "devices":

            qs = Device.objects.all()

            # -------------------------
            # STANDORT
            # -------------------------

            if widget.standort:

                qs = qs.filter(
                    practice=widget.standort
                )

            # -------------------------
            # GERÄTEART
            # -------------------------

            if widget.geraetart:

                qs = qs.filter(
                    geraetart=widget.geraetart
                )

            # -------------------------
            # WERT
            # -------------------------

            widget.value = qs.count()

            # -------------------------
            # LINK
            # -------------------------

            widget.url = reverse(
                "device_list"
            )

            params = []

            if widget.standort:

                params.append(
                    f"practice={widget.standort.id}"
                )

            if widget.geraetart:

                params.append(
                    f"geraetart={widget.geraetart.id}"
                )

            if params:

                widget.url += (
                    "?"
                    + "&".join(params)
                )

        # =================================================
        # GERÄTEÜBERSICHT
        # =================================================

        elif widget.widget_type == "devices_overview":

            widget.value = Device.objects.count()

            widget.url = reverse(
                "device_list"
            )

        # =================================================
        # REPARATUREN
        # =================================================

        elif widget.widget_type == "repairs":

            qs = Reparatur.objects.all()

            status_map = {

                "offen":
                    "Offen",

                "in_bearbeitung":
                    "In Bearbeitung",

                "erledigt":
                    "Erledigt",

            }

            # -------------------------
            # STATUS FILTER
            # -------------------------

            reparatur_status = None

            if widget.reparatur_status:

                reparatur_status = (
                    status_map.get(
                        widget.reparatur_status
                    )
                )

            if reparatur_status:

                qs = qs.filter(
                    status=reparatur_status
                )

            # -------------------------
            # WERT
            # -------------------------

            widget.value = qs.count()

            # -------------------------
            # LINK
            # -------------------------

            if reparatur_status == "Erledigt":

                # Erledigte Reparaturen
                # befinden sich in der Historie

                widget.url = reverse(
                    "reparatur_historie"
                )

            else:

                # Offen / In Bearbeitung

                widget.url = reverse(
                    "reparatur_uebersicht"
                )

                if reparatur_status:

                    from urllib.parse import urlencode

                    widget.url += (
                        "?"
                        + urlencode(
                            {
                                "status":
                                    reparatur_status
                            }
                        )
                    )

        # =================================================
        # FILTERWECHSEL
        # =================================================

        elif widget.widget_type == "filter_history":

            widget.value = (
                Filterwechsel.objects.count()
            )

            widget.url = reverse(
                "filterwechsel_history"
            )

        # =================================================
        # PRÜFUNGSART
        # =================================================

        elif widget.widget_type == "pruefart":

            qs = DevicePruefung.objects.filter(
                aktiv=True,
                device__status="Aktiv",
                naechstes_datum__isnull=False
            )

            # -------------------------
            # PRÜFUNGSART
            # -------------------------

            if widget.pruefart:

                qs = qs.filter(
                    pruefart=widget.pruefart
                )

            # -------------------------
            # STATUS
            # -------------------------

            if widget.pruef_status == "gueltig":

                qs = qs.filter(
                    naechstes_datum__gt=grenze
                )

            elif widget.pruef_status == "faellig":

                qs = qs.filter(
                    naechstes_datum__gte=heute,
                    naechstes_datum__lte=grenze
                )

            elif widget.pruef_status == "ueberfaellig":

                qs = qs.filter(
                    naechstes_datum__lt=heute
                )

            # -------------------------
            # WERT
            # -------------------------

            widget.value = qs.count()

            # -------------------------
            # LINK
            # -------------------------

            if widget.pruefart:

                widget.url = reverse(
                    "faellige_pruefung",
                    args=[
                        widget.pruefart.id
                    ]
                )

                # =============================================
                # PRÜFUNGS STATUS AN URL ÜBERGEBEN
                # =============================================

                if widget.pruef_status:

                    from urllib.parse import urlencode

                    widget.url += (
                        "?"
                        + urlencode(
                            {
                                "status":
                                    widget.pruef_status
                            }
                        )
                    )

            else:

                widget.url = reverse(
                    "device_list"
                )

        # =================================================
        # RECHNUNGEN
        # =================================================

        elif widget.widget_type == "rechnung":

            status_map = {

                "offen":
                    "Offen",

                "in_bearbeitung":
                    "In Bearbeitung",

                "erledigt":
                    "Erledigt",

            }

            rechnung_status = None

            if widget.rechnung_status:

                rechnung_status = (
                    status_map.get(
                        widget.rechnung_status
                    )
                )

            # -------------------------
            # ERLEDIGT
            # -------------------------

            if rechnung_status == "Erledigt":

                qs = Rechnung.objects.filter(
                    status="Erledigt"
                )

                widget.value = qs.count()

                widget.url = reverse(
                    "rechnung_historie"
                )

            # -------------------------
            # OFFEN / IN BEARBEITUNG
            # -------------------------

            else:

                qs = (
                    Rechnung.objects
                    .exclude(
                        status="Erledigt"
                    )
                )

                if rechnung_status:

                    qs = qs.filter(
                        status=rechnung_status
                    )

                widget.value = qs.count()

                widget.url = reverse(
                    "rechnung_uebersicht"
                )

                if rechnung_status:

                    from urllib.parse import urlencode

                    widget.url += (
                        "?"
                        + urlencode(
                            {
                                "status":
                                    rechnung_status
                            }
                        )
                    )

        # =================================================
        # MEDIZINGERÄTE-DOKUMENTE
        # =================================================

        elif widget.widget_type == "device_documents":

            widget.value = (
                DeviceDocument.objects.count()
            )

            widget.url = reverse(
                "documents"
            )

        # =================================================
        # TECHNIKER-DOKUMENTE
        # =================================================

        elif widget.widget_type == "technician_documents":

            widget.value = (
                TechnicianDocument.objects.count()
            )

            widget.url = reverse(
                "technician_documents"
            )

        # =================================================
        # UNBEKANNTER WIDGET-TYP
        # =================================================

        else:

            widget.value = 0
            widget.url = None

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "devices":
            devices,

        "search":
            search,

        "status":
            status,

        # -------------------------------------------------
        # REPARATUREN
        # -------------------------------------------------

        "offene_reparaturen":
            offene_reparaturen,

        "reparaturen_bearbeitung":
            reparaturen_bearbeitung,

        "reparaturen_erledigt":
            reparaturen_erledigt,

        # -------------------------------------------------
        # PRÜFUNGEN
        # -------------------------------------------------

        "pruefungen":
            pruefungen,

        # -------------------------------------------------
        # STANDORTE
        # -------------------------------------------------

        "luebeck_total":
            luebeck_total,

        "ratzeburg_total":
            ratzeburg_total,

        # -------------------------------------------------
        # GERÄTEÜBERSICHT
        # -------------------------------------------------

        "geraete_uebersicht":
            geraete_uebersicht,

        # -------------------------------------------------
        # DASHBOARD EINSTELLUNGEN
        # -------------------------------------------------

        "dashboard_settings":
            dashboard_settings,

        # -------------------------------------------------
        # DASHBOARD WIDGETS
        # -------------------------------------------------

        "dashboard_widgets":
            dashboard_widgets,
    }

    return render(
        request,
        "devices/dashboard.html",
        context
    )

@login_required
def dashboard_settings(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    settings, created = DashboardSettings.objects.get_or_create(
        id=1
    )


    if request.method == "POST":

        settings.show_luebeck = request.POST.get(
            "show_luebeck"
        ) == "on"

        settings.show_ratzeburg = request.POST.get(
            "show_ratzeburg"
        ) == "on"

        settings.show_reparaturen = request.POST.get(
            "show_reparaturen"
        ) == "on"

        settings.show_stk = request.POST.get(
            "show_stk"
        ) == "on"

        settings.show_mtk = request.POST.get(
            "show_mtk"
        ) == "on"

        settings.show_dguv = request.POST.get(
            "show_dguv"
        ) == "on"

        settings.show_geraete_uebersicht = request.POST.get(
            "show_geraete_uebersicht"
        ) == "on"


        settings.save()

        messages.success(
            request,
            "Dashboard Einstellungen wurden erfolgreich gespeichert."
        )

        return redirect("dashboard_settings")


    return render(
        request,
        "devices/dashboard_settings.html",
        {
            "settings": settings
        }
    )


@login_required
def upload_document(request, device_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    device = get_object_or_404(
        Device,
        id=device_id
    )
    if request.method == "POST":

        form = DeviceDocumentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            document = form.save(commit=False)

            document.device = device

            document.save()

            return redirect(
                "device_detail",
                device_id=device.id
            )

    else:

        form = DeviceDocumentForm()

    return render(
        request,
        "devices/upload_document.html",
        {
            "device": device,
            "form": form,
        }
    )

@login_required
def device_documents_list(request, document_type):

    documents = DeviceDocument.objects.filter(
        document_type=document_type
    ).select_related(
        "device"
    ).order_by(
        "-upload_date"
    )


    return render(
        request,
        "devices/device_documents_list.html",
        {
            "documents": documents,
            "document_type": document_type
        }
    )
@login_required
def device_delete(request, device_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    device = get_object_or_404(
        Device,
        id=device_id
    )


    if request.method == "POST":


        AuditLog.objects.create(

            user=request.user,

            action="DELETE",

            model_name="Gerät",

            object_id=device.id,

            description=(
                f"Gerät {device.name} "
                f"(Inventarnummer: {device.inventory_number}, "
                f"Seriennummer: {device.serial_number}) "
                "gelöscht."
            )

        )


        device.delete()


        messages.success(
            request,
            "Gerät erfolgreich gelöscht."
        )


        return redirect(
            "device_list"
        )


    return render(

        request,

        "devices/device_delete_confirm.html",

        {
            "device": device
        }

    )
@login_required
def device_edit(request, device_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    device = get_object_or_404(
        Device,
        id=device_id
    )

    if request.method == "POST":

        form = DeviceForm(
            request.POST,
            request.FILES,
            instance=device
        )

        pruefung_formset = DevicePruefungFormSet(
            request.POST,
            instance=device
        )

        if form.is_valid() and pruefung_formset.is_valid():

            device = form.save()

            pruefung_formset.instance = device
            pruefung_formset.save()

            AuditLog.objects.create(
                user=request.user,
                action="UPDATE",
                model_name="Gerät",
                object_id=device.id,
                description=(
                    f"Gerät {device.name} "
                    f"(Inventarnummer: {device.inventory_number}, "
                    f"Seriennummer: {device.serial_number}) "
                    "geändert."
                )
            )

            messages.success(
                request,
                "Gerät erfolgreich geändert."
            )

            return redirect(
                "device_detail",
                device_id=device.id
            )

    else:

        form = DeviceForm(
            instance=device
        )

        pruefung_formset = DevicePruefungFormSet(
            instance=device
        )

    return render(
        request,
        "devices/device_form.html",
        {
            "form": form,
            "device": device,
            "pruefung_formset": pruefung_formset,

            "geraetarten": Geraetart.objects.filter(
                aktiv=True
            ),

            "pruefarten": Pruefart.objects.filter(
                aktiv=True
            ).order_by(
                "order",
                "name"
            ),
        }
    )
@login_required
def document_delete(request, document_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    document = get_object_or_404(
        DeviceDocument,
        id=document_id
    )


    document_type = document.document_type


    if request.method == "POST":

        if document.file:
            document.file.delete()

        document.delete()


        return redirect(
            "documents_by_type",
            document_type_id=document_type.id
        )


    return render(
        request,
        "devices/document_delete_confirm.html",
        {
            "document": document
        }
    )
@login_required
def document_rename(request, document_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    document = get_object_or_404(
        DeviceDocument,
        id=document_id
    )

    if request.method == "POST":

        new_name = request.POST.get("new_name")

        if new_name:

            document.display_name = new_name

            document.save()

        return redirect(
            "device_detail",
            device_id=document.device.id
        )


    return render(
        request,
        "devices/document_rename.html",
        {
            "document": document
        }
    )
@login_required
def documents(request):

    return render(
        request,
        "devices/documents.html"
    )

@login_required
def documents_by_type(request, document_type_id):

    document_type = get_object_or_404(
        DocumentType,
        id=document_type_id
    )

    # =========================================================
    # ALLE DOKUMENTE DIESES DOKUMENT-TYPS
    # =========================================================

    documents = (
        DeviceDocument.objects
        .filter(document_type=document_type)
        .select_related(
            "device",
            "device__geraetart",
            "device__practice",
            "document_type"
        )
    )

    # =========================================================
    # FILTER GERÄTEART
    # =========================================================

    geraetart = request.GET.get("geraetart", "")

    if geraetart:
        documents = documents.filter(
            device__geraetart_id=geraetart
        )

    # =========================================================
    # FILTER STANDORT
    # =========================================================

    standort = request.GET.get("standort", "")

    if standort:
        documents = documents.filter(
            device__practice_id=standort
        )

    # =========================================================
    # FILTER-OPTIONEN
    # =========================================================

    geraetarten = (
        Geraetart.objects
        .filter(aktiv=True)
        .order_by("name")
    )

    standorte = (
        Standort.objects
        .all()
        .order_by("name")
    )

    # =========================================================
    # AUSGABE
    # =========================================================

    return render(
        request,
        "devices/documents_by_type.html",
        {
            "documents": documents.order_by("-upload_date"),
            "document_type": document_type,
            "standorte": standorte,
            "geraetarten": geraetarten,
            "geraetart": geraetart,
            "standort": standort,
        }
    )

@login_required
def document_type_delete(request, document_type_id):

    # =========================================================
    # NUR ADMIN
    # =========================================================

    if not request.user.is_superuser:
        return redirect("permission_denied")


    # =========================================================
    # DOCUMENT TYPE LADEN
    # =========================================================

    document_type = get_object_or_404(
        DocumentType,
        id=document_type_id
    )


    # =========================================================
    # LÖSCHEN
    # =========================================================

    if request.method == "POST":

        name = document_type.name

        document_type.delete()

        messages.success(
            request,
            f'✅ Dokumenttyp "{name}" wurde erfolgreich gelöscht.'
        )

        return redirect(
            "document_types"
        )


    # =========================================================
    # BESTÄTIGUNG
    # =========================================================

    return render(
        request,
        "devices/document_type_delete_confirm.html",
        {
            "document_type": document_type
        }
    )


@login_required
def technician_documents(request):

    documents = TechnicianDocument.objects.all().order_by("-upload_date")

    return render(
        request,
        "devices/technician_documents.html",
        {
            "documents": documents
        }
    )

@login_required
def technician_document_upload(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    if request.method == "POST":

        form = TechnicianDocumentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            document = form.save(commit=False)
            document.uploaded_by = request.user
            document.save()

            return redirect("technician_documents")

    else:

        form = TechnicianDocumentForm()

    return render(
        request,
        "devices/technician_document_upload.html",
        {
            "form": form
        }
    )

@login_required
def technician_document_rename(request, doc_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    doc = get_object_or_404(
        TechnicianDocument,
        id=doc_id
    )

    if request.method == "POST":

        new_name = request.POST.get("new_name")
        new_category = request.POST.get("category")

        if new_name:
            doc.title = new_name

        if new_category:
            valid_categories = dict(
                TechnicianDocument.CATEGORY_CHOICES
            )

            if new_category in valid_categories:
                doc.category = new_category

        doc.save()

        return redirect("technician_documents")

    return render(
        request,
        "devices/technician_document_rename.html",
        {
            "doc": doc,
            "category_choices": TechnicianDocument.CATEGORY_CHOICES,
        }
    )

@login_required
def technician_document_delete(request, doc_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    doc = get_object_or_404(
        TechnicianDocument,
        id=doc_id
    )

    if request.method == "POST":

        if doc.file:
            doc.file.delete(save=False)

        doc.delete()

        return redirect("technician_documents")

    return render(
        request,
        "devices/technician_document_delete.html",
        {
            "doc": doc
        }
    )

@login_required
def general_documents(request, category):

    documents = GeneralDocument.objects.filter(
        geraetart=geraetart
    ).order_by("-upload_date")


    return render(
        request,
        "devices/general_documents.html",
        {
            "documents": documents,
             "category": category
        }
    )


@login_required
def general_document_upload(request):
    
    category = request.GET.get("category", "Zertifikat")

    if request.method == "POST":

        form = GeneralDocumentForm(request.POST, request.FILES)

        if form.is_valid():

            document = form.save(commit=False)
            document.category = category
            document.save()

            return redirect(
                "general_documents",
                category=document.category
            )

    else:

        form = GeneralDocumentForm(
            initial={
                "category": category
            }
        )

    return render(
        request,
        "devices/general_upload.html",
        {
            "form": form,
            "category": category,
        }
    )
@login_required
def general_document_rename(request, doc_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")
    doc = get_object_or_404(
        GeneralDocument,
        id=doc_id
    )

    if request.method == "POST":

        new_name = request.POST.get("new_name")

        if new_name:
            doc.display_name = new_name
            doc.save()

        return redirect(
            "general_documents",
            category=doc.category
        )

    return render(
        request,
        "devices/general_document_rename.html",
        {
            "doc": doc
        }
    )
@login_required
def general_document_delete(request, doc_id):

    doc = get_object_or_404(
        GeneralDocument,
        id=doc_id
    )


    if request.method == "POST":

        doc.file.delete()
        doc.delete()

        return redirect(
            "general_documents",
            category=doc.category
        )


    return render(
        request,
        "devices/general_document_delete.html",
        {
            "doc": doc
        }
    )

@rechnung_permission_required
def rechnung_neu(request):

    if request.method == "POST":

        rechnungsnummer = request.POST.get(
            "rechnungsnummer",
            ""
        ).strip()

        rechnungsdatum = request.POST.get(
            "rechnungsdatum"
        )

        lieferant = request.POST.get(
            "lieferant",
            ""
        ).strip()

        auftragsnummer = request.POST.get(
            "auftragsnummer",
            ""
        ).strip()

        lieferscheinnummer = request.POST.get(
            "lieferscheinnummer",
            ""
        ).strip()

        kundennummer = request.POST.get(
            "kundennummer",
            ""
        ).strip()

        leistungsdatum = request.POST.get(
            "leistungsdatum"
        )

        rechnungsbetrag = request.POST.get(
            "rechnungsbetrag"
        )

        zahlungsziel = request.POST.get(
            "zahlungsziel"
        )

        faelligkeitsdatum = request.POST.get(
            "faelligkeitsdatum"
        )

        kostenstelle = request.POST.get(
            "kostenstelle",
            ""
        ).strip()

        kategorie_id = request.POST.get(
            "kategorie"
        )

        if kategorie_id:
            kategorie = get_object_or_404(
                RechnungKategorie,
                id=kategorie_id
            )
        else:
            kategorie = None

        # ==========================================
        # VERANTWORTLICHER
        # ==========================================

        verantwortlicher = request.POST.get(
            "verantwortlicher",
            ""
        ).strip()

        bemerkung = request.POST.get(
            "bemerkung",
            ""
        ).strip()

        rechnung_datei = request.FILES.get(
            "rechnung_datei"
        )

        lieferschein_datei = request.FILES.get(
            "lieferschein_datei"
        )

        # ==========================================
        # KATEGORIEN
        # ==========================================

        kategorien = RechnungKategorie.objects.order_by(
            "name"
        )

        # ==========================================
        # PFLICHTFELDER
        # ==========================================

        if not rechnungsnummer:
            messages.error(
                request,
                "Bitte Rechnungsnummer eingeben."
            )

            return render(
                request,
                "devices/rechnung_neu.html",
                {
                    "kategorien": kategorien,
                }
            )

        if not rechnungsdatum:
            messages.error(
                request,
                "Bitte Rechnungsdatum eingeben."
            )

            return render(
                request,
                "devices/rechnung_neu.html",
                {
                    "kategorien": kategorien,
                }
            )

        if not lieferant:
            messages.error(
                request,
                "Bitte Lieferant / Firma eingeben."
            )

            return render(
                request,
                "devices/rechnung_neu.html",
                {
                    "kategorien": kategorien,
                }
            )

        if not rechnungsbetrag:
            messages.error(
                request,
                "Bitte Rechnungsbetrag eingeben."
            )

            return render(
                request,
                "devices/rechnung_neu.html",
                {
                    "kategorien": kategorien,
                }
            )

        # ==========================================
        # RECHNUNG ERSTELLEN
        # ==========================================

        rechnung = Rechnung(
            rechnungsnummer=rechnungsnummer,

            rechnungsdatum=rechnungsdatum,

            lieferant=lieferant,

            auftragsnummer=auftragsnummer,

            lieferscheinnummer=lieferscheinnummer,

            kundennummer=kundennummer,

            leistungsdatum=leistungsdatum or None,

            rechnungsbetrag=rechnungsbetrag,

            zahlungsziel=zahlungsziel or None,

            faelligkeitsdatum=faelligkeitsdatum or None,

            kostenstelle=kostenstelle,

            kategorie=kategorie,

            verantwortlicher=verantwortlicher,

            bemerkung=bemerkung,

            status="Offen",

            rechnung_datei=rechnung_datei,

            lieferschein_datei=lieferschein_datei,

            erstellt_von=request.user,
        )

        rechnung.save()

        # ==========================================
        # ERFOLGSMELDUNG
        # ==========================================

        messages.success(
            request,
            "Rechnung erfolgreich hinzugefügt."
        )

        return redirect(
            "rechnung_uebersicht"
        )

    # ==========================================
    # NEUE RECHNUNG
    # ==========================================

    kategorien = RechnungKategorie.objects.order_by(
        "name"
    )

    return render(
        request,
        "devices/rechnung_neu.html",
        {
            "kategorien": kategorien,
        }
    )
@rechnung_permission_required
def rechnung_detail(request, rechnung_id):
    rechnung = get_object_or_404(
        Rechnung,
        id=rechnung_id
    )
    # =====================================================
    # POST
    # =====================================================
    if request.method == "POST":
        action = request.POST.get("action")
        # =================================================
        # LÖSCHEN
        # =================================================
        if action == "delete":
            if rechnung.rechnung_datei:
                rechnung.rechnung_datei.delete(
                    save=False
                )
            if hasattr(rechnung, "lieferschein_datei"):
                if rechnung.lieferschein_datei:
                    rechnung.lieferschein_datei.delete(
                        save=False
                    )
            rechnung.delete()
            messages.success(
                request,
                "Rechnung erfolgreich gelöscht."
            )
            return redirect(
                "rechnung_uebersicht"
            )
        # =================================================
        # SPEICHERN
        # =================================================
        if action == "save":
            # -------------------------------------------------
            # RECHNUNGSDATEN
            # -------------------------------------------------
            rechnung.rechnungsnummer = (
                request.POST.get(
                    "rechnungsnummer",
                    ""
                ).strip()
            )
            rechnungsdatum = request.POST.get(
                "rechnungsdatum"
            )
            if rechnungsdatum:
                rechnung.rechnungsdatum = rechnungsdatum
            rechnung.lieferant = (
                request.POST.get(
                    "lieferant",
                    ""
                ).strip()
            )
            rechnung.auftragsnummer = (
                request.POST.get(
                    "auftragsnummer",
                    ""
                ).strip()
            )
            rechnung.lieferscheinnummer = (
                request.POST.get(
                    "lieferscheinnummer",
                    ""
                ).strip()
            )
            rechnung.kundennummer = (
                request.POST.get(
                    "kundennummer",
                    ""
                ).strip()
            )
            # -------------------------------------------------
            # LEISTUNGSDATUM
            # -------------------------------------------------
            rechnung.leistungsdatum = (
                request.POST.get(
                    "leistungsdatum"
                ) or None
            )
            # -------------------------------------------------
            # RECHNUNGSBETRAG
            # -------------------------------------------------
            betrag = request.POST.get(
                "rechnungsbetrag",
                ""
            ).strip()
            if betrag:
                betrag = betrag.replace(
                    ",",
                    "."
                )
                try:
                    rechnung.rechnungsbetrag = (
                        Decimal(betrag).quantize(
                            Decimal("0.01")
                        )
                    )
                except InvalidOperation:
                    messages.error(
                        request,
                        "Ungültiger Rechnungsbetrag."
                    )
                    return redirect(
                        "rechnung_detail",
                        rechnung_id=rechnung.id
                    )
            # -------------------------------------------------
            # ZAHLUNGSZIEL
            # -------------------------------------------------
            zahlungsziel = request.POST.get(
                "zahlungsziel",
                ""
            ).strip()
            if zahlungsziel:
                try:
                    rechnung.zahlungsziel = int(
                        zahlungsziel
                    )
                except ValueError:
                    messages.error(
                        request,
                        "Ungültiges Zahlungsziel."
                    )
                    return redirect(
                        "rechnung_detail",
                        rechnung_id=rechnung.id
                    )
            else:
                rechnung.zahlungsziel = None
            # -------------------------------------------------
            # FÄLLIGKEITSDATUM
            # -------------------------------------------------
            rechnung.faelligkeitsdatum = (
                request.POST.get(
                    "faelligkeitsdatum"
                ) or None
            )
            # -------------------------------------------------
            # ZAHLUNG
            # -------------------------------------------------
            rechnung.bezahlt_am = (
                request.POST.get(
                    "bezahlt_am"
                ) or None
            )
            rechnung.zahlungsreferenz = (
                request.POST.get(
                    "zahlungsreferenz",
                    ""
                ).strip()
            )
            # =================================================
            # INTERNE ANGABEN
            # =================================================
            rechnung.kostenstelle = (
                request.POST.get(
                    "kostenstelle",
                    ""
                ).strip()
            )
            # =================================================
            # KATEGORIE
            # =================================================
            #
            # Kategorie kommt aus Neue Rechnung.
            # Wenn im Detail-Formular kein Kategorie-Feld
            # gesendet wird, bleibt die bereits gespeicherte
            # Kategorie unverändert.
            #
            # =================================================
            if "kategorie" in request.POST:
                kategorie_id = request.POST.get(
                    "kategorie"
                )
                if kategorie_id:
                    rechnung.kategorie = get_object_or_404(
                        RechnungKategorie,
                        id=kategorie_id
                    )
            # =================================================
            # BEMERKUNG
            # =================================================
            rechnung.bemerkung = (
                request.POST.get(
                    "bemerkung",
                    ""
                ).strip()
            )
            # =================================================
            # VERANTWORTLICHER
            # =================================================
            rechnung.verantwortlicher = (
                request.POST.get(
                    "verantwortlicher",
                    ""
                ).strip()
            )
            # =================================================
            # STATUS
            # =================================================
            status = request.POST.get(
                "status"
            )
            if status in dict(
                Rechnung.STATUS_CHOICES
            ):
                rechnung.status = status
            # =================================================
            # RECHNUNG DATEI
            # =================================================
            if request.FILES.get(
                "rechnung_datei"
            ):
                if rechnung.rechnung_datei:
                    rechnung.rechnung_datei.delete(
                        save=False
                    )
                rechnung.rechnung_datei = (
                    request.FILES[
                        "rechnung_datei"
                    ]
                )
            # =================================================
            # LIEFERSCHEIN DATEI
            # =================================================
            if request.FILES.get(
                "lieferschein_datei"
            ):
                if hasattr(
                    rechnung,
                    "lieferschein_datei"
                ):
                    if rechnung.lieferschein_datei:
                        rechnung.lieferschein_datei.delete(
                            save=False
                        )
                    rechnung.lieferschein_datei = (
                        request.FILES[
                            "lieferschein_datei"
                        ]
                    )
            # =================================================
            # SPEICHERN
            # =================================================
            rechnung.save()
            messages.success(
                request,
                "Rechnung erfolgreich gespeichert."
            )
            return redirect(
                "rechnung_uebersicht"
            )
    # =====================================================
    # ANZEIGE
    # =====================================================
    return render(
        request,
        "devices/rechnung_detail.html",
        {
            "rechnung": rechnung,
        }
    )

@rechnung_permission_required
def rechnung_uebersicht(request):

    # ==========================================
    # RECHNUNGEN
    # ==========================================

    rechnungen = (
        Rechnung.objects
        .select_related(
            "erstellt_von"
        )
    )

    # ==========================================
    # STATUS FILTER
    # ==========================================

    status = request.GET.get(
        "status",
        ""
    ).strip()

    if status:

        rechnungen = rechnungen.filter(
            status=status
        )

    else:

        # Ohne Filter:
        # nur offene Rechnungen anzeigen

        rechnungen = rechnungen.exclude(
            status="Erledigt"
        )

    # ==========================================
    # SORTIERUNG
    # ==========================================

    rechnungen = rechnungen.order_by(
        "faelligkeitsdatum",
        "-erstellt_am"
    )

    # ==========================================
    # RENDER
    # ==========================================

    return render(
        request,
        "devices/rechnung_uebersicht.html",
        {
            "rechnungen": rechnungen,
            "status": status,
        }
    )
    

@rechnung_permission_required
def rechnung_historie(request):

    # ==========================================
    # RECHNUNGEN
    # ==========================================

    rechnungen = (
        Rechnung.objects
        .filter(
            status="Erledigt"
        )
        .select_related(
            "erstellt_von",
            "kategorie",
        )
    )


    # ==========================================
    # SUCHE
    # ==========================================

    search = request.GET.get(
        "search",
        ""
    ).strip()


    if search:

        rechnungen = rechnungen.filter(

            Q(
                rechnungsnummer__icontains=search
            )
            |
            Q(
                kategorie__name__icontains=search
            )
            |
            Q(
                lieferant__icontains=search
            )
            |
            Q(
                rechnungsbetrag__icontains=search
            )

        )


    # ==========================================
    # KATEGORIE FILTER
    # ==========================================

    kategorie = request.GET.get(
        "kategorie",
        ""
    ).strip()


    if kategorie:

        rechnungen = rechnungen.filter(
            kategorie_id=kategorie
        )


    # ==========================================
    # KATEGORIEN
    # ==========================================

    kategorien = (
        RechnungKategorie.objects
        
        .all()
        .order_by(
            "name"
        )
    )


    # ==========================================
    # DATUM FILTER
    # ==========================================

    datum_von = request.GET.get(
        "datum_von",
        ""
    ).strip()


    datum_bis = request.GET.get(
        "datum_bis",
        ""
    ).strip()


    if datum_von:

        rechnungen = rechnungen.filter(
            rechnungsdatum__gte=datum_von
        )


    if datum_bis:

        rechnungen = rechnungen.filter(
            rechnungsdatum__lte=datum_bis
        )


    # ==========================================
    # MEHRERE RECHNUNGEN LÖSCHEN
    # ==========================================

    if request.method == "POST":

        if request.POST.get(
            "action"
        ) == "delete_selected":

            selected_ids = request.POST.getlist(
                "selected_rechnungen"
            )


            for rechnung_id in selected_ids:

                rechnung = (
                    Rechnung.objects
                    .filter(
                        id=rechnung_id
                    )
                    .first()
                )


                if not rechnung:
                    continue


                # ==================================
                # RECHNUNG DATEI LÖSCHEN
                # ==================================

                if rechnung.rechnung_datei:

                    rechnung.rechnung_datei.delete(
                        save=False
                    )


                # ==================================
                # LIEFERSCHEIN DATEI LÖSCHEN
                # ==================================

                if hasattr(
                    rechnung,
                    "lieferschein_datei"
                ):

                    if rechnung.lieferschein_datei:

                        rechnung.lieferschein_datei.delete(
                            save=False
                        )


                # ==================================
                # RECHNUNG LÖSCHEN
                # ==================================

                rechnung.delete()


            messages.success(
                request,
                "Ausgewählte Rechnungen erfolgreich gelöscht."
            )


            return redirect(
                "rechnung_historie"
            )


    # ==========================================
    # GESAMTSUMME
    # ==========================================

    gesamtsumme = (
        rechnungen
        .aggregate(
            total=Sum(
                "rechnungsbetrag"
            )
        )["total"]
        or 0
    )


    # ==========================================
    # SORTIERUNG
    # ==========================================

    rechnungen = rechnungen.order_by(
        "-bezahlt_am",
        "-erstellt_am"
    )


    # ==========================================
    # RENDER
    # ==========================================

    return render(

        request,

        "devices/rechnung_historie.html",

        {
            "rechnungen": rechnungen,

            "search": search,

            "kategorie": kategorie,

            "kategorien": kategorien,

            "datum_von": datum_von,

            "datum_bis": datum_bis,

            "gesamtsumme": gesamtsumme,
        }

    )

@rechnung_permission_required
def rechnung_historie_delete(request, rechnung_id):

    rechnung = get_object_or_404(
        Rechnung,
        id=rechnung_id
    )

    if request.method == "POST":

        if rechnung.rechnung_datei:

            rechnung.rechnung_datei.delete(
                save=False
            )

        if hasattr(
            rechnung,
            "lieferschein_datei"
        ):

            if rechnung.lieferschein_datei:

                rechnung.lieferschein_datei.delete(
                    save=False
                )

        rechnung.delete()

        messages.success(
            request,
            "Rechnung erfolgreich gelöscht."
        )

    return redirect(
        "rechnung_historie"
    )
@rechnung_permission_required
def rechnung_kategorie_list(request):

    kategorien = RechnungKategorie.objects.order_by("name")

    return render(
        request,
        "devices/rechnung_kategorie_list.html",
        {
            "kategorien": kategorien,
        }
    )

@rechnung_permission_required
def add_rechnung_kategorie(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        if not name:
            messages.error(
                request,
                "Bitte Kategorie eingeben."
            )

            return redirect(
                "add_rechnung_kategorie"
            )

        if RechnungKategorie.objects.filter(
            name__iexact=name
        ).exists():

            messages.error(
                request,
                "Diese Kategorie existiert bereits."
            )

            return redirect(
                "rechnung_kategorie_list"
            )

        RechnungKategorie.objects.create(
            name=name
        )

        messages.success(
            request,
            "Kategorie erfolgreich hinzugefügt."
        )

        return redirect(
            "rechnung_kategorie_list"
        )

    return render(
        request,
        "devices/add_rechnung_kategorie.html"
    )

@rechnung_permission_required
def edit_rechnung_kategorie(request, pk):

    kategorie = get_object_or_404(
        RechnungKategorie,
        id=pk
    )

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        if not name:
            messages.error(
                request,
                "Bitte Kategorie eingeben."
            )

            return redirect(
                "edit_rechnung_kategorie",
                pk=pk
            )

        if RechnungKategorie.objects.filter(
            name__iexact=name
        ).exclude(
            id=pk
        ).exists():

            messages.error(
                request,
                "Diese Kategorie existiert bereits."
            )

            return redirect(
                "edit_rechnung_kategorie",
                pk=pk
            )

        kategorie.name = name
        kategorie.save()

        messages.success(
            request,
            "Kategorie erfolgreich geändert."
        )

        return redirect(
            "rechnung_kategorie_list"
        )

    return render(
        request,
        "devices/edit_rechnung_kategorie.html",
        {
            "kategorie": kategorie,
        }
    )

@rechnung_permission_required
def delete_rechnung_kategorie(request, pk):

    kategorie = get_object_or_404(
        RechnungKategorie,
        id=pk
    )

    if request.method == "POST":

        kategorie.delete()

        messages.success(
            request,
            "Kategorie erfolgreich gelöscht."
        )

    return redirect(
        "rechnung_kategorie_list"
    )

@login_required
def system_settings(request):


    if request.method == "POST":

        theme = request.POST.get("theme")

        request.session["theme"] = theme

        messages.success(
            request,
            "Systemeinstellungen gespeichert"
        )

        return redirect("settings")


    return render(
        request,
        "devices/system_settings.html"
    )


@login_required
def contact_image_change(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    settings = PracticeSettings.objects.first()


    if request.method == "POST":

        if request.FILES.get("contact_image"):

            settings.contact_image = request.FILES["contact_image"]
            settings.save()


        return redirect("contact")


    return render(
        request,
        "devices/contact_image.html",
        {
            "settings": settings
        }
    )

@login_required
def contact_edit(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    settings, created = PracticeSettings.objects.get_or_create(
        id=1,
        defaults={
            "practice_name": "Medizintechnik",
            "contact_person": "Praxis",
            "email": "",
            "phone": "",
            "address": "",
        }
    )


    if request.method == "POST":

        settings.contact_name = request.POST.get(
            "name",
            ""
        )

        settings.email = request.POST.get(
            "email",
            ""
        )

        settings.phone = request.POST.get(
            "phone",
            ""
        )

        settings.address = request.POST.get(
            "address",
            ""
        )


        if request.FILES.get("contact_image"):

            settings.contact_image = request.FILES[
                "contact_image"
            ]


        settings.save()


        messages.success(
            request,
            "Kontaktdaten erfolgreich geändert."
        )


        return redirect("contact")


    return render(
        request,
        "devices/contact_edit.html",
        {
            "settings": settings,
        }
    )



@login_required
def user_list(request):

    # =========================================================
    # ADMIN
    # =========================================================

    if request.user.is_superuser:

        users = User.objects.all().order_by("username")

        is_admin = True

    # =========================================================
    # NORMAL USER
    # =========================================================

    else:

        users = User.objects.filter(
            id=request.user.id
        )

        is_admin = False

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "devices/user_list.html",
        {
            "users": users,
            "is_admin": is_admin,
        }
    )


@login_required
def user_create(request):

    if not request.user.is_superuser:
        return redirect("home")

    if request.method == "POST":

        username = request.POST.get("username")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        role = request.POST.get("role")

        if password1 != password2:
            messages.error(request, "Passwörter stimmen nicht überein.")
            return render(request, "devices/user_create.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Benutzername existiert bereits.")
            return render(request, "devices/user_create.html")

        user = User.objects.create_user(
            username=username,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        if role == "admin":
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_staff = False
            user.is_superuser = False

        user.save()

        messages.success(
            request,
            "Benutzer erfolgreich erstellt."
        )

        return redirect("user_list")

    return render(
        request,
        "devices/user_create.html"
    )

@login_required
def user_edit(request, user_id):

    # =========================================================
    # USER LADEN
    # =========================================================

    user = get_object_or_404(
        User,
        id=user_id
    )

    # =========================================================
    # NORMALER BENUTZER
    # DARF NUR SICH SELBST BEARBEITEN
    # =========================================================

    if not request.user.is_superuser:

        if user != request.user:

            return redirect("permission_denied")

    # =========================================================
    # USER PERMISSION OBJECT
    # =========================================================

    permission, created = UserPermission.objects.get_or_create(
        user=user
    )

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        # =====================================================
        # USER DATA
        # =====================================================

        user.username = request.POST.get(
            "username",
            ""
        ).strip()

        user.first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        user.last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        user.email = request.POST.get(
            "email",
            ""
        ).strip()

        # =====================================================
        # ADMIN
        # =====================================================

        if request.user.is_superuser:

            # ================================================
            # ROLE
            # ================================================

            role = request.POST.get(
                "role"
            )

            if role == "admin":

                user.is_staff = True
                user.is_superuser = True

            else:

                user.is_staff = False
                user.is_superuser = False

            user.save()

            # ================================================
            # PERMISSIONS
            # ================================================

            permission.permission_geraete = (
                "permission_geraete"
                in request.POST
            )

            permission.permission_reparaturen = (
                "permission_reparaturen"
                in request.POST
            )

            permission.permission_filter = (
                "permission_filter"
                in request.POST
            )

            permission.permission_wartung = (
                "permission_wartung"
                in request.POST
            )

            permission.permission_dokumente = (
                "permission_dokumente"
                in request.POST
            )

            permission.permission_rechnung = (
                "permission_rechnung"
                in request.POST
            )

            permission.permission_firmeninfos = (
                "permission_firmeninfos"
                in request.POST
            )

            permission.permission_kontakt = (
                "permission_kontakt"
                in request.POST
            )

            permission.permission_einstellungen = (
                "permission_einstellungen"
                in request.POST
            )



            # =====================================================
            # EINSTELLUNGEN – UNTERBEREICHE
            # =====================================================

            permission.permission_einstellung_benutzer = (
                "permission_einstellung_benutzer"
                in request.POST
            )

            permission.permission_einstellung_standorte = (
                "permission_einstellung_standorte"
                in request.POST
            )

            permission.permission_einstellung_geraetarten = (
                "permission_einstellung_geraetarten"
                in request.POST
            )

            permission.permission_einstellung_pruefarten = (
                "permission_einstellung_pruefarten"
                in request.POST
            )

            permission.permission_einstellung_messmittel = (
                "permission_einstellung_messmittel"
                in request.POST
            )

            permission.permission_einstellung_dokumenttypen = (
                "permission_einstellung_dokumenttypen"
                in request.POST
            )

            permission.permission_einstellung_dashboard_widgets = (
                "permission_einstellung_dashboard_widgets"
                in request.POST
            )

            permission.permission_einstellung_geraetedetails = (
                "permission_einstellung_geraetedetails"
                in request.POST
            )

            permission.permission_einstellung_rechnung_kategorien = (
                "permission_einstellung_rechnung_kategorien"
                in request.POST
            )

            permission.permission_einstellung_backup = (
                "permission_einstellung_backup"
                in request.POST
            )

            permission.permission_einstellung_export = (
                "permission_einstellung_export"
                in request.POST
            )

            permission.permission_einstellung_kontakt = (
                "permission_einstellung_kontakt"
                in request.POST
            )

            permission.permission_einstellung_home = (
                "permission_einstellung_home"
                in request.POST
            )

            permission.permission_einstellung_audit_log = (
                "permission_einstellung_audit_log"
                in request.POST
            )

            permission.permission_einstellung_system_update = (
                "permission_einstellung_system_update"
                in request.POST
            )



            permission.save()

        # =====================================================
        # NORMALER BENUTZER
        # =====================================================

        else:

            # Benutzer darf NUR seine Benutzerdaten ändern.
            # Rolle und Berechtigungen werden NICHT verändert.

            user.save()

        # =====================================================
        # SUCCESS
        # =====================================================

        messages.success(
            request,
            "Benutzerdaten erfolgreich geändert."
        )

        # =====================================================
        # ADMIN → USER LIST
        # NORMALER BENUTZER → SEINE DATEN
        # =====================================================

        return redirect(
            "user_list"
        )

    # =========================================================
    # GET
    # =========================================================

    return render(
        request,
        "devices/user_edit.html",
        {
            "edit_user": user,
            "permissions": permission,
            "is_admin": request.user.is_superuser,
        }
    )


@login_required
def user_delete(request, user_id):

    if not request.user.is_superuser:
        return redirect("home")

    user = get_object_or_404(User, id=user_id)

    # منع حذف المستخدم الحالي
    if user == request.user:
        messages.error(
            request,
            "Sie können Ihren eigenen Benutzer nicht löschen."
        )
        return redirect("user_list")

    # منع حذف آخر Administrator
    if user.is_superuser:
        admins = User.objects.filter(is_superuser=True).count()

        if admins <= 1:
            messages.error(
                request,
                "Der letzte Administrator kann nicht gelöscht werden."
            )
            return redirect("user_list")

    user.delete()

    messages.success(
        request,
        "Benutzer erfolgreich gelöscht."
    )

    return redirect("user_list")

@login_required
def user_password_reset(request, user_id):

    # =========================================================
    # USER LADEN
    # =========================================================

    user = get_object_or_404(
        User,
        id=user_id
    )

    # =========================================================
    # NORMALER BENUTZER
    # DARF NUR SEIN EIGENES PASSWORT ÄNDERN
    # =========================================================

    if not request.user.is_superuser:

        if user != request.user:

            return redirect(
                "permission_denied"
            )

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        # =====================================================
        # PASSWÖRTER AUSLESEN
        # =====================================================

        old_password = request.POST.get(
            "old_password",
            ""
        )

        password1 = request.POST.get(
            "password1",
            ""
        )

        password2 = request.POST.get(
            "password2",
            ""
        )

        # =====================================================
        # NORMALER BENUTZER
        # ALTES PASSWORT PRÜFEN
        # =====================================================

        if not request.user.is_superuser:

            if not request.user.check_password(
                old_password
            ):

                messages.error(
                    request,
                    "Das alte Passwort ist falsch."
                )

                return redirect(
                    "user_password_reset",
                    user_id=user.id
                )

        # =====================================================
        # NEUE PASSWÖRTER VERGLEICHEN
        # =====================================================

        if password1 != password2:

            messages.error(
                request,
                "Die neuen Passwörter stimmen nicht überein."
            )

            return redirect(
                "user_password_reset",
                user_id=user.id
            )

        # =====================================================
        # LEERES PASSWORT VERHINDERN
        # =====================================================

        if not password1:

            messages.error(
                request,
                "Das neue Passwort darf nicht leer sein."
            )

            return redirect(
                "user_password_reset",
                user_id=user.id
            )

        # =====================================================
        # PASSWORT ÄNDERN
        # =====================================================

        user.set_password(
            password1
        )

        user.save()

        # =====================================================
        # SESSION BEIBEHALTEN
        # Nur wenn Benutzer sein eigenes Passwort ändert
        # =====================================================

        if user == request.user:

            update_session_auth_hash(
                request,
                user
            )

        # =====================================================
        # SUCCESS
        # =====================================================

        messages.success(
            request,
            "Passwort erfolgreich geändert."
        )

        # =====================================================
        # ZURÜCK
        # =====================================================

        return redirect(
            "user_list"
        )

    # =========================================================
    # GET
    # =========================================================

    return render(
        request,
        "registration/user_password_reset.html",
        {
            "edit_user": user,
            "is_admin": request.user.is_superuser,
        }
    )

@login_required
def permission_denied(request):
    return render(
        request,
        "devices/permission_denied.html"
    )


@login_required
def profile_settings(request):

    return render(
        request,
        "devices/profile_settings.html"
    )


@login_required
def system_management(request):

    return render(
        request,
        "devices/system_management.html"
    )

@login_required
def standort_list(request):

    standorte = Standort.objects.all().order_by("name")

    return render(
        request,
        "devices/standort_list.html",
        {
            "standorte": standorte
        }
    )


@login_required
def standort_create(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    if request.method == "POST":

        Standort.objects.create(
            name=request.POST.get("name"),
            address=request.POST.get("address"),
            phone=request.POST.get("phone"),
            email=request.POST.get("email"),
            active=True if request.POST.get("active") else False,
        )

        return redirect("standort_list")

    return render(
        request,
        "devices/standort_create.html"
    )

@login_required
def standort_edit(request, standort_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    standort = get_object_or_404(
        Standort,
        id=standort_id
    )

    if request.method == "POST":

        standort.name = request.POST.get("name")
        standort.address = request.POST.get("address")
        standort.phone = request.POST.get("phone")
        standort.email = request.POST.get("email")
        standort.active = True if request.POST.get("active") else False

        standort.save()

        return redirect("standort_list")

    return render(
        request,
        "devices/standort_edit.html",
        {
            "standort": standort
        }
    )

@login_required
def standort_delete(request, standort_id):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    standort = get_object_or_404(
        Standort,
        id=standort_id
    )

    # لا يمكن حذف الفرع إذا كان مستخدمًا
    if Device.objects.filter(practice=standort).exists():

        messages.error(
            request,
            "Dieser Standort wird von Geräten verwendet und kann nicht gelöscht werden."
        )

        return redirect("standort_list")

    standort.delete()

    return redirect("standort_list")




@login_required
def documents_home(request):

    document_types = DocumentType.objects.all().order_by("order")

    return render(
        request,
        "devices/documents_home.html",
        {
            "document_types": document_types
        }
    )


@login_required
def filterwechsel_create(request):

    if request.method == "POST":

        form = FilterwechselForm(request.POST)

        if form.is_valid():

            filterwechsel = form.save(commit=False)

            anzahl = filterwechsel.anzahl_filter

            filtercodes = []

            for i in range(1, anzahl + 1):

                code = request.POST.get(
                    f"filtercode_{i}",
                    ""
                ).strip()

                if code:
                    filtercodes.append(code)

            filterwechsel.filtercode = " | ".join(
                filtercodes
            )

            filterwechsel.save()


            AuditLog.objects.create(

                user=request.user,

                action="CREATE",

                model_name="Filterwechsel",

                object_id=filterwechsel.id,

                description=(

                    f"Filterwechsel erstellt. "
                    f"Gerät: "
                    f"{filterwechsel.geraet.name if filterwechsel.geraet else 'Unbekannt'} "
                    f"(Inventarnummer: "
                    f"{filterwechsel.geraet.inventory_number if filterwechsel.geraet else '—'})"
                )
            )


            messages.success(
                request,
                "Filterwechsel erfolgreich gespeichert."
            )

            return redirect(
                "filterwechsel_history"
            )

    else:

        form = FilterwechselForm()


    return render(
        request,
        "devices/filterwechsel_create.html",
        {
            "form": form
        }
    )


@login_required
def filterwechsel_history(request):

    filterwechsel = (
        Filterwechsel.objects
        .select_related(
            "geraet",
            "geraet__practice"
        )
        .all()
        .order_by(
            "geraet__practice_id",
            "-datum"
        )
    )

    # ==========================================
    # SUCHE
    # ==========================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        filterwechsel = filterwechsel.filter(
            inventarnummer__icontains=search
        )


    # ==========================================
    # STANDORT FILTER
    # ==========================================

    practice = request.GET.get(
        "practice",
        ""
    ).strip()

    if practice:

        filterwechsel = filterwechsel.filter(
            geraet__practice_id=practice
        )


    # ==========================================
    # AUSGEWÄHLTE LÖSCHEN
    # NUR SUPERUSER
    # ==========================================

    if request.method == "POST":

        if not request.user.is_superuser:

            return redirect(
                "permission_denied"
            )


        ids = request.POST.getlist(
            "selected_filterwechsel"
        )


        for filter_id in ids:

            obj = Filterwechsel.objects.filter(
                id=filter_id
            ).first()


            if obj:

                AuditLog.objects.create(

                    user=request.user,

                    action="DELETE",

                    model_name="Filterwechsel",

                    object_id=obj.id,

                    description=(

                        f"Filterwechsel gelöscht. "

                        f"Gerät: "
                        f"{obj.geraet.name if obj.geraet else 'Unbekannt'} "

                        f"(Inventarnummer: "
                        f"{obj.geraet.inventory_number if obj.geraet else '—'})"

                    )

                )


                obj.delete()


        messages.success(

            request,

            "Ausgewählte Filterwechsel gelöscht."

        )


        return redirect(
            "filterwechsel_history"
        )


    # ==========================================
    # STANDORTE
    # Genau wie bei Gesamte Geräte
    # ==========================================

    standorte = (
        Standort.objects
        .filter(
            active=True
        )
        .order_by(
            "name"
        )
    )


    return render(

        request,

        "devices/filterwechsel_history.html",

        {
            "filterwechsel": filterwechsel,
            "search": search,
            "practice": practice,
            "standorte": standorte,
        }

    )

@login_required
def filterwechsel_update(request, id):

    filterwechsel = get_object_or_404(
        Filterwechsel,
        id=id
    )

    original_datum = filterwechsel.datum


    if request.method == "POST":

        form = FilterwechselForm(
            request.POST,
            instance=filterwechsel
        )

        if form.is_valid():

            obj = form.save(
                commit=False
            )

            # Datum nicht ändern
            obj.datum = original_datum

            # Anzahl der Filter
            anzahl = obj.anzahl_filter

            # Neue Filtercodes sammeln
            filtercodes = []

            for i in range(1, anzahl + 1):

                code = request.POST.get(
                    f"filtercode_{i}",
                    ""
                ).strip()

                if code:
                    filtercodes.append(code)

            # Filtercodes speichern
            obj.filtercode = " | ".join(
                filtercodes
            )

            obj.save()


            AuditLog.objects.create(

                user=request.user,

                action="UPDATE",

                model_name="Filterwechsel",

                object_id=obj.id,

                description=(

                    f"Filterwechsel geändert. "

                    f"Gerät: "
                    f"{obj.geraet.name if obj.geraet else 'Unbekannt'} "

                    f"(Inventarnummer: "
                    f"{obj.geraet.inventory_number if obj.geraet else '—'})"

                )

            )


            messages.success(
                request,
                "Filterwechsel geändert."
            )


            return redirect(
                "filterwechsel_history"
            )


    else:

        form = FilterwechselForm(
            instance=filterwechsel
        )


    # ============================
    # Vorhandene Filtercodes
    # ============================

    filtercodes = []

    if filterwechsel.filtercode:

        filtercodes = [
            code.strip()
            for code in filterwechsel.filtercode.split("|")
            if code.strip()
        ]


    return render(

        request,

        "devices/filterwechsel_create.html",

        {
            "form": form,
            "edit": True,
            "filtercodes": filtercodes
        }

    )

@login_required
def filterwechsel_delete(request, id):
    if not request.user.is_superuser:
        return redirect("permission_denied")
    filterwechsel = get_object_or_404(
        Filterwechsel,
        id=id
    )


    if request.method == "POST":


        AuditLog.objects.create(

            user=request.user,

            action="DELETE",

            model_name="Filterwechsel",

            object_id=filterwechsel.id,

            description=(

                f"Filterwechsel gelöscht. "

                f"Gerät: "
                f"{filterwechsel.geraet.name if filterwechsel.geraet else 'Unbekannt'} "

                f"(Inventarnummer: "
                f"{filterwechsel.geraet.inventory_number if filterwechsel.geraet else '—'})"

            )

        )


        filterwechsel.delete()


        messages.success(
            request,
            "Filterwechsel gelöscht."
        )


    return redirect(
        "filterwechsel_history"
    )

@login_required
def geraetarten(request):

    geraetarten = Geraetart.objects.all().order_by("name")

    return render(
        request,
        "devices/geraetarten.html",
        {
            "geraetarten": geraetarten,
        },
    )

@login_required
def geraetart_create(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    if request.method == "POST":

        form = GeraetartForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("geraetarten")

    else:
        form = GeraetartForm()

    return render(
        request,
        "devices/geraetart_form.html",
        {
            "form": form,
            "title": "Gerätart hinzufügen",
        }
    )


@login_required
def geraetart_update(request, id):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    geraetart = get_object_or_404(
        Geraetart,
        id=id
    )

    if request.method == "POST":

        form = GeraetartForm(
            request.POST,
            instance=geraetart
        )

        if form.is_valid():
            form.save()
            return redirect("geraetarten")

    else:

        form = GeraetartForm(
            instance=geraetart
        )

    return render(
        request,
        "devices/geraetart_form.html",
        {
            "form": form,
            "title": "Gerätart bearbeiten",
        }
    )

@login_required
def geraetart_delete(request, id):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    geraetart = get_object_or_404(
        Geraetart,
        id=id
    )

    geraetart.delete()

    return redirect("geraetarten")

@login_required
def document_types(request):
    
    types = DocumentType.objects.all()

    return render(
        request,
        "devices/document_types.html",
        {
            "types": types
        }
    )
@login_required
def add_document_type(request):
    if not request.user.is_superuser:
        return redirect("permission_denied")

    if request.method == "POST":
        name = request.POST.get("name")

        if name:
            last_order = DocumentType.objects.count()

            DocumentType.objects.create(
                name=name,
                order=last_order
            )

            return redirect("document_types")

    return render(
        request,
        "devices/add_document_type.html"
    )

@login_required
def edit_document_type(request, id):
    if not request.user.is_superuser:
            return redirect("permission_denied")

    document_type = DocumentType.objects.get(id=id)

    if request.method == "POST":

        document_type.name = request.POST.get("name")
        document_type.save()

        return redirect("document_types")

    return render(
        request,
        "devices/edit_document_type.html",
        {
            "type": document_type
        }
    )
@login_required
def delete_document_type(request, id):

    document_type = DocumentType.objects.get(id=id)

    document_type.delete()

    return redirect("document_types")


@login_required
def backup(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    backup_dir = os.path.join(settings.BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    if request.method == "POST":

        db_path = os.path.join(settings.BASE_DIR, "db.sqlite3")

        filename = datetime.now().strftime(
            "backup_%Y-%m-%d_%H-%M-%S.sqlite3"
        )

        destination = os.path.join(
            backup_dir,
            filename
        )

        shutil.copy2(
            db_path,
            destination
        )

        messages.success(
            request,
            "Backup erfolgreich erstellt."
        )

        return redirect("backup")

    backups = []

    for file in os.listdir(backup_dir):

        if file.endswith(".sqlite3"):

            path = os.path.join(backup_dir, file)

            backups.append({
                "name": file,
                "size": round(os.path.getsize(path) / 1024 / 1024, 2),
                "date": datetime.fromtimestamp(
                    os.path.getmtime(path)
                ),
            })

    backups.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    return render(
        request,
        "devices/backup.html",
        {
            "backups": backups,
        }
    )

@login_required
def backup_download(request, filename):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    path = os.path.join(
        settings.BASE_DIR,
        "backups",
        filename
    )

    if not os.path.exists(path):
        raise Http404("Backup nicht gefunden.")

    return FileResponse(
        open(path, "rb"),
        as_attachment=True,
        filename=filename
    )


@login_required
def backup_delete(request, filename):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    path = os.path.join(
        settings.BASE_DIR,
        "backups",
        filename
    )

    if os.path.exists(path):
        os.remove(path)
        messages.success(
            request,
            "Backup erfolgreich gelöscht."
        )
    else:
        messages.error(
            request,
            "Backup nicht gefunden."
        )

    return redirect("backup")


@login_required
def backup_delete_all(request):

    # =========================================================
    # NUR ADMIN
    # =========================================================

    if not request.user.is_superuser:
        return redirect("permission_denied")


    # =========================================================
    # NUR POST
    # =========================================================

    if request.method != "POST":
        return redirect("backup")


    # =========================================================
    # BACKUP ORDNER
    # =========================================================

    backup_dir = os.path.join(
        settings.BASE_DIR,
        "backups"
    )


    # =========================================================
    # ORDNER NICHT VORHANDEN
    # =========================================================

    if not os.path.exists(backup_dir):

        messages.warning(
            request,
            "⚠️ Keine Backups vorhanden."
        )

        return redirect("backup")


    # =========================================================
    # ALLE BACKUPS LÖSCHEN
    # =========================================================

    deleted_count = 0


    for filename in os.listdir(backup_dir):

        filepath = os.path.join(
            backup_dir,
            filename
        )


        if not os.path.isfile(filepath):
            continue


        try:

            os.remove(filepath)

            deleted_count += 1

        except OSError:

            continue


    # =========================================================
    # ERGEBNIS
    # =========================================================

    if deleted_count > 0:

        messages.success(
            request,
            f"✅ {deleted_count} Backups wurden erfolgreich gelöscht."
        )

    else:

        messages.warning(
            request,
            "⚠️ Keine Backups zum Löschen vorhanden."
        )


    return redirect("backup")


@login_required
def backup_restore(request, filename):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    if request.method != "POST":
        return redirect("backup")

    backup_path = os.path.join(
        settings.BASE_DIR,
        "backups",
        filename
    )

    db_path = os.path.join(
        settings.BASE_DIR,
        "db.sqlite3"
    )

    if not os.path.exists(backup_path):
        messages.error(
            request,
            "Backup nicht gefunden."
        )
        return redirect("backup")

    shutil.copy2(
        backup_path,
        db_path
    )

    messages.success(
        request,
        "Backup erfolgreich wiederhergestellt. Bitte starten Sie den Server neu."
    )

    return redirect("backup")

def create_daily_backup():

    backup_dir = os.path.join(settings.BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    filename = f"daily_{today}.sqlite3"

    destination = os.path.join(
        backup_dir,
        filename
    )

    if not os.path.exists(destination):

        db = os.path.join(
            settings.BASE_DIR,
            "db.sqlite3"
        )

        shutil.copy2(
            db,
            destination
        )
        return filename

def create_update_backup():

    backup_dir = os.path.join(
        settings.BASE_DIR,
        "backups"
    )

    os.makedirs(
        backup_dir,
        exist_ok=True
    )

    db_path = os.path.join(
        settings.BASE_DIR,
        "db.sqlite3"
    )

    filename = datetime.now().strftime(
        "update_backup_%Y-%m-%d_%H-%M-%S.sqlite3"
    )

    destination = os.path.join(
        backup_dir,
        filename
    )

    shutil.copy2(
        db_path,
        destination
    )

    return filename




@login_required
def export(request):

    # =========================================================
    # USER BERECHTIGUNG
    # =========================================================

    if request.user.is_superuser:

        user_permission = None

    else:

        user_permission, created = (
            UserPermission.objects.get_or_create(
                user=request.user
            )
        )

        if not any([
            user_permission.permission_geraete,
            user_permission.permission_reparaturen,
            user_permission.permission_filter,
            user_permission.permission_wartung,
            user_permission.permission_rechnung,
        ]):

            return redirect("permission_denied")


   

    # =========================================================
    # EXPORT HAUPTORDNER
    # =========================================================

    export_dir = os.path.join(
        settings.BASE_DIR,
        "exports"
    )

    os.makedirs(
        export_dir,
        exist_ok=True
    )


    # =========================================================
    # BENUTZER EXPORT ORDNER
    # =========================================================

    user_export_dir = os.path.join(
        export_dir,
        str(request.user.id)
    )

    os.makedirs(
        user_export_dir,
        exist_ok=True
    )


    # =========================================================
    # POST = EXPORT ERSTELLEN
    # =========================================================

    if request.method == "POST":

        # =====================================================
        # WICHTIG
        # =====================================================

        elektrische_header_row = None

        # Mehrere Maschinen-Tabellen möglich
        maschinen_bloecke = []
        betten_bloecke = []


        export_typ = request.POST.get(
            "export_typ",
            ""
        ).strip()


        # =====================================================
        # EXCEL ERSTELLEN
        # =====================================================

        wb = Workbook()

        ws = wb.active

        ws.title = "Export"


        

        ws.append([])


        # =====================================================
        # 1. GESAMTE GERÄTE
        # =====================================================

        if export_typ == "geraete":

            geraetart_filter = request.POST.get(
                "geraetart",
                ""
            ).strip()

            standort_filter = request.POST.get(
                "standort",
                ""
            ).strip()


            devices = (
                Device.objects
                .select_related(
                    "geraetart",
                    "practice"
                )
                .all()
                .order_by(
                    "inventory_number"
                )
            )


            if geraetart_filter:

                devices = devices.filter(
                    geraetart_id=geraetart_filter
                )


            if standort_filter:

                devices = devices.filter(
                    practice_id=standort_filter
                )


            if not devices.exists():

                messages.warning(
                    request,
                    "⚠️ Keine Geräte zum Exportieren vorhanden."
                )

                return redirect("export")


            ws.append([
                "📋 Gesamte Geräte"
            ])

            ws.append([
                "Erstellt am: "
                + datetime.now().strftime(
                    "%d.%m.%Y %H:%M"
                )
            ])


            if geraetart_filter:

                geraetart_name = (
                    Geraetart.objects
                    .filter(
                        id=geraetart_filter
                    )
                    .values_list(
                        "name",
                        flat=True
                    )
                    .first()
                    or ""
                )

            else:

                geraetart_name = "Alle Gerätarten"


            ws.append([
                "Geräteart: "
                + geraetart_name
            ])


            if standort_filter:

                standort_name = (
                    Standort.objects
                    .filter(
                        id=standort_filter
                    )
                    .values_list(
                        "name",
                        flat=True
                    )
                    .first()
                    or ""
                )

            else:

                standort_name = "Alle Standorte"


            ws.append([
                "Standort: "
                + standort_name
            ])

            ws.append([])


            ws.append([
                "Inventarnummer",
                "Seriennummer",
                "Gerätbezeichnung",
                "Gerätart",
                "Standort",
                "Betriebsstunden",
                "Nächste Prüfung",
                "Status",
            ])


            for device in devices:

                naechste_pruefungen = []


                if device.next_stk:

                    naechste_pruefungen.append(
                        "STK: "
                        + device.next_stk.strftime(
                            "%d.%m.%Y"
                        )
                    )


                if device.next_mtk:

                    naechste_pruefungen.append(
                        "MTK: "
                        + device.next_mtk.strftime(
                            "%d.%m.%Y"
                        )
                    )


                if device.next_dguv:

                    naechste_pruefungen.append(
                        "DGUV V3: "
                        + device.next_dguv.strftime(
                            "%d.%m.%Y"
                        )
                    )


                ws.append([

                    device.inventory_number or "",

                    device.serial_number or "",

                    device.name or "",

                    (
                        device.geraetart.name
                        if device.geraetart
                        else ""
                    ),

                    (
                        device.practice.name
                        if device.practice
                        else ""
                    ),

                    (
                        device.operating_hours
                        if device.operating_hours is not None
                        else ""
                    ),

                    "\n".join(
                        naechste_pruefungen
                    ),

                    device.status or "",
                ])


        # =====================================================
        # 2. REPARATUR
        # =====================================================

        elif export_typ == "reparatur":

            geraetart_filter = request.POST.get(
                "geraetart",
                ""
            ).strip()

            inventarnummer_filter = request.POST.get(
                "inventarnummer",
                ""
            ).strip()

            standort_filter = request.POST.get(
                "standort",
                ""
            ).strip()

            datum_von = request.POST.get(
                "datum_von",
                ""
            ).strip()

            datum_bis = request.POST.get(
                "datum_bis",
                ""
            ).strip()


            # =================================================
            # FILTER PRÜFEN
            # =================================================

            if not geraetart_filter:

                messages.warning(
                    request,
                    "⚠️ Bitte wählen Sie eine Geräteart."
                )

                return redirect("export")


            geraetart = (
                Geraetart.objects
                .filter(
                    id=geraetart_filter
                )
                .first()
            )


            if not geraetart:

                messages.warning(
                    request,
                    "⚠️ Die ausgewählte Geräteart wurde nicht gefunden."
                )

                return redirect("export")


            if not standort_filter:

                messages.warning(
                    request,
                    "⚠️ Bitte wählen Sie einen Standort."
                )

                return redirect("export")


            standort = (
                Standort.objects
                .filter(
                    id=standort_filter
                )
                .first()
            )


            if not standort:

                messages.warning(
                    request,
                    "⚠️ Der ausgewählte Standort wurde nicht gefunden."
                )

                return redirect("export")


            if not datum_von:

                messages.warning(
                    request,
                    "⚠️ Bitte wählen Sie ein Startdatum."
                )

                return redirect("export")


            if not datum_bis:

                messages.warning(
                    request,
                    "⚠️ Bitte wählen Sie ein Enddatum."
                )

                return redirect("export")


            # =================================================
            # DATUM
            # =================================================

            try:

                datum_von_date = datetime.strptime(
                    datum_von,
                    "%Y-%m-%d"
                ).date()

                datum_bis_date = datetime.strptime(
                    datum_bis,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                messages.warning(
                    request,
                    "⚠️ Das ausgewählte Datum ist ungültig."
                )

                return redirect("export")


            if datum_von_date > datum_bis_date:

                messages.warning(
                    request,
                    "⚠️ Das Startdatum darf nicht nach dem Enddatum liegen."
                )

                return redirect("export")


            # =================================================
            # REPARATUREN
            # =================================================

            reparaturen = (
                Reparatur.objects
                .filter(
                    status="Erledigt",

                    geraet__geraetart_id=geraetart_filter,

                    geraet__practice_id=standort_filter,

                    datum__gte=datum_von_date,

                    datum__lte=datum_bis_date,
                )
                .select_related(
                    "geraet",
                    "geraet__geraetart",
                    "geraet__practice",
                )
                .prefetch_related(
                    "messmittel"
                )
                .order_by(
                    "-datum"
                )
            )


            # =================================================
            # INVENTARNUMMER
            # =================================================

            if inventarnummer_filter:

                reparaturen = reparaturen.filter(
                    geraet__inventory_number__iexact=
                        inventarnummer_filter
                )


            # =================================================
            # KEINE DATEN
            # =================================================

            if not reparaturen.exists():

                messages.warning(
                    request,
                    "⚠️ Keine Gerätedetails für Reparaturen mit Status Erledigt vorhanden."
                )

                return redirect("export")


            # =================================================
            # HAUPTÜBERSCHRIFTEN
            # =================================================

            reparaturbericht_nummer = 0

            for reparatur in reparaturen:

                geraet = reparatur.geraet

                # =================================================
                # REPARATURBERICHT-NUMMER
                # =================================================

                reparaturbericht_nummer += 1

                reparaturbericht_row = ws.max_row + 1

                ws.append([
                    f"Reparaturbericht {reparaturbericht_nummer}"
                ])

                
                # =================================================
                # REPARATURBERICHT – MITTE DER SEITE
                # =================================================

                ws.merge_cells(
                    start_row=reparaturbericht_row,
                    start_column=1,
                    end_row=reparaturbericht_row,
                    end_column=4
                )

                ws.cell(
                    row=reparaturbericht_row,
                    column=1
                ).alignment = Alignment(
                    horizontal="center",
                    vertical="center"
                )

                ws.cell(
                    row=reparaturbericht_row,
                    column=1
                ).font = Font(
                    bold=True,
                    size=16
                )

                ws.row_dimensions[
                    reparaturbericht_row
                ].height = 30

                # =================================================
                # GERÄT
                # =================================================

               
                ws.append([
                    "GERÄTEDETAIL"
                ])

                ws.append([])


                ws.append([
                    "Geräteart",
                    (
                        geraet.geraetart.name
                        if geraet and geraet.geraetart
                        else ""
                    )
                ])

                ws.append([
                    "Gerätbezeichnung",
                    (
                        geraet.name
                        if geraet
                        else ""
                    )
                ])

                ws.append([
                    "Inventarnummer",
                    (
                        geraet.inventory_number
                        if geraet
                        else ""
                    )
                ])

                ws.append([
                    "Seriennummer",
                    (
                        geraet.serial_number
                        if geraet
                        else ""
                    )
                ])

                ws.append([
                    "Standort",
                    (
                        geraet.practice.name
                        if geraet and geraet.practice
                        else ""
                    )
                ])


                # =================================================
                # REPARATUR
                # =================================================

                ws.append([])

                ws.append([
                    "REPARATUR"
                ])

                ws.append([])


                ws.append([
                    "Reparaturdatum",
                    (
                        reparatur.reparatur_datum.strftime(
                            "%d.%m.%Y"
                        )
                        if reparatur.reparatur_datum
                        else ""
                    )
                ])

                ws.append([
                    "Erstellt am",
                    (
                        reparatur.datum.strftime(
                            "%d.%m.%Y"
                        )
                        if reparatur.datum
                        else ""
                    )
                ])

                ws.append([
                    "Status",
                    reparatur.status or ""
                ])

                ws.append([
                    "Melder",
                    reparatur.melder or ""
                ])

                ws.append([
                    "Techniker",
                    reparatur.techniker or ""
                ])

                ws.append([
                    "Techniker gelesen",
                    (
                        "Ja"
                        if reparatur.techniker_gelesen
                        else "Nein"
                    )
                ])

                ws.append([
                    "Problembeschreibung",
                    reparatur.beschreibung or ""
                ])

                problem_cell = ws.cell(
                    row=ws.max_row,
                    column=2
                )

                problem_cell.alignment = Alignment(
                    horizontal="left",
                    vertical="top",
                    wrap_text=True
                )

                text = reparatur.beschreibung or ""

                if text:
                    # حساب عدد الأسطر بشكل محافظ
                    lines = 0

                    for paragraph in text.split("\n"):
                        if paragraph:
                            lines += max(
                                1,
                                (len(paragraph) + 49) // 50
                            )
                        else:
                            lines += 1

                    # إضافة مساحة إضافية حتى لا يختفي آخر سطر
                    ws.row_dimensions[ws.max_row].height = (
                        lines * 18 + 10
                    )
                else:
                    ws.row_dimensions[ws.max_row].height = 20


                ws.append([
                    "Ausführung",
                    reparatur.ausfuehrung or ""
                ])

                ausfuehrung_cell = ws.cell(
                    row=ws.max_row,
                    column=2
                )

                ausfuehrung_cell.alignment = Alignment(
                    horizontal="left",
                    vertical="top",
                    wrap_text=True
                )

                text = reparatur.ausfuehrung or ""

                if text:
                    # حساب عدد الأسطر بشكل محافظ
                    lines = 0

                    for paragraph in text.split("\n"):
                        if paragraph:
                            lines += max(
                                1,
                                (len(paragraph) + 49) // 50
                            )
                        else:
                            lines += 1

                    # إضافة مساحة إضافية حتى يظهر آخر سطر بالكامل
                    ws.row_dimensions[ws.max_row].height = (
                        lines * 18 + 10
                    )
                else:
                    ws.row_dimensions[ws.max_row].height = 20

               


                # =================================================
                # MESSMITTEL
                # =================================================

                messmittel = list(
                    reparatur.messmittel.all()
                )

                ws.append([])

                ws.append([
                    "MESSMITTEL"
                ])

                ws.append([])

                if messmittel:

                    for item in messmittel:

                        ws.append([
                            "Messmittel",
                            str(item)
                        ])

                else:

                    ws.append([
                        "Messmittel",
                        "Nicht vorhanden"
                    ])


                # =================================================
                # ELEKTRISCHE PRÜFUNG
                # =================================================

                ws.append([])

                ws.append([
                    "ELEKTRISCHE PRÜFUNG"
                ])

                ws.append([])


                if reparatur.elektrische_pruefung:

                    daten = (
                        reparatur.elektrische_pruefung_daten
                        or {}
                    )


                    # =================================================
                    # MASCHINEN
                    # =================================================

                    if (
                        reparatur.elektrische_pruefung_art
                        == "Maschinen"
                    ):

                        maschinen = (
                            daten.get("maschinen")
                            or {}
                        )


                        # -------------------------------------------------
                        # TABELLENKOPF
                        # -------------------------------------------------

                        ws.append([
                            "Prüfung",
                            "Grenzwert / Bedingung",
                            "Messwert",
                            "OK"
                        ])

                        maschinen_header_row = ws.max_row


                        # =================================================
                        # 1. SCHUTZLEITERWIDERSTAND
                        # =================================================

                        ws.append([
                            "Schutzleiterwiderstand",
                            "≤ 0,3 Ω",
                            (
                                str(
                                    maschinen
                                    .get(
                                        "schutzleiterwiderstand",
                                        {}
                                    )
                                    .get(
                                        "messwert",
                                        ""
                                    )
                                )
                                + (
                                    " Ω"
                                    if maschinen
                                    .get(
                                        "schutzleiterwiderstand",
                                        {}
                                    )
                                    .get(
                                        "messwert",
                                        ""
                                    )
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if maschinen
                                .get(
                                    "schutzleiterwiderstand",
                                    {}
                                )
                                .get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        # =================================================
                        # 2. TYP B
                        # =================================================

                        typ_b_row = ws.max_row + 1

                        ws.append([
                            (
                                "Typ des Anwendungsteils: Typ B\n\n"
                                "Gerätableitströme von Anwendungsteil "
                                "des Typs B gemessen auf Nennspannung "
                                "normiert und unter Berücksichtigung der "
                                "Zusatzbedingungen geprüft.\n\n"
                                "Sollwert: Iₙ ≤ 500 µA\n\n"
                                "Messverfahren:\n"
                                + (
                                    "☑ "
                                    if maschinen
                                    .get(
                                        "differenzstrommessung",
                                        {}
                                    )
                                    .get(
                                        "ok",
                                        False
                                    )
                                    else "☐ "
                                )
                                + "Differenzstrommessung nach Bild 8\n"
                                + (
                                    "☑ "
                                    if maschinen
                                    .get(
                                        "direktmessung",
                                        {}
                                    )
                                    .get(
                                        "ok",
                                        False
                                    )
                                    else "☐ "
                                )
                                + "Direktmessung nach Bild 7"
                            ),
                            "",
                            "",
                            "",
                        ])

                        ws.merge_cells(
                            start_row=typ_b_row,
                            start_column=1,
                            end_row=typ_b_row,
                            end_column=4
                        )


                        # =================================================
                        # 3. NENNSPANNUNG
                        # =================================================

                        nennspannung = (
                            maschinen
                            .get(
                                "nennspannung",
                                {}
                            )
                        )

                        ws.append([
                            "Nennspannung der Netzversorgung U₀",
                            "Nennspannung",
                            (
                                str(
                                    nennspannung.get(
                                        "messwert",
                                        ""
                                    )
                                )
                                + (
                                    " V"
                                    if nennspannung.get(
                                        "messwert",
                                        ""
                                    )
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if nennspannung.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        # =================================================
                        # 4. POLARITÄT L – N
                        # =================================================

                        polaritaet_ln = (
                            maschinen
                            .get(
                                "polaritaet_l_n",
                                {}
                            )
                        )

                        ln_start_row = ws.max_row + 1


                        # BMAX

                        ln_ibmax = (
                            polaritaet_ln
                            .get(
                                "ibmax",
                                {}
                            )
                        )

                        ws.append([
                            "Polarität der Netzversorgung L – N",
                            "Maximaler Geräteableitstrom I_Bmax",
                            (
                                str(
                                    ln_ibmax.get(
                                        "messwert",
                                        ""
                                    )
                                )
                                + (
                                    " µA"
                                    if ln_ibmax.get(
                                        "messwert",
                                        ""
                                    )
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if ln_ibmax.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        # UBMAX

                        ln_ubmax = (
                            polaritaet_ln
                            .get(
                                "ubmax",
                                {}
                            )
                        )

                        ws.append([
                            "",
                            "Zugehörige Netzspannung U_Bmax",
                            (
                                str(
                                    ln_ubmax.get(
                                        "messwert",
                                        ""
                                    )
                                )
                                + (
                                    " V"
                                    if ln_ubmax.get(
                                        "messwert",
                                        ""
                                    )
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if ln_ubmax.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        # IN

                        ln_in = (
                            polaritaet_ln
                            .get(
                                "in",
                                {}
                            )
                        )

                        ws.append([
                            "",
                            (
                                "Auf Nennspannung normierter "
                                "Geräteableitstrom\n\n"
                                "Iₙ = (U₀ × I_Bmax) : U_Bmax"
                            ),
                            (
                                str(
                                    ln_in.get(
                                        "messwert",
                                        ""
                                    )
                                )
                                + (
                                    " µA"
                                    if ln_in.get(
                                        "messwert",
                                        ""
                                    )
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if ln_in.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])

                        ln_end_row = ws.max_row

                        ws.merge_cells(
                            start_row=ln_start_row,
                            start_column=1,
                            end_row=ln_end_row,
                            end_column=1
                        )


                        # =================================================
                        # 5. POLARITÄT N – L
                        # =================================================

                        polaritaet_nl = (
                            maschinen
                            .get(
                                "polaritaet_n_l",
                                {}
                            )
                        )

                        nl_start_row = ws.max_row + 1


                        # BMAX

                        nl_ibmax = (
                            polaritaet_nl
                            .get(
                                "ibmax",
                                {}
                            )
                        )

                        ws.append([
                            "Polarität der Netzversorgung N – L",
                            "Maximaler Geräteableitstrom I_Bmax",
                            (
                                str(
                                    nl_ibmax.get(
                                        "messwert",
                                        ""
                                    )
                                )
                                + (
                                    " µA"
                                    if nl_ibmax.get(
                                        "messwert",
                                        ""
                                    )
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if nl_ibmax.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        # UBMAX

                        nl_ubmax = (
                            polaritaet_nl
                            .get(
                                "ubmax",
                                {}
                            )
                        )

                        ws.append([
                            "",
                            "Zugehörige Netzspannung U_Bmax",
                            (
                                str(
                                    nl_ubmax.get(
                                        "messwert",
                                        ""
                                    )
                                )
                                + (
                                    " V"
                                    if nl_ubmax.get(
                                        "messwert",
                                        ""
                                    )
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if nl_ubmax.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        # IN

                        nl_in = (
                            polaritaet_nl
                            .get(
                                "in",
                                {}
                            )
                        )

                        ws.append([
                            "",
                            (
                                "Auf Nennspannung normierter "
                                "Geräteableitstrom\n\n"
                                "Iₙ = (U₀ × I_Bmax) : U_Bmax"
                            ),
                            (
                                str(
                                    nl_in.get(
                                        "messwert",
                                        ""
                                    )
                                )
                                + (
                                    " µA"
                                    if nl_in.get(
                                        "messwert",
                                        ""
                                    )
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if nl_in.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])

                        nl_end_row = ws.max_row

                        ws.merge_cells(
                            start_row=nl_start_row,
                            start_column=1,
                            end_row=nl_end_row,
                            end_column=1
                        )


                        # =================================================
                        # MASCHINEN-BLOCK SPEICHERN
                        # =================================================

                        maschinen_bloecke.append({
                            "header": maschinen_header_row,
                            "typ_b": typ_b_row,
                            "ln_start": ln_start_row,
                            "ln_end": ln_end_row,
                            "nl_start": nl_start_row,
                            "nl_end": nl_end_row,
                        })


                    # =================================================
                    # BETTEN
                    # =================================================

                    elif (
                        reparatur.elektrische_pruefung_art
                        == "Betten"
                    ):

                        betten = (
                            daten.get("betten")
                            or {}
                        )


                        # =================================================
                        # TABELLENKOPF
                        # =================================================

                        ws.append([
                            "Elektrostimulation",
                            "Grenzwert",
                            "Messwert",
                            "OK"
                        ])

                        betten_header_row = ws.max_row


                        # =================================================
                        # POTENTIALAUSGLEICHSWIDERSTAND
                        # =================================================

                        potential = (
                            betten.get(
                                "potentialausgleichswiderstand"
                            )
                            or {}
                        )

                        potential_start_row = (
                            ws.max_row + 1
                        )


                        # -------------------------------------------------
                        # MESSPUNKT 1
                        # -------------------------------------------------

                        punkt_1 = (
                            potential.get("1")
                            or {}
                        )

                        messwert_1 = str(
                            punkt_1.get(
                                "messwert",
                                ""
                            )
                        ).strip()

                        ws.append([
                            "Potentialausgleichswiderstand\n"
                            "(anhand der Messpunkte)",

                            "< 0,2 Ω",

                            (
                                "Messpunkt 1:"
                                + (
                                    "          " + messwert_1
                                    if messwert_1
                                    else ""
                                )
                            ),

                            (
                                "OK"
                                if punkt_1.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        # -------------------------------------------------
                        # MESSPUNKT 2
                        # -------------------------------------------------

                        punkt_2 = (
                            potential.get("2")
                            or {}
                        )

                        messwert_2 = str(
                            punkt_2.get(
                                "messwert",
                                ""
                            )
                        ).strip()

                        ws.append([
                            "",
                            "",
                            (
                                "Messpunkt 2:"
                                + (
                                    "          " + messwert_2
                                    if messwert_2
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if punkt_2.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        # -------------------------------------------------
                        # MESSPUNKT 3
                        # -------------------------------------------------

                        punkt_3 = (
                            potential.get("3")
                            or {}
                        )

                        messwert_3 = str(
                            punkt_3.get(
                                "messwert",
                                ""
                            )
                        ).strip()

                        ws.append([
                            "",
                            "",
                            (
                                "Messpunkt 3:"
                                + (
                                    "          " + messwert_3
                                    if messwert_3
                                    else ""
                                )
                            ),
                            (
                                "OK"
                                if punkt_3.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        potential_end_row = (
                            ws.max_row
                        )


                        ws.merge_cells(
                            start_row=potential_start_row,
                            start_column=1,
                            end_row=potential_end_row,
                            end_column=1
                        )

                        ws.merge_cells(
                            start_row=potential_start_row,
                            start_column=2,
                            end_row=potential_end_row,
                            end_column=2
                        )


                        # =================================================
                        # GERÄTEABLEITSTROM ERSATZMESSUNG
                        # =================================================

                        ersatzmessung = (
                            betten.get(
                                "geraeteableitstrom_ersatzmessung"
                            )
                            or {}
                        )

                        ersatz_start_row = (
                            ws.max_row + 1
                        )


                        intrakardial = (
                            ersatzmessung.get(
                                "intrakardiale_anwendung"
                            )
                            or {}
                        )

                        ws.append([
                            "Geräteableitstrom\nErsatzmessung",
                            "Intrakardiale Anwendung: < 50 µA",
                            str(
                                intrakardial.get(
                                    "messwert",
                                    ""
                                )
                            ).strip(),
                            (
                                "OK"
                                if intrakardial.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        typ_b = (
                            ersatzmessung.get(
                                "typ_b"
                            )
                            or {}
                        )

                        ws.append([
                            "",
                            "Messung nach Typ B: < 500 µA",
                            str(
                                typ_b.get(
                                    "messwert",
                                    ""
                                )
                            ).strip(),
                            (
                                "OK"
                                if typ_b.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        laserlampe = (
                            ersatzmessung.get(
                                "laserlampe"
                            )
                            or {}
                        )

                        ws.append([
                            "",
                            (
                                "Messung Laserlampe mit eigenem "
                                "Netzstecker: < 50 µA"
                            ),
                            str(
                                laserlampe.get(
                                    "messwert",
                                    ""
                                )
                            ).strip(),
                            (
                                "OK"
                                if laserlampe.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        netzspannung = (
                            ersatzmessung.get(
                                "netzspannung"
                            )
                            or {}
                        )

                        ws.append([
                            "",
                            "Netzspannung: 230 V (EU)",
                            str(
                                netzspannung.get(
                                    "messwert",
                                    ""
                                )
                            ).strip(),
                            (
                                "OK"
                                if netzspannung.get(
                                    "ok",
                                    False
                                )
                                else ""
                            ),
                        ])


                        ersatz_end_row = (
                            ws.max_row
                        )


                        ws.merge_cells(
                            start_row=ersatz_start_row,
                            start_column=1,
                            end_row=ersatz_end_row,
                            end_column=1
                        )


                        # =================================================
                        # BETTEN-BLOCK SPEICHERN
                        # =================================================

                        betten_bloecke.append({

                            "header_row":
                                betten_header_row,

                            "potential_start_row":
                                potential_start_row,

                            "potential_end_row":
                                potential_end_row,

                            "ersatz_start_row":
                                ersatz_start_row,

                            "ersatz_end_row":
                                ersatz_end_row,
                        })


                    # =================================================
                    # ALLE ANDEREN ELEKTRISCHEN PRÜFUNGEN
                    # =================================================

                    else:

                        ws.append([
                            "Prüfung",
                            "Messwert",
                            "Ergebnis"
                        ])

                        elektrische_header_row = (
                            ws.max_row
                        )

                        # -------------------------------------------------
                        # DEIN BISHERIGER CODE
                        # -------------------------------------------------

                        export_pruefung_data(
                            daten
                        )


                # =================================================
                # KEINE ELEKTRISCHE PRÜFUNG
                # =================================================

                else:

                    ws.append([
                        "Elektrische Prüfung",
                        "Nein"
                    ])


                # =================================================
                # TRENNUNG
                # =================================================

                ws.append([])

                ws.append([])


        # =====================================================
        # 3. FILTERWECHSEL HISTORIE
        # =====================================================

        elif export_typ == "filterwechsel":

            standort_filter = request.POST.get(
                "standort",
                ""
            ).strip()

            datum_von = request.POST.get(
                "datum_von",
                ""
            ).strip()

            datum_bis = request.POST.get(
                "datum_bis",
                ""
            ).strip()


            filterwechsel = (
                Filterwechsel.objects
                .select_related(
                    "geraet",
                    "geraet__practice",
                )
                .order_by(
                    "-datum"
                )
            )


            if standort_filter:

                filterwechsel = filterwechsel.filter(
                    geraet__practice_id=standort_filter
                )


            datum_von_date = None
            datum_bis_date = None


            if datum_von:

                try:

                    datum_von_date = datetime.strptime(
                        datum_von,
                        "%Y-%m-%d"
                    ).date()

                    filterwechsel = filterwechsel.filter(
                        datum__gte=datum_von_date
                    )

                except ValueError:

                    messages.warning(
                        request,
                        "⚠️ Das Startdatum ist ungültig."
                    )

                    return redirect("export")


            if datum_bis:

                try:

                    datum_bis_date = datetime.strptime(
                        datum_bis,
                        "%Y-%m-%d"
                    ).date()

                    filterwechsel = filterwechsel.filter(
                        datum__lte=datum_bis_date
                    )

                except ValueError:

                    messages.warning(
                        request,
                        "⚠️ Das Enddatum ist ungültig."
                    )

                    return redirect("export")


            if (
                datum_von_date
                and datum_bis_date
                and datum_von_date > datum_bis_date
            ):

                messages.warning(
                    request,
                    "⚠️ Das Startdatum darf nicht nach dem Enddatum liegen."
                )

                return redirect("export")


            if not filterwechsel.exists():

                messages.warning(
                    request,
                    "⚠️ Keine Filterwechsel für die ausgewählten Filter vorhanden."
                )

                return redirect("export")


            if standort_filter:

                standort_name = (
                    Standort.objects
                    .filter(
                        id=standort_filter
                    )
                    .values_list(
                        "name",
                        flat=True
                    )
                    .first()
                    or ""
                )

            else:

                standort_name = "Alle Standorte"


            ws.append([
                "🔄 Filterwechselhistorie"
            ])

            ws.append([
                "Erstellt am: "
                + datetime.now().strftime(
                    "%d.%m.%Y %H:%M"
                )
            ])

            ws.append([
                "Standort: "
                + standort_name
            ])

            ws.append([
                "Zeitraum von: "
                + (
                    datum_von_date.strftime("%d.%m.%Y")
                    if datum_von_date
                    else "Alle"
                )
            ])

            ws.append([
                "Zeitraum bis: "
                + (
                    datum_bis_date.strftime("%d.%m.%Y")
                    if datum_bis_date
                    else "Alle"
                )
            ])

            ws.append([])


            ws.append([
                "Inventarnummer",
                "Anzahl der Filter",
                "Filtercode",
                "Datum",
                "Durchgeführt von",
                "Standort",
            ])


            for item in filterwechsel:

                geraet = item.geraet

                ws.append([

                    (
                        geraet.inventory_number
                        if geraet
                        else ""
                    ),

                    (
                        item.anzahl_filter
                        if item.anzahl_filter is not None
                        else ""
                    ),

                    item.filtercode or "",

                    (
                        item.datum.strftime("%d.%m.%Y")
                        if item.datum
                        else ""
                    ),

                    getattr(
                        item,
                        "durchgeführt_von",
                        ""
                    ) or "",

                    (
                        geraet.practice.name
                        if geraet and geraet.practice
                        else ""
                    ),
                ])


        # =====================================================
        # 4. WARTUNG / PRÜFUNGEN
        # =====================================================

        elif export_typ == "wartung":

            pruefart_id = request.POST.get(
                "pruefart_id",
                ""
            ).strip()

            pruef_status = request.POST.get(
                "status",
                ""
            ).strip()

            standort = request.POST.get(
                "standort",
                ""
            ).strip()


            if not pruefart_id:

                messages.warning(
                    request,
                    "⚠️ Keine Prüfart ausgewählt."
                )

                return redirect("export")


            try:

                pruefart = (
                    Pruefart.objects
                    .filter(
                        id=int(pruefart_id)
                    )
                    .first()
                )

            except (ValueError, TypeError):

                pruefart = None


            if not pruefart:

                messages.warning(
                    request,
                    "⚠️ Prüfart wurde nicht gefunden."
                )

                return redirect("export")


            pruefungen = (
                DevicePruefung.objects
                .filter(
                    pruefart_id=pruefart.id,
                    aktiv=True,
                    device__status="Aktiv",
                    naechstes_datum__isnull=False,
                )
                .select_related(
                    "device",
                    "pruefart",
                    "device__geraetart",
                    "device__practice",
                )
            )


            # =================================================
            # STANDORT FILTER
            # =================================================

            if standort:

                pruefungen = pruefungen.filter(
                    device__practice__name=standort
                )


            heute = datetime.now().date()

            grenze = heute + timedelta(days=30)


            if pruef_status == "gueltig":

                pruefungen = pruefungen.filter(
                    naechstes_datum__gt=grenze
                )

            elif pruef_status == "faellig":

                pruefungen = pruefungen.filter(
                    naechstes_datum__gte=heute,
                    naechstes_datum__lte=grenze
                )

            elif pruef_status == "ueberfaellig":

                pruefungen = pruefungen.filter(
                    naechstes_datum__lt=heute
                )


            pruefungen = pruefungen.order_by(
                "naechstes_datum"
            )


            if not pruefungen.exists():

                status_name = {

                    "gueltig": "Gültig",

                    "faellig": "Fällig",

                    "ueberfaellig": "Überfällig",

                }.get(
                    pruef_status,
                    "Alle"
                )


                messages.warning(
                    request,
                    f"⚠️ Keine Daten für {pruefart.name} "
                    f"mit Status {status_name} "
                    f"und Standort {standort or 'Alle'} "
                    f"zum Exportieren vorhanden."
                )

                return redirect("export")


            ws.append([
                f"📋 Prüfungen - {pruefart.name}"
            ])

            ws.append([
                "Erstellt am: "
                + datetime.now().strftime(
                    "%d.%m.%Y %H:%M"
                )
            ])

            ws.append([
                "Status: "
                + (
                    "Alle"
                    if not pruef_status
                    else {
                        "gueltig": "Gültig",
                        "faellig": "Fällig",
                        "ueberfaellig": "Überfällig",
                    }.get(
                        pruef_status,
                        pruef_status
                    )
                )
            ])

            ws.append([
                "Standort: "
                + (
                    "Alle"
                    if not standort
                    else standort
                )
            ])

            ws.append([])


            ws.append([
                "Inventarnummer",
                "Seriennummer",
                "Gerätbezeichnung",
                "Gerätart",
                "Standort",
                "Nächste Prüfung",
                "Status",
            ])


            for pruefung in pruefungen:

                device = pruefung.device


                if pruefung.naechstes_datum < heute:

                    status_text = "Überfällig"

                elif pruefung.naechstes_datum <= grenze:

                    status_text = "Fällig"

                else:

                    status_text = "Gültig"


                ws.append([

                    device.inventory_number or "",

                    device.serial_number or "",

                    device.name or "",

                    (
                        device.geraetart.name
                        if device.geraetart
                        else ""
                    ),

                    (
                        device.practice.name
                        if device.practice
                        else ""
                    ),

                    pruefung.naechstes_datum.strftime(
                        "%d.%m.%Y"
                    ),

                    status_text,
                ])

        # =====================================================
        # 5. RECHNUNGSHISTORIE
        # =====================================================

        elif export_typ == "rechnung":

            kategorie_filter = request.POST.get(
                "kategorie",
                ""
            ).strip()

            status_filter = request.POST.get(
                "status",
                ""
            ).strip()

            datum_von = request.POST.get(
                "datum_von",
                ""
            ).strip()

            datum_bis = request.POST.get(
                "datum_bis",
                ""
            ).strip()


            rechnungen = (
                Rechnung.objects
                .select_related(
                    "erstellt_von",
                    "kategorie",
                )
                .all()
                .order_by(
                    "-rechnungsdatum"
                )
            )


            if kategorie_filter:

                rechnungen = rechnungen.filter(
                    kategorie_id=kategorie_filter
                )


            if status_filter:

                rechnungen = rechnungen.filter(
                    status__iexact=status_filter
                )


            datum_von_date = None
            datum_bis_date = None


            if datum_von:

                try:

                    datum_von_date = datetime.strptime(
                        datum_von,
                        "%Y-%m-%d"
                    ).date()

                except ValueError:

                    messages.warning(
                        request,
                        "⚠️ Das Rechnungsdatum von ist ungültig."
                    )

                    return redirect("export")


                rechnungen = rechnungen.filter(
                    rechnungsdatum__gte=datum_von_date
                )


            if datum_bis:

                try:

                    datum_bis_date = datetime.strptime(
                        datum_bis,
                        "%Y-%m-%d"
                    ).date()

                except ValueError:

                    messages.warning(
                        request,
                        "⚠️ Das Rechnungsdatum bis ist ungültig."
                    )

                    return redirect("export")


                rechnungen = rechnungen.filter(
                    rechnungsdatum__lte=datum_bis_date
                )


            if (
                datum_von_date
                and datum_bis_date
                and datum_von_date > datum_bis_date
            ):

                messages.warning(
                    request,
                    "⚠️ Das Rechnungsdatum von darf nicht nach dem Rechnungsdatum bis liegen."
                )

                return redirect("export")


            if not rechnungen.exists():

                messages.warning(
                    request,
                    "⚠️ Keine Rechnungen für die ausgewählten Filter vorhanden."
                )

                return redirect("export")


            if kategorie_filter:

                kategorie_name = (
                    RechnungKategorie.objects
                    .filter(
                        id=kategorie_filter
                    )
                    .values_list(
                        "name",
                        flat=True
                    )
                    .first()
                    or ""
                )

            else:

                kategorie_name = "Alle Kategorien"


            status_name = (
                status_filter
                if status_filter
                else "Alle"
            )


            gesamtsumme = (
                rechnungen.aggregate(
                    total=Sum(
                        "rechnungsbetrag"
                    )
                )["total"]
                or 0
            )


            ws.append([
                "🧾 Rechnungshistorie"
            ])

            ws.append([
                "Erstellt am: "
                + datetime.now().strftime(
                    "%d.%m.%Y %H:%M"
                )
            ])

            ws.append([
                "Kategorie: "
                + kategorie_name
            ])

            ws.append([
                "Status: "
                + status_name
            ])

            ws.append([
                "Rechnungsdatum von: "
                + (
                    datum_von_date.strftime("%d.%m.%Y")
                    if datum_von_date
                    else "Alle"
                )
            ])

            ws.append([
                "Rechnungsdatum bis: "
                + (
                    datum_bis_date.strftime("%d.%m.%Y")
                    if datum_bis_date
                    else "Alle"
                )
            ])

            ws.append([
                "Gesamtsumme: "
                + f"{float(gesamtsumme):.2f} €"
            ])

            ws.append([])


            ws.append([
                "Rechnungsnummer",
                "Rechnungsdatum",
                "Lieferant",
                "Auftragsnummer",
                "Lieferscheinnummer",
                "Kundennummer",
                "Leistungsdatum",
                "Betrag",
                "Zahlungsziel",
                "Fälligkeitsdatum",
                "Kostenstelle",
                "Kategorie",
                "Verantwortlicher",
                "Bezahlt am",
                "Zahlungsreferenz",
                "Status",
                "Bemerkung",
            ])


            for r in rechnungen:

                ws.append([

                    r.rechnungsnummer or "",

                    (
                        r.rechnungsdatum.strftime("%d.%m.%Y")
                        if r.rechnungsdatum
                        else ""
                    ),

                    r.lieferant or "",

                    r.auftragsnummer or "",

                    r.lieferscheinnummer or "",

                    r.kundennummer or "",

                    (
                        r.leistungsdatum.strftime("%d.%m.%Y")
                        if r.leistungsdatum
                        else ""
                    ),

                    float(
                        r.rechnungsbetrag or 0
                    ),

                    (
                        r.zahlungsziel
                        if r.zahlungsziel is not None
                        else ""
                    ),

                    (
                        r.faelligkeitsdatum.strftime("%d.%m.%Y")
                        if r.faelligkeitsdatum
                        else ""
                    ),

                    r.kostenstelle or "",

                    (
                        r.kategorie.name
                        if r.kategorie
                        else ""
                    ),

                    r.verantwortlicher or "",

                    (
                        r.bezahlt_am.strftime("%d.%m.%Y")
                        if r.bezahlt_am
                        else ""
                    ),

                    r.zahlungsreferenz or "",

                    r.status or "",

                    r.bemerkung or "",
                ])


        # =====================================================
        # UNBEKANNTER EXPORT
        # =====================================================

        else:

            messages.error(
                request,
                "Bitte wählen Sie einen Export-Typ."
            )

            return redirect("export")


        # =====================================================
        # EXCEL DESIGN
        # =====================================================

        DARK = "1F4E78"
        BLUE = "D9EAF7"
        LIGHT_BLUE = "EAF3F8"
        GREY = "F2F2F2"
        WHITE = "FFFFFF"
        GREEN = "E2F0D9"
        RED = "FCE4D6"


        title_font = Font(
            name="Calibri",
            size=18,
            bold=True,
            color=WHITE
        )

        section_font = Font(
            name="Calibri",
            size=13,
            bold=True,
            color=WHITE
        )

        label_font = Font(
            name="Calibri",
            size=11,
            bold=True
        )

        normal_font = Font(
            name="Calibri",
            size=11
        )


        title_fill = PatternFill(
            "solid",
            fgColor=DARK
        )

        section_fill = PatternFill(
            "solid",
            fgColor=DARK
        )

        label_fill = PatternFill(
            "solid",
            fgColor=BLUE
        )

        info_fill = PatternFill(
            "solid",
            fgColor=LIGHT_BLUE
        )

        grey_fill = PatternFill(
            "solid",
            fgColor=GREY
        )

        green_fill = PatternFill(
            "solid",
            fgColor=GREEN
        )

        red_fill = PatternFill(
            "solid",
            fgColor=RED
        )


        thin_side = Side(
            style="thin",
            color="B7B7B7"
        )

        medium_side = Side(
            style="medium",
            color=DARK
        )

        thin_border = Border(
            left=thin_side,
            right=thin_side,
            top=thin_side,
            bottom=thin_side
        )

        section_border = Border(
            left=medium_side,
            right=medium_side,
            top=medium_side,
            bottom=medium_side
        )

        

        
        # =====================================================
        # STANDARD FORMATIERUNG
        # =====================================================

        for row in ws.iter_rows():

            for cell in row:

                if cell.value is not None:

                    cell.font = normal_font

                    cell.alignment = Alignment(
                        vertical="top",
                        horizontal="left",
                        wrap_text=True
                    )

                    cell.border = thin_border


        # =====================================================
        # SPALTENBREITEN
        # =====================================================

        widths = {

            "A": 55,
            "B": 38,
            "C": 24,
            "D": 28,
            "E": 28,
            "F": 28,
            "G": 28,
            "H": 28,
            "I": 28,
            "J": 28,
            "K": 28,
            "L": 28,
            "M": 28,
            "N": 28,
            "O": 28,
            "P": 28,
            "Q": 42,

        }


        for column, width in widths.items():

            ws.column_dimensions[
                column
            ].width = width


        # =====================================================
        # MASCHINEN-TABELLE
        # =====================================================

        if export_typ == "reparatur":

            # -------------------------------------------------
            # Alle Zeilen suchen, die als Maschinen-Tabelle
            # markiert wurden.
            # -------------------------------------------------

            maschinen_header_rows = []

            for row_number in range(
                1,
                ws.max_row + 1
            ):

                value_a = ws.cell(
                    row=row_number,
                    column=1
                ).value

                value_b = ws.cell(
                    row=row_number,
                    column=2
                ).value

                value_c = ws.cell(
                    row=row_number,
                    column=3
                ).value

                value_d = ws.cell(
                    row=row_number,
                    column=4
                ).value


                if (
                    value_a == "Prüfung"
                    and
                    value_b == "Grenzwert / Bedingung"
                    and
                    value_c == "Messwert"
                    and
                    value_d == "OK"
                ):

                    maschinen_header_rows.append(
                        row_number
                    )


            # -------------------------------------------------
            # Maschinen Header
            # -------------------------------------------------

            for header_row in maschinen_header_rows:

                for column in range(1, 5):

                    cell = ws.cell(
                        row=header_row,
                        column=column
                    )

                    cell.fill = section_fill

                    cell.font = Font(
                        name="Calibri",
                        size=12,
                        bold=True,
                        color=WHITE
                    )

                    cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center",
                        wrap_text=True
                    )

                    cell.border = section_border


                ws.row_dimensions[
                    header_row
                ].height = 32


        # =====================================================
        # ABSCHNITTE FORMATIEREN
        # =====================================================

        for row_number in range(
            1,
            ws.max_row + 1
        ):

            first_cell = ws.cell(
                row=row_number,
                column=1
            )

            first_value = (
                str(first_cell.value).strip()
                if first_cell.value is not None
                else ""
            )


            # =================================================
            # HAUPTTITEL
            # =================================================

            if (
                first_value.startswith("📋")
                or
                first_value.startswith("🧾")
                or
                first_value.startswith("🔄")
            ):

                ws.merge_cells(
                    start_row=row_number,
                    start_column=1,
                    end_row=row_number,
                    end_column=4
                )

                for column in range(1, 5):

                    cell = ws.cell(
                        row=row_number,
                        column=column
                    )

                    cell.fill = title_fill
                    cell.border = section_border


                cell = ws.cell(
                    row=row_number,
                    column=1
                )

                cell.font = title_font

                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center"
                )

                ws.row_dimensions[
                    row_number
                ].height = 32


            # =================================================
            # SEKTIONSÜBERSCHRIFT
            # =================================================
            
            elif first_value.startswith("Reparaturbericht "):

            
                cell = ws.cell(
                    row=row_number,
                    column=1
                )

                # Keine Hintergrundfarbe
                cell.fill = PatternFill(
                    fill_type=None
                )

                # Kein Rahmen
                cell.border = Border()

                # Groß und fett
                cell.font = Font(
                    name="Calibri",
                    size=16,
                    bold=True
                )

                # In die Mitte
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center"
                )

                ws.row_dimensions[
                    row_number
                ].height = 30

            elif first_value in [
                "GERÄTEDETAIL",
                "REPARATUR",
                "MESSMITTEL",
                "ELEKTRISCHE PRÜFUNG",
            ]:

                # Nur Zelle A formatieren
                cell = ws.cell(
                    row=row_number,
                    column=1
                )

                cell.fill = section_fill

                cell.font = Font(
                    name="Calibri",
                    size=13,
                    bold=True,
                    color=WHITE
                )

                cell.alignment = Alignment(
                    horizontal="left",
                    vertical="center"
                )

                cell.border = section_border

                ws.row_dimensions[
                    row_number
                ].height = 25

                # B, C und D bleiben normal / ohne Titel-Farbe
                for column in range(2, 5):

                    cell = ws.cell(
                        row=row_number,
                        column=column
                    )

                    cell.fill = PatternFill(
                        fill_type=None
                    )

                    cell.border = Border()


        # =====================================================
        # LABEL / VALUE
        # =====================================================

        for row_number in range(
            1,
            ws.max_row + 1
        ):

            label = ws.cell(
                row=row_number,
                column=1
            )

            value = ws.cell(
                row=row_number,
                column=2
            )


            if (
                label.value is not None
                and
                value.value is not None
            ):

                # -------------------------------------------------
                # ELEKTRISCHE PRÜFUNG - 3/4 SPALTEN
                # -------------------------------------------------

                if (
                    str(label.value).strip()
                    == "Prüfung"
                ):

                    continue


                label.font = label_font

                label.fill = label_fill

                label.alignment = Alignment(
                    horizontal="left",
                    vertical="center",
                    wrap_text=True
                )

                label.border = thin_border


                value.font = normal_font

                value.fill = info_fill

                value.alignment = Alignment(
                    horizontal="left",
                    vertical="top",
                    wrap_text=True
                )

                value.border = thin_border


        # =====================================================
        # MASCHINEN-TABELLE FORMATIEREN
        # =====================================================

        if export_typ == "reparatur":

            for header_row in maschinen_header_rows:

                row_number = header_row + 1

                while row_number <= ws.max_row:

                    first_value = ws.cell(
                        row=row_number,
                        column=1
                    ).value


                    # Ende der Tabelle

                    if first_value in [
                        None,
                        "GERÄTEDETAIL",
                        "REPARATUR",
                        "MESSMITTEL",
                        "ELEKTRISCHE PRÜFUNG",
                    ]:

                        break


                    # Neue Maschinen-Tabelle

                    if (
                        ws.cell(
                            row=row_number,
                            column=1
                        ).value
                        == "Prüfung"
                    ):

                        break


                    # -------------------------------------------------
                    # Alle 4 Spalten formatieren
                    # -------------------------------------------------

                    for column in range(1, 5):

                        cell = ws.cell(
                            row=row_number,
                            column=column
                        )

                        cell.border = thin_border

                        cell.alignment = Alignment(
                            horizontal="left"
                            if column != 4
                            else "center",
                            vertical="top",
                            wrap_text=True
                        )


                    # -------------------------------------------------
                    # Prüfung
                    # -------------------------------------------------

                    ws.cell(
                        row=row_number,
                        column=1
                    ).font = Font(
                        name="Calibri",
                        size=11,
                        bold=True
                    )

                    ws.cell(
                        row=row_number,
                        column=1
                    ).fill = info_fill


                    # -------------------------------------------------
                    # Grenzwert
                    # -------------------------------------------------

                    ws.cell(
                        row=row_number,
                        column=2
                    ).fill = info_fill


                    # -------------------------------------------------
                    # Messwert
                    # -------------------------------------------------

                    ws.cell(
                        row=row_number,
                        column=3
                    ).fill = info_fill

                    ws.cell(
                        row=row_number,
                        column=3
                    ).alignment = Alignment(
                        horizontal="center",
                        vertical="center",
                        wrap_text=True
                    )


                    # -------------------------------------------------
                    # OK
                    # -------------------------------------------------

                    ok_cell = ws.cell(
                        row=row_number,
                        column=4
                    )

                    ok_text = str(
                        ok_cell.value or ""
                    ).strip()


                    ok_cell.font = Font(
                        name="Calibri",
                        size=11,
                        bold=True
                    )

                    ok_cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center"
                    )


                    if ok_text == "OK":

                        ok_cell.fill = green_fill

                    else:

                        ok_cell.fill = grey_fill


                    # -------------------------------------------------
                    # Zeilenhöhe
                    # -------------------------------------------------

                    max_length = max(
                        len(
                            str(
                                ws.cell(
                                    row=row_number,
                                    column=1
                                ).value or ""
                            )
                        ),
                        len(
                            str(
                                ws.cell(
                                    row=row_number,
                                    column=2
                                ).value or ""
                            )
                        ),
                    )


                    ws.row_dimensions[
                        row_number
                    ].height = max(
                        30,
                        min(
                            20 * (
                                max_length // 45 + 1
                            ),
                            120
                        )
                    )


                    row_number += 1


        # =====================================================
        # STATUS / OK
        # =====================================================

        for row in ws.iter_rows():

            for cell in row:

                if cell.value is None:

                    continue


                text = str(
                    cell.value
                ).strip()


                if text in [
                    "Erledigt",
                    "OK",
                    "Ja",
                ]:

                    cell.fill = green_fill

                    cell.font = Font(
                        name="Calibri",
                        size=11,
                        bold=True
                    )

                    cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center",
                        wrap_text=True
                    )


                elif text == "Nicht OK":

                    cell.value = ""

                    cell.fill = grey_fill


        # =====================================================
        # META-INFORMATIONEN OBEN
        # =====================================================

        for row_number in range(
            1,
            min(ws.max_row, 10) + 1
        ):

            for column in range(
                1,
                min(ws.max_column, 4) + 1
            ):

                cell = ws.cell(
                    row=row_number,
                    column=column
                )

                if cell.value is None:
                    continue

                text = str(
                    cell.value
                ).strip()

                # -------------------------------------------------
                # Reparaturbericht nicht als Meta-Information formatieren
                # -------------------------------------------------

                if text.startswith("Reparaturbericht "):

                    continue
                # -------------------------------------------------
                # Buchst Eis / Buchst Spai
                # -------------------------------------------------

                if text in [
                    "Buchst Eis",
                    "Buchst Spai"
                ]:

                    cell.font = Font(
                        name="Calibri",
                        size=11,
                        bold=True,
                        italic=False
                    )

                    cell.alignment = Alignment(
                        horizontal="left",
                        vertical="center",
                        wrap_text=False
                    )

                    continue


                # -------------------------------------------------
                # Dunkle Zellen nicht verändern
                # -------------------------------------------------

                if (
                    cell.fill.fgColor.rgb
                    and
                    str(
                        cell.fill.fgColor.rgb
                    ).endswith(DARK)
                ):

                    continue


                # -------------------------------------------------
                # Normale Meta-Informationen
                # -------------------------------------------------

                cell.fill = grey_fill

                cell.font = Font(
                    name="Calibri",
                    size=10,
                    bold=False,
                    italic=True
                )

        # =====================================================
        # ZEILENHÖHE AUTOMATISCH
        # =====================================================

        for row_number in range(
            1,
            ws.max_row + 1
        ):

            current_height = (
                ws.row_dimensions[
                    row_number
                ].height
            )


            if current_height is not None:

                continue


            max_lines = 1


            for column in range(
                1,
                ws.max_column + 1
            ):

                value = ws.cell(
                    row=row_number,
                    column=column
                ).value


                if value is None:

                    continue


                lines = str(
                    value
                ).count("\n") + 1


                max_lines = max(
                    max_lines,
                    lines
                )


            ws.row_dimensions[
                row_number
            ].height = min(
                20 * max_lines,
                100
            )


        # =====================================================
        # FREEZE PANES
        # =====================================================

        ws.freeze_panes = "A2"


        # =====================================================
        # GRIDLINES AUSBLENDEN
        # =====================================================

        ws.sheet_view.showGridLines = False


        # =====================================================
        # DRUCKEINSTELLUNGEN
        # =====================================================

        ws.page_setup.orientation = "landscape"

        # Alle Exporte auf die Seitenbreite anpassen
        ws.sheet_properties.pageSetUpPr.fitToPage = True

        ws.page_setup.fitToWidth = 1

        # Höhe darf über mehrere Seiten gehen
        ws.page_setup.fitToHeight = 0

        # Keine feste Skalierung
        ws.page_setup.scale = None


        # =====================================================
        # SEITENRÄNDER
        # =====================================================

        ws.page_margins.left = 0.2
        ws.page_margins.right = 0.2
        ws.page_margins.top = 0.3
        ws.page_margins.bottom = 0.3

        ws.page_margins.header = 0.1
        ws.page_margins.footer = 0.1

        # =====================================================
        # PRINT AREA
        # =====================================================

        # Letzte tatsächlich verwendete Spalte ermitteln
        last_used_column = 1

        for row in ws.iter_rows():

            for cell in row:

                if cell.value is not None:

                    if cell.column > last_used_column:
                        last_used_column = cell.column


        # Letzte verwendete Zeile
        last_used_row = ws.max_row


        # Druckbereich automatisch auf den tatsächlich
        # verwendeten Bereich begrenzen
        ws.print_area = (
            f"A1:{get_column_letter(last_used_column)}"
            f"{last_used_row}"
        )


        # =====================================================
        # DATEINAME
        # =====================================================

        prefix = {

            "geraete":
                "Geraete",

            "reparatur":
                "Gerätedetail_Reparatur",

            "filterwechsel":
                "Filterwechselhistorie",

            "wartung":
                "Wartung",

            "rechnung":
                "Rechnungshistorie",

        }.get(
            export_typ,
            "Export"
        )


        filename = (
            f"{prefix}_Export_"
            f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
            ".xlsx"
        )


        filepath = os.path.join(
            user_export_dir,
            filename
        )

        # =================================================
        # MASCHINEN – MESSWERTE IMMER ZENTRIEREN
        # =================================================

        for block in maschinen_bloecke:

            start_row = block["header"]
            end_row = block["nl_end"]

            for row in range(start_row, end_row + 1):

                # Spalte C = Messwert
                ws.cell(
                    row=row,
                    column=3
                ).alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True
                )

                # Spalte D = OK
                ws.cell(
                    row=row,
                    column=4
                ).alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True
                )

        # =================================================
        # BETTEN – ALLE MESSWERTE IN SPALTE C ZENTRIEREN
        # =================================================

        for row in range(65, 73):
            ws.cell(
                row=row,
                column=3
            ).alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True
            )
        

        print(
            "FINAL FONT 1:",
            ws.cell(row=2, column=1).font.sz,
            ws.cell(row=2, column=1).font.bold
        )

        print(
            "FINAL FONT 2:",
            ws.cell(row=39, column=1).font.sz,
            ws.cell(row=39, column=1).font.bold
        )

        wb.save(
            filepath
        )


        messages.success(
            request,
            "✅ Export erfolgreich erstellt."
        )


        return redirect("export")


    # =========================================================
    # GET = EXPORT SEITE
    # =========================================================

    exports = []


    for file in os.listdir(
        user_export_dir
    ):

        path = os.path.join(
            user_export_dir,
            file
        )


        if not os.path.isfile(path):

            continue


        if not file.lower().endswith(
            ".xlsx"
        ):

            continue


        exports.append({

            "name":
                file,

            "date":
                datetime.fromtimestamp(
                    os.path.getmtime(path)
                ),

            "size":
                round(
                    os.path.getsize(path)
                    / 1024
                    / 1024,
                    2
                ),

        })


    exports.sort(
        key=lambda x: x["date"],
        reverse=True
    )


    # =========================================================
    # GERÄTARTEN
    # =========================================================

    geraetearten = (
        Geraetart.objects
        .all()
        .order_by(
            "name"
        )
    )


    # =========================================================
    # STANDORTE
    # =========================================================

    standorte = (
        Standort.objects
        .all()
        .order_by(
            "name"
        )
    )


    # =========================================================
    # PRÜFARTEN
    # =========================================================

    pruefarten = (
        Pruefart.objects
        .filter(
            aktiv=True
        )
        .order_by(
            "order",
            "name"
        )
    )


    # =========================================================
    # RECHNUNG KATEGORIEN
    # =========================================================

    kategorien = (
        RechnungKategorie.objects
        .all()
        .order_by(
            "name"
        )
    )


    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "devices/export.html",
        {
            "exports":
                exports,

            "geraetearten":
                geraetearten,

            "standorte":
                standorte,

            "pruefarten":
                pruefarten,

            "kategorien":
                kategorien,
        }
    )

@login_required
def export_download(request, filename):

    export_dir = os.path.join(
        settings.BASE_DIR,
        "exports",
        str(request.user.id)
    )

    filepath = os.path.join(
        export_dir,
        filename
    )

    if not os.path.exists(filepath):

        messages.error(
            request,
            "Export-Datei nicht gefunden."
        )

        return redirect("export")

    return FileResponse(
        open(filepath, "rb"),
        as_attachment=True,
        filename=filename
    )

@login_required
def export_delete(request, filename):

    # =========================================================
    # EXPORT ORDNER DES AKTUELLEN BENUTZERS
    # =========================================================

    export_dir = os.path.join(
        settings.BASE_DIR,
        "exports",
        str(request.user.id)
    )

    filepath = os.path.join(
        export_dir,
        filename
    )


    # =========================================================
    # SICHERHEIT
    # =========================================================

    # Nur Dateien innerhalb des eigenen Benutzerordners
    # dürfen gelöscht werden.

    if not os.path.exists(filepath):

        messages.error(
            request,
            "Export-Datei nicht gefunden."
        )

        return redirect("export")


    # =========================================================
    # LÖSCHEN
    # =========================================================

    try:

        os.remove(filepath)

        messages.success(
            request,
            "Export erfolgreich gelöscht."
        )

    except OSError:

        messages.error(
            request,
            "Export konnte nicht gelöscht werden."
        )


    return redirect("export")

@login_required
def firmeninformationen_list(request):

    search = request.GET.get(
        "search",
        ""
    )


    companies = CompanyInformation.objects.all()


    if search:

        companies = companies.filter(
            Q(company_name__icontains=search) |
            Q(address__icontains=search)
        )


    return render(
        request,
        "devices/firmeninformationen_list.html",
        {
            "companies": companies,
            "search": search
        }
    )



@login_required
def firmeninformationen_manage(request):

    
    companies = CompanyInformation.objects.all()


    return render(
        request,
        "devices/firmeninformationen_manage.html",
        {
            "companies": companies
        }
    )

@login_required
def firmeninformationen_detail(request, id):

    company = CompanyInformation.objects.get(
        id=id
    )

    if request.method == "POST":

        company.company_name = request.POST.get(
            "company_name"
        )

        company.address = request.POST.get(
            "address"
        )

        company.phone = request.POST.get(
            "phone"
        )

        company.email = request.POST.get(
            "email"
        )

        company.customer_number = request.POST.get(
            "customer_number"
        )

        company.ansprechpartner = request.POST.get(
            "ansprechpartner"
        )

        company.save()

        messages.success(
            request,
            "Firmeninformationen erfolgreich gespeichert."
        )

        return redirect(
            "firmeninformationen",
          
        )

    return render(
        request,
        "devices/firmeninformationen_detail.html",
        {
            "company": company
        }
    )


@login_required
def firmeninformationen_create(request):

    if request.method == "POST":

        company = CompanyInformation.objects.create(

            company_name=request.POST.get(
                "company_name"
            ),

            address=request.POST.get(
                "address"
            ),

            phone=request.POST.get(
                "phone"
            ),

            email=request.POST.get(
                "email"
            ),

            customer_number=request.POST.get(
                "customer_number"
            ),

            ansprechpartner=request.POST.get(
                "ansprechpartner"
            ),

        )

        AuditLog.objects.create(

            user=request.user,

            action="CREATE",

            model_name="Firma",

            object_id=company.id,

            description=f"Firma {company.company_name} hinzugefügt."

        )
        messages.success(
            request,
            "Firma erfolgreich hinzugefügt."
        )


        return redirect(
            "firmeninformationen"
        )


    return render(
        request,
        "devices/firmeninformation_create.html"
    )



@login_required
def firmeninformationen_edit(request, id):


    company = CompanyInformation.objects.get(
        id=id
    )


    if request.method == "POST":

        company.company_name = request.POST.get(
            "company_name"
        )

        company.address = request.POST.get(
            "address"
        )

        company.phone = request.POST.get(
            "phone"
        )

        company.email = request.POST.get(
            "email"
        )

        company.customer_number = request.POST.get(
            "customer_number"
        )

        company.ansprechpartner = request.POST.get(
            "ansprechpartner"
        )

        company.save()

        AuditLog.objects.create(

            user=request.user,

            action="UPDATE",

            model_name="Firma",

            object_id=company.id,

            description=f"Firma {company.company_name} geändert."

        )
        messages.success(
            request,
            "Firma geändert."
        )


        return redirect(
            "firmeninformationen"
        )


    return render(
        request,
        "devices/firmeninformationen_edit.html",
        {
            "company": company
        }
    )

@login_required
def firmeninformationen_delete(request, id):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    company = CompanyInformation.objects.get(
        id=id
    )


    if request.method == "POST":

        AuditLog.objects.create(

            user=request.user,

            action="DELETE",

            model_name="Firma",

            object_id=company.id,

            description=f"Firma {company.company_name} gelöscht."

        )
        company.delete()


        messages.success(
            request,
            "Firma erfolgreich gelöscht."
        )


    return redirect(
        "firmeninformationen"
    )

@login_required
def audit_log(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    logs = AuditLog.objects.all()


    search = request.GET.get(
        "search",
        ""
    )


    if search:

        logs = logs.filter(
            Q(user__username__icontains=search) |
            Q(model_name__icontains=search) |
            Q(description__icontains=search)
        )


    return render(
        request,
        "devices/audit_log.html",
        {
            "logs": logs,
            "search": search
        }
    )

@login_required
def audit_log_delete(request, id):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    log = get_object_or_404(
        AuditLog,
        id=id
    )


    if request.method == "POST":

        log.delete()


        messages.success(
            request,
            "Audit Log Eintrag gelöscht."
        )


    return redirect(
        "audit_log"
    )

@login_required
def audit_log_delete_selected(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    if request.method == "POST":

        ids = request.POST.getlist("logs")


        if ids:

            AuditLog.objects.filter(
                id__in=ids
            ).delete()


            messages.success(
                request,
                "Ausgewählte Audit Logs wurden gelöscht."
            )


    return redirect(
        "audit_log"
    )

@login_required
def kontakt_informationen(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")


    kontakt, created = ContactInformation.objects.get_or_create(
        id=1
    )


    if request.method == "POST":

        kontakt.technician_name = request.POST.get(
            "technician_name"
        )

        kontakt.email = request.POST.get(
            "email"
        )

        kontakt.phone = request.POST.get(
            "phone"
        )

        kontakt.address = request.POST.get(
            "address"
        )


        if request.FILES.get("image"):

            kontakt.image = request.FILES.get(
                "image"
            )


        kontakt.save()


        messages.success(
            request,
            "Kontaktdaten gespeichert."
        )


        return redirect(
            "kontakt"
        )


    return render(
        request,
        "devices/kontakt_informationen.html",
        {
            "kontakt": kontakt
        }
    )

@login_required
def kontakt_edit(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    kontakt, created = ContactInformation.objects.get_or_create(id=1)

    if request.method == "POST":

        kontakt.technician_name = request.POST.get("technician_name")
        kontakt.email = request.POST.get("email")
        kontakt.phone = request.POST.get("phone")
        kontakt.address = request.POST.get("address")

        kontakt.save()

        # حذف الصور المحددة
        if "delete_selected" in request.POST:

            delete_ids = request.POST.getlist("delete_images")

            ContactImage.objects.filter(
                id__in=delete_ids,
                contact=kontakt
            ).delete()

        # إضافة الصور الجديدة
        images = request.FILES.getlist("images")

        for image in images:

            ContactImage.objects.create(
                contact=kontakt,
                image=image
            )

        messages.success(
            request,
            "Kontaktdaten gespeichert."
        )

        return redirect("kontakt_edit")

    return render(
        request,
        "devices/kontakt_informationen.html",
        {
            "kontakt": kontakt
        }
    )

@login_required
def dashboard_widgets(request):

    # =========================================================
    # DASHBOARD WIDGETS DES AKTUELLEN BENUTZERS
    # =========================================================

    widgets = (
        DashboardWidget.objects
        .filter(
            user=request.user
        )
        .order_by(
            "order"
        )
    )

    return render(
        request,
        "devices/dashboard_widgets.html",
        {
            "widgets": widgets,
        },
    )

@login_required
def dashboard_widget_create(request):

    if request.method == "POST":

        widget = DashboardWidget()

        # =====================================================
        # BENUTZER
        # =====================================================

        widget.user = request.user

        # =====================================================
        # WIDGET-TYP
        # =====================================================

        widget.widget_type = request.POST.get(
            "widget_type"
        )

        # =====================================================
        # TITEL
        # =====================================================

        widget.title = request.POST.get(
            "title"
        )

        # =====================================================
        # STANDORT
        # Nur für Geräte
        # =====================================================

        standort_id = request.POST.get(
            "standort"
        )

        if (
            widget.widget_type == "devices"
            and standort_id
        ):

            widget.standort = get_object_or_404(
                Standort,
                id=standort_id
            )

        else:

            widget.standort = None

        # =====================================================
        # GERÄTART
        # Nur für Geräte
        # =====================================================

        geraetart_id = request.POST.get(
            "geraetart"
        )

        if (
            widget.widget_type == "devices"
            and geraetart_id
        ):

            widget.geraetart = get_object_or_404(
                Geraetart,
                id=geraetart_id
            )

        else:

            widget.geraetart = None

        # =====================================================
        # REPARATUR STATUS
        # =====================================================

        if widget.widget_type == "repairs":

            widget.reparatur_status = (
                request.POST.get(
                    "reparatur_status"
                )
                or None
            )

        else:

            widget.reparatur_status = None

        # =====================================================
        # PRÜFUNGSART
        # =====================================================

        pruefart_id = request.POST.get(
            "pruefart"
        )

        if (
            widget.widget_type == "pruefart"
            and pruefart_id
        ):

            widget.pruefart = get_object_or_404(
                Pruefart,
                id=pruefart_id
            )

        else:

            widget.pruefart = None

        # =====================================================
        # PRÜFUNGS STATUS
        # =====================================================

        if widget.widget_type == "pruefart":

            widget.pruef_status = (
                request.POST.get(
                    "pruef_status"
                )
                or None
            )

        else:

            widget.pruef_status = None

        # =====================================================
        # RECHNUNG STATUS
        # =====================================================

        if widget.widget_type == "rechnung":

            widget.rechnung_status = (
                request.POST.get(
                    "rechnung_status"
                )
                or None
            )

        else:

            widget.rechnung_status = None

        # =====================================================
        # SICHTBAR
        # =====================================================

        widget.visible = (
            request.POST.get("visible") == "on"
        )

        # =====================================================
        # REIHENFOLGE
        # =====================================================

        widget.order = (
            request.POST.get("order")
            or 0
        )

        # =====================================================
        # FARBE
        # =====================================================

        widget.color = (
            request.POST.get("color")
            or "primary"
        )

        # =====================================================
        # ICON
        # =====================================================

        widget.icon = (
            request.POST.get("icon")
            or "bi-grid"
        )

        # =====================================================
        # SPEICHERN
        # =====================================================

        widget.save()

        messages.success(
            request,
            "Dashboard Widget erstellt."
        )

        return redirect(
            "dashboard_widgets"
        )

    return render(
        request,
        "devices/dashboard_widget_form.html",
        {
            "standorte": Standort.objects.filter(
                active=True
            ),

            "geraetarten": Geraetart.objects.filter(
                aktiv=True
            ),

            "pruefarten": Pruefart.objects.all().order_by(
                "name"
            ),

            "types": DashboardWidget.WIDGET_TYPES,

            "pruef_status_choices":
                DashboardWidget.PRUEF_STATUS_CHOICES,

            "rechnung_status_choices":
                DashboardWidget.RECHNUNG_STATUS_CHOICES,

            "reparatur_status_choices":
                DashboardWidget.REPARATUR_STATUS_CHOICES,
        }
    )


@login_required
def dashboard_widget_edit(request, id):

    # =========================================================
    # NUR EIGENES WIDGET
    # =========================================================

    widget = get_object_or_404(
        DashboardWidget,
        id=id,
        user=request.user
    )

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        # =====================================================
        # WIDGET-TYP
        # =====================================================

        widget.widget_type = request.POST.get(
            "widget_type"
        )

        # =====================================================
        # TITEL
        # =====================================================

        widget.title = request.POST.get(
            "title"
        )

        # =====================================================
        # STANDORT
        # =====================================================

        standort_id = request.POST.get(
            "standort"
        )

        if (
            widget.widget_type == "devices"
            and standort_id
        ):

            widget.standort = get_object_or_404(
                Standort,
                id=standort_id
            )

        else:

            widget.standort = None

        # =====================================================
        # GERÄTART
        # =====================================================

        geraetart_id = request.POST.get(
            "geraetart"
        )

        if (
            widget.widget_type == "devices"
            and geraetart_id
        ):

            widget.geraetart = get_object_or_404(
                Geraetart,
                id=geraetart_id
            )

        else:

            widget.geraetart = None

        # =====================================================
        # REPARATUR STATUS
        # =====================================================

        if widget.widget_type == "repairs":

            widget.reparatur_status = (
                request.POST.get(
                    "reparatur_status"
                )
                or None
            )

        else:

            widget.reparatur_status = None

        # =====================================================
        # PRÜFUNGSART
        # =====================================================

        pruefart_id = request.POST.get(
            "pruefart"
        )

        if (
            widget.widget_type == "pruefart"
            and pruefart_id
        ):

            widget.pruefart = get_object_or_404(
                Pruefart,
                id=pruefart_id
            )

        else:

            widget.pruefart = None

        # =====================================================
        # PRÜFUNGS STATUS
        # =====================================================

        if widget.widget_type == "pruefart":

            widget.pruef_status = (
                request.POST.get(
                    "pruef_status"
                )
                or None
            )

        else:

            widget.pruef_status = None

        # =====================================================
        # RECHNUNG STATUS
        # =====================================================

        if widget.widget_type == "rechnung":

            widget.rechnung_status = (
                request.POST.get(
                    "rechnung_status"
                )
                or None
            )

        else:

            widget.rechnung_status = None

        # =====================================================
        # FARBE
        # =====================================================

        widget.color = (
            request.POST.get(
                "color"
            )
            or "primary"
        )

        # =====================================================
        # ICON
        # =====================================================

        widget.icon = (
            request.POST.get(
                "icon"
            )
            or "bi-grid"
        )

        # =====================================================
        # REIHENFOLGE
        # =====================================================

        widget.order = (
            request.POST.get(
                "order"
            )
            or 0
        )

        # =====================================================
        # SICHTBAR
        # =====================================================

        widget.visible = (
            request.POST.get(
                "visible"
            ) == "on"
        )

        # =====================================================
        # SPEICHERN
        # =====================================================

        widget.save()

        messages.success(
            request,
            "Dashboard Widget geändert."
        )

        return redirect(
            "dashboard_widgets"
        )

    # =========================================================
    # GET
    # =========================================================

    return render(
        request,
        "devices/dashboard_widget_form.html",
        {
            "widget": widget,

            "standorte": Standort.objects.filter(
                active=True
            ),

            "geraetarten": Geraetart.objects.filter(
                aktiv=True
            ),

            "pruefarten": Pruefart.objects.all().order_by(
                "name"
            ),

            "types": DashboardWidget.WIDGET_TYPES,

            "pruef_status_choices":
                DashboardWidget.PRUEF_STATUS_CHOICES,

            "rechnung_status_choices":
                DashboardWidget.RECHNUNG_STATUS_CHOICES,

            "reparatur_status_choices":
                DashboardWidget.REPARATUR_STATUS_CHOICES,
        }
    )


@login_required
def dashboard_widget_delete(request, id):

    # =========================================================
    # NUR EIGENES WIDGET LÖSCHEN
    # =========================================================

    widget = get_object_or_404(
        DashboardWidget,
        id=id,
        user=request.user
    )

    # =========================================================
    # LÖSCHEN
    # =========================================================

    widget.delete()

    messages.success(
        request,
        "Dashboard Widget gelöscht."
    )

    return redirect(
        "dashboard_widgets"
    )


@login_required
def system_update(request):

    import json

    update_file = (
        Path(settings.BASE_DIR)
        / "update"
        / "version.json"
    )

    latest_version = None
    latest_description = None

    update_available = request.session.get(
        "update_available",
        False
    )

    if update_file.exists():

        with open(
            update_file,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            latest_version = data.get("version")
            latest_description = data.get("description")

    history_file = (
        Path(settings.BASE_DIR)
        / "update"
        / "logs"
        / "update_history.json"
    )

    update_history = []

    if history_file.exists():

        with open(
            history_file,
            "r",
            encoding="utf-8-sig"
        ) as f:

            update_history = json.load(f)

    log_file = (
        Path(settings.BASE_DIR)
        / "update"
        / "logs"
        / "update.log"
    )

    update_log = ""

    if log_file.exists():

        with open(
            log_file,
            "r",
            encoding="utf-8"
        ) as f:

            update_log = f.read()

    local_commit = request.session.get(
        "local_commit",
        "-"
    )

    remote_commit = request.session.get(
        "remote_commit",
        "-"
    )

    branch = request.session.get(
        "branch",
        "-"
    )

    last_commit = request.session.get(
        "last_commit",
        "-"
    )

    return render(
        request,
        "devices/system_update.html",
        {
            "current_version": settings.APP_VERSION,
            "latest_version": latest_version,
            "latest_description": latest_description,
            "update_available": update_available,
            "update_history": update_history,
            "update_log": update_log,
            "local_commit": local_commit,
            "remote_commit": remote_commit,
            "branch": branch,
            "last_commit": last_commit,
        }
    )

@login_required
def check_update(request):

    from devices.services.git_service import GitService

    try:

        git = GitService.get_status()

        request.session["update_available"] = git["update_available"]
        request.session["local_commit"] = git["local_commit"]
        request.session["remote_commit"] = git["remote_commit"]
        request.session["branch"] = git["branch"]
        request.session["last_commit"] = git["last_commit"]

        if git["update_available"]:

            messages.success(
                request,
                "New update is available."
            )

        else:

            messages.info(
                request,
                "Your system is already up to date."
            )

    except Exception as e:

        messages.error(
            request,
            str(e)
        )

    return redirect("system_update")


@login_required
def run_update(request):

    if not request.user.is_superuser:
        return redirect("permission_denied")

    if request.method != "POST":
        return redirect("system_update")

    try:
        UpdateService.run(request.user)

        messages.success(
            request,
            "Update process started successfully."
        )

    except Exception as e:

        messages.error(
            request,
            str(e)
        )

    return redirect("system_update")


@login_required
def geraetedetails_settings(request):

    geraetarten = Geraetart.objects.all().order_by("name")

    selected_geraetart_id = request.GET.get("geraetart")

    selected_geraetart = None
    selected_fields = set()

    # =========================================================
    # GERÄTART AUSWÄHLEN
    # =========================================================

    if selected_geraetart_id:

        selected_geraetart = get_object_or_404(
            Geraetart,
            id=selected_geraetart_id
        )

        selected_fields = set(
            DeviceDetailFieldConfig.objects.filter(
                geraetart=selected_geraetart,
                is_visible=True
            ).values_list(
                "field_name",
                flat=True
            )
        )

    # =========================================================
    # SPEICHERN
    # =========================================================

    if request.method == "POST":

        geraetart_id = request.POST.get("geraetart")

        if not geraetart_id:
            return redirect(
                "geraetedetails_settings"
            )

        selected_geraetart = get_object_or_404(
            Geraetart,
            id=geraetart_id
        )

        selected_fields = set(
            request.POST.getlist("fields")
        )

        # Alte Konfiguration dieser Gerätart löschen
        DeviceDetailFieldConfig.objects.filter(
            geraetart=selected_geraetart
        ).delete()

        # Neue Konfiguration speichern
        field_choices = DeviceDetailFieldConfig.FIELD_CHOICES

        for position, (field_name, field_label) in enumerate(
            field_choices
        ):

            DeviceDetailFieldConfig.objects.create(
                geraetart=selected_geraetart,
                field_name=field_name,
                is_visible=(
                    field_name in selected_fields
                ),
                position=position
            )

        return redirect(
            "geraetedetails_settings"
        )

    # =========================================================
    # GESPEICHERTE EINSTELLUNGEN
    # =========================================================

    saved_configs = []

    for geraetart in geraetarten:

        fields = (
            DeviceDetailFieldConfig.objects
            .filter(
                geraetart=geraetart,
                is_visible=True
            )
            .order_by("position")
        )

        if fields.exists():

            saved_configs.append({
                "geraetart": geraetart,
                "fields": fields,
            })

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "devices/geraetedetails.html",
        {
            "geraetarten": geraetarten,
            "selected_geraetart": selected_geraetart,
            "selected_fields": selected_fields,
            "field_choices": DeviceDetailFieldConfig.FIELD_CHOICES,
            "saved_configs": saved_configs,
        }
    )