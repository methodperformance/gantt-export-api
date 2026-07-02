""
Vercel Serverless Function - Google Drive File Proxy v2
Simplified and more reliable implementation
"""
from http.server import BaseHTTPRequestHandler
import json, base64, time, urllib.request, urllib.parse, io

SA_EMAIL = "method-hub-uploader@method-performance-hub.iam.gserviceaccount.com"
SA_KEY   = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDfMFzQgmeiuLuL
7asYQQihQdM6R+F0OsRe9R5psl7jQ/7GIEIoc8mS5QOiBP1z7i6AbSPjfsi5tFKh
+DbuaGWTS7yPOFW+j0pIeQ8gMGOdK+1VqWCMckZca1bqo/98phCqsZocpCM3Kikc
5kHpdzgMYIISrHZOyMZ23+V7xYIxIErTZNcaBcuNpZLKqy3IxKE0W6YU4+m+GKUb
b9eY33K26rbDxBQnzNzlujVSeBkLZ2IkO7RYl2YlfPS4a/rI8SVKzKjYaR8mc3wD
Lc3ir27rMvbiZoJgQdh4gd7fQnSVi/sSWbFvbdoh5Uo8ZhgUQ1gXcBZm1WCamOvr
rOCZngJRAgMBAAECggEAERK3XDvy3D/Fbll//Rr8eK7QZGTwmjOPUgmY31JbGoeD
tc7slgDwKoyE+p/nGOHfgh4si0/nivfVr7jietpW6thK/v8QOsOQqyVCQvQbVVVG
59v3xsahxfAay1hASF4WaE2tvFh8rnugftVztVL+tp5V/5exyn+8BDFHHMYUb4LO
6Vfd2HB3vD2Lb1tdsdw4cj6/ZSaJ/RWOqTVCvqOmY/SKvakeG/MxxZOoLzH30zkG
N3F7bRw3om3GPcz1LhiUZxQWHDLNw3zlThzpjUsRENRtXwM9qjpc+adKK1e8RX4x
Tmwj4cYvyB369ohfVAQ6ttANqqrkpdCSmhTXuDhlAQKBgQD9njgj6WmmdLMhfXgX
FQSfjjQauu/HXUTxnawdHgxRJrVPD8AvLFui0CtOCHW1/5ho4vdcdWx2ISfiS4Lp
d+uZa4md85iod9f6sM78TDRaS0V0oSBNeKrq4IChWpMfChmzJvjm49aDh1kAzMmD
9xXxk3zHfzoX4sGNdPdoUn1muwKBgQDhSPtPxR8huaFwGRuLrYZJ5cmAzarrLjHg
N9hcUryK19IRQkCR7pNiwn1Qz8E2HgMNqBdCt3msi66AZ5KVYb+zG0m456CRUo6H
S7iSbaqNNW88FnxMuj5SbU1M6EOkqjsxfPAyadn7dM6UpNHuK7O6pkKaVxn1Es8K
lWAio/1YYwKBgQD5aVmIZ4kQu39WFg+9k1vilXREPUaE5wJgIlEaqWwvekOfpru3
KIZNjS6pJMSt4Ng/fcUJVij92wlgECaD9vzo+cpyXRbpxkHONYa4szBhA9kgIzyj
M2HSbknRZEN+qO4xMshgN/vDiZ1LnhknABzCX+q8PjAhQUxbEoYkP8s29QKBgAVE
K3vF4+Bp8ngoXhh5yfXYRUmZhTFSNyBCrfAajwW/3c1BezjuFsvsN/m3oZCeSvv6
vfB1UYbTDRU7VpXfXxfUv3hvEbXT9Dj9cCccISyD30HMVMOGZwaOP4xYsZwbzp5t
iT/kcZALPvkCkVW798uZL11kQ9sSwXxB2al1o+p5AoGBAMjFHtDEs/YfV2hJYd6n
xWoM35PQo1udLakIDBgleinjrgdBlpEvU6be1spll7MVgGoS1sdPdgJT56m++oOv
t5vm+yHOdp/QXXiT+Yk5WtbRa3hc/+T+UN7dLTr17BLiR9DVWIGA1qHeZzurYf4k
cDp2QhR23NbzzmeVML4M1ZL2
-----END PRIVATE KEY-----"""

ROOT_FOLDER = '1Wiy5Dx2Ko0OdK48SQFZixclEx7D4QVCi'
TOKEN_URI   = 'https://oauth2.googleapis.com/token'
SCOPE       = 'https://www.googleapis.com/auth/drive'

