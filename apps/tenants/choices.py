"""Lists offered for the legal form and the role of the representative (recette n°1, STR-01/06).

The field keeps the readable label (it is what the documents print), so an older free-text
value stays valid: the form shows it under "Autre".
"""

LEGAL_FORMS = [
    "Particulier (sans activité professionnelle)",
    "Entrepreneur individuel / micro-entrepreneur",
    "Association loi 1901",
    "Association de droit local (Alsace-Moselle)",
    "SARL / EURL",
    "SAS / SASU",
    "SA",
    "Coopérative (SCOP, SCIC)",
    "Commune",
    "Autre collectivité (département, région, intercommunalité)",
    "Établissement public (EPCC, EPIC…)",
    "Fondation / fonds de dotation",
]

# (group, roles): a role is written once so that a stored value points to a single option.
REPRESENTATIVE_ROLES = [
    (
        "Association",
        ["Président(e)", "Co-président(e)", "Vice-président(e)", "Secrétaire", "Trésorier(ère)"],
    ),
    ("Société", ["Gérant(e)", "Co-gérant(e)", "Directeur(rice) général(e)"]),
    (
        "Lieu ou institution",
        [
            "Directeur(rice)",
            "Co-directeur(rice)",
            "Administrateur(rice)",
            "Directeur(rice) délégué(e)",
        ],
    ),
    ("Collectivité", ["Maire", "Adjoint(e) à la culture", "Président(e) de la collectivité"]),
    ("Entrepreneur individuel", ["Exploitant(e)"]),
]

ROLES = [role for _group, roles in REPRESENTATIVE_ROLES for role in roles]
