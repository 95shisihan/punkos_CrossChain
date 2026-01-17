from typing import List, Dict, Any 
class ChainInfo:
    def __init__(
        self,
        chain_id: int,
        symbol: str,
        name: str,
        my_contract_num: int,
        my_contract_list: List[str]        
    ):
        self.chain_id = chain_id
        self.symbol = symbol
        self.name = name
        self.my_contract_num = my_contract_num
        self.my_contract_list = my_contract_list
class HubChainInfo(ChainInfo):
    def __init__(
        self,
        chain_id: int = 0,
        symbol: str = 'HUB',
        name: str = 'CrosschainZone Hubchain',
        my_contract_num: int = 1,
        my_contract_list: List[str] = ['']        
    ):
        ChainInfo.__init__(
            self,
            chain_id=chain_id,
            symbol=symbol,
            name=name,
            my_contract_num=my_contract_num,
            my_contract_list=my_contract_list   
        )
    def update(self, other: 'HubChainInfo') -> Dict[str, Any]:  
        """  
        Compare and update hub chain information  
        
        Args:  
            other (HubChainInfo): New hub chain information  
        
        Returns:  
            Dict[str, Any]: Changed fields  
        """   
        changes: Dict[str, Any] = {}  
        update_fields = {  
            'symbol': (self.symbol, other.symbol),  
            'name': (self.name, other.name),    
            'my_contract_num': (self.my_contract_num, other.my_contract_num),  
            'my_contract_list': (self.my_contract_list, other.my_contract_list)  
        }  
        for field, (current, new) in update_fields.items():  
            if current != new:  
                changes[field] = {  
                    'old': current,  
                    'new': new  
                }  
                setattr(self, field, new)     
        return changes 
class SourceChainInfo(ChainInfo):
    def __init__(
        self,
        chain_id: int = 1,
        symbol: str = 'SC',
        name: str = 'SourceChain',
        my_contract_num: int = 0,
        my_contract_list: List[str] = ['']*3, 
        state: int = 1        
    ):
        ChainInfo.__init__(
            self,
            chain_id=chain_id,
            symbol=symbol,
            name=name,
            my_contract_num=my_contract_num,
            my_contract_list=my_contract_list   
        )
        self.state: int = state
    def update(self, other: 'SourceChainInfo') -> Dict[str, Any]:  
        """  
        Compare and update source chain information  
        
        Args:  
            other (SourceChainInfo): New source chain information  
        
        Returns:  
            Dict[str, Any]: Changed fields  
        """   
        changes: Dict[str, Any] = {}  
        update_fields = {  
            'symbol': (self.symbol, other.symbol),  
            'name': (self.name, other.name),  
            'state': (self.state, other.state),  
            'my_contract_num': (self.my_contract_num, other.my_contract_num),  
            'my_contract_list': (self.my_contract_list, other.my_contract_list)  
        }  
        for field, (current, new) in update_fields.items():  
            if current != new:  
                changes[field] = {  
                    'old': current,  
                    'new': new  
                }  
                setattr(self, field, new)  
        return changes 
class SystemContractInfo:
    def __init__(  
        self,   
        contract_address: str = '',
        contract_id: int = -1,
        chain_id: int = -1,
        level_id: int = -1,
        state: int = 0,
        manager_address: str = ''
    ):   
        self.contract_address=contract_address
        self.chain_id = chain_id
        self.contract_id = contract_id
        self.level_id = level_id
        self.state = state
        self.manager_address = manager_address
    def update(self, other: 'SystemContractInfo') -> Dict[str, Any]:  
        """  
        Compare and update system contract information  
        
        Args:  
            other (SystemContract): New system contract information  
        
        Returns:  
            Dict[str, Any]: Changed fields  
        """  
        changes = {}  
        
        if self.contract_address != other.contract_address:  
            changes['contract_address'] = {  
                'old': self.contract_address,  
                'new': other.contract_address  
            }  
            self.contract_address = other.contract_address    
        
        if self.chain_id != other.chain_id:  
            changes['chain_id'] = {  
                'old': self.chain_id,  
                'new': other.chain_id  
            }  
            self.chain_id = other.chain_id  
        
        if self.level_id != other.level_id:  
            changes['level_id'] = {  
                'old': self.level_id,  
                'new': other.level_id  
            }  
            self.level_id = other.level_id  
        
        if self.state != other.state:  
            changes['state'] = {  
                'old': self.state,  
                'new': other.state  
            }  
            self.state = other.state  
        
        if self.manager_address != other.manager_address:  
            changes['manager_address'] = {  
                'old': self.manager_address,  
                'new': other.manager_address  
            }  
            self.manager_address = other.manager_address  
        
        return changes
