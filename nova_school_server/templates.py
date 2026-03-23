from __future__ import annotations


PROJECT_TEMPLATES: dict[str, dict[str, object]] = {
    "python": {
        "label": "Python Starter",
        "runtime": "python",
        "main_file": "main.py",
        "files": {
            "main.py": """def greet(name: str) -> str:\n    if not name:\n        return \"Bitte gib deinen Namen ein.\"\n    return f\"Hallo {name}, willkommen im Python-Labor.\"\n\n\ndef read_name() -> str:\n    try:\n        return input(\"Name: \").strip()\n    except EOFError:\n        return \"\"\n\n\nif __name__ == \"__main__\":\n    print(greet(read_name() or \"Nova School\"))\n""",
        },
        "notebook": [{"id": "py-1", "title": "Python Zelle", "language": "python", "code": "numbers = [1, 2, 3, 4]\nprint(sum(numbers))\n"}],
    },
    "javascript": {
        "label": "JavaScript Starter",
        "runtime": "javascript",
        "main_file": "main.js",
        "files": {
            "main.js": """function welcome(name) {\n  return `Hallo ${name}, dies ist dein JavaScript-Projekt.`;\n}\n\nconsole.log(welcome('Nova School'));\n""",
        },
        "notebook": [{"id": "js-1", "title": "JavaScript Zelle", "language": "javascript", "code": "const values = [3, 5, 8];\nconsole.log(values.reduce((sum, value) => sum + value, 0));\n"}],
    },
    "cpp": {
        "label": "C++ Starter",
        "runtime": "cpp",
        "main_file": "main.cpp",
        "files": {
            "main.cpp": """#include <iostream>\n#include <vector>\n\nint main() {\n    std::vector<int> values{2, 4, 6, 8};\n    int sum = 0;\n    for (int value : values) {\n        sum += value;\n    }\n    std::cout << \"C++ Summe: \" << sum << std::endl;\n    return 0;\n}\n""",
        },
        "notebook": [],
    },
    "java": {
        "label": "Java Starter",
        "runtime": "java",
        "main_file": "Main.java",
        "files": {
            "Main.java": """public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hallo aus dem Java-Labor.\");\n    }\n}\n""",
        },
        "notebook": [],
    },
    "rust": {
        "label": "Rust Starter",
        "runtime": "rust",
        "main_file": "main.rs",
        "files": {
            "main.rs": """fn main() {\n    let values = [5, 7, 9];\n    let sum: i32 = values.iter().sum();\n    println!(\"Rust Summe: {}\", sum);\n}\n""",
        },
        "notebook": [],
    },
    "html": {
        "label": "HTML/CSS/JS Starter",
        "runtime": "html",
        "main_file": "index.html",
        "files": {
            "index.html": """<!doctype html>\n<html lang=\"de\">\n  <head>\n    <meta charset=\"utf-8\" />\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n    <title>Nova School Web-Labor</title>\n    <link rel=\"stylesheet\" href=\"styles.css\" />\n  </head>\n  <body>\n    <main class=\"hero\">\n      <h1>Nova School Web-Labor</h1>\n      <p>Diese Startseite liegt komplett auf dem Schulserver.</p>\n      <button id=\"ping\">Interaktion testen</button>\n      <output id=\"output\">Bereit</output>\n    </main>\n    <script src=\"app.js\"></script>\n  </body>\n</html>\n""",
            "styles.css": """:root {\n  color-scheme: light;\n  --bg: #f4efe2;\n  --panel: rgba(255, 255, 255, 0.9);\n  --ink: #182126;\n  --accent: #0e6e68;\n  --accent-strong: #8e3b2e;\n}\n\nbody {\n  margin: 0;\n  min-height: 100vh;\n  font-family: 'Segoe UI', sans-serif;\n  background: radial-gradient(circle at top, #f9f5eb 0%, #d8e5e0 45%, #b8cdc6 100%);\n  color: var(--ink);\n}\n\n.hero {\n  max-width: 680px;\n  margin: 12vh auto;\n  padding: 2rem;\n  background: var(--panel);\n  border: 1px solid rgba(24, 33, 38, 0.08);\n  border-radius: 28px;\n  box-shadow: 0 30px 70px rgba(24, 33, 38, 0.15);\n}\n\nbutton {\n  padding: 0.9rem 1.2rem;\n  border: none;\n  border-radius: 999px;\n  background: var(--accent);\n  color: white;\n  cursor: pointer;\n}\n\noutput {\n  display: block;\n  margin-top: 1rem;\n  color: var(--accent-strong);\n}\n""",
            "app.js": """const button = document.getElementById('ping');\nconst output = document.getElementById('output');\n\nbutton?.addEventListener('click', () => {\n  output.textContent = 'Die lokale Vorschau reagiert.';\n});\n""",
        },
        "notebook": [],
    },
    "node": {
        "label": "Node.js Starter",
        "runtime": "node",
        "main_file": "server.js",
        "files": {
            "package.json": """{\n  \"name\": \"nova-school-node-starter\",\n  \"version\": \"1.0.0\",\n  \"private\": true,\n  \"scripts\": {\n    \"start\": \"node server.js\",\n    \"dev\": \"node server.js\"\n  }\n}\n""",
            "server.js": """const http = require('http');\n\nconst server = http.createServer((request, response) => {\n  response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });\n  response.end(JSON.stringify({ ok: true, path: request.url, source: 'Nova School Node Starter' }));\n});\n\nserver.listen(3000, () => {\n  console.log('Node starter listening on http://127.0.0.1:3000');\n});\n""",
        },
        "notebook": [],
    },
    "frontend-lab": {
        "label": "Frontend Labor",
        "runtime": "html",
        "main_file": "index.html",
        "files": {
            "index.html": """<!doctype html>\n<html lang=\"de\">\n  <head>\n    <meta charset=\"utf-8\" />\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n    <title>Frontend Labor</title>\n    <link rel=\"stylesheet\" href=\"src/app.css\" />\n  </head>\n  <body>\n    <div class=\"shell\">\n      <header>\n        <p class=\"eyebrow\">Nova School</p>\n        <h1>Frontend Labor</h1>\n      </header>\n      <section id=\"cards\"></section>\n    </div>\n    <script type=\"module\" src=\"src/main.js\"></script>\n  </body>\n</html>\n""",
            "src/main.js": """const cards = document.getElementById('cards');\nconst topics = ['HTML', 'CSS', 'JavaScript', 'Node.js'];\n\ncards.innerHTML = topics\n  .map((topic, index) => `<article class=\"card\"><span>0${index + 1}</span><h2>${topic}</h2><p>Baue hier dein eigenes Frontend-Modul.</p></article>`)\n  .join('');\n""",
            "src/app.css": """body {\n  margin: 0;\n  font-family: Georgia, 'Times New Roman', serif;\n  background: linear-gradient(135deg, #f7eed9 0%, #d5e9df 50%, #b4d0dd 100%);\n  color: #182126;\n}\n\n.shell {\n  max-width: 1000px;\n  margin: 0 auto;\n  padding: 4rem 1.5rem 6rem;\n}\n\n.eyebrow {\n  letter-spacing: 0.18em;\n  text-transform: uppercase;\n  color: #8a412f;\n}\n\n#cards {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));\n  gap: 1rem;\n}\n\n.card {\n  padding: 1.4rem;\n  border-radius: 22px;\n  background: rgba(255, 255, 255, 0.82);\n  border: 1px solid rgba(24, 33, 38, 0.08);\n  box-shadow: 0 24px 60px rgba(24, 33, 38, 0.12);\n}\n""",
            "package.json": """{\n  \"name\": \"frontend-labor\",\n  \"version\": \"1.0.0\",\n  \"private\": true,\n  \"scripts\": {\n    \"start\": \"node dev-server.js\"\n  }\n}\n""",
            "dev-server.js": """const http = require('http');\nconst fs = require('fs');\nconst path = require('path');\n\nconst root = __dirname;\nconst mime = {\n  '.html': 'text/html; charset=utf-8',\n  '.css': 'text/css; charset=utf-8',\n  '.js': 'application/javascript; charset=utf-8',\n};\n\nhttp.createServer((request, response) => {\n  const target = request.url === '/' ? '/index.html' : request.url;\n  const filePath = path.join(root, target);\n  if (!filePath.startsWith(root)) {\n    response.writeHead(403);\n    response.end('forbidden');\n    return;\n  }\n  fs.readFile(filePath, (error, content) => {\n    if (error) {\n      response.writeHead(404);\n      response.end('not found');\n      return;\n    }\n    response.writeHead(200, { 'Content-Type': mime[path.extname(filePath)] || 'text/plain; charset=utf-8' });\n    response.end(content);\n  });\n}).listen(4173, () => console.log('Frontend Labor on http://127.0.0.1:4173'));\n""",
        },
        "notebook": [],
    },
    "distributed-system": {
        "label": "Distributed System Playground",
        "runtime": "python",
        "main_file": "services/coordinator.py",
        "files": {
            "topology.json": """{\n  \"namespace\": \"playground\",\n  \"services\": [\n    {\n      \"name\": \"coordinator\",\n      \"kind\": \"gateway\",\n      \"runtime\": \"python\",\n      \"entrypoint\": \"services/coordinator.py\",\n      \"port\": 48100\n    },\n    {\n      \"name\": \"worker-alpha\",\n      \"kind\": \"worker\",\n      \"runtime\": \"python\",\n      \"entrypoint\": \"services/worker.py\",\n      \"port\": 48101,\n      \"env\": {\n        \"WORKER_NAME\": \"worker-alpha\",\n        \"WORKER_MESSAGE\": \"Alpha verarbeitet Jobs\"\n      }\n    },\n    {\n      \"name\": \"worker-beta\",\n      \"kind\": \"worker\",\n      \"runtime\": \"python\",\n      \"entrypoint\": \"services/worker.py\",\n      \"port\": 48102,\n      \"env\": {\n        \"WORKER_NAME\": \"worker-beta\",\n        \"WORKER_MESSAGE\": \"Beta verarbeitet Jobs\"\n      }\n    }\n  ]\n}\n""",
            "services/coordinator.py": """import json\nimport os\nfrom http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\nfrom urllib.error import URLError\nfrom urllib.request import urlopen\n\nHOST = os.environ.get('NOVA_PLAYGROUND_BIND_HOST', '127.0.0.1')\nPORT = int(os.environ.get('NOVA_PLAYGROUND_PORT', '48100'))\nSERVICE_URLS = json.loads(os.environ.get('NOVA_PLAYGROUND_URLS', '{}'))\n\n\nclass Handler(BaseHTTPRequestHandler):\n    def do_GET(self):\n        workers = []\n        for name, url in SERVICE_URLS.items():\n            if name == 'coordinator':\n                continue\n            try:\n                with urlopen(f'{url}/health', timeout=1.5) as response:\n                    workers.append(json.loads(response.read().decode('utf-8')))\n            except URLError as exc:\n                workers.append({'service': name, 'status': 'offline', 'detail': str(exc)})\n        payload = {\n            'service': 'coordinator',\n            'port': PORT,\n            'workers': workers,\n            'message': 'Coordinator sammelt Worker-Status.',\n        }\n        body = json.dumps(payload).encode('utf-8')\n        self.send_response(200)\n        self.send_header('Content-Type', 'application/json; charset=utf-8')\n        self.send_header('Content-Length', str(len(body)))\n        self.end_headers()\n        self.wfile.write(body)\n\n    def log_message(self, format, *args):\n        return\n\n\nif __name__ == '__main__':\n    server = ThreadingHTTPServer((HOST, PORT), Handler)\n    print(f'Coordinator on http://{HOST}:{PORT}')\n    server.serve_forever()\n""",
            "services/worker.py": """import json\nimport os\nfrom http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\n\nHOST = os.environ.get('NOVA_PLAYGROUND_BIND_HOST', '127.0.0.1')\nPORT = int(os.environ.get('NOVA_PLAYGROUND_PORT', '48101'))\nWORKER_NAME = os.environ.get('WORKER_NAME', os.environ.get('NOVA_PLAYGROUND_SERVICE', 'worker'))\nWORKER_MESSAGE = os.environ.get('WORKER_MESSAGE', 'Worker bereit')\n\n\nclass Handler(BaseHTTPRequestHandler):\n    def do_GET(self):\n        payload = {\n            'service': WORKER_NAME,\n            'status': 'ready',\n            'message': WORKER_MESSAGE,\n            'port': PORT,\n        }\n        body = json.dumps(payload).encode('utf-8')\n        self.send_response(200)\n        self.send_header('Content-Type', 'application/json; charset=utf-8')\n        self.send_header('Content-Length', str(len(body)))\n        self.end_headers()\n        self.wfile.write(body)\n\n    def log_message(self, format, *args):\n        return\n\n\nif __name__ == '__main__':\n    server = ThreadingHTTPServer((HOST, PORT), Handler)\n    print(f'{WORKER_NAME} on http://{HOST}:{PORT}')\n    server.serve_forever()\n""",
            "README_playground.md": """# Distributed Playground\n\n- `topology.json` beschreibt die Services und Ports.\n- Der Playground dispatcht Services standardmaessig an registrierte Remote-Worker.\n- Jeder Worker-Nodes meldet sich ueber die Nova Security Plane und den Worker-Agenten an.\n- Der Coordinator sammelt die Health-Informationen der Worker ueber die verteilten Service-URLs.\n""",
        },
        "notebook": [
            {
                "id": "dist-1",
                "title": "Playground Notiz",
                "language": "python",
                "code": "services = ['coordinator', 'worker-alpha', 'worker-beta']\nprint('Playground:', ', '.join(services))\n",
                "stdin": "",
                "output": "",
            }
        ],
    },
}


