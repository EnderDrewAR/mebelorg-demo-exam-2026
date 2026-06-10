from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def roles_required(*allowed_roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.user.role_code not in allowed_roles:
                messages.error(
                    request,
                    "У вашей учетной записи нет прав для выполнения этого действия.",
                )
                return redirect("product_list")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator

