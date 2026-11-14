# Demo Video Script (target ≈ 6 minutes, allowed 3–10)

**Speakers:** **JP** = John Paul Palaran (backend) · **EG** = Eian Gabriel Aguilar (frontend & QA)

## Before recording

**Security (do all of these):**
- [ ] **Close the `.env` tab in VS Code** and make sure it is not visible in the file explorer preview. Only ever open `.env.example` on screen.
- [ ] **Do not open the textbee dashboard** pages showing the API key. If you show the dashboard at all, show only the device list.
- [ ] Close other browser tabs, email, chat apps and notifications that could pop up.
- [ ] The `runserver` terminal is fine to show (it contains no secrets).

**App and phones:**
- [ ] The textbee phone is charged, online, textbee app open, SIM with load selected (`TEXTBEE_SIM_SLOT`).
- [ ] Recipient phone (a member's own phone) is ready to show on camera or via screen mirroring (e.g. scrcpy).
- [ ] Do one test send beforehand so you know the SMS arrives.
- [ ] History contains only clean test messages. To start fresh: `python manage.py shell -c "from sms_app.models import SMSMessage; SMSMessage.objects.all().delete()"`
- [ ] `python manage.py runserver` is running; browser at http://127.0.0.1:8000/ zoomed to ~125% so text is readable.
- [ ] Prepare a short, clean demo message, e.g. *"Hello from our IT 120 Django SMS app!"*

---

## Script

### 1. Introduction and purpose · 0:00–0:35 · JP
> "Good day! We are John Paul Palaran and Eian Gabriel Aguilar, and this is our IT 120 project: a Django web application for sending SMS.
> The app lets a user enter a Philippine mobile number and a message, checks the input, and sends a real text message through textbee.dev, an SMS gateway that uses our own Android phone and SIM. It also keeps a history of every attempt and tracks whether each message was actually delivered.
> We used textbee instead of Twilio because Twilio's free trial expires and only texts verified numbers, while textbee's free plan sends real SMS to any PH number."

### 2. UI walkthrough · 0:35–1:05 · EG
*Screen: Send SMS page.*
> "This is the main page. We built it with Bootstrap 5. At the top is the navigation bar with *Send SMS* and *History*. The card has the recipient number field, which accepts +63 format or the local 09 format, the message box with a live counter below it, and the Send SMS button. The note at the bottom reminds the user that *submitted* is not the same as *delivered*."

### 3. Sending a real SMS · 1:05–2:00 · JP
*Screen: show the textbee phone with the app online (camera or mirror) for a few seconds, then the browser.*
> "This is our sender phone with the textbee app running. Now I'll send a message to Eian's phone."

*Type the recipient as `09…` (local format) and the demo message. Click **Send SMS**.*
> "When I click Send, Django validates the form first. Then our `services.py` module calls textbee's REST API with the API key in a request header. textbee pushes the message to the phone, and the phone sends it through the SIM like a normal text."

### 4. Success feedback · 2:00–2:30 · JP
*Screen: green alert.*
> "The green message says the SMS was *submitted to textbee, status pending*. We are careful not to say *delivered* here: a successful API call only means textbee accepted it. Notice the number was converted from 09 format to +63 automatically."

*Show the recipient phone receiving the SMS.*
> "And here it is arriving on Eian's phone."

### 5. Validation and error handling · 2:30–3:25 · EG
*Screen: Send SMS page.*
> "Now some error tests. First, I'll click Send with both fields empty."

*Click Send.* → red errors under both fields.
> "The form is rejected and each field shows its own error. Nothing is sent to textbee."

*Type `12345` as the number and `Test` as the message. Click Send.*
> "An invalid number also gets a clear message with an example of the correct format."

*Open a second terminal (keep `runserver` running in the first) and run `python manage.py test sms_app`.*
> "For errors we can't safely trigger live, like a wrong API key, a network failure or the daily limit, we wrote 33 automated tests. They fake textbee's responses, so no real SMS is sent, and they check that every error shows a friendly message and never exposes the API key. All 33 pass."

### 6. History dashboard and status refresh · 3:25–4:15 · EG
*Screen: History page.*
> "The History page saves every attempt, successful or failed. At the top are totals: all attempts, submitted, and failed. Each status has its own badge colour, explained in the guide below the table."

*Click **Refresh status** on the message just sent.*
> "Refresh status asks textbee for the latest status of this message. It changed from *Pending* to *Sent*, or *Delivered* if the carrier sent a delivery report. This is how we tell submission apart from real delivery. If a message fails, the reason from textbee is shown here too, for example when the SIM has no load."

### 7. Character and segment counter · 4:15–4:40 · EG
*Screen: Send SMS page. Type a sentence, then paste a long text, then add an emoji.*
> "As I type, the counter shows characters out of 1,600 and how many SMS segments the message needs. A normal SMS holds 160 characters; longer messages are split into parts of 153. When I add an emoji, the message switches to Unicode, so a segment holds only 70 characters, and the app warns about it."

### 8. Technologies and security · 4:40–5:30 · JP
*Screen: VS Code. Open `.env.example`, then `.gitignore`, then briefly `sms_app/services.py`.*
> "We used Python, Django 5.2, the requests library for the API calls, python-dotenv, Bootstrap 5, and SQLite.
> For security, the API key, device ID and Django secret key are stored in a `.env` file that is never uploaded. This is the `.env.example` file we share instead; it only has placeholders. `.gitignore` excludes `.env`, the database and the virtual environment.
> In `services.py`, the key is only used in the request header; it is never logged or shown to the user. All forms use Django's CSRF protection, and the refresh button only works with POST."

### 9. Member contributions · 5:30–6:10 · JP then EG
*Screen: GitHub repository → commit history (or Insights → Contributors).*

**JP:**
> "I handled the backend: the Django project setup and settings, the SMSMessage model, the views and URLs, and the textbee integration in services.py with all the error handling, the status refresh and the SIM selection."

**EG:**
> "I handled the frontend and testing: the form and phone validation, the Bootstrap templates, the character counter, the history dashboard, the 33 unit tests, and the README. Our commit history and pull requests on GitHub show each of our contributions, and we reviewed each other's pull requests."

### 10. Closing · 6:10–6:20 · EG
> "That's our Django SMS application. Thank you for watching!"

---

## Timing summary

| Part | Time | Speaker |
|---|---|---|
| 1. Introduction | 0:35 | JP |
| 2. UI walkthrough | 0:30 | EG |
| 3. Sending a real SMS | 0:55 | JP |
| 4. Success feedback | 0:30 | JP |
| 5. Validation and error tests | 0:55 | EG |
| 6. History and status refresh | 0:50 | EG |
| 7. Counter | 0:25 | EG |
| 8. Technologies and security | 0:50 | JP |
| 9. Contributions | 0:40 | JP + EG |
| 10. Closing | 0:10 | EG |
| **Total** | **≈ 6:20** | |

If an SMS takes long to arrive, keep talking through part 4 and show the phone once it arrives. Stay under 10 minutes; anything between 3 and 10 is accepted.
