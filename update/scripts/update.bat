@echo off
title Medical Equipment System Update

cd /d "%~dp0\..\.."

echo ========================================
echo Medical Equipment System Update
echo ========================================

echo.

set BACKUP_DIR=update\backups

if not exist "%BACKUP_DIR%" (
    mkdir "%BACKUP_DIR%"
)

set BACKUP_FILE=%BACKUP_DIR%\update_backup_%date:~-4%-%date:~3,2%-%date:~0,2%_%time:~0,2%-%time:~3,2%.sqlite3


echo Creating database backup...

copy "db.sqlite3" "%BACKUP_FILE%" > nul


if exist "%BACKUP_FILE%" (
    echo Backup created:
    echo %BACKUP_FILE%
) else (
    echo Backup failed!
)


echo.

echo Update preparation finished.
echo.
echo Installing update files...

xcopy "update\package\*" "." /E /Y /I


if %errorlevel%==0 (
    echo Update files copied successfully.


    echo Creating update history...


    powershell -Command ^
    "$file='update\logs\update_history.json';" ^
    "$json=Get-Content 'update\version.json' -Raw | ConvertFrom-Json;" ^
    "if (Test-Path $file) { $data=Get-Content $file -Raw | ConvertFrom-Json } else { $data=@() };" ^
    "$exists=$data | Where-Object {$_.version -eq $json.version};" ^
    "if (-not $exists) {" ^
    "$new=[PSCustomObject]@{version=$json.version;date=(Get-Date -Format 'yyyy-MM-dd');description=$json.description;status='Installed'};" ^
    "$result=@($new)+@($data);" ^
    "$result | ConvertTo-Json -Depth 10 | Set-Content $file -Encoding UTF8" ^
    "}"

    echo Update history updated successfully.

) else (
    echo Update files copy failed.
)


pause