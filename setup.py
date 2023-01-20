from setuptools import find_packages, setup
import os

setup(
    name='rok4tools',
    version=os.environ["VERSION"],
    scripts=["bin/pyr2pyr.py", "bin/make-layer.py"],
    data_files=[
        ('bin', [
            'bin/pyr2pyr.schema.json',
            'bin/pyr2pyr.example.json'
        ])
    ],
    description='Python tools for ROK4 project',
    author='Géoportail<tout_rdev@ign.fr>',
    url='https://github.com/rok4/pytools',
    install_requires=['rok4lib >= 1.2.0', 'jsonschema'],
    setup_requires=['wheel']
)