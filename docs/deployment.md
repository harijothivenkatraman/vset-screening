# Self-Hosted Deployment Guide (VPS / Lightsail)

This guide covers deploying the vSET application using Docker Compose on a VPS (like AWS Lightsail, DigitalOcean, etc.).

## 1. Domain Assignment and Static IP

When deploying on a cloud provider like AWS Lightsail:
1. **Assign a Static IP**: Make sure you assign a static IP address to your instance so it doesn't change upon reboot.
2. **DNS Configuration**: In your domain registrar's DNS settings, create an `A` record for your domain (e.g., `vset.example.com`) pointing to the static IP address of your instance.

## 2. Enabling HTTPS via Caddy

By default, the Caddy server is configured to serve the application over HTTP on port `80`. This is suitable for testing via IP address.

To enable automatic HTTPS (TLS via Let's Encrypt):
1. Open the `frontend/Caddyfile`.
2. Locate the `:80` block at the top of the file.
3. Replace `:80` with your fully qualified domain name (e.g., `vset.example.com`).
4. Rebuild and restart the web container:
   ```bash
   docker-compose up -d --build web
   ```
Caddy will automatically provision and renew the Let's Encrypt certificates.

## 3. CORS Configuration

The `frontend/Caddyfile` is configured to restrict cross-origin resource sharing (CORS). The `Access-Control-Allow-Origin` is set to `{origin}`, which strictly limits API access to requests coming from the same origin. It also adds several security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

*(Note: The file must use LF line endings, which is ensured during the creation/checkout process on Linux/macOS.)*
