from time import time
import setuptools
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
setuptools.setup(
    name='abstract_ide',
    version='0.0.0.343',
    author='putkoff',
    author_email='partners@abstractendeavors.com',
    description='abstract_ide',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/AbstractEndeavors/abstract_ide',
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: 3.11',
    ],
    install_requires=[
        'abstract_apis',
        'PyQt5',
        'abstract_webtools',
        'abstract_utilities',
        'abstract_gui',
        'pydot',
        'abstract_clipit',
        'flask',
        'abstract_paths',
        'PyQt6'
        ]
,
   package_dir={"": "src"},
   packages=setuptools.find_packages(where="src"),
   python_requires=">=3.6",
  

)
