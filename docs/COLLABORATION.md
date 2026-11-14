# Collaboration Plan

Group of 2. The three suggested roles (setup/logic, UI/validation, provider/testing/docs) are divided between us. Every pull request is reviewed by the **other** member before it is merged.

| Member | GitHub | Area |
|---|---|---|
| John Paul Palaran | `newtxrsh` | Backend: project setup, model, views, URLs, textbee service, error handling, status refresh |
| Eian Gabriel Aguilar | _(add username)_ | Frontend & QA: form validation, templates/UI, counter, dashboard, tests, README, demo |

## Branches and commits

The branches build on each other, in this order:

| # | Branch | Author | Commits | Reviewer |
|---|---|---|---|---|
| 0 | `main` | John Paul | `Set up Django project and sms_app with env-based textbee settings` | (base) |
| 1 | `member1/model` | John Paul | `Add SMSMessage model with textbee status choices and admin` | Eian |
| 2 | `member2/forms-validation` | Eian | `Add SMS form with E.164 and PH local number validation` | John Paul |
| 3 | `member1/textbee-service` | John Paul | `Add textbee SMS service, views, URLs and error handling`<br>`Add SIM slot selection and save textbee failure reasons` | Eian |
| 4 | `member2/ui-dashboard` | Eian | `Add Bootstrap UI, history dashboard and live SMS counter` | John Paul |
| 5 | `member2/tests-docs` | Eian | `Add unit tests with mocked textbee API`<br>`Add README with setup, textbee configuration and test results`<br>`Add collaboration plan and demo script` | John Paul |

## Publishing to GitHub

1. **Eian** creates an empty repository named `IT120-DJANGO` on GitHub (no README, no .gitignore, no license, since we already have them). Make it **public** so the instructor can open it, or keep it private and invite the instructor.
2. **Eian** adds John Paul: repository **Settings → Collaborators → Add people → `newtxrsh`**. John Paul accepts the invitation from his email.
3. **Eian** pushes all branches from the project folder:

   ```powershell
   git remote add origin https://github.com/<eian-username>/IT120-DJANGO.git
   git push -u origin main
   git push origin member1/model member2/forms-validation member1/textbee-service member2/ui-dashboard member2/tests-docs
   ```

   Pushing someone else's commits does not change their author. John Paul's commits still count for John Paul, as long as `janpolpalaran@gmail.com` is added and verified in his GitHub email settings.

## Pull requests and merge order

Open and merge the pull requests **one at a time, in this order**, each with base branch `main`:

| Order | Pull request | Opened by | Reviewed and merged by |
|---|---|---|---|
| 1 | `member1/model` → `main` | John Paul | Eian |
| 2 | `member2/forms-validation` → `main` | Eian | John Paul |
| 3 | `member1/textbee-service` → `main` | John Paul | Eian |
| 4 | `member2/ui-dashboard` → `main` | Eian | John Paul |
| 5 | `member2/tests-docs` → `main` | Eian | John Paul |

For each one:

1. **Open:** GitHub → **Pull requests → New pull request**, base `main`, compare the branch. Write a short description of what changed and how to test it.
2. **Review:** the other member reads the **Files changed** tab, leaves at least one comment or question, and clicks **Review changes → Approve**.
3. **Merge:** the reviewer clicks **Merge pull request** using **"Create a merge commit"**. Do not choose *Squash* or *Rebase*: a merge commit keeps each member's original commits in the history.
4. Only then open the next pull request. Because the branches build on each other, each new pull request shows only its own commits once the previous one is merged.

GitHub does not let you approve your own pull request, so John Paul must open pull requests 1 and 3 from his own account.

## After merging

```powershell
git checkout main
git pull
```

Remaining small tasks go on `main` as normal commits (or a short branch + pull request):

- **Eian:** fill in the repository URL, Eian's GitHub username and manual tests M3/M4 in the README.
- **John Paul:** run the full test suite on his own computer after cloning (`python manage.py test sms_app`) to confirm the setup instructions work.

## Making commits as the right person

Each member should commit from their own computer. If both work on one computer, set the author for that repository before committing:

```powershell
git config user.name "newtxrsh"                     # John Paul
git config user.email "janpolpalaran@gmail.com"

git config --unset user.name                         # back to Eian's global identity
git config --unset user.email
```
