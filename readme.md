# Orekit application template

This template provides the basic environment and framework for an orekit-based
application written in python.

Simply click the green *"Use this template"* button to get started, then, follow
these instructions:

1. Rename the `app_name` directory to your application name.
2. Update `pyproject.toml` by:
    1. Update the application name and description on lines 6 and 7.
    2. Update the author(s) on line 9.
    3. Update the app_name on line 31 to the new application directory value from step 1.
3. Update `environment.yaml` by:
    1. Updating the environment name on line 1.
    2. Adding any additional dependencies you know at the start.
4. Update `application.py` by:
    1. Updating the import on line 9 with the application directory name from step 1.
5. Update `src/__main__.py` by:
    1. Updating the import on line 4 with the application directory name from step 1.
6. Update `src/utils/logging.py` by:
    1. Updating the logger on line 24, replacing *app_name_ with the application directory name fro step 1.
7. Delete this list and update this `readme.md` with app-specific details.

# App name

## tl;dr

Build and activate the conda environment from the `environment.yaml`

```bash
mamba env create -f environment.yaml
mamba activate orekit-application
python src/satscheduler
```

## Developers

Recreate the `environment.yaml` as follows:

```bash
mamba env export --from-history | grep -vi '^prefix:' > environment.yaml
```
