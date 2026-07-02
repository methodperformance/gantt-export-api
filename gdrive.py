"""
Vercel Serverless Function - Google Drive File Proxy
Upload/download files to Google Drive using Service Account (no user OAuth needed)
"""
from http.server import BaseHTTPRequestHandler
import json, os, io, base64, time, urllib.request, urllib.parse
import email.mime.multipart

# ── Service Account Credentials ──────────────────────────────────────────────
SA_CREDENTIALS = {
    "type": "service_account",
    "project_id": "method-performance-hub",
    "private_key_id": "5decbbb675c39e33f926d82393cc0a81416c95db",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDfMFzQgmeiuLuL\n7asYQQihQdM6R+F0OsRe9R5psl7jQ/7GIEIoc8mS5QOiBP1z7i6AbSPjfsi5tFKh\n+DbuaGWTS7yPOFW+j0pIeQ8gMGOdK+1VqWCMckZca1bqo/98phCqsZocpCM3Kikc\n5kHpdzgMYIISrHZOyMZ23+V7xYIxIErTZNcaBcuNpZLKqy3IxKE0W6YU4+m+GKUb\nb9eY33K26rbDxBQnzNzlujVSeBkLZ2IkO7RYl2YlfPS4a/rI8SVKzKjYaR8mc3wD\nLc3ir27rMvbiZoJgQdh4gd7fQnSVi/sSWbFvbdoh5Uo8ZhgUQ1gXcBZm1WCamOvr\nrOCZngJRAgMBAAECggEAERK3XDvy3D/Fbll//Rr8eK7QZGTwmjOPUgmY31JbGoeD\ntc7slgDwKoyE+p/nGOHfgh4si0/nivfVr7jietpW6thK/v8QOsOQqyVCQvQbVVVG\n59v3xsahxfAay1hASF4WaE2tvFh8rnugftVztVL+tp5V/5exyn+8BDFHHMYUb4LO\n6Vfd2HB3vD2Lb1tdsdw4cj6/ZSaJ/RWOqTVCvqOmY/SKvakeG/MxxZOoLzH30zkG\nN3F7bRw3om3GPcz1LhiUZxQWHDLNw3zlThzpjUsRENRtXwM9qjpc+adKK1e8RX4x\nTmwj4cYvyB369ohfVAQ6ttANqqrkpdCSmhTXuDhlAQKBgQD9njgj6WmmdLMhfXgX\nFQSfjjQauu/HXUTxnawdHgxRJrVPD8AvLFui0CtOCHW1/5ho4vdcdWx2ISfiS4Lp\nd+uZa4md85iod9f6sM78TDRaS0V0oSBNeKrq4IChWpMfChmzJvjm49aDh1kAzMmD\n9xXxk3zHfzoX4sGNdPdoUn1muwKBgQDhSPtPxR8huaFwGRuLrYZJ5cmAzarrLjHg\nN9hcUryK19IRQkCR7pNiwn1Qz8E2HgMNqBdCt3msi66AZ5KVYb+zG0m456CRUo6H\nS7iSbaqNNW88FnxMuj5SbU1M6EOkqjsxfPAyadn7dM6UpNHuK7O6pkKaVxn1Es8K\nlWAio/1YYwKBgQD5aVmIZ4kQu39WFg+9k1vilXREPUaE5wJgIlEaqWwvekOfpru3\nKIZNjS6pJMSt4Ng/fcUJVij92wlgECaD9vzo+cpyXRbpxkHONYa4szBhA9kgIzyj\nM2HSbknRZEN+qO4xMshgN/vDiZ1LnhknABzCX+q8PjAhQUxbEoYkP8s29QKBgAVE\nK3vF4+Bp8ngoXhh5yfXYRUmZhTFSNyBCrfAajwW/3c1BezjuFsvsN/m3oZCeSvv6\nvfB1UYbTDRU7VpXfXxfUv3hvEbXT9Dj9cCccISyD30HMVMOGZwaOP4xYsZwbzp5t\niT/kcZALPvkCkVW798uZL11kQ9sSwXxB2al1o+p5AoGBAMjFHtDEs/YfV2hJYd6n\nxWoM35PQo1udLakIDBgleinjrgdBlpEvU6be1spll7MVgGoS1sdPdgJT56m++oOv\nt5vm+yHOdp/QXXiT+Yk5WtbRa3hc/+T+UN7dLTr17BLiR9DVWIGA1qHeZzurYf4k\ncDp2QhR23NbzzmeVML4M1ZL2\n-----END PRIVATE KEY-----\n",
    "client_email": "method-hub-uploader@method-performance-hub.iam.gserviceaccount.com",
    "token_uri": "https://oauth2.googleapis.com/token"
}

GDRIVE_FOLDER_ID = '1Wiy5Dx2Ko0OdK48SQFZixclEx7D4QVCi'
DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive.file'

_token_cache = {"token": None, "expiry": 0}

