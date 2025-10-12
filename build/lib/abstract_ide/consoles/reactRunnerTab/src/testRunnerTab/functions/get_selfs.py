from abstract_utilities import *
def replace_solo_selfs(func,solo_names):
    for name in solo_names:
        func = func.replace(f"self.{name}",name)
    return func  
filePath = os.path.join(os.getcwd(),'__init__.py')
self_funcs_path = os.path.join(os.getcwd(),'self_funcs.py')
solo_funcs_path = os.path.join(os.getcwd(),'solo_funcs.py')
content = read_from_file(filePath)
func_splits = content.split('def ')
all_funcs = [f"def {cont}" for cont in func_splits[1:]]
solo_funcs = [cont for cont in all_funcs if 'self.' not in cont]
solo_funcs_names = [cont.split('\n')[0].split(' ')[1].split('(')[0] for cont in solo_funcs]

all_funcs = [replace_solo_selfs(func,solo_funcs_names) for func in all_funcs]
solo_funcs = [cont for cont in all_funcs if 'self.' not in cont]
self_funcs = [cont for cont in all_funcs if 'self.' in cont]

write_to_file(contents='\n'.join(solo_funcs),file_path=solo_funcs_path)

write_to_file(contents='\n'.join(self_funcs),file_path=self_funcs_path)
