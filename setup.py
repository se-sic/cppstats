# -*- coding: utf-8 -*-
# cppstats is a suite of analyses for measuring C preprocessor-based
# variability in software product lines.
# Copyright (C) 2015 University of Passau, Germany
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#
# Contributors:
#     Claus Hunsen <hunsen@fim.uni-passau.de>


from setuptools import setup, find_packages
import cppstats

setup(
    name='cppstats',
    version=cppstats.version(),
    packages=find_packages(exclude=['scripts']),
    url='http://www.fosd.net/cppstats',
    license='LGPLv3',
    author='Claus Hunsen',
    author_email='hunsen@fim.uni-passau.de',
    description='toolsuite for analyzing preprocessor-based software product lines',

    package_data={
        'scripts' : ['*.sh'],
        'preparations' : ['*.xsl']
    },

    install_requires=[
        'statlib==1.2',
        'pyparsing==2.0.3',
        'enum==0.4.4',
        'lxml==3.4.4'
    ],

    dependency_links=[
        'git+https://github.com/Ext3h/python-statlib.git@release-1.2#egg=statlib-1.2'
    ],

    entry_points={'console_scripts': [
        'cppstats = cppstats.cppstats:main',
        'cppstats.analysis = cppstats.analysis:main',
        'cppstats.preparation = cppstats.preparation:main'
    ]}
)
