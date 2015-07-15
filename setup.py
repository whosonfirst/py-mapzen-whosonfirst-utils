#!/usr/bin/env python

from setuptools import setup, find_packages

packages = find_packages()
desc = open("README.md").read(),

setup(
    name='mapzen.whosonfirst.utils',
    namespace_packages=['mapzen', 'mapzen.whosonfirst', 'mapzen.whosonfirst.utils'],
    version='0.22',
    description='Simple Python wrapper for Who\'s On First helper functions',
    author='Mapzen',
    url='https://github.com/mapzen/py-mapzen-whosonfirst-utils',
    install_requires=[
        'mapzen.whosonfirst.placetypes',
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
        'scripts/wof-dump-hierarchies',
        'scripts/wof-concordances-to-db',
        'scripts/wof-placetype-to-csv',
        'scripts/wof-csv-to-feature-collection',
        'scripts/wof-csv-to-s3',
        ],
    download_url='https://github.com/mapzen/py-mapzen-whosonfirst-utils/releases/tag/v0.22',
    license='BSD')
