import re

from django import forms
from django.core.exceptions import ValidationError

MAX_MESSAGE_LENGTH = 1600

# E.164: "+", country code (cannot start with 0), up to 15 digits in total.
E164_PATTERN = re.compile(r'^\+[1-9]\d{7,14}$')
# Philippine mobile numbers: +63 followed by 9 and nine more digits.
PH_E164_PATTERN = re.compile(r'^\+639\d{9}$')
# Philippine local mobile format: 09XXXXXXXXX (11 digits).
PH_LOCAL_PATTERN = re.compile(r'^09\d{9}$')


def normalize_phone_number(raw):
    """Return the number in E.164 format, or None if it is not valid.

    Spaces, dashes, dots and parentheses are ignored, so "0917 123 4567"
    and "+63 917-123-4567" are both accepted. Local PH numbers
    (09XXXXXXXXX) are converted to +639XXXXXXXXX.
    """
    number = re.sub(r'[\s\-().]', '', raw)
    if PH_LOCAL_PATTERN.match(number):
        number = '+63' + number[1:]
    if not E164_PATTERN.match(number):
        return None
    # A +63 number must be a complete PH mobile number.
    if number.startswith('+63') and not PH_E164_PATTERN.match(number):
        return None
    return number


class MessageField(forms.CharField):
    def to_python(self, value):
        # Browsers submit textarea line breaks as "\r\n". Turn them into "\n" before
        # the length check, so a line break counts as 1 character, like the live counter.
        return super().to_python(value).replace('\r\n', '\n')


class SMSForm(forms.Form):
    recipient = forms.CharField(
        label='Recipient phone number',
        max_length=20,
        help_text='International format (+639171234567) or PH local format (09171234567).',
        error_messages={'required': "Please enter the recipient's phone number."},
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+639171234567',
            'autocomplete': 'tel',
            'inputmode': 'tel',
        }),
    )
    # strip=True (the default) turns a whitespace-only message into "",
    # which then fails the "required" check.
    message = MessageField(
        label='Message',
        max_length=MAX_MESSAGE_LENGTH,
        error_messages={
            'required': 'Please enter a message.',
            'max_length': 'Message is too long: %(show_value)d characters (maximum is %(limit_value)d).',
        },
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Type your message...',
        }),
    )

    def clean_recipient(self):
        number = normalize_phone_number(self.cleaned_data['recipient'])
        if number is None:
            raise ValidationError(
                'Enter a valid phone number, e.g. +639171234567 or 09171234567.',
                code='invalid',
            )
        return number
