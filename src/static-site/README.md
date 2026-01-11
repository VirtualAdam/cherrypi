# Static Site Hosting

This directory hosts a static website accessible from the CherryPi navigation bar.

## Privacy Note

The `index.html` file is **gitignored** to keep your private content out of the public CherryPi repo. Only the infrastructure files (Dockerfile, nginx.conf) are committed.

## Setup

### 1. Copy your HTML file to the Pi

From your local machine, use SCP to copy your HTML file:

```powershell
# From Windows (PowerShell)
scp "C:\path\to\your\file.html" pi@<pi-ip>:~/CherryPi/src/static-site/index.html
```

```bash
# From Mac/Linux
scp /path/to/your/file.html pi@<pi-ip>:~/CherryPi/src/static-site/index.html
```

### 2. Build and deploy

On the Pi:

```bash
cd ~/CherryPi
docker compose build family-foundation
docker compose up -d family-foundation
```

Or rebuild everything:

```bash
docker compose up -d --build
```

## Access

- **Local**: http://localhost:8080
- **On network**: http://<pi-ip>:8080
- **From CherryPi**: Click the "🏠 Foundation" link in the navigation bar

## Updating the site

Whenever you update your HTML file:

1. Copy the new file to the Pi (SCP command above)
2. Rebuild: `docker compose build family-foundation && docker compose up -d family-foundation`

## Files

| File | In Git? | Purpose |
|------|---------|---------|
| `Dockerfile` | ✅ Yes | Container definition |
| `nginx.conf` | ✅ Yes | Web server config |
| `index.example.html` | ✅ Yes | Placeholder template |
| `index.html` | ❌ No | **Your private content** |

