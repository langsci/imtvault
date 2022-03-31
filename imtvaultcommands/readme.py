"""

"""
import subprocess

from cldfbench_imtvault import Dataset


def run(args):
    ds = Dataset()
    subprocess.check_call([
        'cldfbench',
        'cldfviz.text',
        str(ds.cldf_specs_dict[None].metadata_path.resolve()),
        '--output', str(ds.dir / 'README.md'),
        '--text-file', str(ds.etc_dir / 'README_tmpl.md')
    ])
