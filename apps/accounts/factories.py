import factory

from .models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "un-mot-de-passe-solide")
        if create:
            self.save()
