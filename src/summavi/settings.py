"""
The Settings class handles user and configuration settings that are provided in
a [`YAML`](http://yaml.org) file.

The idea is that settings are grouped by components or any arbitrary grouping that makes sense for
the application or for the user. The Settings class can read from different YAML files. By default,
settings are loaded from a file called ``settings.yaml``. The default yaml configuration file is
located in the same directory as this module.

The YAML file is read and the configuration parameters for the given group are
made available as instance variables of the returned class.

The intended use is as follows:

    from summavi.settings import Settings

    power_duration_curve_settings = Settings.load("Power Duration Curve")

    print(f"Time granularity: {power_duration_curve_settings.TIME_GRANULARITY}s")
    print(f"Time granularity: {power_duration_curve_settings.MIN_WINDOW_DURATION}s")
    print(f"Time granularity: {power_duration_curve_settings.WINDOW_DURATION_STEP}s")

The above code reads the settings from the default YAML file for a group called ``Power Duration Curve``.
The settings will then be available as variables of the returned class, in this case
``power_duration_curve_settings``. The returned class is and behaves also like a dictionary.

The YAML section for the above code looks like this:

Power Duration Curve:

    TIME_GRANULARITY:       1.0   # Time granularity over which to calculate the average window in a sliding window [s]
    MIN_WINDOW_DURATION:    10    # Minimum duration of a window to include in the PDC [s]
    WINDOW_DURATION_STEP:   60    # Difference in duration between subsequent entries in the PDC [s]

When you want to read settings from another YAML file, specify the ``filename=`` keyword.
If that file is located at a specific location, also use the ``location=`` keyword.

    my_settings = Settings.load(filename="user.yaml", location="/Users/JohnDoe")

The above code will read the complete YAML file, i.e. all the groups into a dictionary.

"""
import inspect
import itertools
import logging
import pathlib
import re
from collections import namedtuple
from typing import NamedTuple

import yaml  # This module is provided by the pip package PyYaml - pip install pyyaml
from rich.text import Text
from rich.tree import Tree

logger = logging.getLogger(__name__)


class SettingsError(Exception):
    pass


def is_defined(cls, name):
    return hasattr(cls, name)


def get_attr_value(cls, name, default=None):
    try:
        return getattr(cls, name)
    except AttributeError:
        return default


def set_attr_value(cls, name, value):
    if hasattr(cls, name):
        raise KeyError(f"Overwriting setting {name} with {value}, was {hasattr(cls, name)}")


# Fix the problem: YAML loads 5e-6 as string and not a number
# https://stackoverflow.com/questions/30458977/yaml-loads-5e-6-as-string-and-not-a-number

SAFE_LOADER = yaml.SafeLoader
SAFE_LOADER.add_implicit_resolver(
    u'tag:yaml.org,2002:float',
    re.compile(u"""^(?:
     [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
    |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
    |\\.[0-9_]+(?:[eE][-+][0-9]+)?
    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*
    |[-+]?\\.(?:inf|Inf|INF)
    |\\.(?:nan|NaN|NAN))$""", re.X),
    list(u'-+0123456789.'))


