from setuptools import setup


setup(
    name='cldfbench_imtvault',
    py_modules=['cldfbench_imtvault'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'imtvault=cldfbench_imtvault:Dataset',
        ],
        'cldfbench.commands': [
            'imtvault=imtvaultcommands',
        ],
    },
    install_requires=[
        'pyigt',
        'cldfbench',
        'cldfviz[cartopy]',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
