"""Fill a development database with a fictional structure, to see the application "in use".

Everything is made up and lives in ONE structure ("Compagnie des Nuits d'Été") with its own two
users, so it never touches the data you typed yourself; `--reset` removes it again. Dates are
relative to today, so the demo always has coming dates, past ones, money received and money
still due. Refused outside development (`DJANGO_DEBUG` must be on) unless `--force`.
"""

import datetime
from decimal import Decimal

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Membership, User
from apps.addressbook.models import Contact, Promoter, Venue
from apps.catalog.models import Show
from apps.documents import invoicing
from apps.documents import services as document_services
from apps.documents.models import Invoice
from apps.finance import services as finance_services
from apps.finance.models import Expense, ExpenseClaim
from apps.gigs.models import Gig, GigMember
from apps.roadmaps import services as roadmap_services
from apps.roadmaps.models import Lodging, Meal, PlaceContact, RoadmapSlot
from apps.tenants import services as tenant_services
from apps.tenants.models import Person, Tenant

TENANT_NAME = "Compagnie des Nuits d'Été"
OWNER_EMAIL = "demo@example.org"
MEMBER_EMAIL = "gestion@example.org"
PASSWORD = "demo-bordpro-2026"

T = datetime.time
D = Decimal


def day(offset):
    return datetime.date.today() + datetime.timedelta(days=offset)


