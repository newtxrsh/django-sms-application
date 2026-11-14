# SMS Sender – Django + textbee.dev

**IT 120 – Integrative Programming and Technologies · Group Assignment: Build a Django Application for Sending SMS**

SMS Sender is a Django web application that lets a user type a recipient's phone number and a message, validates the input, and sends the SMS through the **textbee.dev** SMS gateway, which uses our own Android phone and SIM as the sender. Every attempt is saved, and a history dashboard shows whether each message was only *submitted* or actually *delivered*.

---

## Objectives

- **Purpose:** Show how a Django web application can integrate an external SMS service through a REST API, with proper input validation, error handling and secure credential management.
- **Target users:** Small organizations, teachers, student groups or offices that need to send short text notifications (reminders, announcements, alerts) to Philippine mobile numbers from a simple web page.
- **SMS functionality:**
  - Compose an SMS (recipient number + message) in a web form with a live character and SMS-segment counter.
  - Validate the number (E.164 or PH local `09XXXXXXXXX`) and the message before any API call.
  - Submit the message to textbee, which forwards it to our Android phone to send through the SIM.
  - Report the result honestly: "submitted to textbee (status: pending)" is not the same as "delivered".
  - Track the real delivery status from the History page with a "Refresh status" button.

---

## Group Members & Responsibilities

The activity suggests three roles. Our group has **2 members**, so the tasks of the three roles were divided between us. Both members understand and can explain the whole application.

| Member | Role | Responsibilities |
|---|---|---|
| **John Paul Palaran** (GitHub: `newtxrsh`) | Backend | Django project setup and settings, `SMSMessage` model and admin, views and URL routing, textbee integration (`services.py`), error handling, status refresh, SIM-slot selection |
| **Eian Gabriel Aguilar** (GitHub: `myb.eian`) | Frontend & QA | Django form and phone/message validation, Bootstrap templates and UI, live character/segment counter, history dashboard, unit tests, README, demo coordination |

---

## Features

**Core**
- SMS form with recipient phone number, message box and **Send SMS** button (Django `Form` class, CSRF-protected).
- Validation before sending: required fields, whitespace-only messages rejected, max 1,600 characters, E.164 phone format, PH local format `09XXXXXXXXX` automatically converted to `+639XXXXXXXXX`. Errors are shown under the field that caused them.
- textbee integration in a separate service module with a 15-second timeout.
- Friendly error messages for: missing credentials, invalid API key (401), phone/device problems (400), plan limit (429), network errors and timeouts, and any other provider error.
- Success feedback that never claims delivery: *"Message to +639… was submitted to textbee (status: pending). It is not confirmed yet…"*

**Additional features**
- **Message history dashboard:** every attempt (successful or failed) is saved and listed with colour-coded status badges and totals (total / submitted / failed).
- **Status tracking:** a *Refresh status* button asks textbee for the latest status (pending → dispatched → sent → delivered / failed). If the phone could not send a message, textbee's reason (e.g. "no SMS credit on SIM") is saved and shown.
- **Live character + SMS segment counter:** shows characters used out of 1,600 and how many SMS parts the message needs (160 per SMS for plain text, 153 per part when split; 70 / 67 when emoji or special characters force Unicode).
- **SIM selection:** an optional `TEXTBEE_SIM_SLOT` setting chooses which SIM sends the message on a dual-SIM phone.
- **Django admin** for SMS records (filter by status, search by number or text).
- Double-submit protection (the button is disabled while sending) and a responsive layout for phones.

---

## Technologies & Dependencies

| Technology | Use |
|---|---|
| Python 3.11 | Programming language |
| Django 5.2 | Web framework (forms, ORM, templates, messages, CSRF, admin) |
| requests | HTTP client used to call the textbee REST API |
| python-dotenv | Loads secrets from the `.env` file into environment variables |
| textbee.dev | SMS gateway (REST API + Android app that sends SMS through our SIM) |
| Bootstrap 5.3 + Bootstrap Icons (CDN) | Responsive UI |
| SQLite | Database for the message history |

Full pinned list: [`requirements.txt`](requirements.txt).

### Why textbee instead of Twilio

The reference tutorial uses Twilio. We switched to textbee because Twilio's trial expires after 30 days and must then be upgraded with payment details, and trial accounts can only text verified numbers with a trial prefix added to each message. textbee's free plan needs no credit card and sends **real SMS to Philippine numbers** through our own Android phone and SIM, so the messages arrive like normal texts.

