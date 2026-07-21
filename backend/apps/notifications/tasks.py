from celery import shared_task
from .services import send_whatsapp


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_whatsapp_task(self, phone: str, message: str):
    success = send_whatsapp(phone, message)
    if not success:
        raise self.retry()


@shared_task
def send_campaign_task(campaign_id: int):
    from django.utils.timezone import now
    from apps.users.models import User
    from .models import Campaign

    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return

    qs = User.objects.filter(is_active=True).exclude(phone='')
    seg = campaign.segment
    if seg == 'students':
        qs = qs.filter(role='student')
    elif seg in ('center', 'online'):
        qs = qs.filter(student_type=seg)
    elif seg in ('1st', '2nd', '3rd'):
        qs = qs.filter(academic_year=seg)

    # ponytail: fires one Celery task per user — fine for thousands, use chunked bulk send if >100k recipients
    count = 0
    for phone in qs.values_list('phone', flat=True):
        send_whatsapp_task.delay(phone, campaign.message)
        count += 1

    Campaign.objects.filter(pk=campaign_id).update(
        status='done', sent_count=count, sent_at=now()
    )


@shared_task
def send_email_campaign_task(campaign_id: int):
    from django.core.mail import send_mail
    from django.utils.timezone import now
    from apps.users.models import User
    from .models import EmailCampaign

    try:
        campaign = EmailCampaign.objects.get(pk=campaign_id)
    except EmailCampaign.DoesNotExist:
        return
    qs = User.objects.filter(is_active=True).exclude(email='')

    seg = campaign.segment
    if seg == 'students':
        qs = qs.filter(role='student')
    elif seg in ('center', 'online'):
        qs = qs.filter(student_type=seg)
    elif seg in ('1st', '2nd', '3rd'):
        qs = qs.filter(academic_year=seg)

    count = 0
    for user in qs.values('email', 'first_name'):
        try:
            send_mail(
                subject=campaign.subject,
                message='',  # plain text fallback empty
                html_message=campaign.body_html,
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[user['email']],
                fail_silently=True,
            )
            count += 1
        except Exception:
            pass

    EmailCampaign.objects.filter(pk=campaign_id).update(
        status='done', sent_count=count, sent_at=now()
    )


@shared_task
def notify_admins_task(message: str):
    """Send a WhatsApp to all active admin/staff users."""
    from apps.users.models import User
    phones = User.objects.filter(
        role__in=('admin', 'staff'), is_active=True
    ).values_list('phone', flat=True)
    for phone in phones:
        send_whatsapp_task.delay(phone, message)
