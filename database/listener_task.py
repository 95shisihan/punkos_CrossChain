from typing import Dict, Any, Optional, TypedDict, Union, Literal  
from dataclasses import dataclass  
import queue  
import threading
from enum import Enum 
from queue import Queue, PriorityQueue
from crosschainzone_db import CrosschainZoneDatabaseManager as DatabaseManager
import time
class TaskType(Enum):  
    """  
    Enumeration of supported task types.  
    
    Attributes:  
        DB_WRITE: Database write operation task  
        INIT_RELAY: Relay initialization task  
    """  
    DB_WRITE = "db_write"  
    INIT_RELAY = "init_relay"  

class DBWriteData(TypedDict):  
    """  
    Type definition for DB_WRITE task data.  
    
    Attributes:  
        table_name: Target database table name  
        key_columns: Dictionary of key columns and their values  
        data: Dictionary of column names and values to upsert  
    """  
    table_name: str  
    key_columns: Dict[str, Any]  
    data: Dict[str, Any]

@dataclass  
class Task:  
    """  
    Represents a task with type, data and priority.  
    
    Attributes:  
        task_type (TaskType): Type of the task  
        data (Union[DBWriteData, Dict[str, Any]]): Task-specific data  
        priority (int): Task priority (higher number means higher priority)  
    """  
    task_type: TaskType  
    data: Union[DBWriteData, Dict[str, Any]]  
    priority: int = 1  

    def __post_init__(self) -> None:  
        """  
        Validate task data after initialization.  
        
        Raises:  
            ValueError: If priority is less than 1  
            TypeError: If task_type is not TaskType enum or data format is invalid  
        """  
        if not isinstance(self.task_type, TaskType):  
            raise TypeError("task_type must be a TaskType enum")  
        
        if not isinstance(self.priority, int) or self.priority < 1:  
            raise ValueError("priority must be a positive integer")  
            
        # Validate DB_WRITE task data  
        if self.task_type == TaskType.DB_WRITE:  
            self._validate_db_write_data()  

    def _validate_db_write_data(self) -> None:  
        """  
        Validate DB_WRITE task data format.  
        
        Raises:  
            TypeError: If data format is invalid  
            ValueError: If required fields are missing  
        """  
        required_fields = {'table_name', 'key_columns', 'data'}  
        
        if not isinstance(self.data, dict):  
            raise TypeError("DB_WRITE task data must be a dictionary")  
            
        if not all(field in self.data for field in required_fields):  
            raise ValueError(f"DB_WRITE task data must contain all required fields: {required_fields}")  
            
        if not isinstance(self.data['table_name'], str):  
            raise TypeError("table_name must be a string")  
            
        if not isinstance(self.data['key_columns'], dict):  
            raise TypeError("key_columns must be a dictionary")  
            
        if not isinstance(self.data['data'], dict):  
            raise TypeError("data must be a dictionary")  
            
        if not self.data['key_columns']:  
            raise ValueError("key_columns cannot be empty")  

    def __lt__(self, other: 'Task') -> bool:  
        """  
        Compare tasks based on priority for sorting.  
        Higher priority values have higher precedence.  
        
        Args:  
            other (Task): Another task to compare with  
            
        Returns:  
            bool: True if this task has higher priority than other  
        """  
        if not isinstance(other, Task):  
            return NotImplemented  
        return self.priority > other.priority  
    
    def __eq__(self, other: object) -> bool:  
        """  
        Check if two tasks are equal.  
        
        Args:  
            other (object): Another object to compare with  
            
        Returns:  
            bool: True if tasks are equal  
        """  
        if not isinstance(other, Task):  
            return NotImplemented  
        return (  
            self.task_type == other.task_type and  
            self.data == other.data and  
            self.priority == other.priority  
        )  
    
    def __repr__(self) -> str:  
        """  
        Get string representation of the task.  
        
        Returns:  
            str: Task representation  
        """  
        return f"Task(type={self.task_type.value}, priority={self.priority}, data={self.data})"

class TaskManager:
    def __init__(self, max_queue_size=100):  
        # Thread-safe queue for managing tasks  
        self.task_queue = PriorityQueue(maxsize=max_queue_size)  
        # Event to control thread stopping  
        self.stop_event = threading.Event()  
    def add_task(
        self, 
        task: Task
    ):  
        """  
        Add a task to the queue, blocking if the queue is full  
        """  
        self.task_queue.put(task)   
    def get_task(self) -> Optional[Task]:  
        """  
        Get a task from the queue, blocking if the queue is empty  
        """  
        try:
            self.task_queue.get(block=True)
        except Queue.Empty:  
            return None  
    def task_done(self):  
        """  
        Mark a task as completed  
        """  
        self.task_queue.task_done()  
    def stop(self):  
        """  
        Stop all threads  
        """  
        self.stop_event.set()
class TaskProcessor(threading.Thread):  
    def __init__(
        self,
        db_manager: DatabaseManager,
        task_manager: TaskManager
    ):  
        threading.Thread.__init__(self)
        self.db_manager = db_manager  
        self.task_manager = task_manager  
        self.daemon = True  

    def run(self):  
        while not self.task_manager.stop_event.is_set():  
            try:  
                # Get and process a task  
                task = self.task_manager.get_task()  
                self.process_task(task)  
                # Mark task as completed  
                self.task_manager.task_done()  
            except queue.Empty:  
                time.sleep(0.1)  

    def process_task(
        self,
        task: Task
    ):  
        print(f"Processing task: {task}")
        res = self.db_manager.upsert_generic(
            table_name=task.data.table_name,
            key_columns=task.data.key_columns,
            data=task.data
        )
        if res is None:
            self.db_manager.logger.error(  
                "Unexpected error during database update",  
                extra={    
                    'detail': task  
                },  
                exc_info=True  
            )    
