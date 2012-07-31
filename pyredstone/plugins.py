import urllib2
import json
import urlparse
import os
import sys
import shutil
import logging
import zipfile
import random
import string

api_url = 'http://bukget.org/api/'

download_dir = '/tmp/'
bukkit_base_path = '/tmp/bukkit'
logger = logging.getLogger('plugins')
logger.setLevel("DEBUG")


def random_string():
    """ Returns a random, 16 character lowercase and numeral string prepended by 'pyrs-'."""
    return 'pyrs-' + ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(16))

def download_plugin(plugin_name, version=None):
    """ Given a plugin name and version, retrieves the plugin JSON from the
    API, downloads it to the download_dir, and returns the path to the folder
    as a string. Attempts to leave everything in a working state.

    Server needs to be restarted or reloaded when new plugins are installed.

    Raises SyntaxError when plugin isn't found or can't be decoded to JSON.
    Raises IOError when a directory/file cannot be removed/moved/copied.
    """
    if version is None:
        version = 'latest'
    # Build end of URL
    path = '/'.join(['plugin', plugin_name, version])
    url = urlparse.urljoin(api_url, path)
    logger.error(url)
    try:
        raw_json = urllib2.urlopen(url).read()
    except urllib2.HTTPError as e:
        logger.exception("Error connecting to %s." % (url, ))
        raise SyntaxError("Plugin %s could not be found. Check capitalization." % (plugin_name))
    try:
        json_data = json.loads(raw_json)
    except ValueError as e:
        logger.exception("Could not load raw JSON: %s" % raw_json)
        raise SyntaxError("Could not decode JSON. Can't continue. Check all URLs are correct, or API might be down.")
    # Download link is stored in the first array of 'versions'.
    download_link = json_data['versions'][0]['dl_link']
    filename = json_data['versions'][0]['filename']
    plugin_download_dir = os.path.join(download_dir, random_string())
    logger.info("Creating temporary download directory %s" % (plugin_download_dir, ))
    # Make the directory
    try:
        os.mkdir(plugin_download_dir)
    except OSError as e:
        logger.exception("Could not create plugin_download_dir %s" % (plugin_download_dir, ))
        raise IOError("Could not create tmp download directory %s" % (plugin_download_dir, ))
    output_file = os.path.join(plugin_download_dir, filename)
    try:
        download(download_link, output_file)
    except EnvironmentError as e:
        logger.exception("Could not download file.")
        raise IOError("Download failed: Could not download %s to %s" % (plugin_name, output_file))
    if os.path.exists(output_file):
        return output_file
    else:
        raise IOError("Could not download %s to %s" % (plugin_name, output_file))

def install_plugin(plugin_path, bukkit_base_path, overwrite_config=False):
    logger.debug("Install plugin. Path: %s, Bukkit path: %s, overwrite_config; %s" % (plugin_path, bukkit_base_path, overwrite_config))
    jar_name = plugin_path.split('/')[-1]
    logger.debug("Intial jar_name: %s" % jar_name)
    if jar_name[-4:] != '.jar':
        # Likely an archive. Deal with it here.
        if zipfile.is_zipfile(plugin_path):
            logger.info("Plugin is a zip file. Extracting..")
            # Plugin is a zip. Extract and change jar_name
            # First, get a list of items in plugin_path directory
            pre = os.listdir(os.path.dirname(plugin_path))
            zipper = zipfile.ZipFile(plugin_path)
            zipper.extractall(os.path.dirname(plugin_path))
            # Now get a new listing of items in plugin_path directory
            post = os.listdir(os.path.dirname(plugin_path))
            # Do a set difference
            files = set(post) - set(pre)
            logger.info("Extracted files: %s" % str(files))
            # Find the jar
            for f in files:
                if f[-4:] == '.jar':
                    jar_name = f
    else:
        files = [jar_name, ]
    # If overwrite_config, we need to get rid of the plugin directory first.
    if overwrite_config:
        if os.path.exists(os.path.join(bukkit_base_path, 'plugins', jar_name[:-4])):
            try:
                shutil.move(os.path.join(bukkit_base_path, 'plugins', jar_name[:-4]), os.path.join(bukkit_base_path, 'plugins', jar_name[:-4] + '.bak'))
            except shutil.Error as e:
                logger.exception("Problem moving config folders.")
                raise IOError("Cannot backup existing config directory.")
        for f in files:
            if os.path.isdir(os.path.join(download_dir, f)):
                try:
                    shutil.move(os.path.join(download_dir, f), os.path.join(bukkit_base_path, 'plugins', f))
                except shutil.Error as e:
                    logger.exception("Cannot move folder %s to plugin dir." % (f, ))
                    raise IOError("Cannot move folder %s to plugin dir." % (f, ))
    # Jar: If plugin is already installed, remove plugin. 
    if os.path.exists(os.path.join(bukkit_base_path, 'plugins', jar_name)):
        try:
            shutil.move(os.path.join(bukkit_base_path, 'plugins', jar_name), os.path.join(bukkit_base_path, 'plugins', jar_name + ".bak"))
        except OSError as e:
            logger.exception("Could not remove %s" % (os.path.join(bukkit_base_path, 'plugins', jar_name)))
            raise IOError("Could not remove %s" % (os.path.join(bukkit_base_path, 'plugins', jar_name)))
    try:
        shutil.move(plugin_path, os.path.join(bukkit_base_path, 'plugins', jar_name))
    except shutil.Error as e:
        logger.exception("Could not move plugin: %s to plugins directory: %s." % (jar_name, os.path.join(bukkit_base_path, 'plugins')))
        raise IOError("Could not move plugin: %s to plugins directory: %s." % (jar_name, os.path.join(bukkit_base_path, 'plugins')))
    if os.path.exists(os.path.join(bukkit_base_path, 'plugins', jar_name)):
        return os.path.join(bukkit_base_path, 'plugins', jar_name)
    else:
        logger.error("Jar isn't in directory. Attempting to roll back changes.")
        try:
            shutil.move(os.path.join(bukkit_base_path, 'plugins', jar_name + ".bak"), s.path.join(bukkit_base_path, 'plugins', jar_name,))
        except OSError as e:
            logger.exception("Plugin jar didn't end up in plugin directory and could not roll back changes.")
            raise IOError("Plugin jar didn't end up in plugin directory and could not roll back changes.")

def download(url, output):
    """ Downloads the given url to output with a status bar."""
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    try:
        with open(output, 'wb') as f:
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            print "Downloading: %s Bytes: %s" % (file_name, file_size)

            file_size_dl = 0
            block_sz = 8192
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break

                file_size_dl += len(buffer)
                f.write(buffer)
                status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                status = status + chr(8)*(len(status)+1)
                print status,
    except EnvironmentError as e:
        logger.exception("Could not open output file %s" % output)
        raise


if __name__ == '__main__':
    path = download_plugin(sys.argv[1])
    install_plugin(path, bukkit_base_path=bukkit_base_path)