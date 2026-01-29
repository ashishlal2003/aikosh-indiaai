@echo off
echo ========================================
echo MSME OCR Feature Demo
echo ========================================
echo.

echo Running OCR demo...
echo ----------------------------------------
venv\Scripts\python.exe demo_ocr.py

echo.
echo.
echo Running integration example...
echo ----------------------------------------
venv\Scripts\python.exe example_integration.py

echo.
echo ========================================
echo Demo complete!
echo ========================================
pause
