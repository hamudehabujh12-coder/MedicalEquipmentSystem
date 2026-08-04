@echo off
title Medical Equipment System Update

cd /d "%~dp0\..\.."

set PYTHON=venv\Scripts\python.exe

echo ========================================
echo Medical Equipment System Update
echo ========================================
echo.

:: --------------------------------------------------
:: Create Backup
:: --------------------------------------------------

set BACKUP_DIR=update\backups

if not exist "%BACKUP_DIR%" (
    mkdir "%BACKUP_DIR%"
)

set BACKUP_FILE=%BACKUP_DIR%\update_backup_%date:~-4%-%date:~3,2%-%date:~0,2%_%time:~0,2%-%time:~3,2%.sqlite3

echo Creating database backup...

copy "db.sqlite3" "%BACKUP_FILE%" > nul

if exist "%BACKUP_FILE%" (
    echo Backup created successfully.
    echo %BACKUP_FILE%
) else (
    echo Backup failed!
    pause
    exit /b 1
)

echo.


:: --------------------------------------------------
:: Download latest version from GitHub
:: --------------------------------------------------

echo ========================================
echo Downloading latest version from GitHub...
echo ========================================

git fetch origin

if errorlevel 1 (
    echo.
    echo Git fetch failed.
    pause
    exit /b 1
)


git pull origin main

if errorlevel 1 (
    echo.
    echo Git update failed.
    pause
    exit /b 1
)

echo Git update completed successfully.
echo.


:: --------------------------------------------------
:: Install Requirements
:: --------------------------------------------------

echo ========================================
echo Installing requirements...
echo ========================================

%PYTHON% -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Requirements installation failed.
    pause
    exit /b 1
)

echo Requirements installed successfully.
echo.


:: --------------------------------------------------
:: Database Migration
:: --------------------------------------------------

echo ========================================
echo Running database migrations...
echo ========================================

%PYTHON% manage.py migrate

if errorlevel 1 (
    echo.
    echo Database migration failed.
    pause
    exit /b 1
)

echo Database migration completed successfully.
echo.


:: --------------------------------------------------
:: Collect Static Files
:: --------------------------------------------------

echo ========================================
echo Collecting static files...
echo ========================================

%PYTHON% manage.py collectstatic --noinput

if errorlevel 1 (
    echo.
    echo Collectstatic failed.
    pause
    exit /b 1
)

echo Static files updated successfully.
echo.


:: --------------------------------------------------
:: Update History
:: --------------------------------------------------

echo Creating update history...

if not exist "update\logs" (
    mkdir "update\logs"
)

powershell -Command ^
"$file='update\logs\update_history.json';" ^
"$json=Get-Content 'update\version.json' -Raw | ConvertFrom-Json;" ^
"if (Test-Path $file) { $data=Get-Content $file -Raw | ConvertFrom-Json } else { $data=@() };" ^
"$new=[PSCustomObject]@{version=$json.version;date=(Get-Date -Format 'yyyy-MM-dd HH:mm:ss');description=$json.description;status='Installed'};" ^
"$result=@($new)+@($data);" ^
"$result | ConvertTo-Json -Depth 10 | Set-Content $file -Encoding UTF8"

echo Update history updated successfully.
echo.


:: --------------------------------------------------
:: Restart Service
:: --------------------------------------------------

echo ========================================
echo Restarting MedicalEquipmentSystem...
echo ========================================

net stop MedicalEquipmentSystem

timeout /t 3 /nobreak >nul

net start MedicalEquipmentSystem


if errorlevel 1 (
    echo Failed to restart the service.
) else (
    echo Service restarted successfully.
)


echo.
echo ========================================
echo UPDATE COMPLETED SUCCESSFULLY
echo ========================================

timeout /t 5

exit