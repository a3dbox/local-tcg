# Auth testing
- Login: POST /api/auth/login {"email":"admin@pokebinder.local","password":"admin123"} -> returns user + access_token + refresh_token
- Use Authorization: Bearer <access_token> for all /api endpoints
- GET /api/auth/me returns user
- POST /api/auth/refresh {"refresh_token": ...}
- Brute force: 5 failed logins per ip:email => 429 for 15 min
- Mongo: users.email unique index, bcrypt hash starts with $2b$
