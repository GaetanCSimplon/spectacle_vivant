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

# NAF rév. 2 (valid until 31/12/2026), written as the form stores it: 4 digits and a letter.
# The NAF 2025 replaces it on 1 January 2027: its codes and the correspondence table of the
# INSEE are to be added then. A code typed under "Autre" is already accepted.
APE_CODES = [
    ("9001Z", "Arts du spectacle vivant"),
    ("9002Z", "Activités de soutien au spectacle vivant"),
    ("9003A", "Création artistique relevant des arts plastiques"),
    ("9003B", "Autre création artistique"),
    ("9004Z", "Gestion de salles de spectacles"),
    ("5920Z", "Enregistrement sonore et édition musicale"),
    ("7490B", "Activités spécialisées, scientifiques et techniques diverses"),
    ("7990Z", "Autres services de réservation et activités connexes"),
    ("8230Z", "Organisation de foires, salons professionnels et congrès"),
    ("8552Z", "Enseignement culturel"),
    ("9329Z", "Autres activités récréatives et de loisirs"),
    ("9499Z", "Autres organisations fonctionnant par adhésion volontaire"),
]
APE_CODE_VALUES = [code for code, _label in APE_CODES]