def get_access_token():
    """Get OAuth2 token using service account JWT."""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expiry"] - 60:
        return _token_cache["token"]

    import struct, hashlib, hmac

    # Build JWT
    header = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b'=')
    payload = base64.urlsafe_b64encode(json.dumps({
        "iss": SA_CREDENTIALS["client_email"],
        "scope": DRIVE_SCOPE,
        "aud": SA_CREDENTIALS["token_uri"],
        "exp": int(now) + 3600,
        "iat": int(now)
    }).encode()).rstrip(b'=')

    msg = header + b'.' + payload

    # Sign with private key using cryptography library
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    private_key = serialization.load_pem_private_key(
        SA_CREDENTIALS["private_key"].encode(), password=None
    )
    signature = private_key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=')

    jwt = msg + b'.' + sig_b64

    # Exchange JWT for access token
    data = urllib.parse.urlencode({
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': jwt.decode()
    }).encode()

    req = urllib.request.Request(SA_CREDENTIALS["token_uri"], data=data,
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    _token_cache["token"] = result["access_token"]
    _token_cache["expiry"] = now + result.get("expires_in", 3600)
    return _token_cache["token"]

def drive_request(method, url, headers=None, data=None):
    token = get_access_token()
    h = {'Authorization': f'Bearer {token}'}
    if headers: h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), {}

def find_or_create_folder(name, parent_id):
    q = urllib.parse.quote(f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false")
    status, body, _ = drive_request('GET', f'https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id)')
    files = json.loads(body).get('files', [])
    if files: return files[0]['id']
    meta = json.dumps({'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}).encode()
    status, body, _ = drive_request('POST', 'https://www.googleapis.com/drive/v3/files',
                                     headers={'Content-Type': 'application/json'}, data=meta)
    return json.loads(body)['id']

def find_file(name_prefix, folder_id):
    # Search more broadly — list all files in folder then filter
    q = urllib.parse.quote(f"'{folder_id}' in parents and trashed=false")
    status, body, _ = drive_request('GET', f'https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id,name,mimeType)&pageSize=100')
    all_files = json.loads(body).get('files', [])
    # Filter by prefix match (case-insensitive)
    prefix_lower = name_prefix.lower()
    return [f for f in all_files if f['name'].lower().startswith(prefix_lower)]

def upload_file(filename, content_type, data_bytes, folder_id):
    # Delete existing file with same prefix
    prefix = filename.split('_')[0] if '_' in filename else filename[:10]
    existing = find_file(prefix, folder_id)
    for f in existing:
        drive_request('DELETE', f"https://www.googleapis.com/drive/v3/files/{f['id']}")

    # Multipart upload
    boundary = 'boundary_method_hub'
    meta = json.dumps({'name': filename, 'parents': [folder_id]})
    body = (
        f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n'
        f'--{boundary}\r\nContent-Type: {content_type}\r\n\r\n'
    ).encode() + data_bytes + f'\r\n--{boundary}--'.encode()

    status, resp_body, _ = drive_request(
        'POST',
        'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name',
        headers={'Content-Type': f'multipart/related; boundary={boundary}'},
        data=body
    )
    return json.loads(resp_body)


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        """Download file: GET /api/gdrive?projectId=xxx&evidenceName=yyy"""
        try:
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            project_id = params.get('projectId', '')
            evidence_name = params.get('evidenceName', '')

            if not project_id or not evidence_name:
                self._json(400, {'error': 'Missing projectId or evidenceName'})
                return

            folder_id = find_or_create_folder(project_id, GDRIVE_FOLDER_ID)
            safe = evidence_name.replace(' ', '_').replace('/', '_')
            files = find_file(safe, folder_id)

            if not files:
                self._json(404, {'error': 'File not found'})
                return

            file_id = files[0]['id']
            file_name = files[0]['name']
            status, file_data, file_headers = drive_request(
                'GET', f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media'
            )

            content_type = file_headers.get('Content-Type', 'application/octet-stream')
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Disposition', f'attachment; filename="{file_name}"')
            self.send_header('Content-Length', str(len(file_data)))
            self._cors()
            self.end_headers()
            self.wfile.write(file_data)

        except Exception as e:
            self._json(500, {'error': str(e)})

    def do_POST(self):
        """Upload file: POST /api/gdrive with multipart form data"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            project_id   = data.get('projectId', '')
            evidence_name = data.get('evidenceName', '')
            filename     = data.get('filename', 'file')
            content_type = data.get('contentType', 'application/octet-stream')
            file_b64     = data.get('fileData', '')

            if not project_id or not evidence_name or not file_b64:
                self._json(400, {'error': 'Missing required fields'})
                return

            file_bytes = base64.b64decode(file_b64)
            safe_name  = evidence_name.replace(' ', '_').replace('/', '_')
            upload_filename = f"{safe_name}_{filename}"

            folder_id = find_or_create_folder(project_id, GDRIVE_FOLDER_ID)
            result = upload_file(upload_filename, content_type, file_bytes, folder_id)

            self._json(200, {'success': True, 'fileId': result.get('id'), 'fileName': result.get('name')})

        except Exception as e:
            self._json(500, {'error': str(e)})

    def do_DELETE(self):
        """Delete file: DELETE /api/gdrive?projectId=xxx&evidenceName=yyy"""
        try:
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            project_id    = params.get('projectId', '')
            evidence_name = params.get('evidenceName', '')

            folder_id = find_or_create_folder(project_id, GDRIVE_FOLDER_ID)
            safe = evidence_name.replace(' ', '_').replace('/', '_')
            files = find_file(safe, folder_id)
            for f in files:
                drive_request('DELETE', f"https://www.googleapis.com/drive/v3/files/{f['id']}")

            self._json(200, {'success': True, 'deleted': len(files)})
        except Exception as e:
            self._json(500, {'error': str(e)})

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        pass
