# Free Render deployment for learning

This Blueprint deploys the Vite frontend, Django API, and PostgreSQL database on Render's free plans. It is for practice only, not for real store operations.

## Deploy

1. Push the deployment files to the GitHub branch you want to publish. The required files are `render.yaml`, `backend/config/wsgi.py`, and the Gunicorn dependency in `backend/requirements.txt`.
2. Create a Render account and connect it to the GitHub repository.
3. In Render, choose **New → Blueprint**, select this repository, then apply the Blueprint from `render.yaml`.
4. When Render asks for the initial environment values, enter a Django superuser username, email, and a strong password. These are stored as Render secrets and are used once to create the learning account.
5. Wait for the database and API to deploy, then for the frontend build to finish. Open the `momand-super-store` static site URL shown in Render and sign in through **Admin Login**.

The initial API deploy runs migrations, populates shipping countries, collects Django static files, then creates an admin account, staff roles, and sample catalogue data. New deploys apply migrations and rebuild static files; the one-time initialization command does not run again.

## Free tier limits

- The Django API sleeps after 15 minutes without traffic and can take about a minute to wake up.
- Render's free PostgreSQL database expires 30 days after creation. Download a backup before it expires if you want to keep the learning data.
- This learning setup does not include durable media storage. Product image uploads are not served in production yet; local files would also disappear after a restart, sleep, or deploy.
- Password reset emails are printed to the API service logs because SMTP is not configured.
- Render provides an `onrender.com` address and HTTPS, so buying a domain is unnecessary for this learning deployment.

See Render's [free service limits](https://render.com/docs/free) and [Blueprint documentation](https://render.com/docs/blueprint-spec).
