#!/bin/bash

# Скрипт для создания организации и проектов в Glitchtip через Django shell
# Использование: ./scripts/glitchtip-setup-projects-shell.sh

set -e

ADMIN_EMAIL="${GLITCHTIP_ADMIN_EMAIL:-admin@sattva.tv}"
ORG_NAME="Sattva TV"
ORG_SLUG="sattva-tv"
BACKEND_PROJECT="sattva-tv-backend"
FRONTEND_PROJECT="sattva-tv-frontend"

echo "🚀 Настройка проектов в Glitchtip через Django shell..."
echo ""

# Создание организации и проектов через Django ORM
docker compose -f docker-compose.glitchtip.yml exec -T glitchtip-web python3 manage.py shell << 'PYEOF'
from django.contrib.auth import get_user_model
from organizations_ext.models import Organization, OrganizationUser
from teams.models import Team
from projects.models import Project, ProjectKey

User = get_user_model()

# Получение admin пользователя
admin_email = 'admin@sattva.tv'
try:
    admin_user = User.objects.get(email=admin_email)
    print(f'✅ Admin user found: {admin_user.email}')
except User.DoesNotExist:
    print(f'❌ Admin user not found: {admin_email}')
    exit(1)

# Создание организации
org_name = 'Sattva TV'
org_slug = 'sattva-tv'

org, created = Organization.objects.get_or_create(
    slug=org_slug,
    defaults={'name': org_name}
)

if created:
    print(f'✅ Organization created: {org.name} ({org.slug})')
    # Добавление admin как владельца
    OrganizationUser.objects.get_or_create(
        user=admin_user,
        organization=org,
        defaults={'role': 'owner'}
    )
else:
    print(f'ℹ️  Organization already exists: {org.name} ({org.slug})')

# Создание team (требуется для проектов)
team, team_created = Team.objects.get_or_create(
    organization=org,
    slug=org_slug,
    defaults={'name': org_name}
)

if team_created:
    print(f'✅ Team created: {team.name}')
    team.members.add(admin_user)
else:
    print(f'ℹ️  Team already exists: {team.name}')

# Создание backend проекта
backend_name = 'sattva-tv-backend'
backend_project, created = Project.objects.get_or_create(
    organization=org,
    slug=backend_name,
    defaults={
        'name': backend_name,
        'platform': 'python-fastapi',
        'team': team
    }
)

if created:
    print(f'✅ Backend project created: {backend_project.name}')
else:
    print(f'ℹ️  Backend project already exists: {backend_project.name}')

# Получение/создание DSN key для backend
backend_key = ProjectKey.objects.filter(project=backend_project).first()
if not backend_key:
    backend_key = ProjectKey.objects.create(project=backend_project, label='Default')
    print(f'✅ Backend DSN key created')
else:
    print(f'ℹ️  Backend DSN key already exists')

backend_dsn = backend_key.get_dsn('http://localhost:8080')
print(f'🔑 Backend DSN: {backend_dsn}')

# Создание frontend проекта
frontend_name = 'sattva-tv-frontend'
frontend_project, created = Project.objects.get_or_create(
    organization=org,
    slug=frontend_name,
    defaults={
        'name': frontend_name,
        'platform': 'react',
        'team': team
    }
)

if created:
    print(f'✅ Frontend project created: {frontend_project.name}')
else:
    print(f'ℹ️  Frontend project already exists: {frontend_project.name}')

# Получение/создание DSN key для frontend
frontend_key = ProjectKey.objects.filter(project=frontend_project).first()
if not frontend_key:
    frontend_key = ProjectKey.objects.create(project=frontend_project, label='Default')
    print(f'✅ Frontend DSN key created')
else:
    print(f'ℹ️  Frontend DSN key already exists')

frontend_dsn = frontend_key.get_dsn('http://localhost:8080')
print(f'🔑 Frontend DSN: {frontend_dsn}')

print('')
print('=' * 60)
print('✅ Setup completed!')
print('')
print(f'Backend DSN: {backend_dsn}')
print(f'Frontend DSN: {frontend_dsn}')
print('')
print('Add to .env files:')
print(f'  Backend: SENTRY_DSN={backend_dsn}')
print(f'  Frontend: VITE_SENTRY_DSN={frontend_dsn}')
print('=' * 60)
PYEOF

echo ""
echo "✅ Done!"
echo ""
echo "🌐 Glitchtip UI: http://localhost:8080"
echo "📧 Email: $ADMIN_EMAIL"
