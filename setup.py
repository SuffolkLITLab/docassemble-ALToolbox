import os
import sys
from setuptools import setup, find_packages
from fnmatch import fnmatchcase
from distutils.util import convert_path

standard_exclude = ('*.pyc', '*~', '.*', '*.bak', '*.swp*')
standard_exclude_directories = ('.*', 'CVS', '_darcs', './build', './dist', 'EGG-INFO', '*.egg-info')

def find_package_data(where='.', package='', exclude=standard_exclude, exclude_directories=standard_exclude_directories):
    out = {}
    stack = [(convert_path(where), '', package)]
    while stack:
        where, prefix, package = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where, name)
            if os.path.isdir(fn):
                bad_name = False
                for pattern in exclude_directories:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        break
                if bad_name:
                    continue
                if os.path.isfile(os.path.join(fn, '__init__.py')):
                    if not package:
                        new_package = name
                    else:
                        new_package = package + '.' + name
                        stack.append((fn, '', new_package))
                else:
                    stack.append((fn, prefix + name + '/', package))
            else:
                bad_name = False
                for pattern in exclude:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        break
                if bad_name:
                    continue
                out.setdefault(package, []).append(prefix+name)
    return out

setup(name='docassemble.ALToolbox',
      version='0.11.1',
      description=('Collection of small utility functions, classes, and web components for Docassemble interviews'),
      long_description='# ALToolbox\r\n\r\n[![PyPI version](https://badge.fury.io/py/docassemble-ALToolbox.svg)](https://badge.fury.io/py/docassemble-ALToolbox)\r\n\r\nThis repository is used to host small Python modules, widgets, and JavaScript web components js files that enhance Docassemble interviews. These modules were\r\nbuilt as part of the Suffolk University Law School LIT Lab\'s [Document Assembly Line project](https://suffolklitlab.org/docassemble-AssemblyLine-documentation/).\r\nThey are placed here\r\nrather than in https://github.com/SuffolkLitLab/docassemble-AssemblyLine because we believe these small components can easily be used\r\nby anyone, regardless of whether they use any other code from the Document Assembly Line project.\r\n\r\nIf you want to add a small function to this project, consider adding it to the existing misc.py to avoid creating too many module files.\r\n\r\n## Documentation\r\n\r\nRead the [documentation for the functions and components](https://suffolklitlab.org/docassemble-AssemblyLine-documentation/docs/framework/altoolbox) to learn\r\nhow to use these components in your own [Docassemble](https://github.com/jhpyle/docassemble) projects.\r\n\r\n## Suffolk LIT Lab Document Assembly Line\r\n\r\n<img src="https://user-images.githubusercontent.com/7645641/142245862-c2eb02ab-3090-4e97-9653-bb700bf4c54d.png" alt="drawing of people working together on a website UI" width="300" style="align: center;"/>\r\n\r\nThe Assembly Line Project is a collection of volunteers, students, and institutions who joined together\r\nduring the COVID-19 pandemic to help increase access to the court system. Our vision is mobile-friendly,\r\neasy to use **guided** online forms that help empower litigants to access the court remotely.\r\n\r\nOur signature project is [CourtFormsOnline.org](https://courtformsonline.org).\r\n\r\nWe designed a step-by-step, assembly line style process for automating court forms on top of Docassemble\r\nand built several tools along the way that **you** can use in your home jurisdiction.\r\n\r\nThis package contains **runtime code** and **pre-written questions** to support authoring robust, \r\nconsistent, and attractive Docassemble interviews that help complete court forms.\r\n\r\nRead more on our [documentation page](https://suffolklitlab.org/docassemble-AssemblyLine-documentation/).\r\n\r\n\r\n## Related repositories\r\n\r\n* https://github.com/SuffolkLitLab/docassemble-AssemblyLine\r\n* https://github.com/SuffolkLitLab/docassemble-ALWeaver\r\n* https://github.com/SuffolkLitLab/docassemble-ALMassachusetts\r\n* https://github.com/SuffolkLitLab/docassemble-MassAccess\r\n* https://github.com/SuffolkLitLab/docassemble-ALThemeTemplate\r\n* https://github.com/SuffolkLitLab/EfileProxyServer\r\n\r\n## Contributors:\r\n* @plocket  \r\n* @nonprofittechy\r\n* @purplesky2016\r\n* @brycestevenwilley\r\n',
      long_description_content_type='text/markdown',
      author='AssemblyLine',
      author_email='52798256+plocket@users.noreply.github.com',
      license='The MIT License (MIT)',
      url='https://suffolklitlab.org/docassemble-AssemblyLine-documentation/docs/framework/altoolbox',
      packages=find_packages(),
      namespace_packages=['docassemble'],
      install_requires=['holidays>=0.38', 'pandas>=2.0.3'],
      zip_safe=False,
      package_data=find_package_data(where='docassemble/ALToolbox/', package='docassemble.ALToolbox'),
     )

