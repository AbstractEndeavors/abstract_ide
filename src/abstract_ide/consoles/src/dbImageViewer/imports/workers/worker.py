from ..src.constants import *
import webbrowser
# ── worker ────────────────────────────────────────────────────────────────────

def request_captcha() -> tuple[str, str]:
    body = requests.post(f'{API_BASE}/requestRecaptcha').json()
    print("[captcha]", body)
    return body['challenge'], body['captcha_url']


def login(email: str, password: str, challenge: str, captcha_answer: str) -> str:
    body = requests.post(f'{API_BASE}/login', json={
        'username': email,
        'password': password,
        're_captcha_challenge': challenge,
        're_captcha_response': captcha_answer,
    }).json()
    print("[login]", body)
    if body.get('status') != 'success':
        return False
    return body['auth_token']


def get_api_url(auth_token: str, file_id: str) -> str:
    body = requests.post(f'{API_BASE}/getUrl', json={
        'auth_token': auth_token,
        'file_id': file_id,
    }).json()
    print("[getUrl]", body)
    if body.get('status') != 'success':
        return False
    return body['url']


def download(url: str,name=None) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    name = name or url.rsplit('/', 1)[-1].split('?')[0]
    dest = OUT_DIR / name
    if not os.path.isfile(str(dest)):
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
    return dest

def get_token(token=None):
    if not token:
        challenge, captcha_url = request_captcha()
        print(f"\nOpen this URL and read the captcha text:\n{captcha_url}\n")
        webbrowser.open(captcha_url)
        answer = input("Captcha answer: ").strip()
        token = login(userName, passWord, challenge, answer)
        print(token)
    return token
