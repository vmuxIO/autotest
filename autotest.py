#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# imports
from argparse import (ArgumentParser, ArgumentDefaultsHelpFormatter, Namespace,
                      FileType)
from argcomplete import autocomplete
from configparser import ConfigParser
from logging import (error, info, warn, debug, basicConfig,
                     DEBUG, INFO, WARN, ERROR)
from dataclasses import dataclass, field
from socket import getfqdn
from subprocess import check_output, CalledProcessError
from sys import argv, stdin, stdout, stderr, modules
from time import sleep


# constants
THISMODULE: str = modules[__name__]

LOG_LEVELS: dict[int, int] = {
    0: ERROR,
    1: WARN,
    2: INFO,
    3: DEBUG,
}


# classes
@dataclass
class Server(object):
    """
    Server class.

    This class represents a server.

    Attributes
    ----------
    fqdn : str
        The fully qualified domain name of the server.
    localhost : bool
        True if the server is localhost.
    test_iface : str
        The name of the interface to test.
    test_iface_addr : str
        The PCI bus address of the interface to test.
    moongen_dir : str
        The directory of the MoonGen installation.

    Methods
    -------
    __init__ : Initialize the object.
    __post_init__ : Post initialization.
    is_reachable : Check if the server is reachable.
    __exec_local : Execute a command on the localhost.
    __exec_ssh : Execute a command on the server over SSH.
    exec : Execute command on the server.
    tmux_new : Start a tmux session on the server.
    tmux_kill : Stop a tmux session on the server.
    tmux_send_keys : Send keys to a tmux session on the server.
    __copy_local : Copy a file to the localhost.
    __scp_to : Copy a file to the server.
    __scp_from : Copy a file from the server.
    copy_to : Copy a file to the server.
    copy_from : Copy a file from the server.

    See Also
    --------

    Examples
    --------
    >>> Server('server.test.de')
    Server(fqdn='server.test.de')
    """
    fqdn: str
    test_iface: str
    test_iface_addr: str
    _test_iface_id: int = field(default=None, init=False)
    moongen_dir: str
    localhost: bool = False

    def __post_init__(self: 'Server') -> None:
        """
        Post initialization.

        This method is called after the object is created.

        Parameters
        ----------

        Returns
        -------

        See Also
        --------
        __init__ : Initialize the object.
        """
        self.localhost = self.fqdn == 'localhost' or self.fqdn == getfqdn()

    def is_reachable(self: 'Server') -> bool:
        """
        Check if the server is reachable.

        Parameters
        ----------

        Returns
        -------
        bool
            True if the server is reachable.

        See Also
        --------
        exec : Execute command on the server.
        """
        if self.localhost:
            return True
        else:
            try:
                check_output(f'ping -c 1 -W 1 {self.fqdn}', shell=True)
            except CalledProcessError:
                return False
            else:
                return True

    def __exec_local(self: 'Server', command: str) -> str:
        """
        Execute a command on the localhost.

        This method is called by the exec method if the server is localhost.

        Parameters
        ----------
        command : str
            The command to execute.

        Returns
        -------
        str
            The output of the command.

        See Also
        --------
        exec : Execute command on the server.
        __exec_ssh : Execute a command on the server over SSH.
        """
        return check_output(command, shell=True).decode('utf-8')

    def __exec_ssh(self: 'Server', command: str) -> str:
        """
        Execute a command on the server over SSH.

        This method is called by the exec method if the server is not
        localhost.

        Parameters
        ----------
        command : str
            The command to execute.

        Returns
        -------
        str
            The output of the command.

        See Also
        --------
        exec : Execute command on the server.
        __exec_local : Execute a command on the localhost.
        """
        return check_output(f"ssh {self.fqdn} '{command}'",
                            shell=True).decode('utf-8')

    def exec(self: 'Server', command: str) -> str:
        """
        Execute command on the server.

        If the server is not localhost the command is executed over SSH.

        Parameters
        ----------
        command : str
            The command to execute.

        Returns
        -------
        str
            The output of the command.

        See Also
        --------
        __exec_local : Execute a command on the localhost.
        __exec_ssh : Execute a command on the server over SSH.

        Example
        -------
        >>> print(server.exec('ls -l'))
        .bashrc
        """
        debug(f'Executing command on {self.fqdn}: {command}')
        if self.localhost:
            return self.__exec_local(command)
        else:
            return self.__exec_ssh(command)

    def tmux_new(self: 'Server', session_name: str, command: str) -> None:
        """
        Start a tmux session on the server.

        Parameters
        ----------
        session_name : str
            The name of the session.
        command : str
            The command to execute.

        Returns
        -------

        See Also
        --------
        exec : Execute command on the server.
        tmux_kill : Stop a tmux session on the server.
        tmux_send_keys : Send keys to a tmux session on the server.
        """
        self.exec(f'tmux new-session -s {session_name} -d "{command}"')

    def tmux_kill(self: 'Server', session_name: str) -> None:
        """
        Stop a tmux session on the server.

        Parameters
        ----------
        session_name : str
            The name of the session.

        Returns
        -------

        See Also
        --------
        exec : Execute command on the server.
        tmux_new : Start a tmux session on the server.
        tmux_send_keys : Send keys to a tmux session on the server.
        """
        self.exec(f'tmux kill-session -t {session_name}')

    def tmux_send_keys(self: 'Server', session_name: str, keys: str) -> None:
        """
        Send keys to a tmux session on the server.

        Parameters
        ----------
        session_name : str
            The name of the session.
        keys : str
            The keys to execute.

        Returns
        -------

        See Also
        --------
        exec : Execute keys on the server.
        tmux_new : Start a tmux session on the server.
        tmux_kill : Stop a tmux session on the server.
        """
        self.exec(f'tmux send-keys -t {session_name} {keys}')

    def __copy_local(self: 'Server', source: str, destination: str) -> None:
        """
        Copy a file from the localhost to the server.

        This method is called by the copy method if the server is localhost.

        Parameters
        ----------
        source : str
            The source file.
        destination : str
            The destination file.

        Returns
        -------

        See Also
        --------
        copy : Copy a file from the server to the localhost.
        __copy_ssh : Copy a file from the server to the server over SSH.
        """
        self.exec(f'cp {source} {destination}')

    def __scp_to(self: 'Server', source: str, destination: str) -> None:
        """
        Copy a file from the localhost to the server.

        This method is called by the copy method if the server is not
        localhost.

        Parameters
        ----------
        source : str
            The source file.
        destination : str
            The destination file.

        Returns
        -------

        See Also
        --------
        copy : Copy a file from the server to the localhost.
        __copy_local : Copy a file from the server to the server over SSH.
        __scp_from : Copy a file from the server to the server over SSH.
        """
        self.exec(f'scp {source} {self.fqdn}:{destination}')

    def __scp_from(self: 'Server', source: str, destination: str) -> None:
        """
        Copy a file from the server to the localhost.

        This method is called by the copy method if the server is not
        localhost.

        Parameters
        ----------
        source : str
            The source file.
        destination : str
            The destination file.

        Returns
        -------

        See Also
        --------
        copy : Copy a file from the server to the localhost.
        __copy_local : Copy a file from the server to the server over SSH.
        __scp_to : Copy a file from the server to the server over SSH.
        """
        self.exec(f'scp {self.fqdn}:{source} {destination}')

    def copy_to(self: 'Server', source: str, destination: str) -> None:
        """
        Copy a file from the localhost to the server.

        Parameters
        ----------
        source : str
            The source file.
        destination : str
            The destination file.

        Returns
        -------

        See Also
        --------
        __copy_local : Copy a file from the server to the server over SSH.
        __scp_to : Copy a file from the server to the server over SSH.
        copy_from : Copy a file from the server to the localhost.

        Example
        -------
        >>> server.copy_to('/home/user/file.txt', '/home/user/file.txt')
        """
        if self.localhost:
            self.__copy_local(source, destination)
        else:
            self.__scp_to(source, destination)

    def copy_from(self: 'Server', source: str, destination: str) -> None:
        """
        Copy a file from the server to the localhost.

        Parameters
        ----------
        source : str
            The source file.
        destination : str
            The destination file.

        Returns
        -------

        See Also
        --------
        __copy_local : Copy a file from the server to the server over SSH.
        __scp_from : Copy a file from the server to the server over SSH.
        copy_to : Copy a file from the localhost to the server.

        Example
        -------
        >>> server.copy_from('/home/user/file.txt', '/home/user/file.txt')
        """
        if self.localhost:
            self.__copy_local(source, destination)
        else:
            self.__scp_from(source, destination)

    def get_driver_for_device(self: 'Server', device_addr: str) -> str:
        """
        Get the driver for a device.

        Parameters
        ----------
        device : str
            The device's PCI bus address.

        Returns
        -------
        str
            The driver for the device.

        See Also
        --------
        """
        return self.exec(f'lspci -v -s {device_addr} | grep driver ' +
                         '| cut -d":" -f 2 | tr -d " "')

    def is_test_iface_bound(self: 'Server') -> bool:
        """
        Check if the test interface is bound to DPDK.

        Parameters
        ----------

        Returns
        -------
        bool
            True if the test interface is bound to DPDK.
        """
        return self.get_driver_for_device(self.test_iface_addr) == 'igb_uio'

    def bind_test_iface(self: 'Server') -> None:
        """
        Bind test interface to DPDK.

        Parameters
        ----------

        Returns
        -------
        """
        # check if test interface is already bound
        if self.is_test_iface_bound():
            debug(f"{self.fqdn}'s test interface already bound to DPDK.")
            if not self._test_iface_id:
                self.detect_test_iface_id()
            return

        # bind available interfaces to DPDK
        self.exec(f'cd {self.moongen_dir}; sudo ./bind_interfaces.sh')

        # get the test interface id
        self.detect_test_iface_id()

    def detect_test_iface_id(self: 'Server') -> None:
        """
        Detect the test interface's DPDK ID.

        Parameters
        ----------

        Returns
        -------
        """
        output = self.exec("dpdk-devbind.py -s | grep 'drv=igb_uio'")

        for num, line in enumerate(output.splitlines()):
            if line.startswith(self.test_iface_addr):
                self._test_iface_id = num
                break

    def setup_hugetlbfs(self: 'Server'):
        """
        Setup hugepage interface.

        Parameters
        ----------

        Returns
        -------
        """
        self.exec(f"cd {self.moongen_dir}; sudo ./setup-hugetlbfs.sh")

    def start_l2_reflector(self: 'Server'):
        """
        Start the libmoon L2 reflector.

        Parameters
        ----------

        Returns
        -------
        """
        tbbmalloc_path = ('./build/libmoon/tbb_cmake_build/' +
                          'tbb_cmake_build_subdir_release/libtbbmalloc.so.2')
        self.tmux_new('reflector', f'cd {self.moongen_dir}; ' +
                      f'sudo LD_PRELOAD={tbbmalloc_path} build/MoonGen ' +
                      f'libmoon/examples/reflector.lua {self._test_iface_id}')

    def stop_l2_reflector(self: 'Server'):
        """
        Stop the libmoon L2 reflector.

        Parameters
        ----------

        Returns
        -------
        """
        self.tmux_kill('reflector')


