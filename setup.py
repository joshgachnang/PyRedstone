from distutils.core import setup

setup(
    name='PyRedstone',
    version='0.1.0',
    author='Josh Gachnang',
    author_email='Josh@ServerCobra.com',
    packages=['pyredstone'],
    license='GPLv2',
    url='http://pypi.python.org/pypi/PyRedstone/',
    description='A Minecraft server wrapper and remote API',
    long_description=open('README.txt').read(),
    install_requires=[
        "nbt >= 1.3.0",
    ],    
)