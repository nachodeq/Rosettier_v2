#!/usr/bin/env bash

set -euo pipefail

echo "Starting Rosettier Streamlit app..."
echo "Assuming your conda environment is already activated."
echo "If this fails, try: python -m pip install --no-build-isolation -e \".[app]\""

python -m streamlit run src/rosettier_app/app.py
