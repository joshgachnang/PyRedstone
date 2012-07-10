import os
import ConfigParser
class RedstoneServer:
    def __init__(self, config_file):
        try:
            config = ConfigParser.ConfigParser()
            self.config = config.read(config_file)
        except ConfigParser.Error as e:
            raise IOError("Couldn't read or parse config file.")
        try:
            self.server_type = self.config.get('Server', 'type')
            self.base_path = self.config.get('Server', 'path')
            self.server_jar_name = self.config.get('Server', 'jar')
            