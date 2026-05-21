@echo off
REM Setup script per Smart Mobility Sprint 1 (Windows)

echo 🚀 Smart Mobility - Setup Sprint 1
echo ==================================

REM 1. Crea virtual environment
echo 📦 Configuring Python environment...
python -m venv venv
call venv\Scripts\activate.bat

REM 2. Installa dipendenze
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM 3. Applica migrazioni
echo 🗄️  Applying database migrations...
python manage.py migrate

REM 4. Crea superuser
echo 👤 Creating superuser...
python manage.py shell << END
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@test.it', 'admin123')
    print("✓ Superuser 'admin' created")
else:
    print("✓ Superuser already exists")
END

REM 5. Popola database
echo 📊 Seeding test data...
python manage.py seed_data

REM 6. Raccogli staticfiles
echo 📁 Collecting static files...
python manage.py collectstatic --noinput

echo.
echo ✅ Setup completed!
echo.
echo 🎯 Next steps:
echo 1. Start server: python manage.py runserver
echo 2. Open dashboard: http://localhost:8000/frontend_app/dashboard.html
echo 3. Admin panel: http://localhost:8000/admin (admin/admin123)
echo.
echo 📚 API Documentation:
echo    - Mezzi: GET /api/mezzi/
echo    - Corse: POST /api/corse/avvia/
echo    - Auth: POST /api/auth/login/
echo.
pause
