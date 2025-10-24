# config.py

SIM_DURATION = 3600  # 1 hour simulation (seconds)
WARM_UP = 300        # Ignore first 5 mins

# Intersection Configuration
LANES_CONFIG = {
    'N_Through': {'direction': 'N', 'arrival_rate': 0.25, 'capacity_pcu': 150},
    'S_Through': {'direction': 'S', 'arrival_rate': 0.25, 'capacity_pcu': 150},
    'E_Through': {'direction': 'E', 'arrival_rate': 0.15, 'capacity_pcu': 100},
    'W_Through': {'direction': 'W', 'arrival_rate': 0.15, 'capacity_pcu': 100},
}

# Vehicle Distribution (must sum to 1.0)
VEHICLE_PROBS = {
    'Car': {'prob': 0.70}, # Class definition goes in models.py
    'Van': {'prob': 0.15},
    'Bus': {'prob': 0.10},
    'Truck': {'prob': 0.05}
}

# Fixed Time Schedule (Safety Phase structure for all controllers)
SIGNAL_SCHEDULE = [
    {'phase': 'NS_GREEN', 'lanes': ['N_Through', 'S_Through'], 'duration': 40},
    {'phase': 'NS_YELLOW', 'lanes': [], 'duration': 4},
    {'phase': 'NS_ALLRED', 'lanes': [], 'duration': 2},
    {'phase': 'EW_GREEN', 'lanes': ['E_Through', 'W_Through'], 'duration': 30},
    {'phase': 'EW_YELLOW', 'lanes': [], 'duration': 4},
    {'phase': 'EW_ALLRED', 'lanes': [], 'duration': 2},
]