---

## Project Structure

```
IT120-DJANGO/
├── manage.py
├── requirements.txt
├── .env.example              # placeholder settings (safe to commit)
├── .gitignore                # excludes venv/, .env, db.sqlite3, caches, editor folders
├── README.md
├── docs/
│   ├── COLLABORATION.md      # branches, pull requests and review plan
│   └── DEMO_SCRIPT.md        # timed demo video script
├── sms_project/              # Django project
│   ├── settings.py           # reads SECRET_KEY, DEBUG and textbee settings from .env
│   ├── urls.py               # includes sms_app.urls
│   ├── wsgi.py / asgi.py
└── sms_app/                  # Django application
    ├── models.py             # SMSMessage: recipient, body, provider, provider_message_id, status, error_message, timestamps
    ├── forms.py              # SMSForm + phone number validation/normalisation
    ├── services.py           # textbee API calls (send + status) and error handling
    ├── views.py              # send form, history dashboard, refresh status
    ├── urls.py               # /, /history/, /history/<id>/refresh/
    ├── admin.py              # SMSMessage in Django admin
    ├── tests.py              # 33 unit tests (textbee mocked)
    ├── migrations/
    ├── templatetags/sms_extras.py   # status badge colours, Bootstrap form inputs
    ├── templates/sms_app/
    │   ├── base.html         # navbar, alerts, footer
    │   ├── send_sms.html     # SMS form + counter
    │   └── history.html      # dashboard
    └── static/sms_app/
        ├── css/style.css
        └── js/sms_counter.js # live character / segment counter
```

---

## SMS Workflow

1. **Open the app:** the user opens `http://127.0.0.1:8000/` and sees the *Send an SMS* form.
2. **Enter the number:** e.g. `09171234567` or `+639171234567`.
3. **Compose the message:** the counter shows characters used and SMS segments.
4. **Validate:** on **Send SMS**, `SMSForm` checks the inputs. If anything is wrong, the form is shown again with an error under the field and **nothing is sent**. Local numbers are converted to `+63…`.
5. **Send to textbee:** `services.send_sms()` checks that the credentials exist, then sends `POST https://api.textbee.dev/api/v1/gateway/send-sms` with the `x-api-key` header. textbee pushes the message to our Android phone, which sends it through the SIM.
6. **Show the result:** the attempt is saved in the database.
   - Success: green alert, *"submitted to textbee (status: pending)"*, which means accepted, **not yet delivered**.
   - Failure: red alert with a friendly reason; the user's input stays in the form so they can retry.
7. **Track delivery:** on **History**, *Refresh status* calls `GET /gateway/devices/{deviceId}/sms-batch/{smsBatchId}` and updates the badge (e.g. *Sent* → *Delivered*).

---

## Installation & Setup

Requirements: Python 3.10+ and Git. Commands below are for Windows PowerShell (macOS/Linux equivalents in comments).

```powershell
git clone <repository-url>
cd IT120-DJANGO

python -m venv venv
.\venv\Scripts\Activate.ps1          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

copy .env.example .env               # macOS/Linux: cp .env.example .env
```

Generate a Django secret key and put it in `.env` as `DJANGO_SECRET_KEY`:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Then create the database:

```powershell
python manage.py migrate
python manage.py createsuperuser     # optional, for /admin/
```

### Environment variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | Django secret key (the app refuses to start without it) |
| `DJANGO_DEBUG` | No | `True` for local development; defaults to `False` |
| `DJANGO_ALLOWED_HOSTS` | No | Comma-separated hosts; defaults to `127.0.0.1,localhost` |
| `TEXTBEE_API_KEY` | Yes, to send | API key from the textbee dashboard |
| `TEXTBEE_DEVICE_ID` | Yes, to send | ID of the linked Android phone |
| `TEXTBEE_SIM_SLOT` | No | SIM used for sending: `0` = SIM 1, `1` = SIM 2. Empty = phone default |

---

## textbee Configuration

