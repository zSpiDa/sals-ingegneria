#!/bin/bash
# Setup script per Smart Mobility Sprint 1

echo "🚀 Smart Mobility - Setup Sprint 1"
echo "=================================="

# 1. Crea e attiva virtual environment
echo "📦 Configuring Python environment..."
python -m venv venv
source venv/Scripts/activate 2>/dev/null || . venv/bin/activate

# 2. Installa dipendenze
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# 3. Applica migrazioni
echo "🗄️  Applying database migrations..."
python manage.py migrate

# 4. Crea superuser (opzionale)
echo "👤 Creating superuser..."
python manage.py shell << END
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@test.it', 'admin123')
    print("✓ Superuser 'admin' created")
else:
    print("✓ Superuser already exists")
END

# 5. Popola database con dati test
echo "📊 Seeding test data..."
python manage.py seed_data

# 6. Crea cartella staticfiles
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "✅ Setup completed!"
echo ""
echo "🎯 Next steps:"
echo "1. Start server: python manage.py runserver"
echo "2. Open dashboard: http://localhost:8000/frontend_app/dashboard.html"
echo "3. Admin panel: http://localhost:8000/admin (admin/admin123)"
echo ""
echo "📚 API Documentation:"
echo "   - Mezzi: GET /api/mezzi/"
echo "   - Corse: POST /api/corse/avvia/"
echo "   - Auth: POST /api/auth/login/"
echo ""
