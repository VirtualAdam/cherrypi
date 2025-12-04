#!/usr/bin/env python3
"""
CherryPi Auth Service - Magic QR Code Generator CLI

This script generates a magic QR code for device onboarding.
SECURITY: This script ONLY runs from a physical console (keyboard/monitor).
It will refuse to run over SSH connections.

The QR code is saved as an HTML file that can be opened in a browser,
or as a PNG image that can be viewed with any image viewer.

Usage (from physical console on Raspberry Pi):
    python3 generate_magic_qr.py
"""

import getpass
import json
import os
import sys
import tempfile
import time
import webbrowser

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import qrcode
    from qrcode.image.svg import SvgImage
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

import redis

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def check_physical_console():
    """
    Verify we're running on a physical console, not over SSH.
    Returns True if physical, False if remote.
    """
    ssh_indicators = ['SSH_CLIENT', 'SSH_TTY', 'SSH_CONNECTION']
    
    for var in ssh_indicators:
        if os.environ.get(var):
            return False
    
    if not sys.stdin.isatty():
        return False
    
    display = os.environ.get('DISPLAY', '')
    if display and not display.startswith(':'):
        return False
    
    return True


def generate_qr_html(url: str, code: str, expires_in: int) -> str:
    """Generate an HTML page with the QR code."""
    
    # Generate QR code as SVG using the qrcode library if available
    if HAS_QRCODE:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Generate SVG
        from io import BytesIO
        img = qr.make_image(image_factory=SvgImage)
        svg_buffer = BytesIO()
        img.save(svg_buffer)
        svg_data = svg_buffer.getvalue().decode('utf-8')
        # Remove XML declaration for embedding
        svg_data = svg_data.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
    else:
        # Fallback: Use an external QR code API (works but requires internet)
        svg_data = f'<img src="https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={url}" alt="QR Code">'
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CherryPi Magic Login</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            color: #fff;
        }}
        .container {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            max-width: 400px;
            width: 100%;
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 10px;
            color: #e94560;
        }}
        .subtitle {{
            color: #aaa;
            margin-bottom: 30px;
        }}
        .qr-container {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            display: inline-block;
        }}
        .qr-container svg, .qr-container img {{
            width: 250px;
            height: 250px;
        }}
        .code {{
            font-family: 'Courier New', monospace;
            font-size: 32px;
            font-weight: bold;
            letter-spacing: 4px;
            color: #e94560;
            margin: 20px 0;
        }}
        .expires {{
            color: #aaa;
            font-size: 14px;
        }}
        .timer {{
            font-size: 24px;
            color: #e94560;
            margin-top: 10px;
        }}
        .expired {{
            color: #ff6b6b;
        }}
        .instructions {{
            margin-top: 30px;
            text-align: left;
            color: #ccc;
            font-size: 14px;
        }}
        .instructions ol {{
            padding-left: 20px;
        }}
        .instructions li {{
            margin: 8px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🍒 CherryPi</h1>
        <p class="subtitle">Magic Login QR Code</p>
        
        <div class="qr-container">
            {svg_data}
        </div>
        
        <p>Or enter code manually:</p>
        <div class="code">{code}</div>
        
        <p class="expires">This code expires in:</p>
        <div class="timer" id="timer">{expires_in // 60}:{expires_in % 60:02d}</div>
        
        <div class="instructions">
            <ol>
                <li>Open CherryPi on your mobile device</li>
                <li>Tap "Login with QR Code"</li>
                <li>Scan this QR code or enter the code above</li>
            </ol>
        </div>
    </div>
    
    <script>
        let timeLeft = {expires_in};
        const timerEl = document.getElementById('timer');
        
        function updateTimer() {{
            if (timeLeft <= 0) {{
                timerEl.textContent = 'EXPIRED';
                timerEl.classList.add('expired');
                return;
            }}
            
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            timerEl.textContent = minutes + ':' + seconds.toString().padStart(2, '0');
            
            if (timeLeft <= 30) {{
                timerEl.classList.add('expired');
            }}
            
            timeLeft--;
            setTimeout(updateTimer, 1000);
        }}
        
        updateTimer();
    </script>
</body>
</html>"""
    
    return html


def generate_qr_png(url: str, output_path: str):
    """Generate a PNG QR code image."""
    if not HAS_QRCODE:
        print_error("qrcode library not installed. Cannot generate PNG.")
        return False
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    return True


def request_magic_code(redis_client, admin_token: str) -> dict:
    """Request a magic code from the auth service via Redis."""
    import uuid
    
    request_id = str(uuid.uuid4())
    
    # Subscribe to responses first
    pubsub = redis_client.pubsub()
    pubsub.subscribe('auth:responses')
    
    # Send request
    request = {
        'cmd': 'magic_generate',
        'request_id': request_id,
        'token': admin_token
    }
    
    redis_client.publish('auth:requests', json.dumps(request))
    
    # Wait for response
    start_time = time.time()
    timeout = 10.0
    
    while time.time() - start_time < timeout:
        message = pubsub.get_message(timeout=0.5)
        if message and message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                if data.get('request_id') == request_id:
                    pubsub.unsubscribe()
                    pubsub.close()
                    return data
            except json.JSONDecodeError:
                pass
    
    pubsub.unsubscribe()
    pubsub.close()
    return {'success': False, 'error': 'Timeout waiting for auth service'}


def login_admin(redis_client, username: str, password: str) -> dict:
    """Login as admin to get a token."""
    import uuid
    
    request_id = str(uuid.uuid4())
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe('auth:responses')
    
    request = {
        'cmd': 'login',
        'request_id': request_id,
        'username': username,
        'password': password
    }
    
    redis_client.publish('auth:requests', json.dumps(request))
    
    start_time = time.time()
    timeout = 10.0
    
    while time.time() - start_time < timeout:
        message = pubsub.get_message(timeout=0.5)
        if message and message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                if data.get('request_id') == request_id:
                    pubsub.unsubscribe()
                    pubsub.close()
                    return data
            except json.JSONDecodeError:
                pass
    
    pubsub.unsubscribe()
    pubsub.close()
    return {'success': False, 'error': 'Timeout waiting for auth service'}


def main():
    print(f"\n{Colors.BOLD}╔════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}║  CherryPi Magic QR Code Generator      ║{Colors.END}")
    print(f"{Colors.BOLD}╚════════════════════════════════════════╝{Colors.END}\n")
    
    # Security check: Physical console
    print("Checking environment...", end=" ")
    if not check_physical_console():
        print()
        print_error("SECURITY ERROR: Remote connection detected!")
        print_error("This utility can ONLY be run from a physical console.")
        print_error("Please connect a keyboard and monitor to the Raspberry Pi.")
        sys.exit(1)
    print_success("Physical Console Detected")
    
    # Connect to Redis
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = int(os.environ.get('REDIS_PORT', 6379))
    
    print(f"Connecting to Redis at {redis_host}:{redis_port}...", end=" ")
    try:
        redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        redis_client.ping()
        print_success("Connected")
    except redis.ConnectionError as e:
        print()
        print_error(f"Failed to connect to Redis: {e}")
        sys.exit(1)
    
    # Admin login
    print(f"\n{Colors.BOLD}Admin Authentication Required{Colors.END}")
    print("Only admins can generate magic QR codes.\n")
    
    username = input("Admin username: ").strip()
    password = getpass.getpass("Admin password: ")
    
    print("\nAuthenticating...", end=" ")
    login_result = login_admin(redis_client, username, password)
    
    if not login_result.get('success'):
        print()
        print_error(f"Login failed: {login_result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    if login_result.get('role') != 'admin':
        print()
        print_error("Access denied: Admin role required")
        sys.exit(1)
    
    print_success("Authenticated as admin")
    
    admin_token = login_result.get('token')
    
    # Generate magic code
    print("\nGenerating magic code...", end=" ")
    result = request_magic_code(redis_client, admin_token)
    
    if not result.get('success'):
        print()
        print_error(f"Failed to generate code: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    code = result.get('code')
    expires_in = result.get('expires_in', 300)
    print_success(f"Code generated: {code}")
    
    # Build the magic login URL
    # This should be the frontend URL that handles magic codes
    frontend_url = os.environ.get('CHERRYPI_URL', 'http://cherrypi.local:3000')
    magic_url = f"{frontend_url}/magic?code={code}"
    
    # Generate output files
    output_dir = os.environ.get('MAGIC_QR_OUTPUT_DIR', '/tmp/cherrypi')
    os.makedirs(output_dir, exist_ok=True)
    
    html_path = os.path.join(output_dir, 'magic_qr.html')
    png_path = os.path.join(output_dir, 'magic_qr.png')
    
    # Generate HTML
    html_content = generate_qr_html(magic_url, code, expires_in)
    with open(html_path, 'w') as f:
        f.write(html_content)
    print_success(f"HTML saved: {html_path}")
    
    # Generate PNG if qrcode library is available
    if HAS_QRCODE:
        if generate_qr_png(magic_url, png_path):
            print_success(f"PNG saved: {png_path}")
    else:
        print_warning("qrcode library not installed - PNG not generated")
        print_info("Install with: pip install qrcode[pil]")
    
    # Print summary
    print(f"\n{Colors.BOLD}═══════════════════════════════════════════{Colors.END}")
    print(f"\n{Colors.BOLD}Magic Code:{Colors.END} {Colors.GREEN}{code}{Colors.END}")
    print(f"{Colors.BOLD}URL:{Colors.END} {magic_url}")
    print(f"{Colors.BOLD}Expires in:{Colors.END} {expires_in // 60} minutes")
    print(f"\n{Colors.BOLD}═══════════════════════════════════════════{Colors.END}")
    
    # Ask if user wants to open in browser
    print("\nTo display the QR code:")
    print(f"  1. Open in browser: chromium-browser {html_path}")
    print(f"  2. View image: gpicview {png_path}")
    
    open_browser = input("\nOpen in browser now? [Y/n]: ").strip().lower()
    if open_browser != 'n':
        try:
            webbrowser.open(f'file://{html_path}')
            print_success("Opened in browser")
        except Exception as e:
            print_warning(f"Could not open browser: {e}")
            print_info(f"Please open manually: {html_path}")


if __name__ == '__main__':
    main()
