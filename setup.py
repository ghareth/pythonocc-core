#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='pythonocc',
    version='0.18.2',
    description='description to follow',
    author='Gareth Boyes',
    author_email='gareth.boyes@gxbis.com',
    packages=['pythonocc',
              'pythonocc/Display',
              'pythonocc/Display/WebGl'],
    package_dir={'pythonocc': 'src',
                 'pythonocc/Display': 'src/Display',
                 'pythonocc/Display/WebGl': 'src/Display/WebGl'},
    include_package_data=True)