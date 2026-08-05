from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta

class Geraetart(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
    )


    aktiv = models.BooleanField(
        default=True
    )
    def __str__(self):
        return self.name

class Device(models.Model):
    

    STATUS_CHOICES = [
        ("Aktiv", "Aktiv"),
        ("Nicht aktiv", "Nicht aktiv"),
    ]


    AREA_CHOICES = [
        ("Dialyse", "Dialyse"),
        ("Praxis", "Praxis"),
        ("Labor", "Labor"),
        
    ]


    geraetart = models.ForeignKey(
        Geraetart,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="geraete"
    )
   




    name = models.CharField(
        "Gerätbezeichnung",
        max_length=200
      
    )


    inventory_number = models.CharField(
        "Inventarnummer",
        max_length=100,
        unique=True
    )


    serial_number = models.CharField(
        "Seriennummer",
        max_length=100,
        unique=True
    )


    ec_number = models.CharField(
        "EC-Nummer",
        max_length=100,
        blank=True
    )


    software_version = models.CharField(
        "Software Version",
        max_length=100,
        blank=True
    )

    operating_hours = models.IntegerField(
        "Betriebsstunden",
        blank=True,
        null=True
    )
    manufacturer = models.CharField(
        "Hersteller",
        max_length=200,
        blank=True
    )


    year_built = models.IntegerField(
        "Baujahr",
        blank=True,
        null=True
    )


    practice = models.ForeignKey(
    "Standort",
    on_delete=models.PROTECT,
    related_name="devices",
    verbose_name="Standort"
)  


    area = models.CharField(
        "Bereich",
        max_length=30,
        choices=AREA_CHOICES
    )




    room = models.CharField(
        "Raum",
        max_length=100,
        blank=True
    )


    # MTK
    last_stk = models.DateField(
        "Letzte STK",
        blank=True,
        null=True
    )

    next_stk = models.DateField(
        "Nächste STK",
        blank=True,
        null=True
    )

    # STK
    last_mtk = models.DateField(
        "Letzte MTK",
        blank=True,
        null=True
    )

    next_mtk = models.DateField(
        "Nächste MTK",
        blank=True,
        null=True
    )

    # DGUV V3
    last_dguv = models.DateField(
        "Letzte DGUV V3",
        blank=True,
        null=True
    )

    next_dguv = models.DateField(
        "Nächste DGUV V3",
        blank=True,
        null=True
    )


    status = models.CharField(
        "Status",
        max_length=20,
        choices=STATUS_CHOICES,
        default="Aktiv"
    )


    notes = models.TextField(
        "Bemerkungen",
        blank=True
    )


    image = models.ImageField(
        upload_to="devices/",
        blank=True,
        null=True
    )


    def __str__(self):
        return f"{self.inventory_number} - {self.name}"

    def save(self, *args, **kwargs):

    
        if self.last_stk:
           self.next_stk = self.last_stk + timedelta(days=730)

        if self.last_mtk:
           self.next_mtk = self.last_mtk + timedelta(days=730)

        if self.last_dguv:
           self.next_dguv = self.last_dguv + timedelta(days=365)

        super().save(*args, **kwargs)

class PracticeSettings(models.Model):

    practice_name = models.CharField(
        "Standort",
        max_length=200,
        blank=True
    )

    contact_person = models.CharField(
        "Name",
        max_length=200,
        blank=True
    )

    email = models.EmailField(
        "E-Mail-Adresse",
        blank=True
    )

    phone = models.CharField(
        "Telefonnummer",
        max_length=50,
        blank=True
    )

    address = models.CharField(
        "Adresse",
        max_length=300,
        blank=True
    )

    contact_image = models.ImageField(
        "Kontaktbild",
        upload_to="practice_contact/",
        blank=True,
        null=True
    )


    def __str__(self):
        return self.practice_name

class DocumentType(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Dokumenttyp"
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Reihenfolge"
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

class DeviceDocument(models.Model):


    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="documents"
    )


    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        verbose_name="Dokumenttyp"
    )
    
    display_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    file = models.FileField(
        upload_to="device_documents/"
    )


    upload_date = models.DateTimeField(
        auto_now_add=True
    )


    notes = models.TextField(
        "Bemerkungen",
        blank=True
    )

    def __str__(self):
        return f"{self.device.name} - {self.document_type}"