class Settings:
    """
    The Settings class provides a load() method that loads configuration settings for a group
    into a dynamically created class as instance variables.
    """

    __memoized_yaml = {}  # Memoized settings yaml files

    @classmethod
    def read_configuration_file(cls, filename: str, *, force=False):
        """
        Read the YAML input configuration file. The configuration file is only read
        once and memoized as load optimization.

        Args:
            - filename (str): the fully qualified filename of the YAML file
            - force (bool): force reloading the file

        Returns:
            - Dictionary containing all the configuration settings from the YAML file
        """

        if force or filename not in cls.__memoized_yaml:
            logger.debug(f"Parsing YAML configuration file {filename}.")

            with open(filename, "r") as stream:
                try:
                    yaml_document = yaml.load(stream, Loader=SAFE_LOADER)
                except yaml.YAMLError as exc:
                    logger.error(exc)
                    raise SettingsError(f"Error loading YAML document {filename}") from exc

            cls.__memoized_yaml[filename] = yaml_document

        return cls.__memoized_yaml[filename]

    @classmethod
    def get_memoized_locations(cls):
        return cls.__memoized_yaml.keys()

    @classmethod
    def load(cls, group_name=None, filename="settings.yaml", location=None, *, force=False):
        """
        Load the settings for the given group from YAML configuration file.
        When no group is provided, the complete configuration is returned.

        The default YAML file is 'settings.yaml' and is located in the same directory
        as the settings module.

        About the ``location`` keyword several options are available.

        * when no location is given, i.e. ``location=None``, the YAML settings file is searched for
          at the same location as the settings module.

        * when a relative location is given, the YAML settings file is searched for relative to the
          current working directory.

        * when an absolute location is given, that location is used 'as is'.

        Args:
            group_name (str): the name of one of the main groups from the YAML file
            filename (str): the name of the YAML file to read
            location (str): the path to the location of the YAML file
            force (bool): force reloading the file
            add_local_settings (bool): update the Settings with site specific local settings

        Returns:
            - Dynamically created class with the configuration parameters as instance variables

        Raises:
            - SettingsError when the group is not defined in the YAML file
        """

        _THIS_FILE_LOCATION = pathlib.Path(__file__).resolve().parent

        if location is None:

            # Check if the yaml file is located at the location of the caller,
            # if not, use the file that is located where the Settings module is located.

            caller_dir = get_caller_info(level=2).filename
            caller_dir = pathlib.Path(caller_dir).resolve().parent

            if (caller_dir / filename).is_file():
                yaml_location = caller_dir
            else:
                yaml_location = _THIS_FILE_LOCATION
        else:

            # The location was given as an argument

            yaml_location = pathlib.Path(location).resolve()

        logger.log(5, f"yaml_location in Settings.load(location={location}) is {yaml_location}")

        # Load the YAML global document

        try:
            yaml_document_global = cls.read_configuration_file(
                yaml_location / filename, force=force
            )
        except FileNotFoundError as exc:
            raise SettingsError(
                f"Filename {filename} not found at location {yaml_location}."
            ) from exc

        # Check if there were any groups defined in the YAML document

        if not yaml_document_global:
            raise SettingsError(f"Empty YAML document {filename} at {yaml_location}.")

        if group_name in (None, ""):
            global_settings = AttributeDict(
                {name: value for name, value in yaml_document_global.items()}
            )
            return global_settings

        # Check if the requested group is defined in the YAML document

        if group_name not in yaml_document_global:
            raise SettingsError(
                f"Group name '{group_name}' is not defined in the YAML "
                f"document '{filename}' at '{yaml_location}."
            )

        # Check if the group has any settings

        if not yaml_document_global[group_name]:
            raise SettingsError(f"Empty group in YAML document {filename} at {yaml_location}.")

        group_settings = AttributeDict(
            {name: value for name, value in yaml_document_global[group_name].items()}
        )

        return group_settings

    @classmethod
    def to_string(cls):
        """
        Returns a simple string representation of the cached configuration of this Settings class.
        """
        memoized = cls.__memoized_yaml

        msg = ""
        for key in memoized.keys():
            msg += f"YAML file: {key}\n"
            for field in memoized[key].keys():
                length = 60
                line = str(memoized[key][field])
                trunc = line[:length]
                if len(line) > length:
                    trunc += " ..."
                msg += f"   {field}: {trunc}\n"

        return msg


def get_caller_info(level=1) -> NamedTuple:
    """
    Returns the filename, function name and lineno of the caller.

    The level indicates how many levels to go back in the stack.
    When level is 0 information about this function will be returned. That is usually not
    what you want so the default level is 1 which returns information about the function
    where the call to `get_caller_info` was made.

    There is no check
    Args:
        level (int): the number of levels to go back in the stack

    Returns:
        a namedtuple: CallerInfo['filename', 'function', 'lineno'].
    """

    frame = inspect.currentframe()
    for _ in range(level):
        if frame.f_back is None:
            break
        frame = frame.f_back
    frame_info = inspect.getframeinfo(frame)

    caller_info = namedtuple("CallerInfo", "filename function lineno")

    return caller_info(frame_info.filename, frame_info.function, frame_info.lineno)


class AttributeDict(dict):
    """
    This class is and acts like a dictionary but has the additional functionality
    that all keys in the dictionary are also accessible as instance attributes.

        >>> ad = AttributeDict({'a': 1, 'b': 2, 'c': 3})

        >>> assert ad.a == ad['a']
        >>> assert ad.b == ad['b']
        >>> assert ad.c == ad['c']

    Similarly, adding or defining attributes will make them also keys in the dict.

        >>> ad.d = 4  # creates a new attribute
        >>> print(ad['d'])  # prints 4
        4
    """

    def __init__(self, *args, label: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__["_label"] = label

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __rich__(self) -> Tree:
        label = self.__dict__["_label"] or "AttributeDict"
        tree = Tree(label, guide_style="dim")
        walk_dict_tree(self, tree, text_style="dark grey")
        return tree

    def __repr__(self):

        # We only want the first 10 key:value pairs

        count = 10
        sub_msg = ", ".join(f"{k!r}:{v!r}" for k, v in itertools.islice(self.items(), 0, count))

        # if we left out key:value pairs, print a ', ...' to indicate incompleteness

        return self.__class__.__name__ + f"({{{sub_msg}{', ...' if len(self) > count else ''}}})"


def walk_dict_tree(dictionary: dict, tree: Tree, text_style: str = "green"):

    for k, v in dictionary.items():
        if isinstance(v, dict):
            branch = tree.add(f"[purple]{k}", style="", guide_style="dim")
            walk_dict_tree(v, branch, text_style=text_style)
        else:
            text = Text.assemble((str(k), "medium_purple1"), ": ", (str(v), text_style))
            tree.add(text)
