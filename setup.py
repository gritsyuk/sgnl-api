from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='sgnl-api',
    version='0.0.1',
    author='Igor Gritsyuk',
    author_email='gritsyuk.igor@gmail.com',
    description='Asynchronous python wrapper over API sgnl.pro',
    download_url='https://github.com/gritsyuk/sgnl-api/archive/refs/heads/develop.zip',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/gritsyuk/sgnl-api',
    packages=find_packages(include=['sgnl_api', 'sgnl_api.*']),
    install_requires=['httpx>=0.27.2', 'aiofiles>=24.1.0'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
    ],
    keywords='sgnl api signal docs construction supervision operation inspections constarctionsite building management',
    project_urls={
        'GitHub': 'https://github.com/gritsyuk/sgnl-api'
    },
    python_requires='>=3.9'
)