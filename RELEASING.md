# Releasing imtvault

You must have installed the dataset via
```shell
pip install -e .
```
preferably in a separate virtual environment.

- Recreate the CLDF running
  ```shell
  cldfbench makecldf --with-cldfreadme --with-zenodo cldfbench_imtvault.py --glottolog-version v4.5
  ```
- Recreate the README running
  ```shell
  cldfbench imtvault.readme
  ```
- Commit and push changes to GitHub
- Create a release on GitHub, thereby pushing the version to Zenodo.
