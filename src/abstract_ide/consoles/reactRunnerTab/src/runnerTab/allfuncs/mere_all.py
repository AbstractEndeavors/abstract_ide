import os
from abstract_utilities import read_from_file,write_to_file
abspath = os.path.abspath(__name__)
absbasename = os.path.basename(abspath)
dirname = os.path.dirname(abspath)
filepaths = [os.path.join(dirname,basename) for basename in os.listdir(dirname) if basename and basename != absbasename and basename != '__init__.py' and not os.path.isdir(os.path.join(dirname,basename))]
contents = ''
for filepath in filepaths:
    data = read_from_file(filepath)
    contents += '\n'.join(data.split('\n')[1:])
write_to_file(contents=contents,file_path='all_funcs.py')

