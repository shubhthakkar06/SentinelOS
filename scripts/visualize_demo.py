import pandas as pd
import matplotlib.pyplot as plt

def generate_dashboard():
    # Load the simulation data
    try:
        df = pd.read_csv('data/auv_task_data.csv')
    except FileNotFoundError:
        print("Please run the simulation first to generate data/auv_task_data.csv")
        return

    # Limit to the first 100 ticks for a readable chart
    df = df.head(100)

    plt.style.use('dark_background')
    fig = plt.figure(figsize=(12, 8))
    fig.canvas.manager.set_window_title('SentinelOS AUV Dashboard')

    # Subplot 1: System Memory over Time
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(df['system_time'], df['available_memory'], color='cyan', linewidth=2)
    ax1.set_title("System Available Memory (%)", fontsize=14, color='cyan')
    ax1.set_ylabel("Memory", fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.fill_between(df['system_time'], df['available_memory'], alpha=0.1, color='cyan')

    # Subplot 2: AI Advisor Fault Prevention Map
    ax2 = plt.subplot(2, 1, 2)
    
    # Plot normal tasks
    normal_tasks = df[df['fault_occurred'] == 0]
    ax2.scatter(normal_tasks['system_time'], normal_tasks['base_priority'], 
                color='forestgreen', label='Successful Task Execution', alpha=0.6, s=50)

    # Plot faults
    fault_tasks = df[df['fault_occurred'] == 1]
    ax2.scatter(fault_tasks['system_time'], fault_tasks['base_priority'], 
                color='crimson', label='System Fault (Resource/Deadline)', marker='x', s=100)

    ax2.set_title("Scheduler Task Priority & Fault Scatter", fontsize=14, color='white')
    ax2.set_xlabel("Simulation Time (Ticks)", fontsize=12)
    ax2.set_ylabel("Task Base Priority", fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('sentinel_dashboard.png', dpi=300)
    print("Dashboard saved as sentinel_dashboard.png - Opening now...")
    plt.show()

if __name__ == "__main__":
    generate_dashboard()