class Host(Server):
    """
    Host class.

    This class represents a host, so the server that runs guest VMs. In out
    case it is also used for physical NIC tests.

    See Also
    --------
    Server : Server class.
    Guest : Guest class.
    LoadGen : LoadGen class.

    Examples
    --------
    >>> Host('server.test.de')
    Host(fqdn='server.test.de')
    """

    def __init__(self: 'Host',
                 fqdn: str,
                 test_iface: str,
                 test_iface_addr: str,
                 moongen_dir: str,
                 localhost: bool = False) -> None:
        """
        Initialize the Host class.

        Parameters
        ----------
        fqdn : str
            The fully qualified domain name of the host.
        test_iface : str
            The name of the test interface.
        test_iface_addr : str
            The IP address of the test interface.
        moongen_dir : str
            The directory of the MoonGen installation.
        localhost : bool
            True if the host is localhost.

        Returns
        -------
        Host : The Host object.

        See Also
        --------
        Server : The Server class.
        Server.__init__ : Initialize the Server class.

        Examples
        --------
        >>> Host('server.test.de')
        Host(fqdn='server.test.de')
        """
        super().__init__(fqdn, test_iface, test_iface_addr, moongen_dir,
                         localhost)


class Guest(Server):
    """
    Guest class.

    This class represents a guest, so the VM run on the host.

    See Also
    --------
    Server : The Server class.
    Host : The Host class.
    LoadGen : The LoadGen class.

    Examples
    --------
    >>> Guest('server.test.de')
    Guest(fqdn='server.test.de')
    """

    def __init__(self: 'Guest',
                 fqdn: str,
                 test_iface: str,
                 test_iface_addr: str,
                 moongen_dir: str
                 ) -> None:
        """
        Initialize the Guest class.

        Parameters
        ----------
        fqdn : str
            The fully qualified domain name of the guest.
        test_iface : str
            The name of the test interface.
        test_iface_addr : str
            The IP address of the test interface.
        moongen_dir : str
            The directory of the MoonGen installation.
        localhost : bool
            True if the host is localhost.

        Returns
        -------
        Guest : The Guest object.

        See Also
        --------
        Server : The Server class.
        Server.__init__ : Initialize the Server class.

        Examples
        --------
        >>> Guest('server.test.de')
        Guest(fqdn='server.test.de')
        """
        super().__init__(fqdn, test_iface, test_iface_addr, moongen_dir)


