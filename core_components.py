class Vehicle:
    def __init__(self, id, arrival_time, length, lane_id, route, pcu):
        self.id = id
        self.arrival_time = arrival_time
        self.lane_id = lane_id
        self.route = route
        self.length = length # meters
        self.pcu = pcu
        self.departure_time = None # Tracked later

class Car(Vehicle):
    # PCU: 1.0 (Baseline)
    def __init__(self, id, arrival_time, lane_id, route):
        # Order: id, arrival_time, length, lane_id, route, pcu
        super().__init__(id, arrival_time, 4.5, lane_id, route, pcu=1.0) 

class Van(Vehicle):
    # SUVs/Mini Trucks included. PCU: 1.5
    def __init__(self, id, arrival_time, lane_id, route):
        super().__init__(id, arrival_time, 6.0, lane_id, route, pcu=1.5)

class Bus(Vehicle):
    # Small Trucks/Tippers included. PCU: 2.0
    def __init__(self, id, arrival_time, lane_id, route):
        super().__init__(id, arrival_time, 12.0, lane_id, route, pcu=2.0)

class Truck(Vehicle):
    # Big trucks only. PCU: 3.0
    def __init__(self, id, arrival_time, lane_id, route):
        super().__init__(id, arrival_time, 18.0, lane_id, route, pcu=3.0)

from collections import deque

class LaneQueue:
    def __init__(self, id, max_capacity_pcu, direction):
        self.id = id
        self.max_capacity_pcu = max_capacity_pcu # Max capacity in PCU units
        self.direction = direction
        self.queue = deque()                    # Stores Vehicle objects (FIFO)
        self.current_pcu_length = 0             # Current occupied space
    
    def add_vehicle(self, vehicle):
        # Check if there is enough capacity for the new vehicle's PCU size
        if self.current_pcu_length + vehicle.pcu <= self.max_capacity_pcu:
            self.queue.append(vehicle)
            self.current_pcu_length += vehicle.pcu
            return True # Success
        return False # Queue is full
    
    def remove_vehicle(self):
        # Remove vehicle from the front (FIFO)
        if self.queue:
            vehicle = self.queue.popleft()
            self.current_pcu_length -= vehicle.pcu
            return vehicle
        return None # Queue is empty
    
    def get_length(self):
        # Returns the number of vehicles currently in the queue
        return len(self.queue)
    
    def get_pcu_length(self):
        # Returns the occupied capacity
        return self.current_pcu_length
 
class Intersection:
     """The central hub that holds all LaneQueues and the current Controller."""
     def __init__(self, id, lanes_config):
        self.id = id
        self.lanes = {}
        # Initialize LaneQueue objects using the LaneQueue class
        for lane_id, config in lanes_config.items():
             # Assumes LaneQueue is defined elsewhere in core_components.py
             self.lanes[lane_id] = LaneQueue(
                 lane_id, 
                 config['capacity_pcu'], 
                 config['direction']
             )
        self.controller = None # Placeholder for Fixed/Actuated/Adaptive controller
        
     def set_controller(self, controller):
        """Assigns a control strategy to this intersection."""
        self.controller = controller
        
     def __repr__(self):
        """Simple representation for quick status check."""
        status = f"Intersection {self.id} Status:\n"
        for lane_id, lane in self.lanes.items():
            status += f"  - Lane {lane_id}: {lane.get_length()} veh, {lane.get_pcu_length():.1f}/{lane.max_capacity_pcu} PCU\n"
        return status