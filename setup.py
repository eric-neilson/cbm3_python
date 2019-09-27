import os
from setuptools import setup
from setuptools import find_packages

this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()
    
with open('requirements.txt') as f:
    requirements = f.read().splitlines()
    
access_templates = [
    os.path.join("cbm3data", "access_templates", "*.mdb"),
    os.path.join("cbm3data", "access_templates", "*.accdb")
]

results_queries = [
    os.path.join("cbm3data", "results_queries", "*.sql")
]

setup(
    name="cbm3_python",
    version=0.5,
    description="Scripts to automate tasks with CBM-CFS3",
    keywords=["cbm-cfs3"],
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Carbon Accounting Team - Canadian Forest Service',
    author_email='scott.morken@canada.ca',
    maintainer='Scott Morken',
    maintainer_email='scott.morken@canada.ca',
    license="MPL-2.0",
    url="",
    download_url="",
    packages=find_packages(),
    package_data={
        "cbm3_python":
            access_templates + results_queries
    },
    install_requires=requirements
)

