#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')

# Force fresh import
for mod in list(sys.modules.keys()):
    if mod.startswith('app.'):
        del sys.modules[mod]

from app.core.permissions import expand_wildcard_permission, ALL_PERMISSIONS

print(f"Total permissions in system: {len(ALL_PERMISSIONS)}")
print(f"Sample: {list(ALL_PERMISSIONS)[:3]}")

result = expand_wildcard_permission('sinas.*:all')
print(f"\nResult for 'sinas.*:all': {len(result)} permissions")
if result:
    print("First 5:", list(result)[:5])
else:
    print("EMPTY RESULT - DEBUGGING...")

    # Manual test
    pattern = 'sinas.*:all'
    parts, scope = pattern.rsplit(':', 1)
    parts_list = parts.split('.')
    prefix_parts = parts_list[:-1]

    print(f"Pattern parts: {parts_list}")
    print(f"Prefix parts: {prefix_parts}")
    print(f"Scope: {scope}")

    for perm in list(ALL_PERMISSIONS)[:3]:
        print(f"\nTesting: {perm}")
        perm_parts, perm_scope = perm.rsplit(':', 1)
        perm_parts_list = perm_parts.split('.')
        print(f"  Parts: {perm_parts_list}, Scope: {perm_scope}")

        # Scope check
        scope_ok = not (scope != '*' and scope != 'all' and perm_scope != scope)
        print(f"  Scope OK: {scope_ok}")

        # Length check
        length_ok = len(perm_parts_list) >= len(prefix_parts)
        print(f"  Length OK: {length_ok}")

        # Pattern match
        if length_ok:
            matches = all(pp == pep for pp, pep in zip(prefix_parts, perm_parts_list))
            print(f"  Pattern matches: {matches}")
