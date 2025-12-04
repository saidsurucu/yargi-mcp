#!/bin/bash
# Post-install script for FastMCP Cloud
# Installs Chromium browser for Playwright

echo "Installing Playwright Chromium browser..."
playwright install chromium
echo "Chromium installation complete."
