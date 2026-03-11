
# Re-export all decorators for backward compatibility
from apps.users.decorators import (
    get_client_ip,
    get_current_user,
    pseudonymous_user_required,
    admin_required,
    analyst_required,
    client_required,
)

# Legacy alias
require_auth = pseudonymous_user_required
require_admin = admin_required
require_analyst = analyst_required
