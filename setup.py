from setuptools import setup, find_packages

setup(
    name='outlook-repair',
    version='1.0.0',
    description='Outlook File Repair Tool — diagnose, repair, and recover PST/OST/LST files',
    python_requires='>=3.8',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'outlook-repair=outlook_repair.main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