1. **Create an account** at [textbee.dev](https://textbee.dev) and **verify your email** (unverified accounts get a 400 error when sending).
2. **Install the textbee app** on an Android 7.0+ phone and allow its **SMS permission**.
3. **Link the phone:** on the textbee web dashboard, register a device and scan the QR code with the app.
4. **Copy the API key and device ID** from the dashboard into `.env` (`TEXTBEE_API_KEY`, `TEXTBEE_DEVICE_ID`).
5. **Battery settings:** set the textbee app's battery usage to **Unrestricted** so Android does not stop it in the background.
6. **SIM load:** make sure the SIM has load or an SMS promo that covers the recipient's network (e.g. a TNT-only promo may not cover Globe numbers). On a dual-SIM phone, set `TEXTBEE_SIM_SLOT` to the SIM that has load.
7. Restart `runserver` after changing `.env`.

Never commit `.env`, and never show the API key or the textbee dashboard key page in screenshots or videos.

---

## Running the App

```powershell
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

| Page | URL |
|---|---|
| Send SMS | http://127.0.0.1:8000/ |
| History dashboard | http://127.0.0.1:8000/history/ |
| Django admin | http://127.0.0.1:8000/admin/ |

The Android phone must be online with the textbee app running.

---

## Testing Procedures & Results

### Automated tests

```powershell
python manage.py test sms_app -v 2
```

The tests replace `requests.post` / `requests.get` with mocks, so **no real SMS is sent** and no real API key is needed. They check form validation, every error path of the textbee service, the views, CSRF protection, and that the API key never appears in error messages or logs.

**Result (2026-11-14): 33 tests, all passed.** Related tests are grouped into one row below.

| # | Test case | Input | Expected | Actual | Pass/Fail |
|---|---|---|---|---|---|
| 1 | Valid phone + message | `09171234567`, "Hello"; textbee returns 201 with `smsBatchId` | Record saved with batch ID, status `pending`, success alert | Record saved (`batch123`, `pending`), alert "submitted to textbee (status: pending)" | Pass |
| 2 | Empty phone number | `""`, "Hello" | Rejected with field error | "Please enter the recipient's phone number." | Pass |
| 3 | Empty message | `+639171234567`, `""` | Rejected with field error | "Please enter a message." | Pass |
| 4 | Whitespace-only message | `"   \n  "` | Rejected with field error | "Please enter a message." | Pass |
| 5 | Invalid phone format | `12345`, `09abc234567`, `9171234567`, `+63917123456`, `+0639171234567` | Rejected with field error | All 5 rejected: "Enter a valid phone number…" | Pass |
| 6 | PH local format | `09171234567` | Normalized to `+639171234567` | `+639171234567` | Pass |
| 7 | Spaces and dashes | `0917 123-4567` | Normalized to `+639171234567` | `+639171234567` | Pass |
| 8 | Message length limit | 1,600 / 1,601 characters | 1,600 accepted, 1,601 rejected | As expected ("maximum is 1600") | Pass |
| 9 | Line break counting | 1,600 characters including a `\r\n` | Accepted, line break counts as 1 | Accepted, stored length 1,600 | Pass |
| 10 | Invalid input never reaches textbee | `abc`, `""` | No API call, nothing saved | `requests.post` not called, 0 records | Pass |
| 11 | Missing credentials | Empty `TEXTBEE_API_KEY` / `TEXTBEE_DEVICE_ID` | Friendly error, no API call, no crash | "The SMS service is not configured…", HTTP 200 | Pass |
| 12 | Invalid API key | textbee returns 401 | Friendly error, key not exposed | "textbee rejected the API key…", key not in page or logs | Pass |
| 13 | No enabled device | textbee returns 400 "No enabled device found" | Friendly error with textbee's reason | "…(No enabled device found). Make sure the textbee app is running…" | Pass |
| 14 | Plan limit reached | textbee returns 429 | Friendly error | "The textbee plan limit has been reached (free plan: 50 messages per day, 300 per month)." | Pass |
| 15 | Network connection error | `requests.ConnectionError` | Friendly network error | "Could not connect to textbee…" | Pass |
| 16 | Network timeout | `requests.Timeout` | Friendly timeout error | "textbee did not respond in time…" | Pass |
| 17 | Other provider error | HTTP 500, non-JSON body | Generic error with HTTP code | "The SMS provider returned an error (HTTP 500)…" | Pass |
| 18 | Failed attempt is saved and input kept | 401 from textbee | Record `not_submitted`, form keeps the message | Saved as `not_submitted`, message text still in form | Pass |
| 19 | Success text does not claim delivery | Successful send | Alert says "submitted", not "delivered" | Alert contains "submitted to textbee", no "delivered" | Pass |
| 20 | Request sent to textbee | Successful send | Correct URL, JSON body, `x-api-key` header, 15 s timeout | All match | Pass |
| 21 | SIM slot selection | `TEXTBEE_SIM_SLOT=1` | `simSlotIndex: 1` in request | `simSlotIndex: 1` | Pass |
| 22 | Status refresh → delivered | textbee batch status `delivered` | Record updated to `delivered` | Status `delivered`, alert 'is now "Delivered"' | Pass |
| 23 | Status refresh → failed with reason | `failed` + `errorMessage` | Status `failed`, reason saved | Reason "No SMS credit on SIM." saved and shown | Pass |
| 24 | Unknown status from textbee | `something-new` | Not saved, warning logged | Not saved | Pass |
| 25 | Refresh unsubmitted message | Record without batch ID | No API call, warning | "…never submitted to textbee…" | Pass |
| 26 | Refresh via GET | `GET /history/<id>/refresh/` | Refused | HTTP 405 | Pass |
| 27 | CSRF protection | POST without CSRF token | Refused | HTTP 403 | Pass |
| 28 | History dashboard | 1 pending + 1 not submitted | Correct counts and badges | total 2, submitted 1, failed 1; badges and error shown | Pass |

### Manual tests with the real phone (2026-11-14)

| # | Test case | Input | Expected | Actual | Pass/Fail |
|---|---|---|---|---|---|
| M1 | Real SMS to a group member's number | Valid PH number, short text, Globe SIM | Message arrives; status reaches *Sent*/*Delivered* | Message arrived; *Refresh status* showed **Delivered** | Pass |
| M2 | SIM without load | Same number, TNT SIM with no load | Failure shown, not a false success | Status **Failed**; textbee reported "SMS failed on device… no SMS credit on SIM"; fixed by sending from the Globe SIM (`TEXTBEE_SIM_SLOT=1`) | Pass (handled) |
| M3 | Validation in the browser | Empty fields; `12345` | Red field errors, nothing sent | _(fill in)_ | _(fill in)_ |
| M4 | Character / segment counter | Plain text, 161 characters, emoji | 1 segment → 2 segments; Unicode note appears | _(fill in)_ | _(fill in)_ |

---

## Security Practices

- **No secrets in the code or on GitHub:** the API key, device ID and Django secret key are read from environment variables loaded from `.env` by python-dotenv. `.env` is in `.gitignore`; only `.env.example` with placeholders is committed.
- **`SECRET_KEY` and `DEBUG` come from the environment.** The app refuses to start without a secret key, and `DEBUG` defaults to `False`.
- **The API key is never logged or displayed:** it is only placed in the `x-api-key` request header. Error messages and logs contain the HTTP status and textbee's error text, never the key (checked by the unit tests).
- **Users see friendly messages only,** never tracebacks or raw provider responses.
- **CSRF protection** on every form, including the *Refresh status* buttons. Actions that change data accept **POST only**.
- **Input validation** happens on the server before any API call; the JavaScript counter is only a convenience.
- **Bootstrap is loaded with Subresource Integrity (SRI) hashes,** so the browser rejects a modified CDN file.
- **Authorized recipients only:** we only send test messages to group members' own numbers, with their permission.

---

## Known Limitations

- **The Android phone must stay online** with the textbee app running; if it is off, messages wait or fail.
- **textbee free plan limits:** 50 messages per day, 300 per month, 1 device.
- **Regular carrier SMS charges apply** to the sending SIM; the SIM needs load or a promo covering the recipient's network.
- **Delivery reports depend on the carrier.** Some carriers never send them, so a message can stay at *Sent* even when it arrived.
- **Status updates need a manual refresh.** textbee can push status updates through webhooks, but that requires a public URL, which a locally running app does not have.
- **Refreshing old messages after changing phones:** the status lookup uses the device ID currently in `.env`, so messages sent from a previously linked phone can no longer be refreshed.
- **No user login:** anyone who can open the app can send messages and see the history, so it is meant to run locally, not on the public internet.
- **One recipient per message** (textbee supports several; the form intentionally accepts one).
