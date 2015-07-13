from setuptools import setup, find_packages

setup(
    name='cppstats',
    version='0.8.4.5',
    packages=find_packages(),
    url='http://www.fosd.net/cppstats',
    license='LGPLv3',
    author='Claus Hunsen',
    author_email='hunsen@fim.uni-passau.de',
    description='toolsuite for analyzing preprocessor-based software product lines',

    setup_requires=[
        'statlib==1.1',
        'pyparsing==2.0.3',
        'enum==0.4.4',
        'lxml==3.4.4'
    ]
)
