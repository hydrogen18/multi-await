import setuptools
DESC = 'A python package to wait for multiple awaitables'


setuptools.setup(
name='multi-await',
version='1.0.2',
author='Eric Urban',
author_email='hydrogen18@gmail.com',
description=DESC,
long_description=DESC,
url='https://github.com/hydrogen18/multi-await',
packages=setuptools.find_packages(),
classifiers=[
  "Programming Language :: Python :: 3",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
],
python_requires='>=3.7',
install_requires=['aiotk < 1.0.0'],
)