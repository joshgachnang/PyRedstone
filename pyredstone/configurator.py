import ConfigParser
import os
import logging.config
import logconfig


# Config with logging config file
logging.config.dictConfig(logconfig.LOGGING)
logger = logging.getLogger('pyredstone')


def get_config(config_file=None, server=None):
    logger.info("Getting config from config file %s" % config_file)
    if config_file is None:
        config_file = '/home/minecraft/minecraft/pyredstone.cfg'
    if not os.path.exists(config_file):
        raise IOError("Could not open config file")
    config = ConfigParser.ConfigParser()
    config.read(config_file)

    if server is None:
        try:
            sections = config.sections()
            logger.debug(sections)
            if len(sections) < 1:
                raise SyntaxError("No sections found in config file")
            elif len(sections) > 1:
                logger.warning("More than one server found, no server specified. Using first server.")
            server = sections[0]
        except ConfigParser.Error as e:
            logger.exception("Could not get sections")
    if not config.has_section(server):
        raise SyntaxError("Server section '%s' of config file does not exist. Cannot continue." % (server, ))

    # Now we have a config file and a section.
    data = {}
    try:
        data['session_name'] = config.get(server, 'session_name')
        data['minecraft_dir'] = config.get(server, 'minecraft_dir')
        data['server_jar'] = config.get(server, 'server_jar')
        data['backup_dir'] = config.get(server, 'backup_dir')
    except ConfigParser.Error as e:
        raise SyntaxError("Config file is improperly formated")
    return data


def write_config(config_file, config):
    pass

if __name__ == '__main__':
    print get_config(config_file='example.cfg')
