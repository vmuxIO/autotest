from dataclasses import dataclass, field
from enum import Enum


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
    repetition: int
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
                f"repetition={self.repetition}, " +
                f"outputdir={self.outputdir})")


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
                    for rate in self.rates:
                        for runtime in self.runtimes:
                            for repetition in range(self.repetitions):
                                test = LoadLatencyTest(
                                    machine=machine,
                                    interface=interface,
                                    qemu=qemu,
                                    vhost=vhost,
                                    ioregionfd=ioregionfd,
                                    reflector=reflector,
                                    rate=rate,
                                    runtime=runtime,
                                    repetition=repetition,
                                    outputdir=self.outputdir,
                                )
                                # here we check if test already done
                                print(f"run test {test}")
                            # here we accumulate
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
                                for rate in self.rates:
                                    for runtime in self.runtimes:
                                        for repetition in range(
                                                self.repetitions):
                                            test = LoadLatencyTest(
                                                machine=machine,
                                                interface=interface,
                                                qemu=qemu,
                                                vhost=vhost,
                                                ioregionfd=ioregionfd,
                                                reflector=reflector,
                                                rate=rate,
                                                runtime=runtime,
                                                repetition=repetition,
                                                outputdir=self.outputdir,
                                            )
                                            # here we check if test already
                                            # done
                                            print(f"run test {test}")
                                        # here we accumulate
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
