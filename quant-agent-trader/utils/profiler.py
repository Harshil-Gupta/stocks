"""
Performance Profiler - Profile execution time of system components.

Usage:
    profiler = PerformanceProfiler()
    
    with profiler.profile("agent_execution"):
        run_agents()
        
    with profiler.profile("data_loading"):
        load_data()
        
    # Get report
    profiler.print_report()
    
    # Save to file
    profiler.save_report("profiling_results.json")
"""

import time
import functools
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProfileResult:
    """Result of a profiled operation."""
    name: str
    call_count: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    percentage: float


class PerformanceProfiler:
    """
    Performance profiler for tracking execution times.
    
    Usage:
        profiler = PerformanceProfiler()
        
        with profiler.profile("my_operation"):
            # do work
            pass
        
        profiler.print_report()
    """
    
    def __init__(self):
        self._profiles: Dict[str, List[float]] = {}
        self._start_times: Dict[str, float] = {}
        self._total_time = 0.0
    
    def profile(self, name: str) -> 'ProfileContext':
        """Create a profiling context."""
        return ProfileContext(self, name)
    
    def start(self, name: str) -> None:
        """Start timing an operation."""
        self._start_times[name] = time.time()
    
    def stop(self, name: str) -> float:
        """Stop timing and return elapsed time."""
        if name not in self._start_times:
            logger.warning(f"Started profiling for '{name}' but no start time found")
            return 0.0
        
        elapsed = time.time() - self._start_times[name]
        
        if name not in self._profiles:
            self._profiles[name] = []
        
        self._profiles[name].append(elapsed)
        self._total_time += elapsed
        
        del self._start_times[name]
        
        return elapsed
    
    def get_results(self) -> List[ProfileResult]:
        """Get profiling results."""
        results = []
        
        for name, times in self._profiles.items():
            if not times:
                continue
            
            avg_time = sum(times) / len(times)
            percentage = (sum(times) / self._total_time * 100) if self._total_time > 0 else 0
            
            results.append(ProfileResult(
                name=name,
                call_count=len(times),
                total_time=sum(times),
                avg_time=avg_time,
                min_time=min(times),
                max_time=max(times),
                percentage=percentage
            ))
        
        return sorted(results, key=lambda x: x.total_time, reverse=True)
    
    def print_report(self) -> None:
        """Print profiling report."""
        results = self.get_results()
        
        if not results:
            print("No profiling data")
            return
        
        print("\n" + "="*70)
        print("PERFORMANCE PROFILING REPORT")
        print("="*70)
        
        print(f"\n{'Operation':<30} {'Calls':<8} {'Total(s)':<10} {'Avg(ms)':<10} {'%':<8}")
        print("-"*70)
        
        for r in results:
            print(f"{r.name:<30} {r.call_count:<8} {r.total_time:<10.3f} {r.avg_time*1000:<10.2f} {r.percentage:<8.1f}")
        
        print("\n" + "="*70)
    
    def save_report(self, filepath: str) -> None:
        """Save profiling report to JSON."""
        results = self.get_results()
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_time": self._total_time,
            "profiles": [
                {
                    "name": r.name,
                    "call_count": r.call_count,
                    "total_time": r.total_time,
                    "avg_time": r.avg_time,
                    "min_time": r.min_time,
                    "max_time": r.max_time,
                    "percentage": r.percentage
                }
                for r in results
            ]
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Profiling report saved to {filepath}")
    
    def reset(self) -> None:
        """Reset profiling data."""
        self._profiles.clear()
        self._start_times.clear()
        self._total_time = 0.0


