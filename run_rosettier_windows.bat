@echo off
setlocal

echo Starting Rosettier Streamlit app...
echo Assumes your conda environment is already activated.
echo If launch fails, run: python -m pip install --no-build-isolation -e ".[app]"

python -m streamlit run src\rosettier_app\app.py
