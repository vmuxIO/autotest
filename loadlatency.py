from dataclasses import dataclass
from enum import Enum
from logging import error, info, debug
from time import sleep
from os.path import isfile, join as path_join

from server import Server, Host, Guest, LoadGen


class Machine(Enum):
    # Machine types

    # host machine
    HOST = "host"

    # VM with machine type PC
    PCVM = "pcvm"

    # VM with machine type MicroVM
    MICROVM = "microvm"


class Interface(Enum):
    # Interface types

    # Physical NIC (only works with host machine type)
    PNIC = "pnic"

    # Bridge to physical NIC on host, and for VM additionally VirtIO NIC
    # connected to it via TAP device
    BRIDGE = "bridge"

    # MacVTap to physical NIC on host, and for VM additionally VirtIO NIC
    # connected to it
    MACVTAP = "macvtap"


class Reflector(Enum):
    # Reflector types

    # MoonGen reflector
    MOONGEN = "moongen"

    # XDP reflector
    XDP = "xdp"


@dataclass
class LoadLatencyTest(object):
    """
    Load latency test class
    """
    machine: Machine
    interface: Interface
    mac: str
    qemu: str
    vhost: bool
    ioregionfd: bool
    reflector: Reflector
    rate: int
    runtime: int
    repetitions: int
    outputdir: str

    def test_infix(self):
        if self.machine == Machine.HOST:
            return (
                f"{self.machine.value}_{self.interface.value}" +
                f"_{self.reflector.value}_{self.rate*1000}Mbps" +
                f"_{self.runtime}s"
            )
        else:
            return (
                f"{self.machine.value}_{self.interface.value}" +
                f"_{self.qemu}_vhost{'on' if self.vhost else 'off'}" +
                f"_ioregionfd{'on' if self.ioregionfd else 'off'}" +
                f"_{self.reflector.value}_{self.rate*1000}Mbps" +
                f"_{self.runtime}s"
            )

    def output_filepath(self, repetition: int):
        return path_join(
            self.outputdir,
            f"output_{self.test_infix()}_{repetition}.log"
        )

    def histogram_filepath(self, repetition: int):
        return path_join(
            self.outputdir,
            f"histogram_{self.test_infix()}_{repetition}.csv"
        )

    def test_done(self, repetition: int):
        output_file = self.output_filepath(repetition)
        histogram_file = self.histogram_filepath(repetition)

        return isfile(output_file) and isfile(histogram_file)

    def __str__(self):
        return ("LoadLatencyTest(" +
                f"machine={self.machine.value}, " +
                f"interface={self.interface.value}, " +
                f"mac={self.mac}, " +
                f"qemu={self.qemu}, " +
                f"vhost={self.vhost}, " +
                f"ioregionfd={self.ioregionfd}, " +
                f"reflector={self.reflector.value}, " +
                f"rate={self.rate}, " +
                f"runtime={self.runtime}, " +
                f"repetitions={self.repetitions}, " +
                f"outputdir={self.outputdir})")

    def run(self, loadgen: LoadGen):
        debug(f"Running test {self}")
        for repetition in range(self.repetitions):
            if self.test_done(repetition):
                debug(f"Skipping repetition {repetition}, already done")
                continue
            debug(f'Running repetition {repetition}')

            remote_output_file = path_join(loadgen.moongen_dir,
                                           'output.log')
            remote_histogram_file = path_join(loadgen.moongen_dir,
                                              'histogram.csv')

            try:
                loadgen.exec(f'rm -f {remote_output_file} ' +
                             f'{remote_histogram_file}')
                loadgen.run_l2_load_latency(self.mac, self.rate, self.runtime)
            except Exception as e:
                error(f'Failed to run test due to exception: {e}')
                continue

            sleep(self.runtime + 5)
            try:
                loadgen.wait_for_success(f'ls {remote_histogram_file}')
            except TimeoutError:
                error('Waiting for histogram file to appear timed')
                continue
            sleep(1)
            # TODO here a tmux_exists function would come in handy

            # TODO stopping still fails when the tmux session
            # does not exist
            # loadgen.stop_l2_load_latency()

            # download results
            loadgen.copy_from(remote_output_file,
                              self.output_filepath(repetition))
            loadgen.copy_from(remote_histogram_file,
                              self.histogram_filepath(repetition))

    def accumulate(self):
        assert self.repetitions > 0, 'Reps must be greater than 0.'
        if self.repetitions == 1:
            debug('Skipping accumulation, there is only one repetition.')
            return

        acc_hist_filename = f'acc_histogram_{self.test_infix()}.csv'
        acc_hist_filepath = path_join(self.outputdir, acc_hist_filename)
        if isfile(acc_hist_filepath):
            debug('Skipping accumulation, already done.')
            return

        info("Accumulating histograms.")
        histogram = {}
        for repetition in self.repetitions:
            assert self.test_done(repetition), 'Test not done yet'

            with open(self.histogram_filepath(repetition), 'r') as f:
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


