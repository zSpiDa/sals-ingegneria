ISTRUZIONI PER L'INSTALLAZIONE E AVVIO - ECOGLIDE

1. Prerequisiti: Python 3 installato.
2. Aprire il terminale nella cartella del progetto.
3. Installare le librerie necessarie:
   pip install django djangorestframework django-cors-headers
4. Applicare le migrazioni del database:
   python manage.py migrate
5. (Opzionale) Popolare il database con dati di test:
   python manage.py seed_db
6. Avviare il server backend:
   python manage.py runserver
7. Aprire i file HTML del frontend (es. frontend_app/index.html) nel browser. Assicurarsi che nel file .html la costante API_BASE_URL punti a http://127.0.0.1:8000/api