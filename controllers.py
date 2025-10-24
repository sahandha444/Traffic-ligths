# controllers.py

# Note: These controllers need access to the Intersection and LaneQueue classes!
# from core_components import Intersection, LaneQueue 
# (You'd include this line in a real project)

class FixedTimeController:
    def __init__(self, schedule):
        self.schedule = schedule
        # The total time of one sequence
        self.cycle_length = sum(s['duration'] for s in schedule) 

    def get_current_phase(self, current_time):
        """Returns the current signal phase and the lanes that have green."""
        # Time within the current cycle
        time_in_cycle = current_time % self.cycle_length
        cumulative_time = 0
        
        for phase_info in self.schedule:
            start_time = cumulative_time
            end_time = cumulative_time + phase_info['duration']
            
            if start_time <= time_in_cycle < end_time:
                # Returns the full phase dict (e.g., {'phase': 'NS_GREEN', 'lanes': [...], 'duration': 40})
                return phase_info
                
            cumulative_time = end_time
        
        return None # Should not happen

class ActuatedController:
    # We need to access the Intersection lanes in this class, so it needs to be initialized with it.
    def __init__(self, schedule, intersection):
        self.schedule = schedule
        self.intersection = intersection
        self.cycle_length = sum(s['duration'] for s in schedule)
        
        # State tracking
        self.current_index = 0
        self.time_in_phase = 0
        self.current_phase = self.schedule[0]
        self.min_green = 20 # Minimum green time (seconds)
        self.extension_time = 3 # Time extension if a vehicle is detected
        self.max_green = 60 # Maximum green time (to prevent one side hogging green)

    def get_current_phase(self, current_time):
        
        current_info = self.current_phase
        self.time_in_phase += 1
        
        # 1. HANDLE YELLOW/ALL-RED (Safety Phase Logic)
        if 'YELLOW' in current_info['phase'] or 'ALLRED' in current_info['phase']:
            if self.time_in_phase >= current_info['duration']:
                # Move to the next phase immediately after safety time is met
                self._advance_phase()
            return self.current_phase
            
        # 2. HANDLE GREEN LOGIC (Actuation)
        elif 'GREEN' in current_info['phase']:
            green_lanes = current_info['lanes']
            
            # Check for vehicle presence (simple detection: queue is not empty)
            has_demand = any(self.intersection.lanes[lane_id].get_length() > 0 for lane_id in green_lanes)
            
            # Check if opposing lanes need service (simple check: queue > 5 veh)
            opposing_demand = self._check_opposing_demand(green_lanes)

            # Check if max green is reached
            max_reached = self.time_in_phase >= self.max_green

            # Check if minimum green time has passed
            min_passed = self.time_in_phase >= self.min_green

            # DECISION TIME!
            if min_passed and not has_demand:
                # End green if min time is met AND no vehicles left
                self._advance_phase()
            elif max_reached and opposing_demand:
                # End green if max time is met AND other lanes are waiting
                self._advance_phase()
            # Otherwise, the phase continues (either extending or running min time)
            
            return self.current_phase
            
    def _advance_phase(self):
        """Moves the controller state to the next phase in the schedule."""
        self.current_index = (self.current_index + 1) % len(self.schedule)
        self.current_phase = self.schedule[self.current_index]
        self.time_in_phase = 0 # Reset phase timer

    def _check_opposing_demand(self, current_green_lanes):
        """Simple check if any other lane group has vehicles waiting."""
        current_directions = {self.intersection.lanes[l_id].direction for l_id in current_green_lanes}
        
        for lane_id, lane in self.intersection.lanes.items():
            if lane.direction not in current_directions and lane.get_length() > 5:
                # Opposing lane has at least 5 vehicles waiting
                return True 
        return False

