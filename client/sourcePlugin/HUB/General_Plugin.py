
from typing import Union
from abc import ABC

class GeneralSourcePlugin(ABC):
    def waitSourceTxRecorded(self,txid:str) -> tuple[bool, str, int]:
        pass
    def waitNewSourceBlock(self,blockNum: int) -> bool:
        pass
    def getTopBlockHeight(self) -> int:
        pass
    def getGenesisHeight_RPC(self) -> int:
        pass
  