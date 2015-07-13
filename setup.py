#!/usr/bin/env python

from setuptools import setup, find_packages

packages = find_packages()
desc = open("README.md").read(),

setup(
    name='mapzen.gazetteer',
    namespace_packages=['mapzen', 'mapzen.gazetteer', 'mapzen.gazetteer.utils'],
    version='0.19',
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
        'scripts/wof-dump-concordances',
        'scripts/wof-concordances-to-db',
        'scripts/wof-placetype-to-csv',
        'scripts/wof-csv-to-feature-collection',
        'scripts/wof-csv-to-s3',
        ],
    download_url='https://github.com/thisisaaronland/py-mapzen-gazetteer/releases/tag/v0.19',
    license='BSD')
