from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import SMSForm
from .models import SMSMessage
from .services import get_sms_status, send_sms


def send_sms_view(request):
    """Show the SMS form (GET) or validate it and submit the SMS to textbee (POST)."""
    if request.method == 'POST':
        form = SMSForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            body = form.cleaned_data['message']
            result = send_sms(recipient, body)

            # Every attempt that reaches the provider step is saved, success or not.
            SMSMessage.objects.create(
                recipient=recipient,
                body=body,
                provider_message_id=result.message_id,
                status=result.status,
                error_message=result.error,
            )

            if result.success:
                # Submission is not delivery: textbee has only queued the message.
                messages.success(
                    request,
                    f'Message to {recipient} was submitted to textbee (status: {result.status}). '
                    'It is not confirmed yet; use "Refresh status" on the History page to check.',
                )
                return redirect('sms_app:send_sms')

            # Keep the user's input on the page so they can fix the problem and retry.
            messages.error(request, f'The message was not sent. {result.error}')
    else:
        form = SMSForm()

    return render(request, 'sms_app/send_sms.html', {'form': form})


def history_view(request):
    """List every send attempt with summary counts."""
    sms_list = SMSMessage.objects.all()
    counts = sms_list.aggregate(
        total=Count('id'),
        submitted=Count('id', filter=~Q(provider_message_id='')),
        failed=Count('id', filter=Q(status__in=[
            SMSMessage.Status.NOT_SUBMITTED,
            SMSMessage.Status.FAILED,
        ])),
    )
    return render(request, 'sms_app/history.html', {'sms_list': sms_list, 'counts': counts})


@require_POST
def refresh_status_view(request, pk):
    """Ask textbee for the latest status of one message and save it."""
    sms = get_object_or_404(SMSMessage, pk=pk)

    if not sms.is_submitted:
        messages.warning(request, 'This message was never submitted to textbee, so it has no status to refresh.')
        return redirect('sms_app:history')

    result = get_sms_status(sms.provider_message_id)
    if result.success:
        sms.status = result.status
        sms.save(update_fields=['status', 'updated_at'])
        messages.info(request, f'Status for the message to {sms.recipient} is now "{sms.get_status_display()}".')
    else:
        messages.error(request, f'Could not refresh the status. {result.error}')

    return redirect('sms_app:history')