class TechnicianDocument(models.Model):

    CATEGORY_CHOICES = [
        ("Zertifikat", "📜 Zertifikat"),
        ("Servicehandbuch", "📘 Servicehandbuch"),
        ("Bedienungsanleitung", "📖 Bedienungsanleitung"),
        ("Software", "💻 Software"),
        ("Schulung", "🎓 Schulung"),
        ("Sonstiges", "📄 Sonstiges"),
    ]

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    title = models.CharField(
        "Dokumentname",
        max_length=255
    )

    file = models.FileField(
        upload_to="technician_documents/"
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    upload_date = models.DateTimeField(
        auto_now_add=True
    )

    notes = models.TextField(
        blank=True
    )

    def __str__(self):
        return self.title
class GeneralDocument(models.Model):

    DOCUMENT_CATEGORY = [
        ("Zertifikat", "📜 Techniker Zertifikate"),
        ("Sonstiges", "📄 Sonstige Dokumente"),
    ]


    file = models.FileField(
        upload_to="general_documents/"
    )


    category = models.CharField(
        max_length=50,
        choices=DOCUMENT_CATEGORY
    )


    display_name = models.CharField(
        max_length=200,
        blank=True
    )


    upload_date = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.display_name or self.file.name
    

class UserProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )


    phone = models.CharField(
        max_length=50,
        blank=True
    )


    address = models.CharField(
        max_length=300,
        blank=True
    )


    contact_image = models.ImageField(
        upload_to="contact_images/",
        blank=True,
        null=True
    )


    def __str__(self):
        return self.user.username
    
   

class HomeSlider(models.Model):
    image1 = models.ImageField(upload_to="home_slider/", blank=True, null=True)
    image2 = models.ImageField(upload_to="home_slider/", blank=True, null=True)
    image3 = models.ImageField(upload_to="home_slider/", blank=True, null=True)
    image4 = models.ImageField(upload_to="home_slider/", blank=True, null=True)
    image5 = models.ImageField(upload_to="home_slider/", blank=True, null=True)

    def __str__(self):
        return "Home Slider"

class Reparatur(models.Model):

    STATUS_CHOICES = [
        ("Offen", "Offen"),
        ("In Bearbeitung", "In Bearbeitung"),
        ("Erledigt", "Erledigt"),
    ]


    geraet = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="reparaturen"
    )


    datum = models.DateField(
        auto_now_add=True
    )


    beschreibung = models.TextField(
        "Problem Beschreibung"
    )


    melder = models.CharField(
        "Melder",
        max_length=100,
        blank=True
    )


    techniker = models.CharField(
        "Techniker",
        max_length=100,
        blank=True
    )


    status = models.CharField(
        "Status",
        max_length=50,
        choices=STATUS_CHOICES,
        default="Offen"
    )


    ausfuehrung = models.TextField(
        "Ausführung",
        blank=True
    )


    reparatur_datum = models.DateField(
        "Reparaturdatum",
        null=True,
        blank=True
    )


    def __str__(self):
        return f"{self.geraet} - {self.status}"

    reparaturbericht = models.FileField(
    upload_to="reparaturberichte/",
    blank=True,
    null=True
    )

    reparaturbild = models.ImageField(
    upload_to="reparaturbild/",
    blank=True,
    null=True
    )

class Standort(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    address = models.CharField(
        max_length=255,
        blank=True
    )

    phone = models.CharField(
        max_length=50,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.name


class Filterwechsel(models.Model):

    geraet = models.ForeignKey(
    Device,
    on_delete=models.CASCADE,
    related_name="filterwechsel",
    null=True,
    blank=True
    )

    inventarnummer = models.CharField(max_length=100)

    anzahl_filter = models.IntegerField()

    filtercode = models.CharField(max_length=100)

    datum = models.DateField()

    durchgeführt_von = models.CharField(max_length=100)

    bemerkung = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.inventarnummer} - {self.filtercode}"



    
class DashboardSettings(models.Model):

    show_luebeck = models.BooleanField(
        default=True,
        verbose_name="Gesamtgeräte Lübeck anzeigen"
    )

    show_ratzeburg = models.BooleanField(
        default=True,
        verbose_name="Gesamtgeräte Ratzeburg anzeigen"
    )

    show_reparaturen = models.BooleanField(
        default=True,
        verbose_name="Reparaturen anzeigen"
    )

    show_stk = models.BooleanField(
        default=True,
        verbose_name="STK anzeigen"
    )

    show_mtk = models.BooleanField(
        default=True,
        verbose_name="MTK anzeigen"
    )

    show_dguv = models.BooleanField(
        default=True,
        verbose_name="DGUV anzeigen"
    )

    show_geraete_uebersicht = models.BooleanField(
        default=True,
        verbose_name="Geräteübersicht anzeigen"
    )


    def __str__(self):
        return "Dashboard Einstellungen"


class CompanyInformation(models.Model):

    company_name = models.CharField(
        max_length=200,
        verbose_name="Firmenname"
    )

    address = models.TextField(
        blank=True,
        verbose_name="Adresse"
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Telefon"
    )

    email = models.EmailField(
        blank=True,
        verbose_name="E-Mail"
    )

    ansprechpartner = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    customer_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Kundennummer"
    )


    def __str__(self):
        return self.company_name