class LoadGen(Server):
    """
    LoadGen class.

    This class represents a loadgen server, so the server that runs the load
    generator against the host and guest.

    See Also
    --------
    Server : The Server class.
    Host : The Host class.
    Guest : The Guest class.

    Examples
    --------
    >>> LoadGen('server.test.de')
    LoadGen(fqdn='server.test.de')
    """

    def __init__(self: 'LoadGen',
                 fqdn: str,
                 test_iface: str,
                 test_iface_addr: str,
                 moongen_dir: str,
                 localhost: bool = False) -> None:
        """
        Initialize the LoadGen class.

        Parameters
        ----------
        fqdn : str
            The fully qualified domain name of the load generator.
        test_iface : str
            The name of the test interface.
        test_iface_addr : str
            The IP address of the test interface.
        moongen_dir : str
            The directory of the MoonGen installation.
        localhost : bool
            True if the host is localhost.

        Returns
        -------
        LoadGen : The LoadGen object.

        See Also
        --------
        Server : The Server class.
        Server.__init__ : Initialize the Server class.

        Examples
        --------
        >>> LoadGen('server.test.de')
        LoadGen(fqdn='server.test.de')
        """
        super().__init__(fqdn, test_iface, test_iface_addr, moongen_dir,
                         localhost)

    def run_l2_load_latency(self: 'LoadGen', runtime: int = 60):
        """
        Run the MoonGen L2 load latency test.

        Parameters
        ----------

        Returns
        -------

        See Also
        --------

        Example
        -------
        >>> LoadGen('server.test.de').start_l2_load_latency()
        """
        tbbmalloc_path = ('./build/libmoon/tbb_cmake_build/' +
                          'tbb_cmake_build_subdir_release/libtbbmalloc.so.2')
        self.tmux_new('loadlatency', f'cd {self.moongen_dir}; ' +
                      f'sudo LD_PRELOAD={tbbmalloc_path} timeout {runtime} ' +
                      'build/MoonGen examples/l2-load-latency.lua ' +
                      f'{self._test_iface_id} {self._test_iface_id}')


