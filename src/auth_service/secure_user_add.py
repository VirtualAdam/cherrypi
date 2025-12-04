#!/usr/bin/env python3
"""
CherryPi Auth Service - Secure User Provisioning CLI

This script allows adding users to the encrypted user database.
SECURITY: This script ONLY runs from a physical console (keyboard/monitor).
It will refuse to run over SSH connections.

Usage (from physical console on Raspberry Pi):
    sudo python3 secure_user_add.py
"""

import getpass
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from user_db import UserDatabase


# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def check_physical_console():
    """
    Verify we're running on a physical console, not over SSH.
    Returns True if physical, False if remote.
    """
    # Check for SSH environment variables
    ssh_indicators = ['SSH_CLIENT', 'SSH_TTY', 'SSH_CONNECTION']
    
    for var in ssh_indicators:
        if os.environ.get(var):
            return False
    
    # Check if we're in a TTY
    if not sys.stdin.isatty():
        return False
    
    # Check if DISPLAY is set (could be remote X session)
    # But allow if it's :0 (local display)
    display = os.environ.get('DISPLAY', '')
    if display and not display.startswith(':'):
        return False
    
    return True


def check_root():
    """Check if running as root."""
    return os.geteuid() == 0


def get_valid_input(prompt, validator=None, error_msg="Invalid input"):
    """Get validated input from user."""
    while True:
        value = input(prompt).strip()
        if validator is None or validator(value):
            return value
        print_error(error_msg)


def get_password():
    """Get and confirm password from user."""
    while True:
        password = getpass.getpass("Enter password: ")
        if len(password) < 8:
            print_error("Password must be at least 8 characters")
            continue
        
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print_error("Passwords do not match")
            continue
        
        return password


def select_role():
    """Let user select a role."""
    print("\nAvailable roles:")
    print("  1. admin  - Full access, can create users and magic QR codes")
    print("  2. user   - Can control and edit switches")
    print("  3. guest  - Can only view and control switches (read-only for config)")
    
    while True:
        choice = input("\nSelect role [1-3]: ").strip()
        if choice == '1':
            return 'admin'
        elif choice == '2':
            return 'user'
        elif choice == '3':
            return 'guest'
        else:
            print_error("Please enter 1, 2, or 3")


def add_user_interactive(db: UserDatabase):
    """Interactive user creation flow."""
    print(f"\n{Colors.BOLD}=== Add New User ==={Colors.END}\n")
    
    # Get username
    username = get_valid_input(
        "Enter username: ",
        lambda x: len(x) >= 3 and x.isalnum(),
        "Username must be at least 3 alphanumeric characters"
    )
    
    # Check if user exists
    if db.get_user_by_username(username):
        print_error(f"User '{username}' already exists")
        return False
    
    # Get password
    password = get_password()
    
    # Get role
    role = select_role()
    
    # Confirm
    print(f"\n{Colors.BOLD}Confirm user creation:{Colors.END}")
    print(f"  Username: {username}")
    print(f"  Role: {role}")
    
    confirm = input("\nCreate this user? [y/N]: ").strip().lower()
    if confirm != 'y':
        print_warning("User creation cancelled")
        return False
    
    # Create user
    try:
        user = db.add_user(username, password, role, created_by='physical_console')
        print_success(f"User '{username}' created successfully!")
        print_info("Database encrypted and saved.")
        return True
    except Exception as e:
        print_error(f"Failed to create user: {e}")
        return False


def list_users_interactive(db: UserDatabase):
    """List all users."""
    print(f"\n{Colors.BOLD}=== Current Users ==={Colors.END}\n")
    
    users = db.list_users()
    if not users:
        print_info("No users in database")
        return
    
    print(f"{'Username':<20} {'Role':<10} {'Created':<20}")
    print("-" * 50)
    for user in users:
        created = user.get('created_at', 'Unknown')[:19]
        print(f"{user['username']:<20} {user['role']:<10} {created:<20}")


