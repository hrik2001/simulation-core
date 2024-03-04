# ArcadiaSim
This repository contains code to conduct agent based simulation on Aracadia Finance, and is in active development

## Installation
The codebase assumes that the python version is 3.10.12 (having any release of 3.10 would be fine). 

It is recommended to use a virtual environment for developing this. To create one, kindly run the following command at the root of the project

```
python3.10 -m venv .venv
```

To activate the virtual environment, kindly run the following command
```
source .venv/bin/activate
```
To install the dependencies, the following command should install it all
```
pip install -r requirements.txt
```
To update the `requirements.txt`, the following command should be called
```
pip freeze > requirements.txt
```