# functions
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

    ping_parser = subparsers.add_parser('ping',
                                        help='''Ping all servers.''')
    # TODO a status command would be cool. It should tell us, which nodes
    # are running and how the device status is maybe
    # TODO note this is just temporary, we will have more genernic commands
    # later
    test_pnic_parser = subparsers.add_parser('test-pnic',
                                             help='Test the physical NIC.')

    __do_nothing(ping_parser)

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
            conf['host']['moongen_dir']
        )
    if guest:
        servers['guest'] = Guest(
            conf['guest']['fqdn'],
            conf['guest']['test_iface'],
            conf['guest']['test_iface_addr'],
            conf['guest']['moongen_dir']
        )
    if loadgen:
        servers['loadgen'] = LoadGen(
            conf['loadgen']['fqdn'],
            conf['loadgen']['test_iface'],
            conf['loadgen']['test_iface_addr'],
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
    for name, server in create_servers(conf).items():
        print(f'{name}: ' +
              f"{'reachable' if server.is_reachable() else 'unreachable'}")


def test_pnic(args: Namespace, conf: ConfigParser) -> None:
    """
    Test the physical NIC.

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
    >>> test_physical_nic(args, conf)
    """
    host, loadgen = create_servers(conf, guest=False).values()

    loadgen.bind_test_iface()
    host.bind_test_iface()

    loadgen.setup_hugetlbfs()
    host.setup_hugetlbfs()

    runtime = 60

    try:
        host.start_l2_reflector()
        loadgen.run_l2_load_latency(runtime)
        sleep(1.1*runtime)
    finally:
        host.stop_l2_reflector()


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
