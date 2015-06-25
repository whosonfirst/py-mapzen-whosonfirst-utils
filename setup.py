#!/usr/bin/env python

from setuptools import setup, find_packages

packages = find_packages()
desc = open("README.md").read(),

setup(
    name='mapzen.gazetteer.export',
    namespace_packages=['mapzen', 'mapzen.gazetteer'],
    version='0.1',
    description='Simple Python wrapper for managing Mapzen Gazetteer related functions',
    author='Mapzen',
    url='https://github.com/thisisaaronland/py-mapzen-gazetter',
    install_requires=[
        'geojson',
        ],
    dependency_links=[
        ],
    packages=packages,
    scripts=[
        'scripts/mzg-placetype-to-csv',
        ],
    download_url='https://github.com/thisisaaronland/py-mapzen-gazetteer/releases/tag/v0.1',
    license='BSD')
