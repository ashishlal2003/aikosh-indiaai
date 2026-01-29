@echo off
echo ========================================
echo MSME OCR Feature Test Runner
echo ========================================
echo.

echo Running document processor tests...
echo ----------------------------------------
venv\Scripts\python.exe -m pytest tests/test_document_processor.py -v --tb=short

echo.
echo ========================================
echo Test run complete!
echo ========================================
pause
