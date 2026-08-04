from django.urls import path
from . import views
from django.db.models import Q
from django.contrib.auth import views as auth_views
from devices.views import login_view

urlpatterns = [

    path(
            "accounts/login/",
            login_view,
            name="login"
        ),

    path("", views.login_view, name="login"),

    

    path(
        "home/",
        views.home,
        name="home"
    ),

    path(
    "password-reset/",
    auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html"
    ),
    name="password_reset",
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path(
    "user/<int:user_id>/password/",
    views.user_password_reset,
    name="user_password_reset"
    ),
   

    # إضافة جهاز يجب أن تكون قبل category
    path(
        "devices/new/",
        views.device_create,
        name="device_create"
    ),

    path(
    "devices/<int:device_id>/delete/",
    views.device_delete,
    name="device_delete"
    ),

    path(
        "devices/<int:device_id>/",
        views.device_detail,
        name="device_detail"
    ),
    path(
    "devices/<int:device_id>/edit/",
    views.device_edit,
    name="device_edit"
    ),
    

    path(
    "filterwechsel/create/",
    views.filterwechsel_create,
    name="filterwechsel_create"
    ),  
    path(
    "filterwechsel/<int:id>/edit/",
    views.filterwechsel_update,
    name="filterwechsel_update"
    ),

    path(
    "filterwechsel/<int:id>/delete/",
    views.filterwechsel_delete,
    name="filterwechsel_delete"
    ),

    path(
    "filterwechsel/history/",
    views.filterwechsel_history,
    name="filterwechsel_history"
    ),
    path(
    "devices/<int:device_id>/upload-document/",
    views.upload_document,
    name="upload_document"
    ),

    path(
    "devices/search/",
    views.device_search,
    name="device_search"
    ), 

    path(
    "devices/geraetart/<int:geraetart_id>/new/",
    views.device_create_geraetart,
    name="device_create_geraetart"
    ),
    path(
        "devices/geraetart/<int:geraetart_id>/",
        views.device_geraetart,
        name="device_geraetart"
    ),
  

    path(
        "devices/",
        views.device_list,
        name="device_list"
    ),

    path(
    "contact/",
    views.contact,
    name="contact"
    ),

    path(
    "faellige-stk",
    views.faellige_stk,
    name="faellige_stk"
    ),

    path(
    "wartung/mtk/",
    views.faellige_mtk,
    name="faellige_mtk"
    ),

    path(
    "wartung/dguv/",
    views.faellige_dguv,
    name="faellige_dguv"
    ),
   path(
    "settings/",
    views.settings_view,
    name="settings"
     ),


    path(
    "system/settings/",
    views.system_settings,
    name="system_settings"
    ),
    path(
    "system/management/",
    views.system_management,
    name="system_management"
     ),
    path(
    "practice-settings/edit/",
    views.practice_settings_edit,
    name="practice_settings_edit"
    ),

    path(
    "dashboard/",
    views.dashboard,
    name="dashboard"
    ),
    path(
    "document/<int:document_id>/delete/",
    views.document_delete,
    name="document_delete"
    ),
   path(
    "document/<int:document_id>/rename/",
    views.document_rename,
    name="document_rename"
    ),
    path(
    "documents/",
    views.documents_home,
    name="documents_home"
    ),
    path(
    "documents/",
    views.documents,
    name="documents"
    ),
    path(
    "documents/type/<int:document_type_id>/",
    views.documents_by_type,
    name="documents_by_type"
    ),
    path(
    "documents/technician/",
    views.technician_documents,
    name="technician_documents"
    ),

    path(
    "documents/technician/upload/",
    views.technician_document_upload,
    name="technician_document_upload"
    ),

    path(
    "documents/technician/<int:doc_id>/rename/",
    views.technician_document_rename,
    name="technician_document_rename"
    ),

    path(
    "documents/technician/<int:doc_id>/delete/",
    views.technician_document_delete,
    name="technician_document_delete"
    ),
    path(
    "reparatur/",
    views.reparatur,
    name="reparatur"
     ),

    path(
    "reparatur/neu/",
    views.reparatur_create,
    name="reparatur_create"
    ),

    path(
    "reparatur/<int:pk>/",
    views.reparatur_detail,
    name="reparatur_detail"
    ),

    path(
    "reparatur/<int:repair_id>/delete/",
    views.repair_delete,
    name="repair_delete",
    ),
    path(
    "reparatur/uebersicht/",
    views.reparatur_uebersicht,
    name="reparatur_uebersicht",
    ),

    path(
    "reparatur/historie/",
    views.reparatur_historie,
    name="reparatur_historie",
    ),

    path(
    "reparatur/historie/<int:pk>/",
    views.reparatur_historie_detail,
    name="reparatur_historie_detail",
    ),
    path(
    "device-documents/<str:document_type>/",
    views.device_documents_list,
    name="device_documents_list"
    ),
   
   
     path(
    "profile/contact/",
    views.contact_edit,
    name="contact_edit"
     ),
    
    path(
    "reparatur/device-search/",
    views.search_reparatur_device,
    name="search_reparatur_device"
    ),

    path(
    "geraetarten/",
    views.geraetarten,
    name="geraetarten",
    ),

    path(
    "settings/geraetarten/create/",
    views.geraetart_create,
    name="geraetart_create",
    ),

    path(
    "settings/geraetarten/<int:id>/edit/",
    views.geraetart_update,
    name="geraetart_update",
    ),

    path(
    "settings/geraetarten/<int:id>/delete/",
    views.geraetart_delete,
    name="geraetart_delete",
    ),
     path(
    "contact-image/",
    views.contact_image_change,
    name="contact_image_change"
     ),
    path(
    "home/edit/",
    views.home_edit,
    name="home_edit"
    ),
   

    path(
    "users/",
    views.user_list,
    name="user_list"
     ),

    path(
    "users/edit/<int:user_id>/",
    views.user_edit,
    name="user_edit"
     ),

     path(
    "users/new/",
    views.user_create,
    name="user_create",
    ),

    path(
    "users/delete/<int:user_id>/",
    views.user_delete,
    name="user_delete"
    ),
    path(
    "permission-denied/",
    views.permission_denied,
    name="permission_denied"
    ),

    path(
    "standorte/",
    views.standort_list,
    name="standort_list",
    ),

    path(
    "standorte/neu/",
    views.standort_create,
    name="standort_create",
    ),
    path(
    "standorte/<int:standort_id>/edit/",
    views.standort_edit,
    name="standort_edit",
    ),

    path(
    "standorte/<int:standort_id>/delete/",
    views.standort_delete,
    name="standort_delete",
    ),

    path(
    "einstellungen/dokumenttypen/",
    views.document_types,
    name="document_types"
    ),
    path(
    "einstellungen/dokumenttypen/neu/",
    views.add_document_type,
    name="add_document_type"
    ),

    path(
    "einstellungen/dokumenttypen/bearbeiten/<int:id>/",
    views.edit_document_type,
    name="edit_document_type"
    ),

    path(
    "einstellungen/dokumenttypen/loeschen/<int:id>/",
    views.delete_document_type,
    name="delete_document_type"
    ),

    path(
    "dashboard/widgets/",
    views.dashboard_widgets,
    name="dashboard_widgets"
    ),

    path(
    "dashboard/widgets/new/",
    views.dashboard_widget_create,
    name="dashboard_widget_create"
    ),

    path(
    "dashboard/widgets/<int:id>/edit/",
    views.dashboard_widget_edit,
    name="dashboard_widget_edit"
    ),

    path(
        "dashboard/widgets/<int:id>/delete/",
        views.dashboard_widget_delete,
        name="dashboard_widget_delete"
    ),

    path(
    "dashboard-settings/",
    views.dashboard_settings,
    name="dashboard_settings"
    ),

    path(
    "backup/",
    views.backup,
    name="backup"
    ),

    path(
    "backup/download/<str:filename>/",
    views.backup_download,
    name="backup_download",
    ),

    path(
    "backup/delete/<str:filename>/",
    views.backup_delete,
    name="backup_delete",
    ),

    path(
    "backup/restore/<str:filename>/",
    views.backup_restore,
    name="backup_restore",
    ),

    path(
    "export/",
    views.export,
    name="export",
    ),

    path(
    "export/download/<str:filename>/",
    views.export_download,
    name="export_download",
    ),

    path(
    "export/delete/<str:filename>/",
    views.export_delete,
    name="export_delete",
    ),

    path(
    "firmeninformationen/",
    views.firmeninformationen_list,
    name="firmeninformationen"
    ),


    path(
    "firmeninformationen/manage/",
    views.firmeninformationen_manage,
    name="firmeninformationen_manage"
    ),
    path(
    "firmeninformationen/edit/<int:id>/",
    views.firmeninformationen_edit,
    name="firmeninformationen_edit"
    ),

    path(
    "firmeninformationen/create/",
    views.firmeninformationen_create,
    name="firmeninformationen_create"
    ),  

    path(
    "firmeninformationen/delete/<int:id>/",
    views.firmeninformationen_delete,
    name="firmeninformationen_delete"
    ),

    path(
    "audit_log/",
    views.audit_log,
    name="audit_log"
    ),

    path(
    "audit_log/delete/<int:id>/",
    views.audit_log_delete,
    name="audit_log_delete"
    ),

    path(
    "audit-log/delete-selected/",
    views.audit_log_delete_selected,
    name="audit_log_delete_selected"
    ),
    path(
    "kontakt/",
    views.kontakt_informationen,
    name="kontakt"
    ),

    path(
    "kontakt/edit/",
    views.kontakt_edit,
    name="kontakt_edit"
    ),

    path(
    "system-update/",
    views.system_update,
    name="system_update"
    ),

    path(
    "check-update/",
    views.check_update,
    name="check_update"
    ),

    path(
    "run-update/",
    views.run_update,
    name="run_update"
    ),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]