from distutils.core import setup

setup(
    name='PyRedstone',
    version='0.2.0',
    author='Josh Gachnang',
    author_email='Josh@ServerCobra.com',
    packages=['pyredstone', 'pyredstone.test', ],
    data_files=[('/etc/init.d', ['bin/init.d/minecraft', 'bin/init.d/redstone_server']),
               ],
    scripts=['bin/redstone.py',],
    license='GPLv2',
    url='http://pypi.python.org/pypi/PyRedstone/',
    description='A Minecraft server wrapper and remote API',
    long_description=open('README.rst').read(),
    install_requires=[
        "nbt >= 1.3.0",
        "cherrypy >= 3.2.0",
        "magplus >= 0.2.1"
        "linux-metrics >= 0.1.3",
    ],
)