class AdaptiveController(FixedTimeController):
    """
    Allocates green to the approach with the highest queue or weighted waiting time 
    after the minimum time is met. It jumps directly to the highest demand phase 
    after clearance (Yellow/AllRed).
    """
    def __init__(self, schedule, intersection):
        # We inherit from FixedTimeController to use its schedule structure and cycle length
        super().__init__(schedule)
        self.intersection = intersection
        
        # State tracking 
        self.current_index = 0
        self.time_in_phase = 0
        self.current_phase_name = self.schedule[0]['phase']
        
        self.MIN_GREEN = 20  # Minimum time a phase must run (seconds)
        self.MAX_GREEN = 70  # Maximum time a phase can run (seconds)
        self.DEMAND_THRESHOLD = 5 # Vehicles needed in opposing lane to justify a switch

    def get_current_phase(self, current_time):
        
        current_info = self.schedule[self.current_index]
        self.time_in_phase += 1
        
        # 1. HANDLE YELLOW/ALL-RED (Safety Phase Logic)
        if 'YELLOW' in current_info['phase'] or 'ALLRED' in current_info['phase']:
            if self.time_in_phase >= current_info['duration']:
                # Safety period is over. Time to make the *ADAPTIVE* decision on the next GREEN phase.
                self._make_adaptive_decision() 
            return self.schedule[self.current_index]
        
        # 2. HANDLE GREEN LOGIC (Adaptive Timing)
        elif 'GREEN' in current_info['phase']:
            green_lanes = current_info['lanes']
            
            # 2a. Check for demand in OPPOSING lanes
            opposing_demand = self._calculate_opposing_demand(green_lanes)
            
            # 2b. Check for local demand (if current green lanes are cleared)
            current_demand = sum(self.intersection.lanes[lane_id].get_length() for lane_id in green_lanes)

            # --- DECISION LOGIC ---
            
            # A. Max Green Reached
            if self.time_in_phase >= self.MAX_GREEN:
                # Max time is met, must switch to next safety phase
                self._advance_to_next_safety()
            
            # B. Minimal Green Met AND Local demand is LOW AND Opposing demand is HIGH
            elif self.time_in_phase >= self.MIN_GREEN:
                
                if current_demand == 0 and opposing_demand > self.DEMAND_THRESHOLD:
                    # Current lanes are empty, and opposing lanes are waiting. SWITCH!
                    self._advance_to_next_safety()
                
            return self.schedule[self.current_index]

    def _calculate_opposing_demand(self, current_green_lanes):
        """Calculates the total vehicle queue length for all lanes NOT currently green."""
        opposing_demand = 0
        for lane_id, lane in self.intersection.lanes.items():
            if lane_id not in current_green_lanes:
                opposing_demand += lane.get_length()
        return opposing_demand

    def _advance_to_next_safety(self):
        """Moves the index to the next scheduled phase (Yellow or All-Red)."""
        self.current_index = (self.current_index + 1) % len(self.schedule)
        self.time_in_phase = 0
        
    def _make_adaptive_decision(self):
        """After a safety period, the controller skips forward to the highest demand GREEN phase."""
        
        # 1. Identify all GREEN phases in the schedule
        green_phases = [i for i, info in enumerate(self.schedule) if 'GREEN' in info['phase']]
        
        best_green_index = -1
        max_total_demand = -1
        
        # 2. Find the green phase that has the highest queue demand
        for index in green_phases:
            phase_lanes = self.schedule[index]['lanes']
            # Using PCU length is a better measure of demand severity than just vehicle count
            total_demand = sum(self.intersection.lanes[lane_id].get_pcu_length() for lane_id in phase_lanes)
            
            if total_demand > max_total_demand:
                max_total_demand = total_demand
                best_green_index = index
        
        # 3. Set the current index to the best green phase found
        if best_green_index != -1:
            self.current_index = best_green_index
        else:
            # Fallback: if all queues are empty, just move to the next phase in the cycle
            self.current_index = (self.current_index + 1) % len(self.schedule)

        self.time_in_phase = 0