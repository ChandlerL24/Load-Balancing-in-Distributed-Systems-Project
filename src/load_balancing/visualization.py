"""
Plotting functions for simulation results.
"""

import os
from typing import Dict, Optional
import numpy as np
import matplotlib.pyplot as plt

from load_balancing.metrics import SimulationMetrics


def plot_response_time_comparison(
    results: Dict[str, SimulationMetrics],
    output_path: Optional[str] = None,
    show: bool = True,
):
    """Bar chart of avg and p95 response times."""
    strategies = list(results.keys())
    avg_times = [results[s].avg_response_time for s in strategies]
    p95_times = [results[s].p95_response_time for s in strategies]
    
    x = np.arange(len(strategies))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width/2, avg_times, width, label='Average', color='steelblue')
    ax.bar(x + width/2, p95_times, width, label='P95', color='coral')
    
    ax.set_xlabel('Strategy')
    ax.set_ylabel('Response Time')
    ax.set_title('Response Time by Strategy')
    ax.set_xticks(x)
    ax.set_xticklabels(strategies)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close()


def plot_server_utilization(
    results: Dict[str, SimulationMetrics],
    output_path: Optional[str] = None,
    show: bool = True,
):
    """Grouped bar chart of server utilization."""
    strategies = list(results.keys())
    num_servers = len(results[strategies[0]].server_utilizations)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(num_servers)
    width = 0.25
    colors = ['steelblue', 'coral', 'seagreen', 'purple']
    
    for i, strat in enumerate(strategies):
        utils = results[strat].server_utilizations
        offset = (i - len(strategies)/2 + 0.5) * width
        ax.bar(x + offset, utils, width, label=strat, color=colors[i % len(colors)])
    
    ax.set_xlabel('Server')
    ax.set_ylabel('Utilization')
    ax.set_title('Server Utilization')
    ax.set_xticks(x)
    ax.set_xticklabels([f'S{i}' for i in range(num_servers)])
    ax.legend()
    ax.set_ylim(0, 1.1)
    ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close()


def plot_response_time_distribution(
    results: Dict[str, SimulationMetrics],
    output_path: Optional[str] = None,
    show: bool = True,
):
    """Histograms of response times."""
    strategies = list(results.keys())
    n = len(strategies)
    
    fig, axes = plt.subplots(1, n, figsize=(5*n, 5), sharey=True)
    if n == 1:
        axes = [axes]
    
    colors = ['steelblue', 'coral', 'seagreen', 'purple']
    
    for i, strat in enumerate(strategies):
        times = results[strat].response_times
        if times:
            axes[i].hist(times, bins=50, color=colors[i % len(colors)], 
                        alpha=0.7, edgecolor='black')
            axes[i].axvline(results[strat].avg_response_time, color='red', 
                           linestyle='--', label=f'Mean')
            axes[i].axvline(results[strat].p95_response_time, color='orange', 
                           linestyle='--', label=f'P95')
        
        axes[i].set_xlabel('Response Time')
        axes[i].set_title(strat)
        axes[i].legend(fontsize=8)
        axes[i].grid(alpha=0.3)
    
    axes[0].set_ylabel('Count')
    fig.suptitle('Response Time Distributions')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close()


def plot_throughput_comparison(
    results: Dict[str, SimulationMetrics],
    output_path: Optional[str] = None,
    show: bool = True,
):
    """Bar chart of throughput."""
    strategies = list(results.keys())
    throughputs = [results[s].throughput for s in strategies]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    colors = ['steelblue', 'coral', 'seagreen', 'purple']
    bars = ax.bar(strategies, throughputs, 
                  color=[colors[i % len(colors)] for i in range(len(strategies))])
    
    ax.set_xlabel('Strategy')
    ax.set_ylabel('Throughput (req/unit)')
    ax.set_title('Throughput Comparison')
    ax.grid(axis='y', alpha=0.3)
    
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f'{h:.2f}', xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close()


def plot_summary_dashboard(
    results: Dict[str, SimulationMetrics],
    output_path: Optional[str] = None,
    show: bool = True,
):
    """4-panel dashboard with key metrics."""
    strategies = list(results.keys())
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = ['steelblue', 'coral', 'seagreen', 'purple']
    
    # Response times
    ax = axes[0, 0]
    avg = [results[s].avg_response_time for s in strategies]
    p95 = [results[s].p95_response_time for s in strategies]
    x = np.arange(len(strategies))
    w = 0.35
    ax.bar(x - w/2, avg, w, label='Avg', color='steelblue')
    ax.bar(x + w/2, p95, w, label='P95', color='coral')
    ax.set_xticks(x)
    ax.set_xticklabels(strategies, rotation=15)
    ax.set_ylabel('Response Time')
    ax.set_title('Response Times')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Throughput
    ax = axes[0, 1]
    tput = [results[s].throughput for s in strategies]
    bars = ax.bar(strategies, tput, color=[colors[i % len(colors)] for i in range(len(strategies))])
    ax.set_ylabel('Throughput')
    ax.set_title('Throughput')
    ax.grid(axis='y', alpha=0.3)
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f'{h:.1f}', xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9)
    
    # Avg utilization
    ax = axes[1, 0]
    avg_util = [np.mean(results[s].server_utilizations) for s in strategies]
    bars = ax.bar(strategies, avg_util, color=[colors[i % len(colors)] for i in range(len(strategies))])
    ax.set_ylabel('Avg Utilization')
    ax.set_title('Average Utilization')
    ax.set_ylim(0, 1.1)
    ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5)
    ax.grid(axis='y', alpha=0.3)
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f'{h:.1%}', xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9)
    
    # Load balance (std dev of utilization)
    ax = axes[1, 1]
    stds = [np.std(results[s].server_utilizations) for s in strategies]
    bars = ax.bar(strategies, stds, color=[colors[i % len(colors)] for i in range(len(strategies))])
    ax.set_ylabel('Util Std Dev')
    ax.set_title('Load Balance (lower = better)')
    ax.grid(axis='y', alpha=0.3)
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f'{h:.4f}', xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9)
    
    plt.suptitle('Load Balancing Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close()


def generate_all_plots(
    results: Dict[str, SimulationMetrics],
    output_dir: str,
    show: bool = False,
):
    """Generate and save all plots."""
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nGenerating plots...")
    
    plot_response_time_comparison(
        results, os.path.join(output_dir, "response_times.png"), show)
    
    plot_server_utilization(
        results, os.path.join(output_dir, "utilization.png"), show)
    
    plot_response_time_distribution(
        results, os.path.join(output_dir, "response_dist.png"), show)
    
    plot_throughput_comparison(
        results, os.path.join(output_dir, "throughput.png"), show)
    
    plot_summary_dashboard(
        results, os.path.join(output_dir, "dashboard.png"), show)
    
    print(f"Plots saved to {output_dir}")
