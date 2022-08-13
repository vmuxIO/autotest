#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# imports
from argparse import (ArgumentParser, ArgumentDefaultsHelpFormatter, Namespace,
                      FileType, ArgumentTypeError)
from argcomplete import autocomplete
from configparser import ConfigParser
from logging import (info, debug, error, basicConfig,
                     DEBUG, INFO, WARN, ERROR)
from sys import argv, stderr, modules
from time import sleep
from os import (access, W_OK)
from os.path import isdir, isfile, join as path_join


# project imports
from server import Server, Host, Guest, LoadGen


# constants
THISMODULE: str = modules[__name__]

LOG_LEVELS: dict[int, int] = {
    0: ERROR,
    1: WARN,
    2: INFO,
    3: DEBUG,
}


# functions
def format_command(command: str) -> str:
    """
    Format the given command.

    This replaces linebreaks and trims lines.

    Parameters
    ----------
    command : str
        The command to format.

    Returns
    -------
    str
        The formatted command.

    See Also
    --------

    Example
    -------
    >>> cmd = '''
    ...     echo "hello" &&
    ...     echo "world";
    ...     ls -lah
    ...     '''
    >>> format_command(cmd)
    'echo "hello" && echo "world"; ls -lah'
    """
    formatted = ''
    for line in command.splitlines():
        formatted += line.strip() + ' '
    return formatted


def __do_nothing(variable: any) -> None:
    """
    Do nothing with the given variable.

    This is just to prevent linting errors for unused variables.

    Parameters
    ----------
    variable : any
        The variable to do nothing with.

    Returns
    -------
    """
    pass


