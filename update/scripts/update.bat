@echo off
setlocal EnableDelayedExpansion
title Medical Equipment System Update

cd /d "%~dp0\..\.."

set PYTHON=%CD%\venv\Scripts\python.exe
set LOG=update\logs\update.log

if not exist "update\logs" (
    mkdir "update\logs"
)

echo.>>"%LOG%"
echo =====================================================>>"%LOG%"
echo [%date% %time%] Update Started>>"%LOG%"
echo =====================================================>>"%LOG%"

echo.
echo ========================================
echo Medical Equipment System Update
echo ========================================
echo.

:: --------------------------------------------------
:: Backup Database
:: --------------------------------------------------

set BACKUP_DIR=update\backups

if not exist "%BACKUP_DIR%" (
    mkdir "%BACKUP_DIR%"
)

set BACKUP_FILE=%BACKUP_DIR%\backup_%date:~-4%-%date:~3,2%-%date:~0,2%_%time:~0,2%-%time:~3,2%.sqlite3
set BACKUP_FILE=%BACKUP_FILE: =0%

echo Creating database backup...
echo Creating database backup...>>"%LOG%"

copy "db.sqlite3" "%BACKUP_FILE%" >nul

if errorlevel 1 (
    echo ERROR: Backup failed>>"%LOG%"
    goto ERROR
)

echo Backup completed.>>"%LOG%"

:: --------------------------------------------------
:: Stop Service
:: --------------------------------------------------

echo Stopping service...
echo Stopping service...>>"%LOG%"

net stop "MedicalEquipmentSystem" >>"%LOG%" 2>&1

timeout /t 3 /nobreak >nul

:: --------------------------------------------------
:: Git Update
:: --------------------------------------------------

echo Updating from GitHub...
echo Updating from GitHub...>>"%LOG%"

git config --global --add safe.directory "%CD%" >>"%LOG%" 2>&1

git fetch origin >>"%LOG%" 2>&1

if errorlevel 1 (
    echo ERROR: Git Fetch failed>>"%LOG%"
    goto ERROR
)

git pull origin main >>"%LOG%" 2>&1

if errorlevel 1 (
    echo ERROR: Git Pull failed>>"%LOG%"
    goto ERROR
)

for /f %%i in ('git rev-parse HEAD') do set COMMIT=%%i

echo Installed Commit: !COMMIT!>>"%LOG%"

:: --------------------------------------------------
:: Install Requirements
:: --------------------------------------------------

if exist requirements.txt (

    echo Installing requirements...
    echo Installing requirements...>>"%LOG%"

    "%PYTHON%" -m pip install -r requirements.txt >>"%LOG%" 2>&1

    if errorlevel 1 (
        echo ERROR: Requirements installation failed>>"%LOG%"
        goto ERROR
    )
)

:: --------------------------------------------------
:: Database Migration
:: --------------------------------------------------

echo Running migrations...
echo Running migrations...>>"%LOG%"

"%PYTHON%" manage.py migrate >>"%LOG%" 2>&1

if errorlevel 1 (
    echo ERROR: Migration failed>>"%LOG%"
    goto ERROR
)

:: --------------------------------------------------
:: Collect Static Files
:: --------------------------------------------------

echo Collecting static files...
echo Collecting static files...>>"%LOG%"

"%PYTHON%" manage.py collectstatic --noinput >>"%LOG%" 2>&1

if errorlevel 1 (
    echo ERROR: Collectstatic failed>>"%LOG%"
    goto ERROR
)

:: --------------------------------------------------
:: Django Check
:: --------------------------------------------------

echo Checking Django project...
echo Checking Django project...>>"%LOG%"

"%PYTHON%" manage.py check >>"%LOG%" 2>&1

if errorlevel 1 (
    echo ERROR: Django check failed>>"%LOG%"
    goto ERROR
)

:: --------------------------------------------------
:: Update Database Status
:: --------------------------------------------------

"%PYTHON%" manage.py shell -c "from devices.models import SystemUpdate; from django.utils import timezone; u=SystemUpdate.objects.filter(status='RUNNING').order_by('-id').first(); u.status='SUCCESS'; u.local_commit='!COMMIT!'; u.finished_at=timezone.now(); u.save() if u else None"

:: --------------------------------------------------
:: Restart Service
:: --------------------------------------------------

echo Starting service...
echo Starting service...>>"%LOG%"

net start "MedicalEquipmentSystem" >>"%LOG%" 2>&1

if errorlevel 1 (
    echo ERROR: Service failed to start>>"%LOG%"
    exit /b 1
)

echo.
echo ========================================
echo UPDATE COMPLETED SUCCESSFULLY
echo ========================================

echo Update completed successfully.>>"%LOG%"
echo Installed Commit: !COMMIT!>>"%LOG%"
echo [%date% %time%] Finished>>"%LOG%"

exit /b 0

:ERROR

echo.
echo Update failed.
echo Restarting service...

net start "MedicalEquipmentSystem" >>"%LOG%" 2>&1

"%PYTHON%" manage.py shell -c "from devices.models import SystemUpdate; from django.utils import timezone; u=SystemUpdate.objects.filter(status='RUNNING').order_by('-id').first(); u.status='FAILED'; u.finished_at=timezone.now(); u.save() if u else None"

echo ERROR: Update failed.>>"%LOG%"
echo [%date% %time%] Finished with ERROR>>"%LOG%"

exit /b 1