def get_token():
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    now = int(time.time())
    header  = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b'=')
    payload = base64.urlsafe_b64encode(json.dumps({
        "iss": SA_EMAIL, "scope": SCOPE,
        "aud": TOKEN_URI, "exp": now+3600, "iat": now
    }).encode()).rstrip(b'=')

    msg = header + b'.' + payload
    key = serialization.load_pem_private_key(SA_KEY.encode(), password=None)
    sig = base64.urlsafe_b64encode(key.sign(msg, padding.PKCS1v15(), hashes.SHA256())).rstrip(b'=')
    jwt = (msg + b'.' + sig).decode()

    data = urllib.parse.urlencode({
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': jwt
    }).encode()
    req = urllib.request.Request(TOKEN_URI, data=data,
          headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['access_token']

def api(method, url, token, body=None, content_type=None):
    headers = {'Authorization': f'Bearer {token}'}
    if content_type: headers['Content-Type'] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), {}

def list_files(token, folder_id):
    q = urllib.parse.quote(f"'{folder_id}' in parents and trashed=false")
    _, body, _ = api('GET',
        f'https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id,name)&pageSize=200',
        token)
    return json.loads(body).get('files', [])

def find_or_create_folder(token, name, parent_id):
    files = list_files(token, parent_id)
    for f in files:
        if f['name'] == name:
            return f['id']
    meta = json.dumps({'name': name,
                       'mimeType': 'application/vnd.google-apps.folder',
                       'parents': [parent_id]}).encode()
    _, body, _ = api('POST', 'https://www.googleapis.com/drive/v3/files',
                     token, meta, 'application/json')
    return json.loads(body)['id']

def find_file_by_prefix(token, folder_id, prefix):
    files = list_files(token, folder_id)
    print(f"DEBUG find_file_by_prefix: prefix={prefix}, all_files={[f['name'] for f in files]}")
    prefix_lower = prefix.lower()
    return [f for f in files if f['name'].lower().startswith(prefix_lower)]


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        try:
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            pid  = params.get('projectId','')
            ename = params.get('evidenceName','')
            if not pid or not ename:
                return self._json(400,{'error':'Missing params'})

            token = get_token()
            folder_id = find_or_create_folder(token, pid, ROOT_FOLDER)
            safe = ename.replace(' ','_').replace('/','_')
            files = find_file_by_prefix(token, folder_id, safe)

            if not files:
                return self._json(404,{'error':'File not found',
                                       'looked_for': safe,
                                       'folder_id': folder_id})

            fid = files[0]['id']
            fname = files[0]['name']
            _, fdata, fhdrs = api('GET',
                f'https://www.googleapis.com/drive/v3/files/{fid}?alt=media', token)

            ct = fhdrs.get('Content-Type','application/octet-stream')
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
            self.send_header('Content-Length', str(len(fdata)))
            self._cors(); self.end_headers()
            self.wfile.write(fdata)

        except Exception as e:
            self._json(500,{'error':str(e)})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length',0))
            data   = json.loads(self.rfile.read(length))
            pid    = data.get('projectId','')
            ename  = data.get('evidenceName','')
            fname  = data.get('filename','file')
            ct     = data.get('contentType','application/octet-stream')
            fb64   = data.get('fileData','')

            if not pid or not ename or not fb64:
                return self._json(400,{'error':'Missing fields'})

            token     = get_token()
            folder_id = find_or_create_folder(token, pid, ROOT_FOLDER)
            safe      = ename.replace(' ','_').replace('/','_')
            upload_name = f"{safe}_{fname}"

            # Delete existing
            existing = find_file_by_prefix(token, folder_id, safe)
            for f in existing:
                api('DELETE',
                    f"https://www.googleapis.com/drive/v3/files/{f['id']}", token)

            # Upload
            fbytes = base64.b64decode(fb64)
            boundary = 'mhub_boundary_xyz'
            meta = json.dumps({'name': upload_name, 'parents': [folder_id]})
            body = (
                f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n'
                f'--{boundary}\r\nContent-Type: {ct}\r\n\r\n'
            ).encode() + fbytes + f'\r\n--{boundary}--'.encode()

            _, rbody, _ = api('POST',
                'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name',
                token, body, f'multipart/related; boundary={boundary}')
            result = json.loads(rbody)
            self._json(200,{'success':True,'fileId':result.get('id'),'fileName':result.get('name')})

        except Exception as e:
            self._json(500,{'error':str(e)})

    def do_DELETE(self):
        try:
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            pid   = params.get('projectId','')
            ename = params.get('evidenceName','')
            token = get_token()
            folder_id = find_or_create_folder(token, pid, ROOT_FOLDER)
            safe  = ename.replace(' ','_').replace('/','_')
            files = find_file_by_prefix(token, folder_id, safe)
            for f in files:
                api('DELETE',
                    f"https://www.googleapis.com/drive/v3/files/{f['id']}", token)
            self._json(200,{'success':True,'deleted':len(files)})
        except Exception as e:
            self._json(500,{'error':str(e)})

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self._cors(); self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')

    def log_message(self, *a): pass