def delete_user_interactive(db: UserDatabase):
    """Delete a user interactively."""
    print(f"\n{Colors.BOLD}=== Delete User ==={Colors.END}\n")
    
    users = db.list_users()
    if not users:
        print_info("No users in database")
        return False
    
    # Show users
    list_users_interactive(db)
    
    # Get username to delete
    username = input("\nEnter username to delete (or 'cancel'): ").strip()
    if username.lower() == 'cancel':
        return False
    
    user = db.get_user_by_username(username)
    if not user:
        print_error(f"User '{username}' not found")
        return False
    
    # Prevent deleting last admin
    if user['role'] == 'admin':
        admin_count = sum(1 for u in users if u['role'] == 'admin')
        if admin_count <= 1:
            print_error("Cannot delete the last admin user")
            return False
    
    # Confirm
    confirm = input(f"Delete user '{username}'? [y/N]: ").strip().lower()
    if confirm != 'y':
        print_warning("Deletion cancelled")
        return False
    
    if db.delete_user(user['id']):
        print_success(f"User '{username}' deleted")
        return True
    else:
        print_error("Failed to delete user")
        return False


def main_menu(db: UserDatabase):
    """Main interactive menu."""
    while True:
        print(f"\n{Colors.BOLD}=== CherryPi User Management ==={Colors.END}")
        print(f"Database: {db.db_path}")
        print(f"Users: {db.user_count()}")
        print()
        print("  1. Add user")
        print("  2. List users")
        print("  3. Delete user")
        print("  4. Exit")
        
        choice = input("\nSelect option [1-4]: ").strip()
        
        if choice == '1':
            add_user_interactive(db)
        elif choice == '2':
            list_users_interactive(db)
        elif choice == '3':
            delete_user_interactive(db)
        elif choice == '4':
            print_info("Goodbye!")
            break
        else:
            print_error("Invalid option")


def main():
    print(f"\n{Colors.BOLD}╔════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}║  CherryPi Secure User Provisioning     ║{Colors.END}")
    print(f"{Colors.BOLD}╚════════════════════════════════════════╝{Colors.END}\n")
    
    # Security check 1: Physical console
    print("Checking environment...", end=" ")
    if not check_physical_console():
        print()
        print_error("SECURITY ERROR: Remote connection detected!")
        print_error("This utility can ONLY be run from a physical console.")
        print_error("Please connect a keyboard and monitor to the Raspberry Pi.")
        sys.exit(1)
    print_success("Physical Console Detected")
    
    # Security check 2: Root access (optional, but recommended for file access)
    if not check_root():
        print_warning("Running without root privileges.")
        print_warning("You may have permission issues with the database file.")
        print()
    
    # Get configuration from environment or use defaults
    data_dir = os.environ.get('AUTH_DATA_DIR', '/data')
    db_key = os.environ.get('AUTH_DB_KEY')
    
    # If no key in environment, prompt for it
    if not db_key:
        print_info("AUTH_DB_KEY not set in environment.")
        print_info("You can set it with: export AUTH_DB_KEY='your-secret-key'")
        print()
        db_key = getpass.getpass("Enter database encryption key: ")
        if not db_key:
            print_error("Encryption key is required")
            sys.exit(1)
    
    # Ensure data directory exists
    db_path = os.path.join(data_dir, 'users.enc')
    os.makedirs(data_dir, exist_ok=True)
    
    # Initialize database
    try:
        print(f"\nInitializing database at {db_path}...")
        db = UserDatabase(db_path, db_key)
        print_success("Database ready")
    except ValueError as e:
        print_error(f"Database error: {e}")
        print_error("If the key is wrong, you cannot recover the existing database.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to initialize database: {e}")
        sys.exit(1)
    
    # Check if this is first run (no admin exists)
    if not db.has_admin():
        print()
        print_warning("No admin user exists!")
        print_info("You must create an admin user to use CherryPi.")
        print()
        
        if not add_user_interactive(db):
            print_error("Admin user creation failed or cancelled")
            print_error("CherryPi requires at least one admin user")
            sys.exit(1)
    
    # Run main menu
    main_menu(db)


if __name__ == '__main__':
    main()
