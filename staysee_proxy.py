from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.error, json, os, sys

PORT = 8765
TOKEN = 'sk_e583d1d91a57d1c22bf28246ee0c322c'
STAYSEE = 'https://api.staysee.jp'
FOLDER  = os.path.dirname(os.path.abspath(sys.argv[0]))

MIME = {'.html':'text/html','.css':'text/css','.js':'application/javascript','.json':'application/json'}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, f, *a): print(f'[{self.address_string()}] {f%a}')

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type,Authorization')

    def do_OPTIONS(self):
        self.send_response(200); self.send_cors(); self.end_headers()

    def do_GET(self):
        if self.path.startswith('/v1/'):
            self._proxy('GET', None)
        else:
            self._static()

    def do_POST(self):
        n = int(self.headers.get('Content-Length',0))
        self._proxy('POST', self.rfile.read(n) if n else None)

    def _static(self):
        path = self.path.split('?')[0]
        if path == '/': path = '/drink-order.html'
        fpath = os.path.join(FOLDER, path.lstrip('/'))
        if not os.path.isfile(fpath):
            self.send_response(404); self.end_headers(); self.wfile.write(b'Not found'); return
        ext = os.path.splitext(fpath)[1]
        mime = MIME.get(ext,'text/plain')
        with open(fpath,'rb') as f: data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', len(data))
        self.send_cors()
        self.end_headers()
        self.wfile.write(data)

    def _proxy(self, method, body):
        url = STAYSEE + self.path
        req = urllib.request.Request(url, data=body, method=method,
              headers={'Authorization':f'Bearer {TOKEN}','Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req) as r:
                data = r.read()
                self.send_response(r.status)
                self.send_cors()
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_cors()
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(data)

if __name__ == '__main__':
    print('='*50)
    print(f'  folder : {FOLDER}')
    print(f'  port   : {PORT}')
    print(f'  PC     : http://localhost:{PORT}/drink-order.html')
    print(f'  iPhone : http://192.168.0.55:{PORT}/drink-order.html')
    print('  close this window to stop')
    print('='*50)
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
