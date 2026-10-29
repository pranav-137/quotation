# Quotation Maker (Django)

- Public landing page -> "Sign in" -> **Google** or **email + 6-digit code**.
- After sign-in: fill the form -> **Download PDF**. Quotation data is NOT stored.
- Only the user's email is saved (in the database), viewable at `/admin/` and exportable as CSV.

## Run locally
```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations accounts   # only needed if accounts/migrations has no 0001 file
python manage.py migrate
python manage.py createsuperuser           # for /admin/
python manage.py runserver
```
Locally, the email code is printed in the terminal (console backend). Locally it uses SQLite.

## Google sign-in setup
1. https://console.cloud.google.com -> create/select a project.
2. APIs & Services -> OAuth consent screen -> External -> fill app name + your email. Publish the app (so anyone can sign in, not only test users).
3. Credentials -> Create credentials -> OAuth client ID -> **Web application**.
4. Authorized redirect URIs (add both):
   - `http://127.0.0.1:8000/accounts/google/callback/`
   - `https://YOUR-APP.vercel.app/accounts/google/callback/`
5. Set env vars `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
If these are empty, the Google button is hidden and only email-code sign-in is shown.

## Environment variables
| Name | Needed for | Example |
|---|---|---|
| DJANGO_SECRET_KEY | production | long random string |
| DJANGO_DEBUG | production | `0` |
| DATABASE_URL | production Postgres | set automatically by Vercel when you add a database |
| DJANGO_EMAIL_BACKEND | real emails | `django.core.mail.backends.smtp.EmailBackend` |
| EMAIL_HOST_USER / EMAIL_HOST_PASSWORD | real emails | Gmail address / Gmail App Password |
| GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET | Google login | from Google Cloud |
| CSRF_TRUSTED_ORIGINS | custom domain | `https://yourdomain.com` |

## Deploy to Vercel
1. Push this folder to GitHub (the `.gitignore` is included).
2. Vercel -> Add New Project -> import the repo. Vercel detects Django from `manage.py`.
3. Project -> Storage -> add a **Postgres** database (e.g. Neon). This sets `DATABASE_URL`.
4. Project -> Settings -> Environment Variables: add the variables from the table above.
5. Deploy.
6. Create the tables ONCE (from your computer, against the production database):
   ```bash
   npm i -g vercel && vercel link && vercel pull      # saves env vars to .env.local
   # copy DATABASE_URL from .env.local, then:
   export DATABASE_URL="postgresql://..."             # Windows: set DATABASE_URL=...
   python manage.py migrate
   python manage.py createsuperuser
   ```
7. Open `https://YOUR-APP.vercel.app/admin/` -> Users to see all collected emails.
