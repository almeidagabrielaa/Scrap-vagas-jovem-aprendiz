from .base import Fonte
from .bne import BNE
from .catho import Catho
from .gupy import Gupy
from .infojobs import InfoJobs
from .trabalha_brasil import TrabalhaBrasil
from .vagas_com import VagasCom

TODAS: dict[str, Fonte] = {f.nome: f for f in (Gupy(), InfoJobs(), Catho(), TrabalhaBrasil(), VagasCom(), BNE())}

__all__ = ["Fonte", "TODAS"]
