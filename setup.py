from setuptools import setup, find_packages
setup(
  name="viscom",
  version="1.0.0",
  package=["viscom"],
  include_package_metadata=True,
  packages=find_packages(),
  install_requires=[
    "flask",
    "requests",
    "dlib"
  ]
)
