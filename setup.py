"""
Setup script with post-install hook for Playwright Chromium installation.
This runs during `pip install .` to ensure browser binaries are available.
"""
import subprocess
import sys
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop


def install_playwright_chromium():
    """Install Playwright Chromium browser."""
    print("Installing Playwright Chromium browser...")
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True
        )
        print("Playwright Chromium installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Playwright Chromium installation failed: {e}")
    except Exception as e:
        print(f"Warning: Could not install Playwright Chromium: {e}")


class PostInstallCommand(install):
    """Post-installation command to install Playwright browsers."""
    def run(self):
        install.run(self)
        install_playwright_chromium()


class PostDevelopCommand(develop):
    """Post-develop command to install Playwright browsers."""
    def run(self):
        develop.run(self)
        install_playwright_chromium()


# Minimal setup - main config is in pyproject.toml
setup(
    cmdclass={
        'install': PostInstallCommand,
        'develop': PostDevelopCommand,
    },
)
