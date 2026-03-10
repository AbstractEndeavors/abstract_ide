from abstract_utilities import get_caller_dir,initFuncs as _initFuncs
MODE="prod" if 'site-packages' in get_caller_dir() else "dev"
def initFuncs(self,mode=None):
    self.log(MODE)
    _initFuncs(self,mode="prod")
