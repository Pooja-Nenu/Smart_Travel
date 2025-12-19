====================================================================================================
Smart Travel Checklist + Expense Splitter
====================================================================================================

Phase 1: Environment & Installation

===========================
1. Create a Project Folder
============================
mkdir SmartTravelApp
cd SmartTravelApp


================================
2. Create a Virtual Environment
================================
python -m venv venv


===================================
3. Activate the Virtual Environment
===================================
venv\Scripts\activate


===================================
4. Install Django
===================================
pip install django


Phase 2: Project Initialization

===================================
1. Start the Django Project
===================================
django-admin startproject config .


===================================
2.Create the Main App
===================================
python manage.py startapp travel

===================================
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

pip install django-allauth