def writable_dir(path: str) -> str:
    """
    Check if the given path is a writable directory.

    Parameters
    ----------
    path : str
        The path to check.

    Returns
    -------
    str
        The path if it is a writable directory.
    """
    if not isdir(path):
        raise ArgumentTypeError(f'{path} is not a directory.')
    if not access(path, W_OK):
        raise ArgumentTypeError(f'{path} is not writable.')
    return path


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

    subparsers = parser.add_subparsers(help='commands', dest='command')

    ping_parser = subparsers.add_parser(
        'ping',
        formatter_class=ArgumentDefaultsHelpFormatter,
        help='''Ping all servers.'''
    )
    # TODO a status command would be cool. It should tell us, which nodes
    # are running and how the device status is maybe
    # TODO note this is just temporary, we will have more genernic commands
    # later
    run_guest_parser = subparsers.add_parser(
        'run-guest',
        formatter_class=ArgumentDefaultsHelpFormatter,
        help='Run the guest VM.'
    )
    run_guest_parser.add_argument('-i',
                                  '--interface',
                                  type=str,
                                  choices=['brtap', 'macvtap'],
                                  default='brtap',
                                  help='Test network interface type.',
                                  )
    run_guest_parser.add_argument('-m',
                                  '--machine',
                                  type=str,
                                  choices=['pc', 'microvm'],
                                  default='pc',
                                  help='Machine type of the guest',
                                  )
    run_guest_parser.add_argument('-D',
                                  '--disk',
                                  type=FileType('rw'),
                                  help='Disk image path for the guest\'s ' +
                                       'root partition.',
                                  )
    run_guest_parser.add_argument('-d',
                                  '--debug',
                                  action='store_true',
                                  help='''Attach GDB to Qemu. The GDB server
                                  will listen on port 1234.''',
                                  )
    run_guest_parser.add_argument('-I',
                                  '--ioregionfd',
                                  action='store_true',
                                  help='''Use the IORegionFD enhanced
                                  virtio-net-device for the test interface.'''
                                  )
    kill_guest_parser = subparsers.add_parser(
        'kill-guest',
        formatter_class=ArgumentDefaultsHelpFormatter,
        help='Kill the guest VM.'
    )
    setup_network_parser = subparsers.add_parser(
        'setup-network',
        formatter_class=ArgumentDefaultsHelpFormatter,
        help='''Just setup the network
        for the guest.'''
    )
    setup_network_parser.add_argument('-i',
                                      '--interface',
                                      type=str,
                                      choices=['brtap', 'macvtap'],
                                      default='brtap',
                                      help='Test network interface type.',
                                      )
    teardown_network_parser = subparsers.add_parser(
        'teardown-network',
        formatter_class=ArgumentDefaultsHelpFormatter,
        help='''Teardown the guest
        network.'''
    )
    test_file_parser = subparsers.add_parser(
        'test-load-lat-file',
        formatter_class=ArgumentDefaultsHelpFormatter,
        help='Run load latency tests defined in a test config file.'
    )
    test_file_parser.add_argument('-t',
                                  '--testconfig',
                                  default='./tests.cfg',
                                  type=FileType('r'),
                                  help='Test configuration file path',
                                  )
    test_cli_parser = subparsers.add_parser(
        'test-load-lat-cli',
        formatter_class=ArgumentDefaultsHelpFormatter,
        help='Run load latency tests defined in the command line.'
    )
    test_cli_parser.add_argument('-N',
                                 '--name',
                                 type=str,
                                 default='l2-load-latency',
                                 help='Test name.',
                                 )
    test_cli_parser.add_argument('-i',
                                 '--interfaces',
                                 nargs='+',
                                 default=['pnic'],
                                 help='Test network interface type. ' +
                                      'Can be pnic, brtap or macvtap.',
                                 )
    test_cli_parser.add_argument('-o',
                                 '--outdir',
                                 type=writable_dir,
                                 default='./outputs',
                                 help='Test output directory.',
                                 )
    test_cli_parser.add_argument('-L',
                                 '--loadprog',
                                 type=FileType('r'),
                                 default='./moonprogs/l2-load-latency.lua',
                                 help='Load generator program.',
                                 )
    test_cli_parser.add_argument('-R',
                                 '--reflprog',
                                 type=FileType('r'),
                                 default='./moonprogs/reflector.lua',
                                 help='Reflector program.',
                                 )
    test_cli_parser.add_argument('-r',
                                 '--rates',
                                 nargs='+',
                                 default=[10000],
                                 help='List of throughput rates.',
                                 )
    test_cli_parser.add_argument('-T',
                                 '--threads',
                                 nargs='+',
                                 default=[1],
                                 help='List of number of threads.',
                                 )
    test_cli_parser.add_argument('-u',
                                 '--runtime',
                                 type=int,
                                 default=60,
                                 help='Test runtime.',
                                 )
    test_cli_parser.add_argument('-e',
                                 '--reps',
                                 type=int,
                                 default=1,
                                 help='Number of repetitions.',
                                 )
    test_cli_parser.add_argument('-a',
                                 '--accumulate',
                                 action='store_true',
                                 default=False,
                                 help='Accumulate the histograms of the ' +
                                      'repetitions.',
                                 )
    # TODO maybe we want to alter test parameters directly via the arguments

    __do_nothing(ping_parser)
    __do_nothing(kill_guest_parser)
    __do_nothing(teardown_network_parser)

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

    if not args.command:
        parser.print_usage(stderr)
        print(f'{argv[0]}: error: argument missing.', file=stderr)
        exit(1)

    if args.command == 'run-load-lat-cli':
        for interface in args.interfaces:
            if interface not in ['pnic', 'brtap', 'macvtap']:
                parser.print_usage(stderr)
                print(f'{argv[0]}: error: invalid interface type. ' +
                      'Must be one of: pnic, brtap, macvtap', file=stderr)
                exit(1)
        for rate in args.rates:
            if rate < 1:
                parser.print_usage(stderr)
                print(f'{argv[0]}: error: invalid rate. Must be >= 1',
                      file=stderr)
                exit(1)
        for thread in args.threads:
            if thread < 1:
                parser.print_usage(stderr)
                print(f'{argv[0]}: error: invalid thread. Must be >= 1',
                      file=stderr)
                exit(1)
        if args.runtime < 1:
            parser.print_usage(stderr)
            print(f'{argv[0]}: error: invalid runtime. Must be >= 1',
                  file=stderr)
            exit(1)
        if args.reps < 1:
            parser.print_usage(stderr)
            print(f'{argv[0]}: error: invalid number of repetitions. ' +
                  'Must be >= 1', file=stderr)
            exit(1)

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

    Example
    -------
    >>> setup_and_parse_config(args)
    ConfigParser(...)
    """
    conf = ConfigParser()
    conf.read(args.config.name)
    debug(f'configuration read from config file: {conf._sections}')
    return conf


def setup_logging(args: Namespace) -> None:
    """
    Setup the logging.

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.

    Returns
    -------

    See Also
    --------

    Example
    -------
    >>> setup_logging(args)
    """
    basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                level=LOG_LEVELS[args.verbosity])


def create_servers(conf: ConfigParser,
                   host: bool = True,
                   guest: bool = True,
                   loadgen: bool = True) -> dict[str, Server]:
    """
    Create the servers.

    Note that the insertion order of the servers is host, guest and finally
    loadgen.

    Parameters
    ----------
    conf : ConfigParser
        The config parser.
    host : bool
        Create the host server.
    guest : bool
        Create the guest server.
    loadgen : bool
        Create the loadgen server.

    Returns
    -------
    Dict[Server]
        A dictionary of servers.

    See Also
    --------

    Example
    -------
    >>> create_servers(conf)
    {'host': Host(...), ...}
    """
    servers = {}
    if host:
        servers['host'] = Host(
            conf['host']['fqdn'],
            conf['host']['test_iface'],
            conf['host']['test_iface_addr'],
            conf['host']['test_iface_driv'],
            conf['host']['moongen_dir'],
            conf['host']['xdp_reflector_dir']
        )
    if guest:
        servers['guest'] = Guest(
            conf['guest']['fqdn'],
            conf['guest']['test_iface'],
            conf['guest']['test_iface_addr'],
            conf['guest']['test_iface_driv'],
            conf['guest']['moongen_dir'],
            conf['host']['xdp_reflector_dir']
        )
    if loadgen:
        servers['loadgen'] = LoadGen(
            conf['loadgen']['fqdn'],
            conf['loadgen']['test_iface'],
            conf['loadgen']['test_iface_addr'],
            conf['loadgen']['test_iface_driv'],
            conf['loadgen']['moongen_dir']
        )
    return servers


def ping(args: Namespace, conf: ConfigParser) -> None:
    """
    Ping all servers.

    This a command function and is therefore called by execute_command().

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.
    conf : ConfigParser
        The config parser.

    Returns
    -------

    See Also
    --------
    execute_command : Execute the command.

    Example
    -------
    >>> ping(args, conf)
    """
    name: str
    server: Server
    # TODO here type annotation could be difficult
    for name, server in create_servers(conf).items():
        print(f'{name}: ' +
              f"{'reachable' if server.is_reachable() else 'unreachable'}")


def run_guest(args: Namespace, conf: ConfigParser) -> None:
    """
    Run the guest VM.

    This a command function and is therefore called by execute_command().

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.
    conf : ConfigParser
        The config parser.

    Returns
    -------

    See Also
    --------
    execute_command : Execute the command.

    Example
    -------
    >>> run_guest(args, conf)
    """
    host: Host = create_servers(conf, guest=False, loadgen=False)['host']

    try:
        host.setup_admin_tap()
        if args.interface == 'brtap':
            host.setup_test_br_tap()
        else:
            host.setup_test_macvtap()

        disk = args.disk if args.disk else conf['guest']['root_disk_file']

        host.run_guest(args.interface, args.machine, disk, args.debug,
                       args.ioregionfd)
    except Exception:
        host.kill_guest()
        host.cleanup_network()


def kill_guest(args: Namespace, conf: ConfigParser) -> None:
    """
    Kill the guest VM.

    This a command function and is therefore called by execute_command().

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.
    conf : ConfigParser
        The config parser.

    Returns
    -------

    See Also
    --------
    execute_command : Execute the command.

    Example
    -------
    >>> kill_guest(args, conf)
    """
    host: Host = create_servers(conf, guest=False, loadgen=False)['host']

    host.kill_guest()
    host.cleanup_network()


def setup_network(args: Namespace, conf: ConfigParser) -> None:
    """
    Just setup the network for the guest.

    This a command function and is therefore called by execute_command().

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.
    conf : ConfigParser
        The config parser.

    Returns
    -------

    See Also
    --------
    execute_command : Execute the command.

    Example
    -------
    >>> run_guest(args, conf)
    """
    host: Host = create_servers(conf, guest=False, loadgen=False)['host']

    try:
        host.setup_admin_tap()
        if args.interface == 'brtap':
            host.setup_test_br_tap()
        else:
            host.setup_test_macvtap()
    except Exception:
        host.cleanup_network()


def teardown_network(args: Namespace, conf: ConfigParser) -> None:
    """
    Just teardown the guest's network.

    This a command function and is therefore called by execute_command().

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.
    conf : ConfigParser
        The config parser.

    Returns
    -------

    See Also
    --------
    execute_command : Execute the command.

    Example
    -------
    >>> kill_guest(args, conf)
    """
    host: Host = create_servers(conf, guest=False, loadgen=False)['host']

    host.cleanup_network()


def test_infix(interface: str, rate: int, nthreads: int, rep: int) -> str:
    """
    Create a test infix for the test.

    Parameters
    ----------
    interface : str
        The interface to test.
    rate : int
        The rate to test.
    nthreads : int
        The number of threads to test.
    rep : int
        The number of repetitions to test.
    """
    return f'{interface}_r{rate}_t{nthreads}_{rep}'


def output_filepath(outdir: str, interface: str, rate: int, nthreads: int,
                    rep: int) -> str:
    """
    Create the output filename.

    Parameters
    ----------
    outdir : str
        The output directory.
    interface : str
        The interface name.
    rate : int
        The rate in Mbit/s.
    nthreads : int
        The number of threads.
    rep : int
        The repetition number.

    Returns
    -------
    str
        The output filename.
    """
    infix = test_infix(interface, rate, nthreads, rep)
    filename = f'output_{infix}.log'
    return path_join(outdir, filename)


def histogram_filepath(outdir: str, interface: str, rate: int, nthreads: int,
                       rep: int) -> str:
    """
    Create the histogram filename.

    Parameters
    ----------
    outdir : str
        The output directory.
    interface : str
        The interface name.
    rate : int
        The rate in Mbit/s.
    nthreads : int
        The number of threads.
    rep : int
        The repetition number.

    Returns
    -------
    str
        The histogram filename.
    """
    infix = test_infix(interface, rate, nthreads, rep)
    filename = f'histogram_{infix}.csv'
    return path_join(outdir, filename)


def test_done(outdir: str, interface: str, rate: int,
              nthreads: int, rep: int) -> bool:
    """
    Check if the test result is already available.

    Parameters
    ----------
    interface : str
        The interface to use.
    rate : int
        The rate to use.
    nthreads : int
        The number of threads to use.
    rep : int
        The iteration of the test.
    outdir : str
        The output directory.

    Returns
    -------
    bool
        True if the test result is already available.
    """
    output_file = output_filepath(outdir, interface, rate, nthreads, rep)
    histogram_file = histogram_filepath(outdir, interface, rate, nthreads,
                                        rep)

    return isfile(output_file) and isfile(histogram_file)


def accumulate_histograms(outdir: str, interface: str, rate: int,
                          nthreads: int, reps: int) -> None:
    """
    Accumulate the histograms for all repetitions.

    Parameters
    ----------
    outdir : str
        The output directory.
    interface : str
        The interface to use.
    rate : int
        The rate to use.
    nthreads : int
        The number of threads to use.
    reps : int
        The number of repetitions.
    """
    info("Accumulating histograms.")
    assert reps > 0, 'Reps must be greater than 0'
    if reps == 1:
        debug(f'Skipping accumulation: {interface} {rate} {nthreads}' +
              ', there is only one repetition')
        return

    acc_hist_filename = f'acc_histogram_{interface}_r{rate}_t{nthreads}.csv'
    acc_hist_filepath = path_join(outdir, acc_hist_filename)
    if isfile(acc_hist_filepath):
        debug(f'Skipping accumulation: {interface} {rate} {nthreads}' +
              ', already done')
        return

    histogram = {}
    for rep in range(reps):
        assert test_done(outdir, interface, rate, nthreads, rep), \
            'Test not done yet'

        with open(histogram_filepath(outdir, interface, rate, nthreads, rep)
                  ) as f:
            for line in f:
                if line.startswith('#'):
                    continue
                key, value = [int(n) for n in line.split(',')]
                if key not in histogram:
                    histogram[key] = 0
                histogram[key] += value

    with open(acc_hist_filepath, 'w') as f:
        for key, value in histogram.items():
            f.write(f'{key},{value}\n')


def accumulate_all_histograms(
    outdir: str,
    test_done: dict[str, dict[int, dict[int, bool]]]
) -> None:
    """
    Accumulate the histograms for all repetitions.

    Parameters
    ----------
    outdir : str
        The output directory.
    test_done : dict[str, dict[int, dict[int, bool]]]
        The test done dictionary.
    """
    for interface in test_done:
        for rate in test_done[interface]:
            for nthreads in test_done[interface][rate]:
                accumulate_histograms(
                    outdir,
                    interface,
                    rate,
                    nthreads,
                    max(test_done[interface][rate][nthreads].keys()) + 1
                )


def test_load_latency(
    name: str,
    interfaces: list[str],
    outdir: str,
    loadprog: str,
    reflprog: str,
    rates: list[int],
    threads: list[int],
    runtime: int,
    reps: int,
    accumulate: bool,
    args: Namespace,
    conf: ConfigParser
) -> None:
    """
    Run the load latency tests.

    Parameters
    ----------
    name : str
        The name of the test.
    interfaces : list[str]
        The interfaces to use.
    outdir : str
        The output directory.
    loadprog : str
        The load program.
    reflprog : str
        The reflector program.
    rates : list[int]
        The rates to use.
    threads : list[int]
        The threads to use.
    runtime : int
        The runtime to use.
    reps : int
        The number of repetitions to use.
    accumulate : bool
        Whether to accumulate the histogram of multiple repetitions.

    Returns
    -------
    """
    info('Running test:')
    info(f'  name      : {name}')
    info(f'  interfaces: {interfaces}')
    info(f'  outdir    : {outdir}')
    info(f'  loadprog  : {loadprog}')
    info(f'  reflprog  : {reflprog}')
    info(f'  rates     : {rates}')
    info(f'  threads   : {threads}')
    info(f'  runtime   : {runtime}')
    info(f'  reps      : {reps}')
    info(f'  accumulate: {accumulate}')

    # check which test results are still missing
    tests_todo = {
        interface: {
            rate: {
                nthreads: {
                    rep: not test_done(outdir, interface, rate, nthreads, rep)
                    for rep in range(reps)
                }
                for nthreads in (threads if interface != 'macvtap' else [1])
            }
            for rate in rates
        }
        for interface in interfaces
    }

    # check which interfaces are still needed
    interfaces_needed = []
    for interface in interfaces:
        needed = False
        for rate in rates:
            for nthreads in threads:
                needed = any(tests_todo[interface][rate][nthreads].values())
                if needed:
                    break
            if needed:
                break
        if needed:
            interfaces_needed.append(interface)
    if not interfaces_needed:
        info('All tests are already done.')
        # accumulate the histogram of multiple repetitions here
        if accumulate:
            accumulate_all_histograms(outdir, tests_todo)
        return

    # create server
    host: Host
    guest: Guest
    loadgen: LoadGen
    host, guest, loadgen = create_servers(conf).values()

    # prepare loadgen
    loadgen.bind_test_iface()
    loadgen.setup_hugetlbfs()

    # clean up guest and network first
    try:
        host.kill_guest()
    except Exception:
        pass
    host.cleanup_network()

    # loop over needed interfaces
    for interface in interfaces_needed:
        # setup interface
        dut: Server
        mac: str
        if interface in ['brtap', 'macvtap']:
            disk = conf['guest']['root_disk_file']
            host.setup_admin_tap()
            if interface == 'brtap':
                host.setup_test_br_tap()
            else:
                host.setup_test_macvtap()
            host.run_guest(net_type=interface, machine_type='pc',
                           root_disk=disk)
            dut = guest
            mac = '52:54:00:fa:00:60'
        else:
            dut = host
            mac = '64:9d:99:b1:0b:59'
        dut.bind_test_iface()
        dut.setup_hugetlbfs()

        # run missing tests for interface one by one and download test results
        # dut.stop_moongen_reflector()
        dut.start_moongen_reflector()
        sleep(5)
        for rate in rates:
            for nthreads in threads:
                for rep in range(reps):
                    if not tests_todo[interface][rate][nthreads][rep]:
                        debug(f'Skipping test: {interface} {rate} {nthreads}' +
                              f' {rep}, already done')
                        continue
                    info(f'Running test: {interface} {rate} {nthreads} {rep}')
                    # run test
                    remote_output_file = path_join(loadgen.moongen_dir,
                                                   'output.log')
                    remote_histogram_file = path_join(loadgen.moongen_dir,
                                                      'histogram.csv')
                    try:
                        loadgen.exec(f'rm -f {remote_output_file} ' +
                                     f'{remote_histogram_file}')
                        loadgen.run_l2_load_latency(mac, rate, runtime)
                        sleep(1.1*runtime)
                    except Exception as e:
                        error(f'Failed to run test: {interface} {rate} ' +
                              f'{nthreads} {rep} due to exception: {e}')
                        continue
                    # TODO stopping still fails when the tmux session
                    # does not exist
                    # loadgen.stop_l2_load_latency()

                    # download results
                    output_file = output_filepath(outdir, interface, rate,
                                                  nthreads, rep)
                    histogram_file = histogram_filepath(outdir, interface,
                                                        rate, nthreads, rep)
                    loadgen.copy_from(remote_output_file, output_file)
                    loadgen.copy_from(remote_histogram_file, histogram_file)
        dut.stop_moongen_reflector()
        # TODO try again when connection is lost

        # teardown interface
        if interface in ['brtap', 'macvtap']:
            host.kill_guest()
        host.cleanup_network()

    # accumulate the histogram of multiple repetitions here
    if accumulate:
        accumulate_all_histograms(outdir, tests_todo)


def test_load_lat_file(args: Namespace, conf: ConfigParser) -> None:
    """
    Run the load latency tests defined in a test config file.

    This a command function and is therefore called by execute_command().

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.
    conf : ConfigParser
        The config parser.

    Returns
    -------
    """
    test_conf = ConfigParser()
    test_conf.read(args.testconfig.name)

    for section in test_conf.sections():
        test_load_latency(
            test_conf[section]['name'],
            [i.strip() for i in test_conf[section]['interfaces'].split(',')],
            test_conf[section]['outdir'],
            test_conf[section]['loadprog'],
            test_conf[section]['reflprog'],
            [int(r.strip()) for r in test_conf[section]['rates'].split(',')],
            [int(t.strip()) for t in test_conf[section]['threads'].split(',')],
            int(test_conf[section]['runtime']),
            int(test_conf[section]['reps']),
            True if test_conf[section]['accumulate'] == 'true' else False,
            args,
            conf
        )


def test_load_lat_cli(args: Namespace, conf: ConfigParser) -> None:
    """
    Run the load latency tests defined in the command line.

    This a command function and is therefore called by execute_command().

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.
    conf : ConfigParser
        The config parser.

    Returns
    -------
    """
    test_load_latency(
        args.name,
        args.interfaces,
        args.outdir,
        args.loadprog.name,
        args.reflprog.name,
        args.rates,
        args.threads,
        args.runtime,
        args.reps,
        args.accumulate,
        args,
        conf
    )


def execute_command(args: Namespace, conf: ConfigParser) -> None:
    """
    Execute the function for the given command.

    This function runs the function corresponding to the high level command
    given by the user.

    Parameters
    ----------
    args : Namespace
        The argparse namespace containing the parsed arguments.
    conf : ConfigParser
        The config parser.

    Returns
    -------

    See Also
    --------

    Example
    -------
    >>> execute_command(args)
    """
    function_name = args.command
    if hasattr(args, 'sub_command') and args.sub_command:
        function_name += f'_{args.sub_command}'
    function_name = function_name.replace('-', '_')
    function = getattr(THISMODULE, function_name)
    debug(f'running command function {function_name}()')
    function(args, conf)


# main function
def main() -> None:
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
    # parse arguments, config file and setup logging
    parser: ArgumentParser = setup_parser()
    args: Namespace = parse_args(parser)
    setup_logging(args)
    conf: ConfigParser = setup_and_parse_config(args)

    # execute the requested command
    execute_command(args, conf)


if __name__ == '__main__':
    main()
