"""
Migration script to convert plaintext emails to hashed emails.
Run this AFTER applying Django migrations for the new email_hash field.

Usage:
    python manage.py shell < scripts/migrate_email_to_hash.py
    
Or run directly:
    python scripts/migrate_email_to_hash.py
"""

import os
import sys
import django

# Setup Django if running standalone
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shadowiq.settings')
    django.setup()

from core.models import PseudonymousUser, hash_email


def migrate_emails_to_hash():
    """
    Migrate existing plaintext emails to hashed format.
    This is a one-way operation - emails cannot be recovered after hashing.
    """
    users_with_email = PseudonymousUser.objects.filter(
        email__isnull=False
    ).exclude(email='')
    
    total = users_with_email.count()
    migrated = 0
    skipped = 0
    errors = 0
    
    print(f"Found {total} users with plaintext emails to migrate.")
    print("-" * 50)
    
    for user in users_with_email:
        try:
            if user.email_hash:
                print(f"SKIP: {user.alias} - already has email_hash")
                skipped += 1
                continue
            
            # Hash the email
            email_hash = hash_email(user.email)
            
            # Check for duplicates
            existing = PseudonymousUser.objects.filter(email_hash=email_hash).exclude(id=user.id).first()
            if existing:
                print(f"WARNING: {user.alias} - duplicate email hash (same as {existing.alias})")
                errors += 1
                continue
            
            # Update user
            user.email_hash = email_hash
            user.email = None  # Clear plaintext email
            user.save(update_fields=['email_hash', 'email'])
            
            print(f"OK: {user.alias} - email migrated to hash")
            migrated += 1
            
        except Exception as e:
            print(f"ERROR: {user.alias} - {str(e)}")
            errors += 1
    
    print("-" * 50)
    print(f"Migration complete:")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped:  {skipped}")
    print(f"  Errors:   {errors}")
    print(f"  Total:    {total}")


if __name__ == "__main__":
    print("=" * 50)
    print("EMAIL TO HASH MIGRATION SCRIPT")
    print("=" * 50)
    print()
    print("WARNING: This will permanently hash all plaintext emails.")
    print("Make sure you have a database backup before proceeding.")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response == 'yes':
        migrate_emails_to_hash()
    else:
        print("Migration cancelled.")
