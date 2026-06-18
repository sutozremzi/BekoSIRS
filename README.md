# BekoSIRS

BekoSIRS is a full-stack smart inventory, delivery, and recommendation system built for Beko product workflows. The project includes a Django REST backend, a React web admin panel, and an Expo mobile application for customer, seller, admin, and delivery use cases.

## Highlights

- Role-based authentication and authorization with JWT
- Product, category, customer, review, service request, and delivery workflows
- React web admin panel with dashboards, charts, filters, and management screens
- Expo mobile app with authentication, product browsing, wishlist, profile, notifications, and delivery flows
- Hybrid recommendation engine with collaborative, content-based, and popularity-based signals
- Stock intelligence and sales forecasting modules
- Delivery planning, route optimization, and assignment workflows
- Biometric login and liveness-related backend integration
- Test coverage across backend, web, and mobile modules

## Tech Stack

- **Backend:** Python, Django, Django REST Framework, Simple JWT
- **Web:** React, TypeScript, Vite, Axios, Recharts, Leaflet
- **Mobile:** React Native, Expo, TypeScript, Expo Router
- **Database:** PostgreSQL / Supabase-compatible configuration
- **ML:** scikit-learn, pandas, NumPy, DeepFace
- **DevOps:** Docker, GitHub Actions, Gunicorn, Nginx deployment assets

## Project Structure

```text
BekoSIRS_api/       Django REST API, ML modules, migrations, tests
BekoSIRS_Web/       React + TypeScript web admin panel
BekoSIRS_Frontend/  Expo React Native mobile application
.github/            GitHub Actions workflows
docker-compose.yml  Local service orchestration
start-all.sh        Helper script for local startup
```

## Local Setup

### Backend

```bash
cd BekoSIRS_api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

On Windows, activate the virtual environment with:

```powershell
venv\Scripts\activate
```

### Web Admin Panel

```bash
cd BekoSIRS_Web
npm install
npm run dev -- --host
```

Default local web URL:

```text
http://localhost:5173
```

### Mobile App

```bash
cd BekoSIRS_Frontend
npm install
npx expo start
```

Configure the mobile API URL in a local `.env` file:

```text
EXPO_PUBLIC_API_URL=http://localhost:8000/
EXPO_PUBLIC_PROD_API_URL=https://api.bekosirs.com/
```

For physical device testing, replace `localhost` with your computer's LAN IP address.

## API Documentation

When the backend is running, Swagger UI is available at:

```text
http://localhost:8000/api/schema/swagger-ui/
```

Main API base URL:

```text
http://localhost:8000/api/v1/
```

## Testing

Backend:

```bash
cd BekoSIRS_api
python -m pytest
```

Web:

```bash
cd BekoSIRS_Web
npm run test:run
npm run build
```

Mobile:

```bash
cd BekoSIRS_Frontend
npm test
```

## Security Notes

- Keep `.env` files, local database files, private keys, logs, and generated media out of git.
- Use environment variables for API URLs, database credentials, JWT secrets, and production settings.
- Review authentication, role permissions, and serializer exposure before production deployment.
- Do not commit real user data, production exports, or private service credentials.

## Status

This repository is maintained as a senior capstone and portfolio project. It demonstrates full-stack product development, mobile integration, operational dashboards, role-based workflows, and ML-assisted inventory intelligence.
