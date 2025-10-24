from config import SIM_DURATION, WARM_UP, LANES_CONFIG, SIGNAL_SCHEDULE, VEHICLE_PROBS

from core_components import (
    Intersection, 
    LaneQueue, 
    Vehicle, 
    Car, 
    Van, 
    Bus, 
    Truck
)

from controllers import (
    FixedTimeController, 
    ActuatedController, 
    AdaptiveController
)
import pandas as pd
import numpy as np
import random
from collections import deque # Already imported but good for clarity

VEHICLE_CLASS_MAP = {
    'Car': Car, 
    'Van': Van, 
    'Bus': Bus, 
    'Truck': Truck
}

class Simulator:
    def __init__(self, intersection, controller, duration, warmup_time):
        self.intersection = intersection
        self.controller = controller
        self.duration = duration
        self.warmup_time = warmup_time
        self.time_series_data = []
        self.served_vehicles = []
        self.vehicle_id_counter = 0

    def create_new_vehicle(self, arrival_time, lane_id):
        # 1. Randomly select the vehicle type name (e.g., 'Car') based on probability
        vehicle_type_name = random.choices(
            list(VEHICLE_PROBS.keys()), 
            weights=[v['prob'] for v in VEHICLE_PROBS.values()]
        )[0]
        
        # 2. Get the actual class object from the map you created
        VehicleClass = VEHICLE_CLASS_MAP[vehicle_type_name]  # <--- THIS IS THE NEW LOOK!
        
        # 3. Create the instance
        self.vehicle_id_counter += 1
        return VehicleClass(self.vehicle_id_counter, arrival_time, lane_id, route='through')


    def run(self):
        self.intersection.set_controller(self.controller)
        print(f"Starting simulation for {self.duration}s...")
        
        # Time step is 1 second (t)
        for t in range(self.duration):
            
            # 1. ARRIVALS (New vehicles enter queues)
            for lane_id, config in LANES_CONFIG.items():
                # Poisson random generation for new vehicles
                arrivals = np.random.poisson(config['arrival_rate'])
                for _ in range(arrivals):
                    new_veh = self.create_new_vehicle(t, lane_id)
                    # Attempt to add to the queue; if full, vehicle is rejected/spilled
                    self.intersection.lanes[lane_id].add_vehicle(new_veh) 

            # 2. CONTROLLER & MOVEMENT
            current_phase = self.controller.get_current_phase(t)
            green_lanes = current_phase['lanes']

            # Move one vehicle from each green lane
            for lane_id in green_lanes:
                lane = self.intersection.lanes[lane_id]
                vehicle = lane.remove_vehicle()
                
                if vehicle:
                    vehicle.departure_time = t
                    self.served_vehicles.append(vehicle)

            # 3. METRICS COLLECTION
            if t >= self.warmup_time:
                data_point = {'time': t, 'phase': current_phase['phase']}
                for lane_id, lane in self.intersection.lanes.items():
                    data_point[f'queue_veh_{lane_id}'] = lane.get_length()
                    data_point[f'queue_pcu_{lane_id}'] = lane.get_pcu_length()
                self.time_series_data.append(data_point)

    def generate_report(self):
        df_ts = pd.DataFrame(self.time_series_data)
        df_vehicles = pd.DataFrame([v.__dict__ for v in self.served_vehicles])
        
        # Filter vehicles by completion time and after warmup
        df_completed = df_vehicles[
            (df_vehicles['departure_time'].notna()) & 
            (df_vehicles['arrival_time'] >= self.warmup_time)
        ].copy()
        
        if df_completed.empty:
            return "No vehicles completed their journey after the warm-up period. 📉"

        # Calculate key metrics
        df_completed['delay'] = df_completed['departure_time'] - df_completed['arrival_time']
        
        metrics = {
            'Total Throughput (Vehicles)': len(df_completed),
            'Avg Delay (s)': df_completed['delay'].mean(),
            'Max Delay (s)': df_completed['delay'].max(),
            '95th Percentile Delay (s)': df_completed['delay'].quantile(0.95),
            'Avg Queue Length (Vehicles)': {
                lane: df_ts[f'queue_veh_{lane}'].mean() 
                for lane in LANES_CONFIG.keys()
            }
        }
        
        # Stratified delay (e.g., truck delay)
        vehicle_delays = df_completed.groupby('pcu')['delay'].mean().to_dict()
        metrics['Avg Delay by PCU Group (s)'] = {
            f'{pcu:.1f} PCU': delay for pcu, delay in vehicle_delays.items()
        }
        
        return metrics

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # 1. Setup
    intersection = Intersection(id='Central', lanes_config=LANES_CONFIG)
    controller = AdaptiveController(SIGNAL_SCHEDULE, intersection)

    output_filename = 'sim_timeseries_actuated.csv'
    sim = Simulator(intersection, controller, SIM_DURATION, WARM_UP)

    # 2. Run
    sim.run()
    report = sim.generate_report()

    # 3. Output
    print("\n" + "="*40)
    print("--- SIMULATION REPORT: FIXED-TIME CONTROL --- ⏱️")
    print(f"Total Served Vehicles (Post-Warmup): {report.get('Total Throughput (Vehicles)', 0)}")
    print("="*40)
    
    # Print Metrics
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"\n{key}:")
            for k, v in value.items():
                print(f"  - {k}: {v:.2f} s" if 'Delay' in key else f"  - {k}: {v:.2f} veh")
        elif 'Throughput' in key:
            print(f"- {key}: {value}")
        elif isinstance(value, float):
            print(f"- {key}: {value:.2f} s")
        else:
            print(f"- {key}: {value}")

    # Export Data
    pd.DataFrame(sim.time_series_data).to_csv('sim_timeseries_fixed.csv', index=False)
    print("\n✅ Time series data exported to 'sim_timeseries_fixed.csv' for analysis/plotting.")


import matplotlib.pyplot as plt
import pandas as pd

def visualize_queues(file_name, title):
    try:
        df = pd.read_csv(file_name)
    except FileNotFoundError:
        print(f"File {file_name} not found. Run the simulation first!")
        return
    
    queue_cols = [col for col in df.columns if col.startswith('queue_veh_')]
    
    plt.figure(figsize=(14, 6))
    for col in queue_cols:
        plt.plot(df['time'], df[col], label=col.replace('queue_veh_', ''))

    plt.title(f'{title} - Queue Lengths Over Time (Vehicles)')
    plt.xlabel('Time (Seconds)')
    plt.ylabel('Queue Length (Vehicles)')
    plt.legend(title='Lane')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.show()

# Run the plotting for both files:
visualize_queues('sim_timeseries_fixed.csv', 'Fixed-Time Control')
visualize_queues('sim_timeseries_actuated.csv', 'Actuated Control')