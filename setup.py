from setuptools import find_packages, setup

with open('requirements.in') as f:
    REQUIREMENTS = [line for line in f if line and line[0] not in '#-']

with open('test-requirements.in') as f:
    TEST_REQUIREMENTS = [line for line in f if line and line[0] not in '#-']

setup(
    name='kiwi-structlog-config',
    version='0.1.4',
    url='https://github.com/kiwicom/kiwi-structlog-config',
    author='Platform Team',
    author_email='platform@kiwi.com',
    packages=find_packages(),
    install_requires=REQUIREMENTS,
    tests_require=TEST_REQUIREMENTS,
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
)
