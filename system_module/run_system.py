from system_module.core.system_simulator import SystemSimulator

def main():
    print("Starting SentinelOS Simulation...")
    simulator = SystemSimulator()
    simulator.initialize()
    simulator.run()
    print("Simulation finished.")

if __name__ == "__main__":
    main()
