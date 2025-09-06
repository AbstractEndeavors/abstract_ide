from ..imports import *
def _setup_logging(self):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Remove any prior QTextEditLogger bound to stale widgets
    for h in list(root.handlers):
        if isinstance(h, QTextEditLogger):
            root.removeHandler(h)
    handler = QTextEditLogger(self.log_output)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s','%H:%M:%S'))
    root.addHandler(handler)
    # keep a reference for teardown
    self._log_handler = handler
def logWidgetInit(self,
                  layout,
                  label=None,
                  readOnly=True,
                  minHeight=None,
                  maxHeight=None,
                  Expanding=(True,True),
                  setVisible=False
                  ):
    label = label or "Logs:"
    addLabel(layout,label)
    self.log_output = getOutput(
          label=label,
          readOnly=readOnly,
          minHeight=minHeight,
          maxHeight=maxHeight,
          Expanding=Expanding,
          setVisible=setVisible
        )
    layout.addWidget(self.log_output)
