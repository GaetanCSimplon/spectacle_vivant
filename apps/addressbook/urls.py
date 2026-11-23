from django.urls import path

from . import info_views, views

app_name = "addressbook"

urlpatterns = [
    path("contacts/", views.DirectoryView.as_view(), name="directory"),
    path(
        "organisateurs/",
        views.DirectoryRedirectView.as_view(kind="organisateurs"),
        name="promoter-list-moved",
    ),
    path("organisateurs/export/", views.PromoterExportView.as_view(), name="promoter-export"),
    path("organisateurs/nouveau/", views.PromoterCreateView.as_view(), name="promoter-create"),
    path("organisateurs/<int:pk>/", views.PromoterDetailView.as_view(), name="promoter-detail"),
    path(
        "organisateurs/<int:pk>/modifier/",
        views.PromoterUpdateView.as_view(),
        name="promoter-update",
    ),
    path(
        "organisateurs/<int:pk>/supprimer/",
        views.PromoterDeleteView.as_view(),
        name="promoter-delete",
    ),
    path(
        "organisateurs/<int:pk>/formulaire/",
        views.PromoterInviteView.as_view(),
        name="promoter-invite",
    ),
    path(
        "organisateurs/<int:pk>/formulaire/annuler/",
        views.PromoterInviteRevokeView.as_view(),
        name="promoter-invite-revoke",
    ),
    path(
        "organisateurs/<int:pk>/reponse/",
        views.PromoterAnswerView.as_view(),
        name="promoter-answer",
    ),
    path(
        "lieux/",
        views.DirectoryRedirectView.as_view(kind="lieux"),
        name="venue-list-moved",
    ),
    path("lieux/export/", views.VenueExportView.as_view(), name="venue-export"),
    path("lieux/nouveau/", views.VenueCreateView.as_view(), name="venue-create"),
    path("lieux/<int:pk>/", views.VenueDetailView.as_view(), name="venue-detail"),
    path("lieux/<int:pk>/modifier/", views.VenueUpdateView.as_view(), name="venue-update"),
    path("lieux/<int:pk>/supprimer/", views.VenueDeleteView.as_view(), name="venue-delete"),
    path(
        "organisateurs/<int:promoter_pk>/contacts/nouveau/",
        views.PromoterContactCreateView.as_view(),
        name="promoter-contact-create",
    ),
    path(
        "lieux/<int:venue_pk>/contacts/nouveau/",
        views.VenueContactCreateView.as_view(),
        name="venue-contact-create",
    ),
    path(
        "organisateurs/<int:pk>/suivi/",
        views.PromoterFollowUpView.as_view(),
        name="promoter-follow-up",
    ),
    path(
        "organisateurs/<int:pk>/contacts/rattacher/",
        views.PromoterContactLinkView.as_view(action="attach"),
        name="promoter-contact-attach",
    ),
    path(
        "organisateurs/<int:pk>/contacts/<int:contact_pk>/retirer/",
        views.PromoterContactLinkView.as_view(action="detach"),
        name="promoter-contact-detach",
    ),
    path(
        "lieux/<int:pk>/contacts/rattacher/",
        views.VenueContactLinkView.as_view(action="attach"),
        name="venue-contact-attach",
    ),
    path(
        "lieux/<int:pk>/contacts/<int:contact_pk>/retirer/",
        views.VenueContactLinkView.as_view(action="detach"),
        name="venue-contact-detach",
    ),
    path("annuaire/importer/", views.ImportView.as_view(), name="import"),
    path("annuaire/importer/confirmer/", views.ImportConfirmView.as_view(), name="import-confirm"),
    path(
        "annuaire/importer/modele/<slug:kind>/",
        views.ImportTemplateView.as_view(),
        name="import-template",
    ),
    path("contacts/export/", views.ContactExportView.as_view(), name="contact-export"),
    path("contacts/nouveau/", views.ContactQuickCreateView.as_view(), name="contact-create"),
    path("contacts/<int:pk>/modifier/", views.ContactUpdateView.as_view(), name="contact-update"),
    path(
        "contacts/<int:pk>/formulaire/",
        info_views.InfoInviteView.as_view(kind="contact"),
        name="contact-info-invite",
    ),
    path(
        "contacts/<int:pk>/formulaire/annuler/",
        info_views.InfoRevokeView.as_view(kind="contact"),
        name="contact-info-revoke",
    ),
    path(
        "contacts/<int:pk>/reponse/",
        info_views.InfoAnswerView.as_view(kind="contact"),
        name="contact-info-answer",
    ),
    path("contacts/<int:pk>/supprimer/", views.ContactDeleteView.as_view(), name="contact-delete"),
]
