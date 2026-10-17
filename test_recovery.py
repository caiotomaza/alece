import http.client
import urllib.parse
import re

conn = http.client.HTTPConnection('127.0.0.1', 8000)

# Test login
conn.request('GET', '/login/')
resp = conn.getresponse()
csrftoken = None
for header in resp.getheaders():
    if header[0].lower() == 'set-cookie' and 'csrftoken' in header[1]:
        csrftoken = header[1].split(';')[0].split('=')[1]
        break

params = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123', 'csrfmiddlewaretoken': csrftoken})
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': 'csrftoken=' + csrftoken,
    'Referer': 'http://127.0.0.1:8000/login/'
}
conn.request('POST', '/login/', params, headers)
resp = conn.getresponse()
session_cookie = None
for header in resp.getheaders():
    if header[0].lower() == 'set-cookie' and 'sessionid' in header[1]:
        session_cookie = header[1].split(';')[0]
        break
print('Session:', session_cookie)

# Get recovery generate page to get CSRF token
headers_auth = {'Cookie': session_cookie}
conn.request('GET', '/recovery/generate/', '', headers_auth)
resp = conn.getresponse()
print('Recovery generate GET:', resp.status)
content = resp.read().decode()
csrftoken2 = None
for header in resp.getheaders():
    if header[0].lower() == 'set-cookie' and 'csrftoken' in header[1]:
        csrftoken2 = header[1].split(';')[0].split('=')[1]
        break
if not csrftoken2:
    # Try to extract from form
    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', content)
    if csrf_match:
        csrftoken2 = csrf_match.group(1)
print('CSRF for generate:', csrftoken2)

# Generate recovery code (POST)
params = urllib.parse.urlencode({'csrfmiddlewaretoken': csrftoken2})
headers_post = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': session_cookie + '; csrftoken=' + csrftoken2,
    'Referer': 'http://127.0.0.1:8000/recovery/generate/'
}
conn.request('POST', '/recovery/generate/', params, headers_post)
resp = conn.getresponse()
print('Recovery generate POST:', resp.status)
content = resp.read().decode()
print('Content length:', len(content))

# Extract code from response
code_match = re.search(r'class="code-display">([A-Za-z0-9_-]+)</div>', content)
if code_match:
    code = code_match.group(1)
    print('Recovery code:', code)
else:
    print('Could not extract code')
    print(content[:3000])

conn.close()