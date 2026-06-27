from concurrent.futures import ThreadPoolExecutor, as_completed
from .db import DownloadRegistry, DownloadRecord
from ..src import *
from ..src.soupManager import *
from ..workers.worker import *
from ..src import BASE_URL
class LISTMANAGER(metaclass=SingletonMeta):
    def __init__(self, dsn: str = None, worker_count: int = 4):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.registry = DownloadRegistry(dsn or DB_DSN)
            self.worker_count = worker_count
            self.token = get_token()
            print(self.token)
    def get_token_url(self, url):
        url_spl = url.split(BASE_URL)[1].split('/')
        file_id = url_spl[0]
        if self.registry.has(file_id):
            return False, {}
        file_name = url_spl[1].split('?')[0]
        url_js = get_url_js(url)
        url_js['file_id'] = file_id
        url_js['file_name'] = file_name
        url_js['original_url'] = url
        token_url = get_api_url(self.token, file_id)
        return token_url, url_js

    def download_file(self, url):

        token_url, url_js = self.get_token_url(url)
        if not token_url:
            return
        path = download(token_url, url_js['file_name'])
        self.registry.save(DownloadRecord(
            file_id=url_js['file_id'],
            file_name=url_js['file_name'],
            original_url=url_js['original_url'],
            token_url=token_url,
            path=str(path),
        ))
        print(f"Done: {path}")

    def download_files(self, urls):
        with ThreadPoolExecutor(max_workers=self.worker_count) as ex:
            futures = {ex.submit(self.download_file, url): url for url in urls}
            for future in as_completed(futures):
                if exc := future.exception():
                    print(f"[error] {futures[future]}: {exc}")
def get_all_valid_links(i, user=None, list_mgr: LISTMANAGER = None):
    list_mgr = list_mgr or LISTMANAGER()
    user = user or USER
    all_links = []
    for article in get_site_articles(i, user):
        k2s_link = is_getable(article)
        if k2s_link:
            all_links.append(k2s_link)
                

    list_mgr.download_files(all_links)
    

