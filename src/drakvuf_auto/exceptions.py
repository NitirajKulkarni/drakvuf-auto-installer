"""DRAKVUF Auto-Installer Exception Hierarchy.

Author: Nitiraj Kulkarni
"""

class DrakvufError(Exception):
    """Base exception for all drakvuf-auto-installer errors."""
    pass


class HardwareIncompatibleError(DrakvufError):
    """Raised when host CPU lacks Intel VT-x, EPT, or required virtualization extensions."""
    pass


class PreFlightCheckError(DrakvufError):
    """Raised when environment prerequisites (RAM, disk, OS) are not met."""
    pass


class XenInstallationError(DrakvufError):
    """Raised during Xen hypervisor compilation, packaging, or installation."""
    pass


class RebootRequiredError(DrakvufError):
    """Special signal indicating host must reboot into Xen Dom0 before proceeding."""
    pass


class XenNotActiveError(DrakvufError):
    """Raised after reboot when system is still running bare-metal Linux instead of Xen Dom0."""
    pass


class EngineCompilationError(DrakvufError):
    """Raised during LibVMI or DRAKVUF C/C++ build failure."""
    pass


class NetworkBridgeError(DrakvufError):
    """Raised when setting up xenbr0 bridge or NAT routing fails."""
    pass


class GuestProvisioningError(DrakvufError):
    """Raised during Windows guest disk creation, ISO handling, or unattended setup."""
    pass


class SymbolExtractionError(DrakvufError):
    """Raised when extracting Windows kernel binaries or downloading PDB symbols fails."""
    pass


class ProfileSynthesisError(DrakvufError):
    """Raised when generating the LibVMI JSON profile fails."""
    pass


class ServiceDeploymentError(DrakvufError):
    """Raised when DrakCore, DrakWeb, Redis, or MinIO fails to start."""
    pass


class VerificationError(DrakvufError):
    """Raised when self-validation or test malware analysis injection fails."""
    pass
