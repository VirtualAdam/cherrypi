# External Connectivity Guide for CherryPi

This guide will help you access your CherryPi dashboard from outside your home network (e.g., from your phone while away).

## Overview

To make your local CherryPi server accessible from the internet, you need to perform three main steps:
1.  **Assign a Static Local IP** to your Raspberry Pi.
2.  **Set up Port Forwarding** on your router.
3.  **Determine your Public IP** (or set up Dynamic DNS).

---

## Step 1: Assign a Static Local IP

Your router assigns IP addresses to devices (like your Raspberry Pi) automatically. These can change after a reboot. For port forwarding to work reliably, your Pi needs a permanent address.

### Method A: Router DHCP Reservation (Recommended)
This is the safest method as it's managed by your router.
1.  Log in to your router's admin page (usually `192.168.1.1` or `192.168.0.1`).
2.  Look for settings named **DHCP Server**, **LAN Setup**, or **Address Reservation**.
3.  Find your Raspberry Pi in the list of connected devices.
4.  Select it and assign it a permanent IP address (e.g., `192.168.1.50`).
5.  Save settings and reboot your Pi to ensure it gets the new IP.

### Method B: On the Raspberry Pi
If you can't access your router settings, you can configure the Pi directly.
1.  Open a terminal on your Pi.
2.  Edit the DHCP configuration file:
    ```bash
    sudo nano /etc/dhcpcd.conf
    ```
3.  Scroll to the bottom and add the following lines (adjusting for your network):
    ```text
    interface wlan0
    static ip_address=192.168.1.50/24
    static routers=192.168.1.1
    static domain_name_servers=1.1.1.1 8.8.8.8
    ```
    *(Note: Use `eth0` instead of `wlan0` if connected via ethernet cable. Check your current gateway IP with `ip route | grep default`)*.
4.  Save (Ctrl+O, Enter) and Exit (Ctrl+X).
5.  Reboot: `sudo reboot`.

---

## Step 2: Set up Port Forwarding

Port forwarding tells your router: "When someone from the internet knocks on this port, send them to the CherryPi."

1.  Log in to your router's admin page.
2.  Look for **Port Forwarding**, **Virtual Server**, or **NAT**.
3.  Create a new rule:
    *   **Service Name**: CherryPi
    *   **Protocol**: TCP
    *   **External Port**: 3000 (or 80 if you want to just type the address without `:3000`)
    *   **Internal Port**: 3000 (This MUST match the frontend port in `docker-compose.yml`)
    *   **Internal IP**: The Static IP you set in Step 1 (e.g., `192.168.1.50`).
4.  Save the rule.

---

## Step 3: Accessing from the Internet

### Find your Public IP
1.  While connected to your home network, Google "what is my ip".
2.  Note down the IP address (e.g., `123.45.67.89`).

### Test Connection
1.  Disconnect your phone from WiFi (use 4G/5G data).
2.  Open a browser and go to: `http://123.45.67.89:3000` (replace with your Public IP).
    *   *Note: If you used External Port 80 in Step 2, you can just visit `http://123.45.67.89`.*

### Dynamic DNS (Optional but Recommended)
Home Public IPs change occasionally. To avoid checking your IP constantly, use a Dynamic DNS service (like No-IP, DuckDNS, or DynDNS).
1.  Sign up for a free DDNS service.
2.  You'll get a domain like `my-cherrypi.duckdns.org`.
3.  Configure your router (if it supports DDNS) or install a DDNS updater on your Pi to keep the domain pointed to your IP.

---

## ⚠️ Security Warning

By following these steps, you are exposing your development server to the entire internet.
*   **The current setup uses a development server (`npm start`) which is not optimized for security.**
*   Anyone with your IP can control your switches.

**Recommendations for better security:**
1.  **Add Authentication**: Ensure your app has a login screen (it looks like `Login.js` exists, make sure it's active!).
2.  **Use a VPN**: Instead of port forwarding, set up a VPN server (like **WireGuard** or **Tailscale**) on your Pi. This is MUCH safer. You connect to the VPN on your phone, and then access the Pi as if you were at home, without exposing it to the public internet.
