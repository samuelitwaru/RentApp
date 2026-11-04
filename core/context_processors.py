from .models import LandlordProfile


def landlord_profile(request):
    return {"landlord_profile": LandlordProfile.get_solo()}