@dataclass
class LoadLatencyTestGenerator(object):
    """
    Load latency test generator class
    """
    machines: set[Machine]
    interfaces: set[Interface]
    qemus: set[str]
    vhosts: set[bool]
    ioregionfds: set[bool]
    reflectors: set[Reflector]
    rates: set[int]
    runtimes: set[int]
    repetitions: int
    accumulate: bool
    outputdir: str

    def run_interface_tests(self, loadgen: LoadGen, machine: Machine,
                            interface: Interface, mac: str, qemu: str,
                            vhost: bool, ioregionfd: bool,
                            reflector: Reflector):
        """
        Run tests for the given interface
        """
        for rate in self.rates:
            for runtime in self.runtimes:
                test = LoadLatencyTest(
                    machine=machine,
                    interface=interface,
                    mac=mac,
                    qemu=qemu,
                    vhost=vhost,
                    ioregionfd=ioregionfd,
                    reflector=reflector,
                    rate=rate,
                    runtime=runtime,
                    repetitions=self.repetitions,
                    outputdir=self.outputdir,
                )
                test.run(loadgen)
                if self.accumulate:
                    test.accumulate()

    def setup_interface(self, host: Host, machine: Machine,
                        interface: Interface, bridge_mac: str = None):
        if interface == Interface.BRIDGE:
            if machine == Machine.HOST:
                host.setup_test_bridge()
            else:
                host.setup_test_br_tap()
        elif interface == Interface.MACVTAP:
            host.setup_test_macvtap()

    def start_reflector(self, server: Server, reflector: Reflector,
                        iface: str = None):
        if reflector == Reflector.MOONGEN:
            server.bind_test_iface()
            server.setup_hugetlbfs()
            server.start_moongen_reflector()
        else:
            server.start_xdp_reflector(iface)
        sleep(5)

    def stop_reflector(self, server: Server, reflector: Reflector,
                       iface: str = None):
        if reflector == Reflector.MOONGEN:
            server.stop_moongen_reflector()
        else:
            server.stop_xdp_reflector(iface)

    def run_guest(self, host: Host, machine: Machine,
                  interface: Interface, qemu: str, vhost: bool,
                  ioregionfd: bool):
        host.run_guest(
            net_type='brtap' if interface == Interface.BRIDGE else 'macvtap',
            machine_type='pc' if machine == Machine.PCVM else 'microvm',
            root_disk=None,
            debug_qemu=False,
            ioregionfd=ioregionfd,
            qemu_build_dir=qemu,
            vhost=vhost
        )

    def run(self, host: Host, guest: Guest, loadgen: LoadGen):
        """
        Run the generator
        """

        info('Running test generator:')
        info(f'  machines   : {set(m.value for m in self.machines)}')
        info(f'  interfaces : {set(i.value for i in self.interfaces)}')
        info(f'  qemus      : {self.qemus}')
        info(f'  vhosts     : {self.vhosts}')
        info(f'  ioregionfds: {self.ioregionfds}')
        info(f'  reflectors : {set(r.value for r in self.reflectors)}')
        info(f'  rates      : {self.rates}')
        info(f'  runtimes   : {self.runtimes}')
        info(f'  repetitions: {self.repetitions}')
        info(f'  accumulate : {self.accumulate}')
        info(f'  outputdir  : {self.outputdir}')
        # TODO Qemus should contain strings like
        #   normal:/home/networkadmin/qemu-build
        #   replace-ioeventfd:/home/networkadmin/qemu-build-2
        # Empty path is also possible.
        # Before the : is the name, this goes to the test runner.
        # The rest is the path to the qemu build directory and just used here
        # to start the guest.
        # In case no name is given, we could number them.

        debug("initial cleanup")
        try:
            host.kill_guest()
        except Exception:
            pass
        host.cleanup_network()

        if Machine.HOST in self.machines:
            info("Running host tests")
            machine = Machine.HOST
            qemu = None
            vhost = None
            ioregionfd = None

            for interface in self.interfaces:
                debug(f"setup host interface {interface.value}")
                host.detect_test_iface()
                self.setup_interface(host, machine, interface)

                for reflector in self.reflectors:
                    if (interface != Interface.PNIC and
                            reflector == Reflector.MOONGEN):
                        continue

                    debug(f"start reflector {reflector.value}")
                    self.start_reflector(host, reflector)

                    mac = host.test_iface_mac if interface == Interface.PNIC \
                        else host.guest_test_iface_mac
                    self.run_interface_tests(
                        loadgen=loadgen,
                        machine=machine,
                        interface=interface,
                        mac=mac,
                        qemu=qemu,
                        vhost=vhost,
                        ioregionfd=ioregionfd,
                        reflector=reflector
                    )

                    debug(f"stop reflector {reflector.value}")
                    self.stop_reflector(host, reflector)

                debug(f"teardown host interface {interface.value}")
                host.cleanup_network()

        for machine in self.machines - {Machine.HOST}:
            info(f"Running {machine.value} guest tests")

            for interface in self.interfaces - {Interface.PNIC}:
                debug(f"setup guest interface {interface.value}")
                self.setup_interface(host, machine, interface)

                for qemu in self.qemus:
                    qemu_name, qemu_path = qemu.split(':')

                    for vhost in self.vhosts:
                        for ioregionfd in self.ioregionfds:
                            if ioregionfd and machine != Machine.MICROVM:
                                continue

                            debug(f"run guest {machine.value} " +
                                  f"{interface.value} {qemu_name} {vhost} " +
                                  f"{ioregionfd}")
                            self.run_guest(host, guest, machine, interface,
                                           qemu_path, vhost, ioregionfd)

                            debug("wait for guest connectability")
                            try:
                                guest.wait_for_connection()
                            except TimeoutError:
                                error('Waiting for connection to guest ' +
                                      'timed out.')
                                return

                            debug("detect guest test interface")
                            guest.detect_test_iface()

                            for reflector in self.reflectors:
                                debug(f"start reflector {reflector.value}")
                                self.start_reflector(guest, reflector)

                                self.run_interface_tests(
                                    loadgen=loadgen,
                                    machine=machine,
                                    interface=interface,
                                    mac=guest.test_iface_mac,
                                    qemu=qemu_name,
                                    vhost=vhost,
                                    ioregionfd=ioregionfd,
                                    reflector=reflector
                                )

                                debug(f"stop reflector {reflector.value}")
                                self.stop_reflector(guest, reflector)

                            debug(f"kill guest {machine.value} " +
                                  f"{interface.value} {qemu_name} {vhost} " +
                                  f"{ioregionfd}")
                            host.kill_guest()

                debug(f"teardown guest interface {interface.value}")
                host.cleanup_network()


if __name__ == "__main__":
    machines = {Machine.HOST, Machine.PCVM, Machine.MICROVM}
    interfaces = {Interface.PNIC, Interface.BRIDGE, Interface.MACVTAP}
    qemus = {"/home/networkadmin/qemu-build/qemu-system-x86_64",
             "/home/networkadmin/qemu-build2/qemu-system-x86_64"}
    vhosts = {True, False}
    ioregionfds = {True, False}
    reflectors = {Reflector.MOONGEN, Reflector.XDP}
    rates = {1, 10, 100}
    runtimes = {30, 60}
    repetitions = 3
    accumulate = True
    outputdir = "/home/networkadmin/loadlatency"

    generator = LoadLatencyTestGenerator(
        machines, interfaces, qemus, vhosts, ioregionfds, reflectors,
        rates, runtimes, repetitions, accumulate, outputdir
    )
    generator.run()
