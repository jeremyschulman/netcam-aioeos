# -*- coding: utf-8 -*-
from setuptools import setup

packages = [
    "netcam_aio_devices",
    "netcam_aio_devices.design_services",
    "netcam_aio_devices.eos",
    "netcam_aio_devices.eos.testing_services",
]

package_data = {"": ["*"]}

install_requires = ["aio-eapi>=0.2.1,<0.3.0", "interrogate>=1.5.0,<2.0.0"]

setup_kwargs = {
    "name": "netcam-aio-devices",
    "version": "0.1.0",
    "description": "",
    "long_description": None,
    "author": "Jeremy Schulman",
    "author_email": None,
    "maintainer": None,
    "maintainer_email": None,
    "url": None,
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "python_requires": ">=3.8,<4.0",
}


setup(**setup_kwargs)
