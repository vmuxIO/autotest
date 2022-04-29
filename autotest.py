#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# imports
from argparse import (ArgumentParser, ArgumentDefaultsHelpFormatter, Namespace,
                      FileType)
from argcomplete import autocomplete
from configparser import ConfigParser
from logging import (error, info, warn, debug, basicConfig,
                     DEBUG, INFO, WARN, ERROR)


# constants
LOG_LEVELS = {
    0: ERROR,
    1: WARN,
    2: INFO,
    3: DEBUG,
}


# functions
def setup_parser() -> ArgumentParser:
    """
    Setup the argument parser.

    This function creates the argument parser and defines all the
    arguments before returning it.

    Parameters
    ----------

    Returns
    -------
    ArgumentParser
        The argument parser

    See Also
    --------
    parse_args : Parse the command line arguments.

    Examples
    --------
    >>> setup_parser()
    ArgumentParser(...)
    """
    # create the argument parser
    parser = ArgumentParser(
        description='''
        This program automates performance testing of Qemu's virtio-net-pci
        device for the vmuxIO project.''',
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    # define all the arguments
    parser.add_argument('-c',
                        '--config',
                        default='./autotest.cfg',
                        type=FileType('r'),
                        help='Configuration file path',
                        )
    parser.add_argument('-v',
                        '--verbose',
                        dest='verbosity',
                        action='count',
                        default=0,
                        help='''Verbosity, can be given multiple times to set
                             the log level (0: error, 1: warn, 2: info, 3:
                             debug)''',
                        )

    # return the parser
    return parser


def parse_args(parser: ArgumentParser) -> Namespace:
    """
    Parse the command line arguments.

    This function takes the argument parser, parses the arguments, does the
    auto-completion, and some further argument manipulations.

    Parameters
    ----------
    parser : ArgumentsParser
        The argparse argument parser.

    Returns
    -------
    Namespace
        The argparse namespace containing the parsed arguments.

    See Also
    --------
    setup_parser : Setup the argument parser.

    Examples
    --------
    >>> parser_args(parser)
    Namespace(...)
    """
    autocomplete(parser)
    args = parser.parse_args()

    args.verbosity = min(args.verbosity, len(LOG_LEVELS)-1)

    return args


def setup_and_parse_config(args: Namespace) -> ConfigParser:
    """
    Setup and parse the config file.

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.

    Returns
    -------
    ConfigParser
        The config parser.

    See Also
    --------

    Examples
    --------
    >>> setup_and_parse_config(args)
    ConfigParser(...)
    """
    conf = ConfigParser()
    conf.read(args.config.name)
    debug(f'configuration read from config file: {conf._sections}')
    return conf


def setup_logging(args):
    basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                level=LOG_LEVELS[args.verbosity])


# main function
def main():
    """
    autotest's main function.

    This is the main function of the autotest program. It parses the command
    line arguments, runs the specified tests and retrieves the performance
    data.

    Parameters
    ----------

    Returns
    -------

    See Also
    --------
    setup_parser : Setup the argument parser.
    parser_args : Parse the command line arguments.

    Example
    -------
    >>> main()
    """
    parser = setup_parser()
    args = parse_args(parser)
    setup_logging(args)
    conf = setup_and_parse_config(args)


if __name__ == '__main__':
    main()
