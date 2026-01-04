"""
Email Notification Utilities for Ruang Dengar Platform
Handles all email notifications: laporan, booking, alerts, etc.
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_notification_email(subject, recipient_list, template_name, context, fail_silently=True):
    """
    Generic email sender with HTML template support
    
    Args:
        subject (str): Email subject
        recipient_list (list): List of recipient email addresses
        template_name (str): Path to HTML template (e.g., 'emails/laporan_created.html')
        context (dict): Template context variables
        fail_silently (bool): Whether to suppress exceptions
    
    Returns:
        int: Number of emails sent successfully
    """
    try:
        # Render HTML content
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)  # Fallback plain text
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        result = email.send(fail_silently=fail_silently)
        
        logger.info(f"Email sent: {subject} to {recipient_list}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to send email: {subject} to {recipient_list}. Error: {str(e)}")
        if not fail_silently:
            raise
        return 0


# ==================== LAPORAN NOTIFICATIONS ====================

def send_laporan_created_notification(laporan, admin_emails):
    """
    Notify admins when a new laporan is created
    
    Args:
        laporan: Laporan instance
        admin_emails: List of admin email addresses
    """
    subject = f"[Ruang Dengar] Laporan Baru: {laporan.kode}"
    
    context = {
        'kode_laporan': laporan.kode,
        'jenis': laporan.get_jenis_display(),
        'urgency': laporan.ai_urgency or 'SEDANG',
        'is_anonim': laporan.is_anonim,
        'created_at': laporan.created_at,
        'pelapor_nama': laporan.pelapor.nama_lengkap if not laporan.is_anonim else 'Anonim',
        'laporan_url': f"{settings.SITE_URL}/admin/laporan/{laporan.id}/detail/",
    }
    
    return send_notification_email(
        subject=subject,
        recipient_list=admin_emails,
        template_name='emails/laporan_created_admin.html',
        context=context
    )


def send_laporan_status_updated_notification(laporan, old_status, new_status, catatan=None):
    """
    Notify pelapor when laporan status changes
    
    Args:
        laporan: Laporan instance
        old_status: Previous status
        new_status: New status
        catatan: Optional note/comment from admin
    """
    # Don't send email for anonymous reports without email
    if laporan.is_anonim or not laporan.pelapor.email:
        logger.info(f"Skipping email for anonim laporan: {laporan.kode}")
        return 0
    
    subject = f"[Ruang Dengar] Status Laporan {laporan.kode} Diperbarui"
    
    context = {
        'kode_laporan': laporan.kode,
        'old_status': old_status,
        'new_status': new_status,
        'catatan': catatan,
        'pelapor_nama': laporan.pelapor.nama_lengkap,
        'laporan_url': f"{settings.SITE_URL}/laporan/{laporan.id}/detail/",
        'updated_at': laporan.updated_at,
    }
    
    return send_notification_email(
        subject=subject,
        recipient_list=[laporan.pelapor.email],
        template_name='emails/laporan_status_updated.html',
        context=context
    )


def send_urgent_laporan_alert(laporan, management_emails):
    """
    Send urgent alert for DARURAT cases
    
    Args:
        laporan: Laporan instance with ai_urgency=DARURAT
        management_emails: List of management email addresses
    """
    subject = f"🚨 [URGENT] Laporan Darurat: {laporan.kode}"
    
    context = {
        'kode_laporan': laporan.kode,
        'jenis': laporan.get_jenis_display(),
        'urgency': laporan.ai_urgency,
        'toxicity_score': laporan.ai_toxicity_score,
        'created_at': laporan.created_at,
        'laporan_url': f"{settings.SITE_URL}/admin/laporan/{laporan.id}/detail/",
        'deskripsi_singkat': laporan.cronologi_singkat[:200] + '...' if len(laporan.cronologi_singkat) > 200 else laporan.cronologi_singkat,
    }
    
    return send_notification_email(
        subject=subject,
        recipient_list=management_emails,
        template_name='emails/laporan_urgent_alert.html',
        context=context
    )


# ==================== BOOKING NOTIFICATIONS ====================

def send_booking_created_notification(booking):
    """
    Notify pelapor when booking is created
    
    Args:
        booking: Booking instance
    """
    # Email to Pelapor (confirmation)
    pelapor_subject = f"[Ruang Dengar] Konfirmasi Booking Konseling"
    pelapor_context = {
        'pelapor_nama': booking.user.nama_lengkap,
        'konselor_nama': booking.konselor,
        'tanggal': booking.tanggal,
        'waktu_mulai': booking.waktu,
        'tipe_sesi': booking.jenis or 'Tidak disebutkan',
        'lokasi': booking.lokasi_konseling,
        'topik': booking.topik or 'Tidak disebutkan',
        'booking_url': f"{settings.SITE_URL}/booking/{booking.id}/detail/",
    }
    
    pelapor_email_sent = send_notification_email(
        subject=pelapor_subject,
        recipient_list=[booking.user.email],
        template_name='emails/booking_created_pelapor.html',
        context=pelapor_context
    )
    
    return pelapor_email_sent


def send_booking_reminder(booking):
    """
    Send reminder 24 hours before booking (untuk cronjob/celery task)
    
    Args:
        booking: Booking instance
    """
    subject = f"[Ruang Dengar] Reminder: Sesi Konseling Besok"
    
    context = {
        'pelapor_nama': booking.user.nama_lengkap,
        'konselor_nama': booking.konselor,
        'tanggal': booking.tanggal,
        'waktu_mulai': booking.waktu,
        'tipe_sesi': booking.jenis or 'Tidak disebutkan',
        'lokasi': booking.lokasi_konseling,
        'booking_url': f"{settings.SITE_URL}/booking/{booking.id}/detail/",
    }
    
    return send_notification_email(
        subject=subject,
        recipient_list=[booking.user.email],
        template_name='emails/booking_reminder.html',
        context=context
    )


# ==================== REKAM MEDIS NOTIFICATIONS ====================

def send_high_risk_alert(rekam_medis, management_emails):
    """
    Send HIGH RISK alert for rekam medis with TINGGI risk level
    
    Args:
        rekam_medis: RekamMedisKonseling instance
        management_emails: List of management email addresses
    """
    subject = f"🚨 [HIGH RISK ALERT] Klien: {rekam_medis.pelapor.nama_lengkap}"
    
    context = {
        'pelapor_nama': rekam_medis.pelapor.nama_lengkap,
        'konselor_nama': rekam_medis.konselor.nama_lengkap,
        'sesi_ke': rekam_medis.sesi_ke,
        'tanggal_sesi': rekam_medis.tanggal_sesi,
        'risk_bunuh_diri': rekam_medis.risk_bunuh_diri,
        'risk_self_harm': rekam_medis.risk_self_harm,
        'mood_klien': rekam_medis.mood_klien,
        'rekam_medis_url': f"{settings.SITE_URL}/admin/rekam-medis/{rekam_medis.id}/",
        'urgent_action_required': True,
    }
    
    return send_notification_email(
        subject=subject,
        recipient_list=management_emails,
        template_name='emails/high_risk_alert.html',
        context=context
    )


def send_rekam_medis_created_notification(rekam_medis):
    """
    Notify pelapor that rekam medis has been created (optional, untuk transparency)
    
    Args:
        rekam_medis: RekamMedisKonseling instance
    """
    subject = f"[Ruang Dengar] Catatan Konseling Sesi {rekam_medis.sesi_ke}"
    
    context = {
        'pelapor_nama': rekam_medis.pelapor.nama_lengkap,
        'sesi_ke': rekam_medis.sesi_ke,
        'tanggal_sesi': rekam_medis.tanggal_sesi,
        'sesi_selanjutnya': rekam_medis.sesi_selanjutnya,
        'rekam_medis_url': f"{settings.SITE_URL}/rekam-medis/{rekam_medis.id}/",
    }
    
    return send_notification_email(
        subject=subject,
        recipient_list=[rekam_medis.pelapor.email],
        template_name='emails/rekam_medis_created.html',
        context=context
    )


# ==================== HELPER FUNCTIONS ====================

def get_admin_emails():
    """Get all admin emails for notifications"""
    from users.models import CustomUser
    return list(CustomUser.objects.filter(role='admin', is_active=True).values_list('email', flat=True))


def get_management_emails():
    """Get management/superuser emails for high priority alerts"""
    from users.models import CustomUser
    return list(CustomUser.objects.filter(is_superuser=True, is_active=True).values_list('email', flat=True))
