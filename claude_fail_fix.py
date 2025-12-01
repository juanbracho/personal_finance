#!/usr/bin/env python3
"""
Claude Code Update Fix Script
Automates the steps to fix Claude Code auto-update failures
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description, shell=False):
    """Run a command and print its status"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Running: {command if isinstance(command, str) else ' '.join(command)}\n")

    try:
        if shell:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command, capture_output=True, text=True)

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"⚠️  {description} - FAILED (exit code: {result.returncode})")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_path_exists(path):
    """Check if a path exists"""
    return Path(path).expanduser().exists()


def main():
    print("="*60)
    print("🚀 Claude Code Update Fix Script")
    print("="*60)
    print("This script will attempt to fix Claude Code update issues")
    print("by clearing caches and reinstalling.\n")

    # Get user confirmation
    response = input("Do you want to proceed? (y/n): ").strip().lower()
    if response != 'y':
        print("Aborted by user.")
        sys.exit(0)

    # Step 1: Clear Claude Code cache directories FIRST
    possible_cache_paths = [
        Path.home() / ".config" / "claude-code",
        Path.home() / "Library" / "Application Support" / "claude-code",
        Path.home() / ".claude",
    ]

    for cache_path in possible_cache_paths:
        if check_path_exists(cache_path):
            print(f"\n{'='*60}")
            print(f"🗑️  Found Claude Code directory at: {cache_path}")
            print(f"{'='*60}")
            confirm = input("Delete this directory? (y/n): ").strip().lower()
            if confirm == 'y':
                run_command(
                    f"rm -rf '{cache_path}'",
                    f"Removing {cache_path}",
                    shell=True
                )
            else:
                print(f"Skipped clearing {cache_path}")

    # Step 2: Remove npm global installation directory
    npm_global_paths = [
        Path.home() / ".npm-global" / "lib" / "node_modules" / "@anthropic-ai" / "claude-code",
        Path("/usr/local/lib/node_modules/@anthropic-ai/claude-code"),
    ]

    for npm_path in npm_global_paths:
        if check_path_exists(npm_path):
            print(f"\n{'='*60}")
            print(f"🗑️  Found npm installation at: {npm_path}")
            print(f"{'='*60}")
            confirm = input("Delete this directory? (y/n): ").strip().lower()
            if confirm == 'y':
                run_command(
                    f"rm -rf '{npm_path}'",
                    f"Removing npm installation at {npm_path}",
                    shell=True
                )
            else:
                print(f"Skipped removing {npm_path}")

    # Step 3: Clear npm cache
    run_command(
        ["npm", "cache", "clean", "--force"],
        "Clearing npm cache"
    )

    # Step 4: Update Claude Code
    run_command(
        ["npm", "i", "-g", "@anthropic-ai/claude-code"],
        "Updating Claude Code via npm"
    )

    # Step 5: Verify installation
    print("\n" + "="*60)
    print("🏥 Verification")
    print("="*60)
    run_command(
        ["claude", "--version"],
        "Checking Claude Code version"
    )

    # Alternative solution suggestion
    print("\n" + "="*60)
    print("💡 Alternative Solution")
    print("="*60)
    print("If the update still fails, consider using the native installer:")
    print("  curl -fsSL https://claude.ai/install.sh | bash")
    print("\nOr migrate to the native installer:")
    print("  claude migrate-installer")
    print("="*60)

    print("\n✨ Script completed!")


if __name__ == "__main__":
    main()
