from django import template

register = template.Library()

# Bootstrap badge colour for each message status.
STATUS_BADGES = {
    'not_submitted': 'text-bg-warning',
    'pending': 'text-bg-secondary',
    'dispatched': 'text-bg-info',
    'sent': 'text-bg-primary',
    'delivered': 'text-bg-success',
    'failed': 'text-bg-danger',
}


@register.filter
def status_badge(status):
    """{{ sms.status|status_badge }} -> CSS classes for the status badge."""
    return STATUS_BADGES.get(status, 'text-bg-light')


@register.filter
def bootstrap_input(field):
    """Render a form field with Bootstrap classes, marked red when it has errors."""
    css = 'form-control is-invalid' if field.errors else 'form-control'
    return field.as_widget(attrs={'class': css})