class AuditLog(models.Model):

    ACTION_CHOICES = [

        ("CREATE", "Erstellt"),
        ("UPDATE", "Geändert"),
        ("DELETE", "Gelöscht"),
        ("EXPORT", "Export"),
        ("BACKUP", "Backup"),

    ]


    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )


    model_name = models.CharField(
        max_length=100
    )


    object_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )


    description = models.TextField(
        blank=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        ordering = [
            "-created_at"
        ]


    def __str__(self):
        return f"{self.action} - {self.model_name}"


class ContactInformation(models.Model):

    technician_name = models.CharField(
        max_length=200,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    phone = models.CharField(
        max_length=100,
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    image = models.ImageField(
        upload_to="contact/",
        blank=True,
        null=True
    )


    def __str__(self):
        return self.technician_name


class ContactImage(models.Model):

    contact = models.ForeignKey(
        ContactInformation,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="contact/gallery/"
    )

    title = models.CharField(
        max_length=200,
        blank=True
    )


    def __str__(self):
        return self.title or "Kontakt Bild"


class HomeInformation(models.Model):

    title = models.CharField(
        max_length=200,
        blank=True,
        default=""
    )

    def __str__(self):
        return self.title or "Home"


class HomeImage(models.Model):

    home = models.ForeignKey(
        HomeInformation,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="home/gallery/"
    )

    title = models.CharField(
        max_length=200,
        blank=True
    )

    def __str__(self):
        return self.title or "Home Bild"



class DashboardWidget(models.Model):

    WIDGET_TYPES = [

        ("devices_overview", "Geräteübersicht"),

        ("devices", "Geräte"),

        ("repairs_open", "Offene Reparaturen"),

        ("repairs_progress", "Reparaturen in Bearbeitung"),

        ("repairs_done", "Reparaturen erledigt"),

        ("repair_history", "Reparaturhistorie"),

        ("filter_history", "Filterwechselhistorie"),

        ("stk", "STK fällig"),

        ("mtk", "MTK fällig"),

        ("dguv", "DGUV fällig"),

        ("device_documents", "Medizingeräte Dokumente"),

        ("technician_documents", "Technikerdokumente"),

    ]


    widget_type = models.CharField(
        max_length=50,
        choices=WIDGET_TYPES
    )


    title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Eigener Titel"
    )


    standort = models.ForeignKey(
        Standort,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )


    geraetart = models.ForeignKey(
        Geraetart,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )


    visible = models.BooleanField(
        default=True,
        verbose_name="Im Dashboard anzeigen"
    )


    order = models.PositiveIntegerField(
        default=0
    )


    COLOR_CHOICES = [

        ("primary", "🔵 Blau"),

        ("success", "🟢 Grün"),

        ("danger", "🔴 Rot"),

        ("warning", "🟡 Gelb"),

        ("info", "🔷 Türkis"),

        ("purple", "🟣 Lila"),

        ("dark", "⚫ Schwarz"),

        ("orange", "🟠 Orange"),

        ("teal", "🟦 Petrol"),

        ("pink", "🩷 Pink"),

        ("brown", "🟤 Braun"),

        ("gray", "⚪ Grau"),

    ]


    color = models.CharField(
        max_length=20,
        choices=COLOR_CHOICES,
        default="primary"
    )


    ICON_CHOICES = [

        ("bi-grid", "📊 Übersicht"),

        ("bi-hospital", "🏥 Krankenhaus"),

        ("bi-heart-pulse", "❤️ Medizin"),

        ("bi-tools", "🛠 Reparaturen"),

        ("bi-wrench", "🔧 Wartung"),

        ("bi-filter", "🧪 Filterwechsel"),

        ("bi-file-earmark-text", "📄 Dokumente"),

        ("bi-building", "🏢 Firma"),

        ("bi-folder", "📁 Ordner"),

        ("bi-gear", "⚙ Einstellungen"),

    ]


    icon = models.CharField(
        max_length=50,
        choices=ICON_CHOICES,
        default="bi-grid"
    )


    class Meta:

        ordering = [
            "order"
        ]


    @property
    def display_title(self):

        if self.title:

            return self.title


        if (
            self.widget_type == "devices"
            and self.standort
            and self.geraetart
        ):

            return f"{self.geraetart.name} - {self.standort.name}"


        return self.get_widget_type_display()
    def save(self, *args, **kwargs):

        if self.widget_type == "devices_overview":
            self.icon = "bi-grid"

        elif self.widget_type == "devices":
            self.icon = "bi-hospital"

        elif self.widget_type in [
            "repairs_open",
            "repairs_progress",
            "repairs_done",
            "repair_history"
        ]:
            self.icon = "bi-tools"

        elif self.widget_type == "filter_history":
            self.icon = "bi-filter"

        elif self.widget_type in [
            "stk",
            "mtk",
            "dguv"
        ]:
            self.icon = "bi-calendar-check"

        elif self.widget_type in [
            "device_documents",
            "technician_documents"
        ]:
            self.icon = "bi-file-earmark-text"


        super().save(*args, **kwargs)

    def __str__(self):

        return self.display_title


class SystemUpdate(models.Model):

    STATUS_CHOICES = [
        ("IDLE", "Idle"),
        ("RUNNING", "Running"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    version = models.CharField(
        max_length=50,
        blank=True
    )

    local_commit = models.CharField(
        max_length=40,
        blank=True
    )

    remote_commit = models.CharField(
        max_length=40,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="IDLE"
    )

    description = models.TextField(
        blank=True
    )

    started_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True
    )

    error = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.version} - {self.status}"