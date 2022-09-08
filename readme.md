# orbit tool

Simple tool providing a series of helpful orbit-related functions.

## Setup and installation

### Anaconda setup

If you already have an anaconda installation, skip this section. Otherwise, follow these steps to install `mamba`:

1. Follow [these instructions](https://conda.io/projects/conda/en/latest/user-guide/install/index.html) to install `conda`. Note for windows users, I recommend installing the linux version on wsl2.  However that's a personal preference.

2. Follow [these instructions](https://mamba.readthedocs.io/en/latest/installation.html) to install `mamba`. Or, if you don't want to click the link, just run the following command:

```bash
conda install mamba -n base -c conda-forge
```

### Environment setup

Build and activate the conda environment from the `environment.yaml`

```bash
mamba env create -f environment.yaml
mamba activate orbit-tool
python src --help
usage: src [-h] [-c CONFIG] [--quiet | --error | --warn | --info | --debug] {checktle,convert-orbit} ...
```