class Command(BaseCommand):
    help = "Create (or with --reset, delete and recreate) a fictional demo structure."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Delete the demo, then recreate it."
        )
        parser.add_argument("--remove", action="store_true", help="Delete the demo and stop.")
        parser.add_argument(
            "--no-map", action="store_true", help="Skip the map lookup of addresses."
        )
        parser.add_argument("--force", action="store_true", help="Allow it when DEBUG is off.")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("seed_demo is for development only (DJANGO_DEBUG is off).")
        existing = Tenant.objects.filter(name=TENANT_NAME).first()
        if existing and not (options["reset"] or options["remove"]):
            raise CommandError("The demo already exists: use --reset to recreate it.")
        if existing:
            tenant_services.purge_tenant(existing)
            User.objects.filter(email__in=[OWNER_EMAIL, MEMBER_EMAIL]).delete()
            self.stdout.write("Demo removed.")
        if options["remove"]:
            return
        geocoding = settings.GEOCODING_ENABLED
        settings.GEOCODING_ENABLED = False  # one lookup per second is done at the end, politely
        try:
            with transaction.atomic():
                summary = self.build()
        finally:
            settings.GEOCODING_ENABLED = geocoding
        if geocoding and not options["no_map"]:
            call_command("geocode_places")
        self.stdout.write(self.style.SUCCESS("Demo created."))
        for line in summary:
            self.stdout.write(line)

    # ------------------------------------------------------------------------------------------

    def build(self):
        tenant = self.tenant_and_users()
        shows = self.shows(tenant)
        people = self.team(tenant, shows)
        promoters = self.promoters(tenant)
        venues = self.venues(tenant)
        self.contacts(tenant, promoters, venues)
        gigs = self.gigs(tenant, shows, promoters, venues, people)
        self.money(tenant, gigs)
        self.expenses(tenant, gigs, people)
        link = self.roadmaps(tenant, gigs, people)
        return [
            f"  Owner:   {OWNER_EMAIL} / {PASSWORD}",
            f"  Manager: {MEMBER_EMAIL} / {PASSWORD}  (role « membre »)",
            f"  {len(gigs)} dates, {len(shows)} shows, {len(people)} people, "
            f"{len(promoters)} organisers, {len(venues)} venues.",
            f"  Personal link of Léa (open it in a private window): {link}",
        ]

    def tenant_and_users(self):
        tenant = Tenant.objects.create(
            name=TENANT_NAME,
            legal_form="Association loi 1901",
            siret="12345678900012",
            code_ape="9001Z",
            address="12 rue des Arts",
            postal_code="34000",
            city="Montpellier",
            department="34",
            vat_regime=Tenant.VatRegime.FRANCHISE,
            iban="FR1420041010050500013M02606",
            bic="BNPAFRPP",
            phone="04 67 00 00 00",
            email="contact@nuits-ete.example",
            licence_number="PLATESV-D-2026-000000",
            representative_name="Camille Martin",
            representative_role="Présidente",
            jurisdiction_city="Montpellier",
        )
        for email, role in (
            (OWNER_EMAIL, Membership.Role.OWNER),
            (MEMBER_EMAIL, Membership.Role.MEMBER),
        ):
            user = User.objects.create_user(email=email, password=PASSWORD)
            EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
            Membership.objects.create(user=user, tenant=tenant, role=role)
        return tenant

    def shows(self, tenant):
        rows = [
            ("Nuits d'été", "Les Nocturnes", 75, "1200.00", 5, 3, 2, 45, "NE-2026"),
            ("Le Bal des Marins", "Orchestre Marée Haute", 120, "1800.00", 7, 5, 2, 60, "BM-2026"),
            ("Petites Oreilles", "Trio Cabrioles", 45, "650.00", 3, 2, 1, 30, "PO-2026"),
        ]
        return [
            Show.objects.create(
                tenant=tenant,
                title=title,
                group_name=group,
                duration_minutes=minutes,
                default_price=price,
                crew_size=crew,
                artists_count=artists,
                technicians_count=techs,
                soundcheck_minutes=soundcheck,
                analytic_code=code,
                sacem_number="123456" if i == 0 else "",
                tech_sheet_text="Scène 6 m x 4 m, 2 retours, 8 prises 16 A, accès camionnette.",
            )
            for i, (
                title,
                group,
                minutes,
                price,
                crew,
                artists,
                techs,
                soundcheck,
                code,
            ) in enumerate(rows)
        ]

    def team(self, tenant, shows):
        rows = [
            (
                "Léa",
                "Durand",
                "Chant",
                "Intermittente",
                True,
                False,
                datetime.date(1988, 3, 14),
                "06 11 22 33 44",
            ),
            (
                "Marc",
                "Roux",
                "Guitare",
                "Intermittent",
                True,
                False,
                datetime.date(1985, 11, 2),
                "06 22 33 44 55",
            ),
            (
                "Sofia",
                "Benali",
                "Batterie",
                "Intermittente",
                True,
                False,
                datetime.date(1991, 7, 21),
                "06 33 44 55 66",
            ),
            (
                "Hugo",
                "Lambert",
                "Régie son",
                "Intermittent",
                False,
                True,
                datetime.date(1990, 1, 30),
                "06 44 55 66 77",
            ),
            (
                "Inès",
                "Moreau",
                "Régie lumière",
                "Intermittente",
                False,
                True,
                datetime.date(1994, 9, 9),
                "06 55 66 77 88",
            ),
            (
                "Paul",
                "Fabre",
                "Production",
                "Salarié",
                False,
                True,
                datetime.date(1979, 5, 25),
                "06 66 77 88 99",
            ),
        ]
        people = {}
        for first, last, role, status, artist, tech, born, phone in rows:
            people[first] = Person.objects.create(
                tenant=tenant,
                first_name=first,
                last_name=last,
                role=role,
                status=status,
                is_artist=artist,
                is_technician=tech,
                birth_date=born,
                phone=phone,
                email=f"{first.lower().replace('è', 'e')}.{last.lower()}@example.org",
                average_fee="150.00" if artist else "120.00",
            )
        casts = [
            ["Léa", "Marc", "Sofia", "Hugo"],
            ["Marc", "Sofia", "Léa", "Inès"],
            ["Léa", "Sofia"],
        ]
        for show, names in zip(shows, casts, strict=True):
            show.cast.set([people[name] for name in names])
        return people

    def promoters(self, tenant):
        rows = [
            (
                "Association Les Escales",
                "active",
                "Sète",
                "34200",
                "Quai de Bosc",
                "escales@example.org",
            ),
            (
                "Festival Voix du Sud",
                "active",
                "Nîmes",
                "30000",
                "Boulevard des Arènes",
                "voix@example.org",
            ),
            (
                "Mairie de Lavérune",
                "negotiating",
                "Lavérune",
                "34880",
                "Place de la Mairie",
                "culture@example.org",
            ),
            (
                "MJC de Castelnau",
                "prospect",
                "Castelnau-le-Lez",
                "34170",
                "Rue de la Mairie",
                "mjc@example.org",
            ),
            (
                "Comité des fêtes de Mauguio",
                "signing",
                "Mauguio",
                "34130",
                "Avenue de la Gare",
                "fetes@example.org",
            ),
            (
                "Théâtre du Port",
                "dropped",
                "Marseille",
                "13002",
                "Place de la Joliette",
                "port@example.org",
            ),
        ]
        kinds = list(Promoter.QUALIFICATION["kinds"][0].values)
        events = list(Promoter.QUALIFICATION["event_types"][0].values)
        styles = list(Promoter.QUALIFICATION["aesthetics"][0].values)
        out = []
        for i, (name, follow_up, city, code, street, email) in enumerate(rows):
            out.append(
                Promoter.objects.create(
                    tenant=tenant,
                    name=name,
                    follow_up=follow_up,
                    email=email,
                    phone=f"04 67 1{i} 2{i} 3{i}",
                    billing_address=f"1 {street}",
                    postal_code=code,
                    city=city,
                    siret=f"4{i}234567800015",
                    representative_name="Alex Moreau",
                    representative_role="Président(e)",
                    kinds=[kinds[i % len(kinds)]],
                    event_types=[events[i % len(events)]],
                    aesthetics=styles[i % len(styles) : i % len(styles) + 2],
                )
            )
        return out

    def venues(self, tenant):
        rows = [
            ("Théâtre de verdure", "Quai de Bosc", "34200", "Sète", 450, "plein air"),
            ("Salle des Arènes", "Boulevard des Arènes", "30000", "Nîmes", 800, "debout"),
            ("Salle Georges Brassens", "Place de la Comédie", "34000", "Montpellier", 300, "assis"),
            (
                "Espace culturel de Lavérune",
                "Place de la Mairie",
                "34880",
                "Lavérune",
                180,
                "assis",
            ),
            ("Halle des sports", "Avenue de la Gare", "34130", "Mauguio", 600, "debout"),
            ("Salle polyvalente", "Rue de la Mairie", "34170", "Castelnau-le-Lez", 250, "assis"),
        ]
        return [
            Venue.objects.create(
                tenant=tenant,
                name=name,
                address=f"1 {street}" if i else street,
                postal_code=code,
                city=city,
                capacity=capacity,
                configuration=configuration,
                phone=f"04 67 2{i} 3{i} 4{i}",
                access_info="Chargement par l'arrière, parking réservé aux artistes."
                if i % 2 == 0
                else "",
            )
            for i, (name, street, code, city, capacity, configuration) in enumerate(rows)
        ]

    def contacts(self, tenant, promoters, venues):
        """The address book: contacts of one organiser or venue, one who works for two
        organisers, one for a venue and an organiser, and two kept "sans rattachement"."""

        def add(name, role, email, phone, promoter_list=(), venue_list=()):
            contact = Contact.objects.create(
                tenant=tenant, name=name, role=role, email=email, phone=phone
            )
            contact.promoters.set(promoter_list)
            contact.venues.set(venue_list)
            return contact

        people = [
            ("Julie Garnier", "Programmation"),
            ("Thomas Petit", "Direction"),
            ("Nadia Cherif", "Culture"),
            ("Éric Vidal", "Animation"),
            ("Sandrine Lopez", "Trésorerie"),
            ("Yann Roche", "Programmation"),
        ]
        for promoter, (name, role) in zip(promoters, people, strict=True):
            add(name, role, f"{name.split()[0].lower()}@example.org", "06 10 20 30 40", [promoter])
        staff = [
            ("Marc Aubert", "Régisseur"),
            ("Clara Dupuis", "Accueil artistes"),
            ("Omar Haddad", "Régisseur"),
            ("Léa Fontaine", "Technique"),
            ("Bruno Colin", "Gardien"),
            ("Anna Costa", "Accueil"),
        ]
        for venue, (name, role) in zip(venues, staff, strict=True):
            add(
                name,
                role,
                f"{name.split()[0].lower()}.salle@example.org",
                "06 50 60 70 80",
                (),
                [venue],
            )
        # One person, several organisations: a technician who works for two organisers and a venue.
        add(
            "Pierre Mallet",
            "Technique",
            "pierre@example.org",
            "06 12 12 12 12",
            promoters[:2],
            venues[:1],
        )
        # A freelance programmer for two festivals.
        add(
            "Sabine Roy",
            "Programmation / Direction",
            "sabine@example.org",
            "06 77 88 99 00",
            [promoters[1], promoters[4]],
        )
        # The directory also keeps people met along the way, not linked to anything yet.
        add("Karim Benzema (rencontré au salon)", "Programmateur", "karim@example.org", "", ())
        add("Hélène Vasseur", "Presse locale", "helene@example.org", "06 01 02 03 04", ())
        # Venues that work with several organisers.
        venues[0].promoters.set([promoters[0], promoters[1]])
        venues[1].promoters.set([promoters[1]])
        venues[4].promoters.set([promoters[4], promoters[2]])

    def gigs(self, tenant, shows, promoters, venues, people):
        plan = [  # (days from today, show, promoter, venue, status, price)
            (-75, 0, 0, 0, "signed", "1200.00"),
            (-60, 1, 1, 1, "signed", "1800.00"),
            (-45, 2, 3, 5, "signed", "650.00"),
            (-30, 0, 4, 4, "signed", "1200.00"),
            (-18, 1, 0, 0, "signed", "1800.00"),
            (-9, 2, 2, 3, "signed", "650.00"),
            (3, 0, 1, 1, "signed", "1200.00"),
            (7, 1, 4, 4, "confirmed", "1800.00"),
            (12, 2, 3, 5, "confirmed", "650.00"),
            (15, 0, 5, 2, "cancelled", "1200.00"),
            (19, 1, 0, 0, "confirmed", "1800.00"),
            (26, 0, 2, 3, "option", "1200.00"),
            (33, 2, 1, 1, "option", "650.00"),
            (45, 1, 4, 4, "confirmed", "1800.00"),
            (60, 0, 0, 2, "option", "1250.00"),
        ]
        gigs = []
        for offset, s, p, v, status, price in plan:
            gig = Gig.objects.create(
                tenant=tenant,
                show=shows[s],
                promoter=promoters[p],
                venue=venues[v],
                date=day(offset),
                status="confirmed" if status == "signed" else status,  # signed in money()
                price=price,
                deposit_percent=D("30"),
                get_in_time=T(15, 0),
                soundcheck_time=T(17, 30),
                performance_time=T(21, 0) if s != 2 else T(16, 0),
                crew_headcount=shows[s].crew_size,
                option_expires_on=day(offset - 10) if status == "option" else None,
                deposit_due_on=day(offset - 30),
                balance_due_on=day(offset + 15),
                payment_method=Gig.PaymentMethod.TRANSFER,
                event_name="Festival d'été" if p == 1 else "",
            )
            roster = {
                0: ["Léa", "Marc", "Sofia", "Hugo"],
                1: ["Marc", "Sofia", "Léa", "Inès", "Paul"],
                2: ["Léa", "Sofia"],
            }[s]
            for name in roster:
                person = people[name]
                GigMember.objects.create(
                    tenant=tenant,
                    gig=gig,
                    person=person,
                    name=person.full_name,
                    role=person.role,
                    phone=person.phone,
                    email=person.email,
                )
            gigs.append(gig)
        return gigs

    def money(self, tenant, gigs):
        """Invoices for the dates that are behind us (some paid, one late, one half paid)."""
        owner = User.objects.get(email=OWNER_EMAIL)
        for gig in gigs[:6]:
            document_services.generate_contract_pdf(gig, owner)
            document_services.mark_contract_signed(gig)
        for index, gig in enumerate(gigs[:6]):
            deposit = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.DEPOSIT))
            balance = invoicing.issue_invoice(invoicing.create_invoice(gig, Invoice.Kind.BALANCE))
            if index <= 3:  # fully paid
                for invoice in (deposit, balance):
                    finance_services.record_payment(
                        invoice, finance_services.remaining_to_pay(invoice), gig.date, "transfer"
                    )
            elif index == 4:  # deposit paid, balance late
                finance_services.record_payment(
                    deposit,
                    finance_services.remaining_to_pay(deposit),
                    gig.date - datetime.timedelta(days=20),
                    "transfer",
                )
                Invoice.objects.filter(pk=balance.pk).update(due_date=day(-5))
            else:  # nothing yet, recent
                Invoice.objects.filter(pk__in=[deposit.pk, balance.pk]).update(due_date=day(10))
        # the next signed date: only its contract is signed
        document_services.generate_contract_pdf(gigs[6], owner)
        document_services.mark_contract_signed(gigs[6])

    def expenses(self, tenant, gigs, people):
        rows = [  # (gig index, category, label, amount, person, reimbursed)
            (0, "transport", "Essence (aller-retour Sète)", "64.20", None, False),
            (0, "technical", "Location sono d'appoint", "180.00", None, False),
            (1, "transport", "Train Léa Nîmes", "38.50", "Léa", True),
            (1, "lodging", "Hôtel Nîmes (2 chambres)", "176.00", "Paul", True),
            (2, "communication", "Affiches et flyers", "92.00", None, False),
            (3, "transport", "Péage A9", "27.40", "Marc", False),
            (3, "other", "Repas équipe", "86.00", "Sofia", False),
            (4, "lodging", "Hôtel Sète", "210.00", None, False),
            (4, "transport", "Essence camion", "58.30", "Hugo", False),
            (5, "other", "Café et goûter jeune public", "24.80", None, False),
            (6, "transport", "Location camionnette", "140.00", "Paul", False),
        ]
        for index, category, label, amount, person, reimbursed in rows:
            gig = gigs[index]
            Expense.objects.create(
                tenant=tenant,
                gig=gig,
                category=category,
                label=label,
                amount=amount,
                date=gig.date,
                person=people[person] if person else None,
                reimbursed_on=gig.date + datetime.timedelta(days=12) if reimbursed else None,
            )
        for gig_index, person, label, amount in (
            (6, "Hugo", "Gaffer et câbles", "34.90"),
            (5, "Léa", "Taxi retour", "22.00"),
        ):
            ExpenseClaim.objects.create(
                tenant=tenant,
                gig=gigs[gig_index],
                person=people[person],
                category="other",
                label=label,
                amount=amount,
                date=min(gigs[gig_index].date, day(0)),
            )

    def roadmaps(self, tenant, gigs, people):
        preparations = [
            (
                6,
                "Hôtel Le Mistral",
                "2 Place de la Comédie",
                "34000",
                "Montpellier",
                "Mme Garcia",
                "Réception",
                "04 67 11 22 33",
                "Chez Paul",
            ),
            (
                7,
                "Hôtel de la Plage",
                "Quai de Bosc",
                "34200",
                "Sète",
                "M. Roux",
                "Réception",
                "04 67 44 55 66",
                "Brasserie du Port",
            ),
            (
                10,
                "Hôtel des Arènes",
                "Boulevard des Arènes",
                "30000",
                "Nîmes",
                "Mme Blanc",
                "Accueil",
                "04 66 33 22 11",
                "Le Relais",
            ),
        ]
        for index, hotel, street, code, city, contact, role, phone, meal in preparations:
            gig = gigs[index]
            roadmap = roadmap_services.get_or_create_roadmap(gig)
            RoadmapSlot.objects.create(
                tenant=tenant, roadmap=roadmap, kind="meal", time=T(19, 0), label=meal
            )
            RoadmapSlot.objects.create(
                tenant=tenant,
                roadmap=roadmap,
                kind="departure",
                time=T(23, 30),
                label="Retour à l'hôtel",
            )
            lodging = Lodging.objects.create(
                tenant=tenant,
                roadmap=roadmap,
                name=hotel,
                address=street,
                postal_code=code,
                city=city,
                arrival_time=T(14, 0),
                notes="Petit-déjeuner de 7 h à 10 h.",
            )
            PlaceContact.objects.create(
                tenant=tenant, lodging=lodging, name=contact, role=role, phone=phone
            )
            dinner = Meal.objects.create(
                tenant=tenant,
                roadmap=roadmap,
                place=meal,
                time=T(19, 0),
                notes="Menu artistes réservé.",
            )
            PlaceContact.objects.create(
                tenant=tenant,
                meal=dinner,
                name="Patron du restaurant",
                role="Réservation",
                phone="04 67 00 11 22",
            )
            roadmap.notes = (
                "Merci d'arriver à l'heure pour les balances. Apportez vos pièces d'identité."
            )
            roadmap.save(update_fields=["notes"])
        roadmap_services.publish(roadmap_services.get_or_create_roadmap(gigs[6]))
        lea = people["Léa"]
        tenant_services.enable_team_space(lea)
        lea.refresh_from_db()
        return f"/equipe/{lea.access_token}/"
