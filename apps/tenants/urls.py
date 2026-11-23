from django.urls import path
from django.views.generic import RedirectView

from apps.addressbook import info_views
from apps.core.views import PrefixRedirectView

from . import views

app_name = "tenants"

urlpatterns = [
    path("bord/", views.BordView.as_view(), name="profile"),
    path("bord/dates/<int:pk>/statut/", views.BordStatusView.as_view(), name="bord-status"),
    path("structure/", views.TenantSettingsView.as_view(), name="settings"),
    path("structure/compte/", views.AccountView.as_view(), name="account"),
    path("structure/paratge/", views.ParatgeView.as_view(), name="paratge"),
    path(
        "structure/documents/",
        views.MessageTemplatesView.as_view(),
        name="message-templates",
    ),
    path("structure/compte/supprimer/", views.DeleteTenantView.as_view(), name="delete"),
    path(
        "structure/compte/annuler-suppression/",
        views.CancelDeletionView.as_view(),
        name="cancel-deletion",
    ),
    path("structure/compte/quitter/", views.LeaveTenantView.as_view(), name="leave"),
    path("structure/equipe/", views.PersonListView.as_view(), name="person-list"),
    path("structure/equipe/nouveau/", views.PersonCreateView.as_view(), name="person-create"),
    path(
        "structure/equipe/<int:pk>/formulaire/",
        info_views.InfoInviteView.as_view(kind="person"),
        name="person-info-invite",
    ),
    path(
        "structure/equipe/<int:pk>/formulaire/annuler/",
        info_views.InfoRevokeView.as_view(kind="person"),
        name="person-info-revoke",
    ),
    path(
        "structure/equipe/<int:pk>/reponse/",
        info_views.InfoAnswerView.as_view(kind="person"),
        name="person-info-answer",
    ),
    path("structure/equipe/<int:pk>/", views.PersonDetailView.as_view(), name="person-detail"),
    path(
        "structure/equipe/<int:pk>/modifier/",
        views.PersonUpdateView.as_view(),
        name="person-update",
    ),
    path(
        "structure/equipe/<int:pk>/supprimer/",
        views.PersonDeleteView.as_view(),
        name="person-delete",
    ),
    path(
        "structure/equipe/<int:pk>/espace/creer/",
        views.PersonAccessView.as_view(action="enable"),
        name="person-access-enable",
    ),
    path(
        "structure/equipe/<int:pk>/espace/revoquer/",
        views.PersonAccessView.as_view(action="revoke"),
        name="person-access-revoke",
    ),
    path("social/", views.SocialView.as_view(), name="social"),
    path("social/suivi/", views.SocialFollowView.as_view(), name="social-follow"),
    path("social/historique/", views.SocialHistoryView.as_view(), name="social-history"),
    path("social/export/", views.SocialExportView.as_view(), name="social-export"),
    path("social/pdf/", views.SocialPdfView.as_view(), name="social-pdf"),
    path("structure/compte/export-donnees/", views.DataExportView.as_view(), name="data-export"),
]

# Former addresses of the Social pages (301): they now live under /social/.
for _old, _name in (
    ("", "social"),
    ("suivi/", "social-follow"),
    ("historique/", "social-history"),
    ("export/", "social-export"),
    ("pdf/", "social-pdf"),
):
    urlpatterns.append(
        path(
            f"bord/equipe/social/{_old}",
            RedirectView.as_view(
                pattern_name=f"tenants:{_name}", permanent=True, query_string=True
            ),
        )
    )

# Former addresses of Ma structure (301).
for _old, _name in (
    ("bord/informations/messages/", "tenants:message-templates"),
    ("bord/informations/", "tenants:settings"),
    ("bord/supprimer/", "tenants:delete"),
    ("bord/annuler-suppression/", "tenants:cancel-deletion"),
    ("bord/quitter/", "tenants:leave"),
    ("bord/export-donnees/", "tenants:data-export"),
):
    urlpatterns.append(
        path(_old, RedirectView.as_view(pattern_name=_name, permanent=True, query_string=True))
    )
urlpatterns.append(
    path("bord/equipe/<path:rest>", PrefixRedirectView.as_view(new_prefix="/structure/equipe/"))
)
urlpatterns.append(
    path("bord/equipe/", PrefixRedirectView.as_view(new_prefix="/structure/equipe/"))
)
