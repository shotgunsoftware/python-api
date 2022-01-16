import sys

sys.path.insert(0, "/Users/ariel.calzada/instances/github.com/000paradox000/shotgunsoftware/python-api")

from shotgun_api3.lib.six.moves.configparser import SafeConfigParser as ConfigParser


def main():
    config_path = "/Users/ariel.calzada/instances/github.com/000paradox000/shotgunsoftware/python-api/tests/config"
    config_parser = ConfigParser()
    config_parser.read(config_path)
    for section in config_parser.sections():
        for option in config_parser.options(section):
            value = config_parser.get(section, option)
            print("Section: {}, Option: {}, Value: {}".format(
                section, option, value
            ))


if __name__ == "__main__":
    main()
