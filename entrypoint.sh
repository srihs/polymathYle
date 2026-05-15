#!/bin/bash

# Copy credentials file
if [ -f /keys/wp-email-352000-7fb066ae7224.json ]; then
    cp /keys/wp-email-352000-7fb066ae7224.json /credentials.json
    echo "Credentials file copied."
else
    echo "Credentials file not found in /keys/"
fi

# Wait for database to be ready using Python
echo "Waiting for database..."
python -c "
import time
import socket
while True:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('db', 3306))
        sock.close()
        break
    except socket.error:
        time.sleep(1)
"
echo "Database is ready!"

# Run migrations
python manage.py migrate

# Create or update superuser from ADMIN_USERNAME / ADMIN_PASSWORD env vars
if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
    python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
username = "$ADMIN_USERNAME"
password = "$ADMIN_PASSWORD"
email = username if "@" in username else ""
user, created = User.objects.get_or_create(username=username, defaults={"email": email})
user.is_superuser = True
user.is_staff = True
user.is_active = True
if email and not user.email:
    user.email = email
user.set_password(password)
user.save()
print(f"Superuser {'created' if created else 'updated'}: {username}")
EOF
else
    echo "ADMIN_USERNAME / ADMIN_PASSWORD not set — skipping superuser bootstrap."
fi

# Collect static files
python manage.py collectstatic --noinput

# Start server
exec "$@"