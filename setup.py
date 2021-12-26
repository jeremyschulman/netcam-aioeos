# -*- coding: utf-8 -*-

#  Copyright 2021 Jeremy Schulman
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from setuptools import setup

packages = ["netcam_aioeos", "netcam_aioeos.eos"]

package_data = {"": ["*"]}

install_requires = ["aio-eapi>=0.2.1,<0.3.0", "interrogate>=1.5.0,<2.0.0"]

setup_kwargs = {
    "name": "netcam-aioeos",
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