class ProfileContext:
    """Context manager for profiling."""
    
    def __init__(self, profiler: PerformanceProfiler, name: str):
        self.profiler = profiler
        self.name = name
    
    def __enter__(self):
        self.profiler.start(self.name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = self.profiler.stop(self.name)
        logger.debug(f"{self.name} took {elapsed:.3f}s")


def profile(profiler: Optional[PerformanceProfiler] = None):
    """
    Decorator for profiling functions.
    
    Usage:
        @profile()
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if profiler is None:
                p = PerformanceProfiler()
            else:
                p = profiler
            
            with p.profile(func.__name__):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


class AgentProfiler:
    """Profile individual agent execution times."""
    
    def __init__(self):
        self.profiler = PerformanceProfiler()
        self._agent_times: Dict[str, List[float]] = {}
    
    def profile_agent(self, agent_name: str, func: Callable, *args, **kwargs) -> Any:
        """Profile a single agent execution."""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        
        if agent_name not in self._agent_times:
            self._agent_times[agent_name] = []
        
        self._agent_times[agent_name].append(elapsed)
        
        return result
    
    def get_agent_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics per agent."""
        stats = {}
        
        for agent, times in self._agent_times.items():
            if not times:
                continue
            
            stats[agent] = {
                "call_count": len(times),
                "total_time": sum(times),
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times)
            }
        
        return stats
    
    def print_agent_report(self) -> None:
        """Print agent performance report."""
        stats = self.get_agent_stats()
        
        if not stats:
            print("No agent profiling data")
            return
        
        print("\n" + "="*70)
        print("AGENT PERFORMANCE REPORT")
        print("="*70)
        
        print(f"\n{'Agent':<30} {'Calls':<8} {'Avg(ms)':<12} {'Total(s)':<12}")
        print("-"*70)
        
        sorted_agents = sorted(
            stats.items(),
            key=lambda x: x[1]["total_time"],
            reverse=True
        )
        
        for agent, s in sorted_agents:
            print(f"{agent:<30} {s['call_count']:<8} {s['avg_time']*1000:<12.2f} {s['total_time']:<12.3f}")
        
        print("\n" + "="*70)


class DataLoaderProfiler:
    """Profile data loading performance."""
    
    def __init__(self):
        self.loads: List[Dict[str, Any]] = []
    
    def log_load(
        self,
        source: str,
        symbol: str,
        rows: int,
        time_taken: float
    ) -> None:
        """Log a data load operation."""
        self.loads.append({
            "source": source,
            "symbol": symbol,
            "rows": rows,
            "time": time_taken,
            "rows_per_sec": rows / time_taken if time_taken > 0 else 0,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get data loading statistics."""
        if not self.loads:
            return {}
        
        total_rows = sum(l["rows"] for l in self.loads)
        total_time = sum(l["time"] for l in self.loads)
        
        by_source = {}
        for load in self.loads:
            source = load["source"]
            if source not in by_source:
                by_source[source] = {"rows": 0, "time": 0, "loads": 0}
            by_source[source]["rows"] += load["rows"]
            by_source[source]["time"] += load["time"]
            by_source[source]["loads"] += 1
        
        return {
            "total_loads": len(self.loads),
            "total_rows": total_rows,
            "total_time": total_time,
            "avg_rows_per_sec": total_rows / total_time if total_time > 0 else 0,
            "by_source": by_source
        }
    
    def print_report(self) -> None:
        """Print data loading report."""
        stats = self.get_stats()
        
        if not stats:
            print("No data loading profiling data")
            return
        
        print("\n" + "="*70)
        print("DATA LOADING PERFORMANCE")
        print("="*70)
        
        print(f"\nTotal Loads: {stats['total_loads']}")
        print(f"Total Rows: {stats['total_rows']:,}")
        print(f"Total Time: {stats['total_time']:.2f}s")
        print(f"Avg Speed: {stats['avg_rows_per_sec']:,.0f} rows/sec")
        
        print("\nBy Source:")
        print(f"{'Source':<20} {'Loads':<8} {'Rows':<12} {'Time(s)':<10}")
        print("-"*60)
        
        for source, s in stats["by_source"].items():
            print(f"{source:<20} {s['loads']:<8} {s['rows']:<12,} {s['time']:<10.2f}")
        
        print("\n" + "="*70)


_global_profiler = None


def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance."""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler
