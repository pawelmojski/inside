#!/usr/bin/env python3
"""
Initialize Inside Tower database with schema and default admin user.

This script is used during Tower installation to create the database schema
and set up the default admin user.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("=" * 60)
    print("Inside Tower - Database Initialization")
    print("=" * 60)
    print()
    
    # Get admin password from environment variable
    admin_password = os.environ.get('ADMIN_PASSWORD', '')
    
    try:
        from src.core.database import Base, engine, SessionLocal, User
        from werkzeug.security import generate_password_hash
        
        # Create all tables from SQLAlchemy models
        print("Creating database schema...")
        Base.metadata.create_all(bind=engine)
        print("✓ Database schema created successfully")
        print()
        
        # Check if admin user already exists
        db = SessionLocal()
        try:
            existing_admin = db.query(User).filter(User.username == 'admin').first()
            if existing_admin:
                print("⚠ Admin user already exists, skipping creation")
                return 0
            
            # Create default admin user
            print("Creating default admin user...")
            
            admin = User(
                username='admin',
                email='admin@localhost',
                full_name='System Administrator',
                is_active=True,
                permission_level=0  # 0 = SuperAdmin
            )
            
            # Set password hash if ADMIN_PASSWORD is provided
            if admin_password:
                admin.password_hash = generate_password_hash(
                    admin_password, 
                    method='pbkdf2:sha256', 
                    salt_length=16
                )
                print(f"✓ Admin password set from ADMIN_PASSWORD environment variable")
            else:
                print("⚠ WARNING: ADMIN_PASSWORD not set - admin will have no password!")
                print("  You must set password manually using the web interface")
            
            db.add(admin)
            db.commit()
            
            print("✓ Default admin user created")
            print()
            print("Default credentials:")
            print("  Username: admin")
            if admin_password:
                print(f"  Password: {admin_password}")
            else:
                print("  Password: NOT SET - configure manually!")
            print()
            
            return 0
            
        finally:
            db.close()
            
    except ImportError as e:
        print(f"✗ ERROR: Failed to import required modules: {e}")
        print()
        print("Make sure you're running this from the Tower installation directory")
        print("and that the virtual environment is activated.")
        return 1
        
    except Exception as e:
        print(f"✗ ERROR: Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
