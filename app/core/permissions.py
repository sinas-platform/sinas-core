"""Permission management utilities."""
from pathlib import Path
from typing import Set, Dict, List


def load_permissions() -> Set[str]:
    """Load all valid permission strings from permissions.txt file."""
    permissions_file = Path(__file__).parent / "permissions.txt"
    permissions = set()

    with open(permissions_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                permissions.add(line)

    return permissions


# Cache of all valid permissions
ALL_PERMISSIONS: Set[str] = load_permissions()


def expand_wildcard_permission(permission: str) -> Set[str]:
    """
    Expand a wildcard permission to all matching concrete permissions.

    Supports:
    - service.*:scope -> all permissions for that service and scope (matches any remaining parts)
    - service.resource.*:scope -> all actions for that resource and scope
    - scope can also be wildcard (*) or 'all' to match all scopes

    Args:
        permission: Permission string with potential wildcards

    Returns:
        Set of concrete permissions matching the wildcard
    """
    if '*' not in permission:
        return {permission} if permission in ALL_PERMISSIONS else set()

    matching_permissions = set()

    # Parse the wildcard pattern
    try:
        parts, scope = permission.rsplit(':', 1)
        parts_list = parts.split('.')

        for perm in ALL_PERMISSIONS:
            try:
                perm_parts, perm_scope = perm.rsplit(':', 1)
            except ValueError:
                # Skip permissions without scope
                continue

            perm_parts_list = perm_parts.split('.')

            # Check scope - if scope is wildcard or 'all', match any scope
            if scope != '*' and scope != 'all' and perm_scope != scope:
                continue

            # Check if pattern matches
            # If pattern ends with wildcard, only check the parts before it
            if parts_list[-1] == '*':
                # Pattern like "sinas.*" should match any permission starting with "sinas."
                # Compare only the non-wildcard parts
                prefix_parts = parts_list[:-1]
                if len(perm_parts_list) < len(prefix_parts):
                    continue

                matches = True
                for pattern_part, perm_part in zip(prefix_parts, perm_parts_list):
                    if pattern_part != perm_part:
                        matches = False
                        break

                if matches:
                    matching_permissions.add(perm)
            else:
                # Exact length match required
                if len(parts_list) != len(perm_parts_list):
                    continue

                matches = True
                for pattern_part, perm_part in zip(parts_list, perm_parts_list):
                    if pattern_part != '*' and pattern_part != perm_part:
                        matches = False
                        break

                if matches:
                    matching_permissions.add(perm)

    except ValueError as e:
        # Pattern doesn't have scope separator
        return set()

    return matching_permissions


def expand_permission_dict(permissions: Dict[str, bool]) -> Dict[str, bool]:
    """
    Expand a permission dictionary containing wildcards to concrete permissions.

    Args:
        permissions: Dict mapping permission strings to boolean values

    Returns:
        Dict with all wildcards expanded to concrete permissions
    """
    expanded = {}

    for perm, value in permissions.items():
        if '*' in perm:
            # Expand wildcard
            concrete_perms = expand_wildcard_permission(perm)
            for concrete_perm in concrete_perms:
                # Later definitions override earlier ones
                expanded[concrete_perm] = value
        else:
            # Direct permission
            if perm in ALL_PERMISSIONS:
                expanded[perm] = value

    return expanded


def check_permission(user_permissions: Dict[str, bool], required_permission: str) -> bool:
    """
    Check if user has a required permission, considering wildcards.

    Args:
        user_permissions: Dict mapping permission strings to boolean values
        required_permission: The permission being checked (concrete, no wildcards)

    Returns:
        True if user has the permission, False otherwise
    """
    # Check for exact match first
    if required_permission in user_permissions:
        return user_permissions[required_permission]

    # Check for wildcard matches
    try:
        parts, scope = required_permission.rsplit(':', 1)
        parts_list = parts.split('.')

        # Check increasingly broader wildcards
        # e.g., for "sinas.chats.create:own", check:
        # 1. "sinas.chats.*:own"
        # 2. "sinas.*:own"

        if len(parts_list) >= 3:
            # Check service.resource.*:scope
            wildcard = f"{parts_list[0]}.{parts_list[1]}.*:{scope}"
            if wildcard in user_permissions and user_permissions[wildcard]:
                return True

        if len(parts_list) >= 2:
            # Check service.*:scope
            wildcard = f"{parts_list[0]}.*:{scope}"
            if wildcard in user_permissions and user_permissions[wildcard]:
                return True

    except (ValueError, IndexError):
        pass

    return False


def validate_permission_subset(
    subset_perms: Dict[str, bool],
    superset_perms: Dict[str, bool]
) -> tuple[bool, List[str]]:
    """
    Validate that subset permissions are contained within superset permissions.

    Used for API key creation - ensures API keys can't have more permissions
    than the user's group permissions.

    Args:
        subset_perms: Permissions to validate
        superset_perms: Permissions that must contain the subset

    Returns:
        Tuple of (is_valid, list_of_violations)
    """
    # Expand wildcards in both
    subset_expanded = expand_permission_dict(subset_perms)
    superset_expanded = expand_permission_dict(superset_perms)

    violations = []

    for perm, value in subset_expanded.items():
        if value:  # Only check permissions that are granted (True)
            # Check if superset has this permission granted
            superset_value = superset_expanded.get(perm, False)
            if not superset_value:
                violations.append(perm)

    return len(violations) == 0, violations


# Default group permissions
DEFAULT_GROUP_PERMISSIONS = {
    "GuestUsers": {
        "sinas.*:own": False,  # No access by default
        "sinas.users.read:own": True,
        "sinas.users.update:own": True,
    },
    "Users": {
        # Chats
        "sinas.chats.create:own": True,
        "sinas.chats.read:own": True,
        "sinas.chats.read:group": True,
        "sinas.chats.update:own": True,
        "sinas.chats.delete:own": True,

        # Messages
        "sinas.messages.create:own": True,
        "sinas.messages.read:own": True,
        "sinas.messages.read:group": True,

        # Assistants
        "sinas.assistants.create:own": True,
        "sinas.assistants.read:own": True,
        "sinas.assistants.update:own": True,
        "sinas.assistants.delete:own": True,

        # Memories
        "sinas.memories.create:own": True,
        "sinas.memories.read:own": True,
        "sinas.memories.update:own": True,
        "sinas.memories.delete:own": True,

        # Functions
        "sinas.functions.create:own": True,
        "sinas.functions.read:own": True,
        "sinas.functions.update:own": True,
        "sinas.functions.delete:own": True,
        "sinas.functions.execute:own": True,

        # Webhooks
        "sinas.webhooks.create:own": True,
        "sinas.webhooks.read:own": True,
        "sinas.webhooks.update:own": True,
        "sinas.webhooks.delete:own": True,

        # Schedules
        "sinas.schedules.create:own": True,
        "sinas.schedules.read:own": True,
        "sinas.schedules.update:own": True,
        "sinas.schedules.delete:own": True,

        # Executions
        "sinas.executions.read:own": True,

        # Packages
        "sinas.packages.install:own": True,
        "sinas.packages.read:own": True,
        "sinas.packages.delete:own": True,

        # Users
        "sinas.users.read:own": True,
        "sinas.users.update:own": True,

        # API Keys
        "sinas.apikeys.create:own": True,
        "sinas.apikeys.read:own": True,
        "sinas.apikeys.update:own": True,
        "sinas.apikeys.delete:own": True,
    },
    "Admins": {
        "sinas.*:all": True,  # Full access to everything
    }
}
