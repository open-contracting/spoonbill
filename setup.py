from setuptools import find_packages, setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='spoonbill',
    version='0.0.1',
    author='Open Contracting Partnership',
    author_email='data@open-contracting.org',
    url='https://github.com/open-contracting/spoonbill',
    description='An instrument to flatten OCDS data',
    license='BSD',
    packages=find_packages(exclude=['tests', 'tests.*']),
    long_description=long_description,
    install_requires=[
        'ijson>=2.5',
        'jsonref',
        'xlsxwriter',
        'requests',
        'click',        
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-cov',
            'coveralls',
        ],
        'docs': [
            'Sphinx',
            'sphinx-autobuild',
            'sphinx-rtd-theme',
        ],
    },
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        # 'Programming Language :: Python :: 3.6',
        # 'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    entry_points={
    }
)
