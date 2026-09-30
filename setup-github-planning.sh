#!/usr/bin/env bash
# Crée les labels, puis les issues correspondant aux tâches non cochées
# de docs/04-feuille-de-route.md, avec le bon milestone.
#
# Pré-requis :
#   - `gh` (GitHub CLI) installé et authentifié (`gh auth login`)
#   - lancé depuis la racine du dépôt (celui qui contient CLAUDE.md)
#   - les milestones ci-dessous déjà créés dans GitHub
#     (Issues > Milestones > New milestone) : Phase 0, Phase 1, Phase 2,
#     Sprint 3.1 ... Sprint 3.8, Phase 4, Phase 5
#
# Usage : bash setup-github-planning.sh

set -euo pipefail

echo "== Labels =="
gh label create "phase:0"        --color "5319E7" --description "Validation métier" --force
gh label create "phase:1"        --color "5319E7" --description "Squelette déployé" --force
gh label create "phase:2"        --color "5319E7" --description "PoC vertical" --force
gh label create "phase:3"        --color "5319E7" --description "MVP" --force
gh label create "phase:4"        --color "5319E7" --description "Bêta fermée" --force
gh label create "phase:5"        --color "5319E7" --description "Version 1 payante" --force

gh label create "area:accounts"     --color "0E8A16" --force
gh label create "area:tenants"      --color "0E8A16" --force
gh label create "area:catalog"      --color "0E8A16" --force
gh label create "area:addressbook"  --color "0E8A16" --force
gh label create "area:gigs"         --color "0E8A16" --force
gh label create "area:documents"    --color "0E8A16" --force
gh label create "area:roadmaps"     --color "0E8A16" --force
gh label create "area:finance"      --color "0E8A16" --force
gh label create "area:infra"        --color "0E8A16" --force
gh label create "area:legal"        --color "0E8A16" --force

gh label create "decision-attendue" --color "D93F0B" --description "Bloqué tant qu'une question ouverte (§14) n'est pas tranchée" --force

echo "== Issues : Phase 0 — Validation métier =="
gh issue create --title "Lire 02-guide-metier.md" --milestone "Phase 0" --label "phase:0"
gh issue create --title "Lister 10-15 artistes/associations à contacter" --milestone "Phase 0" --label "phase:0"
gh issue create --title "Mener 5 entretiens (trame guide métier §5)" --milestone "Phase 0" --label "phase:0"
gh issue create --title "Repérer 2-3 modèles de contrats de référence, vérifier droits de réutilisation" --milestone "Phase 0" --label "phase:0"
gh issue create --title "Identifier un professionnel relecteur (juriste/comptable/CAE)" --milestone "Phase 0" --label "phase:0"
gh issue create --title "Obtenir les réponses du collègue aux questions ouvertes Q1-Q14 (cahier des charges §14)" --milestone "Phase 0" --label "phase:0" --label "decision-attendue"
gh issue create --title "⚠️ Trancher Q8 : clause 293B/Nécitge 2000 retirée du contrat, confirmer avec le collègue" --milestone "Phase 0" --label "phase:0" --label "area:documents" --label "decision-attendue"
gh issue create --title "Rédiger synthèse d'une page (problèmes, fonctionnalités demandées, vocabulaire, prix)" --milestone "Phase 0" --label "phase:0"
gh issue create --title "Décider : go / go modifié / stop" --milestone "Phase 0" --label "phase:0"

echo "== Issues : Phase 1 — Squelette déployé (reliquat) =="
gh issue create --title "Créer compte Scalingo + app staging + addon PostgreSQL" --milestone "Phase 1" --label "phase:1" --label "area:infra"
gh issue create --title "Rendre WeasyPrint opérationnel sur Scalingo (buildpack apt)" --milestone "Phase 1" --label "phase:1" --label "area:infra"
gh issue create --title "Route /health/ + moniteur d'uptime gratuit" --milestone "Phase 1" --label "phase:1" --label "area:infra"
gh issue create --title "Brancher Sentry (région UE)" --milestone "Phase 1" --label "phase:1" --label "area:infra"
gh issue create --title "Déploiement automatique de main vers staging" --milestone "Phase 1" --label "phase:1" --label "area:infra"
gh issue create --title "Tester mot de passe oublié (django-allauth)" --milestone "Phase 1" --label "phase:1" --label "area:accounts"

echo "== Issues : Phase 2 — PoC vertical (reliquat) =="
gh issue create --title "Retirer le filigrane 'gabarit provisoire' une fois le contrat validé" --milestone "Phase 2" --label "phase:2" --label "area:documents"
gh issue create --title "Afficher le logo de la structure sur le PDF du contrat" --milestone "Phase 2" --label "phase:2" --label "area:documents"
gh issue create --title "Déployer sur staging + test utilisateur avec 3 personnes" --milestone "Phase 2" --label "phase:2"
gh issue create --title "Faire relire le PDF de contrat par le relecteur identifié en Phase 0" --milestone "Phase 2" --label "phase:2"

