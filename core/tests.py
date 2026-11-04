from django.test import TestCase

from core.models import LandlordProfile, Property, Unit


class LandlordProfileTests(TestCase):
    def test_singleton_enforced(self):
        LandlordProfile.objects.create(business_name="First")
        LandlordProfile.objects.create(business_name="Second")
        self.assertEqual(LandlordProfile.objects.count(), 1)
        self.assertEqual(LandlordProfile.get_solo().business_name, "Second")

    def test_get_solo_creates_if_missing(self):
        self.assertEqual(LandlordProfile.objects.count(), 0)
        profile = LandlordProfile.get_solo()
        self.assertEqual(LandlordProfile.objects.count(), 1)
        self.assertTrue(profile.business_name)


class UnitTests(TestCase):
    def test_unit_unique_per_property(self):
        prop = Property.objects.create(name="Test Property")
        Unit.objects.create(property=prop, name="A1", monthly_rent=100_000)
        with self.assertRaises(Exception):
            Unit.objects.create(property=prop, name="A1", monthly_rent=200_000)
