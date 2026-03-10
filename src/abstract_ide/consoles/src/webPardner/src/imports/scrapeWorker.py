from .imports import *
from .emulatorConfig import *
from .politeFetcher import *
from .baseEngine import *
from .seleneumEngine import *
from .playwriteEngine import *
class ScrapeWorker(QThread):
    result_signal = pyqtSignal(dict)
    log_signal = pyqtSignal(str)

    def __init__(self, cfg: EmulatorConfig, task: Dict):
        super().__init__()
        self.cfg = cfg
        self.task = task
        self._cancel = False

    def cancel(self): self._cancel = True

    def _make_engine(self) -> BaseEngine:
        if self.cfg.engine == "Playwright":
            return PlaywrightEngine(self.cfg)
        return SeleniumEngine(self.cfg)

    def run(self):
        engine: Optional[BaseEngine] = None
        try:
            if self._cancel: return
            engine = self._make_engine()
            if self._cancel: return
            res = engine.scrape(
                url=self.task['url'],
                wait_for=self.task.get('wait_for'),
                selectors=self.task.get('selectors', {})
            )
            self.result_signal.emit(res)
        except Exception as e:
            self.result_signal.emit({'url': self.task.get('url'), 'status': 'failed', 'error': f"[{type(e).__name__}] {str(e)}"})
        finally:
            self.log_signal.emit(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Scraping completed for {self.task.get('url')}")
            if engine: engine.quit()
