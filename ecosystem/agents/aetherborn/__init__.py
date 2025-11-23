# AETHERBORN SWARM v3.0 – Initialization Kernel
# Directory: ecosystem/agents/aetherborn/

from .swarm_brain import SwarmBrain
from .predator_kernel import PredatorKernel
from .aetherborn_identity import (
    AETHERBORN_NAME,
    AETHERBORN_VERSION,
    AETHERBORN_BANNER,
)

__all__ = [
    "SwarmBrain",
    "PredatorKernel",
    "AETHERBORN_NAME",
    "AETHERBORN_VERSION",
    "AETHERBORN_BANNER",
]
