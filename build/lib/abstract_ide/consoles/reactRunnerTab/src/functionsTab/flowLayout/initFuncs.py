

from .functions import (_doLayout, addItem, addWidget, count, expandingDirections, hasHeightForWidth, heightForWidth, itemAt, minimumSize, setGeometry, sizeHint, takeAt)

def initFuncs(self):
    try:
        for f in (_doLayout, addItem, addWidget, count, expandingDirections, hasHeightForWidth, heightForWidth, itemAt, minimumSize, setGeometry, sizeHint, takeAt):
            setattr(self, f.__name__, f)
    except Exception as e:
        logger.info(f"{e}")
    return self