echo "== Issues : Sprint 3.1 — Comptes, onboarding, structure, navigation =="
gh issue create --title "Activer confirmation d'e-mail + choisir prestataire transactionnel" --milestone "Sprint 3.1" --label "phase:3" --label "area:accounts"
gh issue create --title "Ma structure : ajouter vat_number, iban, logo, forme juridique (liste), code_ape" --milestone "Sprint 3.1" --label "phase:3" --label "area:tenants"
gh issue create --title "Gestion du régime de TVA (assujetti / franchise / non assujetti)" --milestone "Sprint 3.1" --label "phase:3" --label "area:tenants"

echo "== Issues : Sprint 3.2 — Carnet d'adresses et spectacles =="
gh issue create --title "CRUD Contact (contrainte promoter OU venue)" --milestone "Sprint 3.2" --label "phase:3" --label "area:addressbook"
gh issue create --title "Rôles de contact suggérés : Accueil, Technique, Comm'" --milestone "Sprint 3.2" --label "phase:3" --label "area:addressbook"
gh issue create --title "Recherche en direct HTMX sur les listes (debounce)" --milestone "Sprint 3.2" --label "phase:3" --label "area:addressbook"
gh issue create --title "Fiches de détail organisateur/lieu (contacts + historique des dates)" --milestone "Sprint 3.2" --label "phase:3" --label "area:addressbook"
gh issue create --title "CRUD Show (fiche technique, nom du groupe, distribution, rider, lien EPK)" --milestone "Sprint 3.2" --label "phase:3" --label "area:catalog"
gh issue create --title "Suppression sécurisée (organisateur utilisé = bloqué ou archivage)" --milestone "Sprint 3.2" --label "phase:3" --label "area:addressbook"

echo "== Issues : Sprint 3.3 — Dates : statuts, liste, calendrier, détail =="
gh issue create --title "Statuts option/confirmed/signed/cancelled avec transitions contrôlées (service)" --milestone "Sprint 3.3" --label "phase:3" --label "area:gigs"
gh issue create --title "Date de fin d'option + mise en évidence des options qui expirent" --milestone "Sprint 3.3" --label "phase:3" --label "area:gigs"
gh issue create --title "Page de détail d'une date (tableau de bord)" --milestone "Sprint 3.3" --label "phase:3" --label "area:gigs"
gh issue create --title "Liste filtrable (statut, mois, spectacle) via HTMX" --milestone "Sprint 3.3" --label "phase:3" --label "area:gigs"
gh issue create --title "Vue calendrier mensuel" --milestone "Sprint 3.3" --label "phase:3" --label "area:gigs"
gh issue create --title "Annulation d'une date (conservation historique)" --milestone "Sprint 3.3" --label "phase:3" --label "area:gigs"
gh issue create --title "Comptage des dates de l'année (prépare le quota)" --milestone "Sprint 3.3" --label "phase:3" --label "area:gigs"

echo "== Issues : Sprint 3.4 — Contrats =="
gh issue create --title "Conditions particulières éditables sur le contrat" --milestone "Sprint 3.4" --label "phase:3" --label "area:documents"
gh issue create --title "Aperçu avant génération + historique des versions" --milestone "Sprint 3.4" --label "phase:3" --label "area:documents"
gh issue create --title "Numérotation des contrats par tenant" --milestone "Sprint 3.4" --label "phase:3" --label "area:documents"
gh issue create --title "Marquage signé : figeage PDF + upload PDF signé" --milestone "Sprint 3.4" --label "phase:3" --label "area:documents"
gh issue create --title "Stockage S3 européen des PDF figés (django-storages)" --milestone "Sprint 3.4" --label "phase:3" --label "area:infra"

echo "== Issues : Sprint 3.5 — Devis et factures =="
gh issue create --title "Modèles Quote, Invoice, DocumentLine, InvoiceSequence" --milestone "Sprint 3.5" --label "phase:3" --label "area:documents"
gh issue create --title "Création devis/facture avec suggestion acompte/solde" --milestone "Sprint 3.5" --label "phase:3" --label "area:documents"
gh issue create --title "Émission : numéro sous verrou + snapshot infos légales" --milestone "Sprint 3.5" --label "phase:3" --label "area:documents"
gh issue create --title "Immutabilité facture émise + avoirs" --milestone "Sprint 3.5" --label "phase:3" --label "area:documents"
gh issue create --title "Distinguer recette prévue / facturée / encaissée (F-57)" --milestone "Sprint 3.5" --label "phase:3" --label "area:finance"
gh issue create --title "Affichage euros entiers, stockage centime-exact (F-58)" --milestone "Sprint 3.5" --label "phase:3" --label "area:finance"
gh issue create --title "Relecture du PDF de facture par le comptable" --milestone "Sprint 3.5" --label "phase:3" --label "area:documents"

