from dataclasses import dataclass, field
from subprocess import check_output, CalledProcessError
from socket import getfqdn
from logging import (error, info, warn, debug, basicConfig,
                     DEBUG, INFO, WARN, ERROR)
from abc import ABC


@dataclass
class Server(ABC):
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
        self.exec(f'cd {self.moongen_dir}; sudo ./bind-interfaces.sh')

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

    def setup_admin_tap(self: 'Host'):
        """
        Setup the admin tap.

        This sets up the tap device for the admin interface of the guest VM.
        So the interface to SSH connections and stuff.

        Parameters
        ----------

        Returns
        -------
        """
        self.exec('sudo modprobe tun tap')
        self.exec('sudo ip link show tap0 2>/dev/null' +
                  ' || (sudo tunctl -t tap0 -u networkadmin' +
                  ' && sudo brctl addif br0 tap0; true)')
        self.exec('sudo ip link set tap0 up')

    def setup_test_br_tap(self: 'Host'):
        """
        Setup the bridged test tap device.

        This sets up the tap device for the test interface of the guest VM.
        So the VirtIO device.

        Parameters
        ----------

        Returns
        -------
        """
        # load kernel modules
        self.exec('sudo modprobe tun tap')

        # create bridge and tap device
        self.exec('sudo ip link show br1 2>/dev/null || sudo brctl addbr br1')
        self.exec('sudo ip link show tap1 2>/dev/null || ' +
                  'sudo ip tuntap add dev tap1 mode tap user networkadmin ' +
                  'multi_queue')

        # add tap device and physical nic to bridge
        tap1_output = self.exec('sudo ip link show tap1')
        if 'master br1' not in tap1_output:
            self.exec('sudo brctl addif br1 tap1')
        test_iface_output = self.exec(f'sudo ip link show {self.test_iface}')
        if 'master br1' not in test_iface_output:
            self.exec(f'sudo brctl addif br1 {self.test_iface}')

        # bring up all interfaces (nic, bridge and tap)
        self.exec(f'sudo ip link set {self.test_iface} up ' +
                  '&& sudo ip link set br1 up && sudo ip link set tap1 up')

    def destroy_br_tap(self: 'Host'):
        """
        Destroy the bridged test tap device.

        Parameters
        ----------

        Returns
        -------
        """
        self.exec('sudo ip link set tap1 down')
        self.exec('sudo brctl delif br1 tap1')
        self.exec('sudo ip link delete tap1')
        self.exec('sudo brctl delbr br1')

    def run_guest(self: 'Host') -> None:
        # TODO this function should get a Guest object as argument
        """
        Run a guest VM.

        Parameters
        ----------

        Returns
        -------
        """
        # TODO this command should be build by the Guest object
        # it should take all the settings from the config file
        # and compile them.
        self.tmux_new(
            'qemu',
            'qemu-system-x86_64' +
            ' -cpu host' +
            ' -smp 4' +
            ' -m 4096' +
            ' -enable-kvm' +
            ' -drive format=raw,file=/dev/ssd/vm_test,if=virtio,cache=none' +
            ' -cdrom /home/networkadmin/images/test_init.iso' +
            ' -serial stdio' +
            ' -netdev tap,vhost=on,id=admin0,ifname=tap0,script=no,' +
            'downscript=no' +
            ' -device virtio-net-pci,netdev=admin0,mac=52:54:00:fa:00:5f' +
            ' -netdev tap,vhost=on,id=admin1,ifname=tap1,script=no,' +
            'downscript=no,queues=4' +
            ' -device virtio-net-pci,netdev=admin1,mac=52:54:00:fa:00:60,mq=on'
            )

    def kill_guest(self: 'Host') -> None:
        """
        Kill a guest VM.

        Parameters
        ----------

        Returns
        -------
        """
        self.tmux_kill('qemu')


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

    def stop_l2_load_latency(self: 'Server'):
        """
        Stop the MoonGen L2 load latency test.

        Parameters
        ----------

        Returns
        -------
        """
        self.tmux_kill('loadlatency')