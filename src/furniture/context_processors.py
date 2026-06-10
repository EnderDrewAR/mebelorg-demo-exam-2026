from .models import Role


def access_flags(request):
    role_code = ""
    if request.user.is_authenticated:
        role_code = request.user.role_code
    return {
        "role_code": role_code,
        "is_manager": role_code == Role.Codes.MANAGER,
        "is_app_admin": role_code == Role.Codes.ADMIN,
        "can_manage_catalog": role_code in {
            Role.Codes.MANAGER,
            Role.Codes.ADMIN,
        },
    }

