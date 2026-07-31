# Medical Equipment System

## Version

Current Version: **1.0.0**

---

# Description

Medical Equipment System is a Django-based web application developed for managing medical devices, repairs, maintenance, calibration, documentation, users and system updates.

The application includes:

- Medical Device Management
- Repair Management
- Preventive Maintenance
- Calibration
- Dashboard
- Audit Log
- Contacts
- Backup & Restore
- Automatic Update System
- User Management
- Document Management

---

# Technologies

- Python 3.12
- Django 6.0.7
- SQLite
- HTML
- CSS
- JavaScript
- OpenPyXL
- Pillow

---

# Repository

```bash
git clone https://github.com/hamudehabujh12-coder/MedicalEquipmentSystem.git
```

---

# Installation

## Create Virtual Environment

```bash
python -m venv venv
```

Windows

```bash
venv\Scripts\activate
```

Linux

```bash
source venv/bin/activate
```

---

## Install Packages

```bash
pip install -r requirements.txt
```

---

## Database Migration

```bash
python manage.py migrate
```

---

## Create Administrator

```bash
python manage.py createsuperuser
```

---

## Run Development Server

```bash
python manage.py runserver
```

---

# Collect Static Files

```bash
python manage.py collectstatic
```

---

# Backup Database

Database:

```
db.sqlite3
```

Automatic backup location:

```
update/backups/
```

---

# Restore Database

Replace

```
db.sqlite3
```

with a backup from

```
update/backups/
```

---

# Update System

Current update system:

```
update/
│
├── package/
├── scripts/
├── logs/
├── backups/
├── version.json
└── update.bat
```

To install an update:

1. Open **System Update**
2. Click **Check Update**
3. Click **Install Update**

The system automatically:

- Creates database backup
- Copies update files
- Stores update history

---

# Manual Update

Run

```cmd
update\scripts\update.bat
```

---

# Django Management Commands

Run server

```bash
python manage.py runserver
```

Create migrations

```bash
python manage.py makemigrations
```

Apply migrations

```bash
python manage.py migrate
```

Create superuser

```bash
python manage.py createsuperuser
```

Collect static files

```bash
python manage.py collectstatic
```

Open Django shell

```bash
python manage.py shell
```

Check project

```bash
python manage.py check
```

---

# Git Commands

Clone

```bash
git clone https://github.com/hamudehabujh12-coder/MedicalEquipmentSystem.git
```

Status

```bash
git status
```

Add files

```bash
git add .
```

Commit

```bash
git commit -m "Update description"
```

Push

```bash
git push
```

Pull

```bash
git pull
```

---

# Requirements

```
Python 3.12
Git
Virtual Environment
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create

```
.env
```

Required variables

```text
SECRET_KEY=

DEBUG=False

EMAIL_HOST=

EMAIL_PORT=587

EMAIL_USE_TLS=True

EMAIL_HOST_USER=

EMAIL_HOST_PASSWORD=

DEFAULT_FROM_EMAIL=
```

---

# Default Project Structure

```
MedicalEquipmentSystem/

devices/

medicalsystem/

templates/

media/

update/

requirements.txt

manage.py

version.txt

README.md
```

---

# Security

- Login Required
- Django Authentication
- CSRF Protection
- Hidden Secret Key (.env)
- Audit Log
- User Permissions

---

# Author

Mohammed Abujheisha

Medical Equipment Engineer

Luebeck, Germany

---

# License

Internal company software.

All rights reserved.