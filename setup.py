from setuptools import setup, find_packages

setup(
    name='much',
    version='0.0.4',
    license='Apache 2.0',
    author='Zeio Nara',
    author_email='zeionara@gmail.com',
    packages=find_packages(),
    description='A simple utility for crawling text from 2ch',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url='https://github.com/zeionara/much',
    project_urls={
        'Documentation': 'https://github.com/zeionara/much#readme',
        'Bug Reports': 'https://github.com/zeionara/much/issues',
        'Source Code': 'https://github.com/zeionara/much'
    },
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.11"
    ],
    install_requires = ['click', 'bs4', 'requests']
)
