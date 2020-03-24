# TRAM v0.5

Threat Report ATT&CK<sup>®</sup> Mapping (TRAM) is a tool to aid analyst in mapping finished reports to ATT&CK. TRAM is currently in its beta phase and is actively being developed.
​
## Requirements
- [python3](https://www.python.org/) (3.7+)
- Google Chrome is our only supported/tested browser

## Installation
Start by cloning this repository.
```
git clone https://github.com/mitre-attack/tram.git
```
From the root of this project, install the PIP requirements.
```
pip install -r requirements.txt
```
Then start the server.
```
python tram.py
```
Once the server has started, point your browser to localhost:9999, and you can then enter a URL on the home page.
It currently takes several minutes to analyze a report, so please do not leave the page while it processes.

Configuration defaults can be changed [here](https://github.com/mitre-attack/tram/wiki/TRAM-Configuration)

## Intended Use
Please note that TRAM is currently intended to be used as a local, single user application. We are aware of the benefit of using the application in a centralized location for multiple analysts to access at once, and will work in the future to add features to make this viable.

## How do I contribute?

We welcome all the help we can get in making TRAM a more useful tool for the community. We have made a working prototype and acknowledge that there will need to be increased efforts in the future to maintain and improve it.

Read [CONTRIBUTING.md](CONTRIBUTING.md) to better understand what we're looking for. There's also a Developer Certificate of Origin that you'll need to sign off on.
​
## Notice

Copyright 2020 The MITRE Corporation

Approved for Public Release; Distribution Unlimited. Case Number 19-3429.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0
   
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This project makes use of ATT&CK®

ATT&CK® Terms of Use - https://attack.mitre.org/resources/terms-of-use/