echo "== Issues : Sprint 3.6 — Feuille de route =="
gh issue create --title "Modèles Roadmap, RoadmapSlot, Lodging, Meal, GigMember" --milestone "Sprint 3.6" --label "phase:3" --label "area:roadmaps"
gh issue create --title "Éditeur de feuille de route (HTMX)" --milestone "Sprint 3.6" --label "phase:3" --label "area:roadmaps"
gh issue create --title "Lien secret : génération, activation/révocation, page publique" --milestone "Sprint 3.6" --label "phase:3" --label "area:roadmaps"
gh issue create --title "Vue mobile-first + export PDF" --milestone "Sprint 3.6" --label "phase:3" --label "area:roadmaps"

echo "== Issues : Sprint 3.7 — Finances =="
gh issue create --title "Payment et Expense (formulaires rapides HTMX)" --milestone "Sprint 3.7" --label "phase:3" --label "area:finance"
gh issue create --title "Bilan par date (facturé/encaissé/dépensé/résultat)" --milestone "Sprint 3.7" --label "phase:3" --label "area:finance"
gh issue create --title "Tableau de bord global (totaux, retards, dates sans contrat)" --milestone "Sprint 3.7" --label "phase:3" --label "area:finance"
gh issue create --title "Export CSV (';', UTF-8 BOM)" --milestone "Sprint 3.7" --label "phase:3" --label "area:finance"

echo "== Issues : Sprint 3.8 — Légal, sécurité, finition, recette =="
gh issue create --title "Pages légales (mentions, CGU, confidentialité)" --milestone "Sprint 3.8" --label "phase:3" --label "area:legal"
gh issue create --title "Export des données + suppression de compte (F-81)" --milestone "Sprint 3.8" --label "phase:3" --label "area:legal"
gh issue create --title "Audit d'isolation complet (toutes les URLs, 2 tenants)" --milestone "Sprint 3.8" --label "phase:3" --label "area:infra"
gh issue create --title "Revue sécurité (check --deploy, dépendances, secrets)" --milestone "Sprint 3.8" --label "phase:3" --label "area:infra"
gh issue create --title "Recette complète (cahier des charges §11) sur staging" --milestone "Sprint 3.8" --label "phase:3"
gh issue create --title "Sauvegarde + test de restauration" --milestone "Sprint 3.8" --label "phase:3" --label "area:infra"
gh issue create --title "Déploiement en production" --milestone "Sprint 3.8" --label "phase:3" --label "area:infra"

echo "== Issues : Phase 4 — Bêta fermée =="
gh issue create --title "Recruter 5-10 bêta-testeurs" --milestone "Phase 4" --label "phase:4"
gh issue create --title "Guide de démarrage court + canal de retour" --milestone "Phase 4" --label "phase:4"
gh issue create --title "Suivi : Sentry, uptime, comptes créés, abandons onboarding" --milestone "Phase 4" --label "phase:4" --label "area:infra"
gh issue create --title "Faire valider définitivement contrat/factures/mentions légales" --milestone "Phase 4" --label "phase:4" --label "area:legal"
gh issue create --title "Registre des traitements RGPD" --milestone "Phase 4" --label "phase:4" --label "area:legal"

echo "== Issues : Phase 5 — Version 1 payante =="
gh issue create --title "⚠️ Choisir la grille tarifaire : freemium ou formules Essentiel/Collectif (Q9)" --milestone "Phase 5" --label "phase:5" --label "decision-attendue"
gh issue create --title "Intégrer Stripe (Checkout + webhooks)" --milestone "Phase 5" --label "phase:5" --label "area:finance"
gh issue create --title "Lot 3 : facturation électronique conforme (Factur-X, PA)" --milestone "Phase 5" --label "phase:5" --label "area:documents"
gh issue create --title "Signature électronique (prestataire)" --milestone "Phase 5" --label "phase:5" --label "area:documents"
gh issue create --title "Relances et rappels automatiques (options, contrats, factures)" --milestone "Phase 5" --label "phase:5"
gh issue create --title "Export iCal + connexion Google Calendar (idée du 28/09)" --milestone "Phase 5" --label "phase:5" --label "area:gigs"
gh issue create --title "PWA de la feuille de route (hors-ligne)" --milestone "Phase 5" --label "phase:5" --label "area:roadmaps"
gh issue create --title "Formulaire d'auto-saisie envoyé à l'organisateur (idée du 28/09)" --milestone "Phase 5" --label "phase:5" --label "decision-attendue"

echo "Terminé. Vérifie le Project : les nouvelles issues doivent apparaître automatiquement en colonne Backlog."