from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Create a superuser for Ruang Dengar with minimal required fields'

    def handle(self, *args, **options):
        email = 'admin@telkomuniversity.ac.id'
        password = 'admin123'
        nama_lengkap = 'Admin Ruang Dengar'
        username = 'admin'

        if CustomUser.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Superuser dengan email {email} sudah ada!'))
            return

        try:
            user = CustomUser.objects.create_superuser(
                email=email,
                password=password,
                nama_lengkap=nama_lengkap,
                username=username,
                role=CustomUser.Role.ADMIN,
                is_staff=True,
                is_superuser=True,
                is_approved=True,
                is_profile_complete=True
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Superuser berhasil dibuat!'))
            self.stdout.write(self.style.SUCCESS(f''))
            self.stdout.write(self.style.SUCCESS(f'Email: {email}'))
            self.stdout.write(self.style.SUCCESS(f'Password: {password}'))
            self.stdout.write(self.style.SUCCESS(f''))
            self.stdout.write(self.style.SUCCESS(f'Login di: {settings.SITE_URL}/admin'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
