#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path

def switch_environment(env_type):
    """
    Switch between different environments by creating a symlink to the appropriate .env file
    
    Args:
        env_type: 'dev', 'prod', or 'safari'
    """
    base_dir = Path(__file__).resolve().parent.parent
    envs_dir = base_dir / "envs"
    
    # Map environment types to their files
    env_files = {
        'dev': envs_dir / "dev.mac.env",
        'prod': envs_dir / "prod.mac.env", 
        'safari': envs_dir / "dev.safari.env"
    }
    
    if env_type not in env_files:
        print(f"Error: Unknown environment '{env_type}'. Use 'dev', 'prod', or 'safari'.")
        return False
    
    env_file = env_files[env_type]
    env_link = base_dir / ".env"
    
    # Remove existing symlink if it exists
    if env_link.exists() or env_link.is_symlink():
        os.unlink(env_link)
    
    # Create new symlink
    os.symlink(env_file, env_link)
    
    print(f"Switched to {env_type} environment. Using {env_file.name}")
    
    # Print database info based on environment
    if env_type in ['dev', 'safari']:
        print("Using SQLite database")
    else:
        print("Using PostgreSQL database - make sure PostgreSQL is running")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Switch between development and production environments")
    parser.add_argument("environment", choices=["dev", "prod", "safari"], 
                        help="Environment to switch to (dev, prod, or safari)")
    
    args = parser.parse_args()
    switch_environment(args.environment) 