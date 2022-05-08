# imports
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# project imports
from server import Server, Host


# classes
@dataclass
class NetworkInterface(ABC):
    """
    Network interface class.

    This class represents a network interface.

    Attributes
    ----------
    server : Server
        The server that uses the network interface.
    name : str
        The name of the network interface.
    pci_addr : str
        The PCI bus address of the network interface.
    mac_addr : str
        The MAC address of the network interface.

    Methods
    -------
    """
    name: str
    pci_addr: str
    mac_addr: str


class PhysicalNic(NetworkInterface):
    """
    Physical NIC class.

    This class represents a physical network interface.

    Attributes
    ----------
    name : str
        The name of the network interface.
    pci_addr : str
        The PCI bus address of the network interface.

    Methods
    -------
    __init__ : Initialize the network interface.
    """
    pass


class VirtIoInterface(NetworkInterface, ABC):
    """
    VirtIO interface class.

    This class represents a VirtIO network interface.

    Attributes
    ----------
    name : str
        The name of the network interface in the guest.
    pci_addr : str
        The PCI bus address of the network interface in the guest.
    mac_addr : str
        The MAC address of the network interface.

    Methods
    -------
    __init__ : Initialize the network interface.
    """
    pass


class BridgedTap(VirtIoInterface):
    """
    Bridged TAP device class.

    This class represents a bridged TAP device.

    Attributes
    ----------
    name : str
        The name of the network interface in the guest.
    pci_addr : str
        The PCI bus address of the network interface in the guest.
    mac_addr : str
        The MAC address of the network interface in the guest.
    tap_name : str
        The name of the TAP device on the host.
    br_name : str
        The name of the bridge to which the TAP device is bridged.

    Methods
    -------
    __init__ : Initialize the network interface.
    """
    tap_name: str
    br_name: str


class MacVTap(VirtIoInterface):
    """
    MacVTap NIC class.

    This class represents a MacVTap device.

    Attributes
    ----------
    name : str
        The name of the network interface in the guest.
    pci_addr : str
        The PCI bus address of the network interface in the guest.
    mac_addr : str
        The MAC address of the network interface in the guest.
    macvtap_name : str
        The name of the MacVTap device on the host.

    Methods
    -------
    __init__ : Initialize the network interface.
    """
    macvtap_name: str
