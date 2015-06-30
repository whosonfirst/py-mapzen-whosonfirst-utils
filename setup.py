#!/usr/bin/env python

from setuptools import setup, find_packages

packages = find_packages()
desc = open("README.md").read(),

setup(
    name='mapzen.gazetteer.export',
    namespace_packages=['mapzen', 'mapzen.gazetteer'],
    version='0.14',
    description='Simple Python wrapper for managing Mapzen Gazetteer related functions',
    author='Mapzen',
    url='https://github.com/mapzen/py-mapzen-gazetter',
    install_requires=[
        'requests',
        'shapely',
        'geojson',
        'boto',
        ],
    dependency_links=[
        ],
    packages=packages,
    scripts=[
        'scripts/mzg-placetype-to-csv',
        'scripts/mzg-csv-to-feature-collection',
        'scripts/mzg-csv-to-s3',
        ],
    download_url='https://github.com/thisisaaronland/py-mapzen-gazetteer/releases/tag/v0.14',
    license='BSD')
