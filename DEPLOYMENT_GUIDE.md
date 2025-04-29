# 1. System at a Glance

| Layer         | What Runs                                         | Key File         |
|---------------|---------------------------------------------------|------------------|
| Oracle VM     | Ubuntu 22.04 (Ampere A1 ARM) • ports 22/80/443 open | –                |
| Docker Compose| backend + caddy services                           | docker-compose.yml |
| backend       | Gunicorn → Flask-Socket.IO app (w/ undo-redo)     | server.py + requirements.txt |
| caddy         | HTTPS termination, ACME certificates, reverse-proxy | Caddyfile        |
| Volumes       | /data (TLS certs) • /config (autosave)            | Docker named volumes |
| nginx         | –                                                 | –                |

Internet → Caddy :443/80 → Gunicorn (Flask app) :5000

---

# 2. What Each Code File Does

| File                 | Purpose                                                              | Change Notes                                                                                                     |
|----------------------|----------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| server.py            | Flask-Socket.IO server: sessions dict, undo/redo stacks              | Keep interface events stable (update_paths, undo_request, etc.) so the React client doesn’t break.               |
| requirements.txt     | Python deps (pinned)                                                 | Flask 2.2.5 + Jinja 3.0.3 chosen for compatibility (bump together if upgrading).                                  |
| Dockerfile           | 6-line slim image (ARM/AMD)                                          | `CMD gunicorn -k eventlet … server:app` – change module here if main file is renamed.                            |
| docker-compose.yml   | Orchestrates build/run; mounts Caddyfile                             | Don’t expose backend port 5000 to host; Caddy talks on the Docker network.                                       |
| Caddyfile            | Declares e-mail + site block + proxies                               | First line must match DNS host-name. Reload Caddy after edits.                                                   |
| README / this guide  | Ops reference                                                        | Update when you add env vars, volumes, etc.                                                                      |

---

# 3. Daily-to-Weekly Tasks

| Task                | Command (run on VM unless noted)                                          |
|---------------------|---------------------------------------------------------------------------|
| SSH in              | `ssh -i ~/.ssh/oci_whiteboard ubuntu@<VM_IP>`                             |
| View container status| `docker compose ps`                                                       |
| Follow logs         | `docker compose logs -f backend` / `docker compose logs -f caddy`          |
| System updates      | `sudo apt update && sudo apt upgrade -y` (monthly)                         |
| Renew TLS           | Caddy auto-renews; nothing to do.                                          |
| Restart services    | `docker compose restart caddy` (or backend)                                |

---

# 4. Push-to-Deploy Workflow

1. Edit locally → commit → `git push`.
2. On VM:
    ```bash
    cd ~/Websocket     # project root
    git pull
    docker compose up -d --build
    ```
    (`--build` ensures new Python deps are baked in.)

Optional: automate step 2 via a GitHub Action + ssh-agent or Watchtower.

---

# 5. Common Pitfalls & Fixes

| Symptom                                               | Root Cause                            | Fix                                                                                          |
|-------------------------------------------------------|---------------------------------------|----------------------------------------------------------------------------------------------|
| `curl -I https://… → 502 Bad Gateway`                 | backend container crashed             | `docker compose logs backend` → missing package or bad import. Re-pin versions.              |
| Caddy log: “challenge failed … 404”                   | DNS points to wrong IP / port 80 blocked | Correct A-record; ensure OCI security list has TCP 80/443 open.                              |
| Caddy log: “remote error: tls: no application protocol”| Site block name ≠ DNS host            | First line of `Caddyfile` must be `whiteboard.tutorspace.app {`.                            |
| Gunicorn crash: `ModuleNotFoundError: No module named 'server'` | File renamed            | Edit Dockerfile CMD (mainfile:app) or add wrapper `server.py`.                               |
| LibreSSL error in browser                             | Certificate not yet issued            | Wait 1-2 min after Caddy reload; check `docker compose logs caddy`.                          |
| React fails on `ws://` vs `wss://`                    | Mixed-content block                   | Always use `wss://<host>` from HTTPS pages.                                                 |

---

# 6. Extending / Upgrading

| Need                        | What to Change                                                                            |
|-----------------------------|--------------------------------------------------------------------------------------------|
| More RAM / CPUs            | In OCI console → Instance Details → Shape → Raise OCPU/Memory (up to free 4 OCPU / 24 GB). |
| Env variables              | Add under `backend.environment:` in `docker-compose.yml`.                                  |
| Persist uploads            | Add a volumes mount (e.g., `./data:/app/uploads`).                                         |
| Zero-downtime code hot-reload | Switch CMD to `gunicorn --reload …` (dev only).                                        |
| Auto update containers     | Run Watchtower: `docker run -d -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower --label-enable`. |
| Upgrade to Flask 3         | Change `flask==3.x`, remove the Jinja pin, rebuild.                                        |

---

# 7. Handy One-Liners

| Purpose                                    | Command                                                  |
|--------------------------------------------|----------------------------------------------------------|
| Run a one-shot shell inside backend        | `docker compose exec backend sh`                         |
| Check open ports from VM                   | `ss -tulpn`                                             |
| Test internal proxy from Caddy             | `docker compose exec caddy curl -s http://backend:5000/` |
| Free disk usage                            | `docker system prune -af`                                |
| Rebuild only backend                       | `docker compose build backend && docker compose up -d backend` |
| Get public IP quickly                      | `curl -s https://checkip.amazonaws.com`                  |

---

# 8. Security Notes

• SSH key-only login (no passwords) – rotate keys if staff leave.  
• Enable ufw in addition to OCI security list if you want host-level firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw enable
```

• Keep packages current (`apt upgrade`, `pip list --outdated`).  
• Oracle “Always-Free” bandwidth: 10 TB outbound / mo – monitor with OCI monitoring. Exceeding quota bills at ~$0.008/GB.

---

# 9. When Things Go Really Wrong

• Snapshot the boot volume in OCI before major surgery.  
• Spin up a second free VM → clone repo → `docker compose up -d` to A/B test.  
• Roll DNS over when satisfied.