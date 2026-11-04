from functools import wraps

from django_ratelimit.decorators import ratelimit


def public_view(rate="30/h"):
    """Rate-limit a public, no-login view per IP and set privacy-conscious headers."""

    def decorator(view_func):
        limited = ratelimit(key="ip", rate=rate, block=True)(view_func)

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = limited(request, *args, **kwargs)
            response["X-Robots-Tag"] = "noindex, nofollow"
            # "no-referrer" (rather than "same-origin") would cause browsers to send
            # Origin: null on same-origin POST form submissions from this page (per the
            # Fetch spec's Origin-header algorithm), which Django's CSRF middleware then
            # rejects. "same-origin" still fully blocks the Referer header from leaking
            # this page's URL/token to any external site.
            response["Referrer-Policy"] = "same-origin"
            response["Cache-Control"] = "no-store"
            return response

        return wrapper

    return decorator
