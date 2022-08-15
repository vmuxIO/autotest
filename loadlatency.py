from dataclasses import dataclass
from enum import Enum
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
    qemu: str
    vhost: bool
    ioregionfd: bool
    reflector: Reflector
    rate: int
    runtime: int
    repetitions: int
    outputdir: str

    def __str__(self):
        return ("LoadLatencyTest(" +
                f"machine={self.machine.value}, " +
                f"interface={self.interface.value}, " +
                f"qemu={self.qemu}, " +
                f"vhost={self.vhost}, " +
                f"ioregionfd={self.ioregionfd}, " +
                f"reflector={self.reflector.value}, " +
                f"rate={self.rate}, " +
                f"runtime={self.runtime}, " +
                f"repetition={self.repetitions}, " +
                f"outputdir={self.outputdir})")

    def run(self):
        print(f"run test {self}")
        for repetition in range(self.repetitions):
            # here we check if test repetition already done
            # run test repetition
            pass

    def accumulate(self):
        pass


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

    def run_interface_tests(self, machine, interface, qemu, vhost, ioregionfd,
                            reflector):
        """
        Run tests for the given interface
        """
        for rate in self.rates:
            for runtime in self.runtimes:
                test = LoadLatencyTest(
                    machine=machine,
                    interface=interface,
                    qemu=qemu,
                    vhost=vhost,
                    ioregionfd=ioregionfd,
                    reflector=reflector,
                    rate=rate,
                    runtime=runtime,
                    repetitions=self.repetitions,
                    outputdir=self.outputdir,
                )
                test.run()
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

    def run(self):
        """
        Run the generator
        """
        if Machine.HOST in self.machines:
            machine = Machine.HOST
            qemu = None
            vhost = None
            ioregionfd = None
            for interface in self.interfaces:
                print("setup interface")
                for reflector in self.reflectors:
                    if (interface != Interface.PNIC and
                            reflector == Reflector.MOONGEN):
                        continue
                    print("start reflector")
                    self.run_interface_tests(
                        machine=machine,
                        interface=interface,
                        qemu=qemu,
                        vhost=vhost,
                        ioregionfd=ioregionfd,
                        reflector=reflector
                    )
                    print("stop reflector")
                print("teardown interface")

        for machine in self.machines - {Machine.HOST}:
            for interface in self.interfaces - {Interface.PNIC}:
                print("setup host interface")
                for qemu in self.qemus:
                    for vhost in self.vhosts:
                        for ioregionfd in self.ioregionfds:
                            if ioregionfd and machine != Machine.MICROVM:
                                continue
                            print("run guest")
                            for reflector in self.reflectors:
                                print("start reflector")
                                self.run_interface_tests(
                                    machine=machine,
                                    interface=interface,
                                    qemu=qemu,
                                    vhost=vhost,
                                    ioregionfd=ioregionfd,
                                    reflector=reflector
                                )
                                print("stop reflector")
                            print("kill guest")
                print("teardown host interface")


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