OFFLINE_DOCS: dict[str, dict[str, object]] = {
    "python": {"title": "Python Schnellstart", "tags": ["python", "backend", "lernen"], "content": """# Python Schnellstart\n\n- Datei-Endung: `.py`\n- Start: `python main.py`\n- Pakete nur mit Freigabe und Gruppenrecht.\n\n```python\nvalues = [1, 2, 3]\nprint(sum(values))\n```\n\n```python\ndef greet(name: str) -> str:\n    return f\"Hallo {name}\"\n```\n\n- Nutze Funktionen statt langer globaler Skripte.\n- Endlosschleifen stoppt der Server nach dem Timeout.\n"""},
    "javascript": {"title": "JavaScript Schnellstart", "tags": ["javascript", "node", "web"], "content": """# JavaScript Schnellstart\n\n- Datei-Endung: `.js`\n- Browser-Skripte laufen ueber HTML.\n- Node.js-Skripte laufen mit `node main.js`.\n\n```javascript\nconst items = [2, 4, 6];\nconsole.log(items.reduce((sum, item) => sum + item, 0));\n```\n\n- Nutze `const` standardmaessig und `let` fuer veraenderliche Werte.\n- Trenne DOM-Code, Datenlogik und Styles.\n"""},
    "cpp": {"title": "C++ Schnellstart", "tags": ["cpp", "compiler"], "content": """# C++ Schnellstart\n\n- Datei-Endung: `.cpp`\n- Kompilierung im Server: `g++ -std=c++20 -O2`\n- Einstiegspunkt: `int main()`\n\n```cpp\n#include <iostream>\n\nint main() {\n    std::cout << \"Hallo C++\" << std::endl;\n    return 0;\n}\n```\n\n- Externe Bibliotheken muessen lokal verfuegbar sein.\n- Lange Build-Jobs koennen am Timeout enden.\n"""},
    "java": {"title": "Java Schnellstart", "tags": ["java", "jvm"], "content": """# Java Schnellstart\n\n- Datei-Endung: `.java`\n- Kompilierung: `javac Main.java`\n- Start: `java Main`\n\n```java\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hallo Java\");\n    }\n}\n```\n\n- Dateiname und `public class` muessen zusammenpassen.\n"""},
    "rust": {"title": "Rust Schnellstart", "tags": ["rust", "systems"], "content": """# Rust Schnellstart\n\n- Datei-Endung: `.rs`\n- Einzeldateien: `rustc main.rs`\n- Cargo-Projekte: `cargo run`\n\n```rust\nfn main() {\n    let values = [1, 2, 3];\n    let sum: i32 = values.iter().sum();\n    println!(\"{}\", sum);\n}\n```\n\n- Fuer groessere Projekte ist `cargo` sinnvoll.\n"""},
    "html-css": {"title": "HTML und CSS", "tags": ["html", "css", "frontend"], "content": """# HTML und CSS\n\n- Startdatei ist meist `index.html`.\n- Styles liegen in `styles.css` oder im `head`.\n- Die Vorschau laeuft lokal ueber den Schulserver.\n\n```html\n<section class=\"card\">\n  <h1>Nova School</h1>\n</section>\n```\n\n```css\n.card {\n  padding: 1rem;\n  border-radius: 1rem;\n}\n```\n"""},
    "node-npm": {"title": "Node.js und npm", "tags": ["node", "npm", "backend", "frontend"], "content": """# Node.js und npm\n\n- `node server.js` startet einfache Skripte.\n- `npm run <script>` startet Skripte aus `package.json`.\n- `npm install` benoetigt Webfreigabe.\n\n```json\n{\n  \"scripts\": {\n    \"start\": \"node server.js\",\n    \"dev\": \"node server.js\"\n  }\n}\n```\n\n- Ohne Webfreigabe blockiert der Server netzwerknahe npm-Pfade.\n"""},
    "web-frontend": {"title": "Frontend Entwicklung", "tags": ["frontend", "ui", "web"], "content": """# Frontend Entwicklung im Schulserver\n\n- Bearbeite HTML, CSS und JavaScript direkt im Editor.\n- Nutze die Vorschau fuer statische Projekte.\n- Fuer Node-Toolchains stehen `node` und `npm` als Runner bereit, sofern freigegeben.\n\nEmpfohlene Struktur:\n\n- `index.html`\n- `src/main.js`\n- `src/app.css`\n- `package.json`\n"""},
    "nova-school": {"title": "Nova School Server Leitfaden", "tags": ["server", "rechte", "hilfe"], "content": """# Nova School Server Leitfaden\n\n- Jeder User bekommt einen eigenen Profilordner.\n- Gruppen koennen gemeinsame Arbeitsbereiche und Projekte besitzen.\n- Rechte fuer Webzugriff, LM Studio und einzelne Runner werden zentral gesteuert.\n- Chat, Offline-Dokumentation und Notebook-Zellen sind direkt in die Editor-Oberflaeche integriert.\n\nNova-shell wird genutzt fuer:\n\n- `SecurityPlane`\n- `ToolSandbox`\n- `NovaAIProviderRuntime`\n"""},
}
