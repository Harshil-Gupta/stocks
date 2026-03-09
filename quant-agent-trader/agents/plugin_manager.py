"""
Agent Plugin System - Dynamic agent loading and discovery.

Usage:
    plugin_manager = AgentPluginManager()
    
    # Discover all agents
    agents = plugin_manager.discover_agents()
    
    # Load specific category
    technical = plugin_manager.load_category("technical")
    
    # Load from custom path
    plugin_manager.load_from_path("my_agents/")
"""

import os
import importlib
import inspect
import logging
from typing import Dict, List, Any, Optional, Type, Set
from pathlib import Path
from dataclasses import dataclass

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Information about a discovered agent."""
    name: str
    class_name: str
    module: str
    category: str
    description: str
    agent_class: Type[BaseAgent]


class AgentPluginManager:
    """
    Manages agent plugins with dynamic loading.
    
    Features:
    - Auto-discover agents in directories
    - Load by category
    - Plugin validation
    - Hot reload support
    """
    
    BASE_AGENT_PATHS = [
        "agents/technical",
        "agents/fundamental",
        "agents/sentiment",
        "agents/macro",
        "agents/market_structure",
        "agents/risk",
        "agents/quant",
        "agents/india"
    ]
    
    CATEGORY_MAP = {
        "technical": "agents/technical",
        "fundamental": "agents/fundamental",
        "sentiment": "agents/sentiment",
        "macro": "agents/macro",
        "market_structure": "agents/market_structure",
        "risk": "agents/risk",
        "quant": "agents/quant",
        "india": "agents/india"
    }
    
    def __init__(self):
        self.discovered_agents: Dict[str, AgentInfo] = {}
        self._scan_base_paths()
    
    def _scan_base_paths(self) -> None:
        """Scan all base agent paths."""
        for category, path in self.CATEGORY_MAP.items():
            self._scan_path(path, category)
    
    def _scan_path(self, path: str, category: str) -> None:
        """Scan a directory for agent classes."""
        if not os.path.exists(path):
            return
        
        for filename in os.listdir(path):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            
            if filename == "base_agent.py":
                continue
            
            module_name = filename[:-3]
            full_module = f"{path.replace('/', '.')}.{module_name}"
            
            try:
                self._import_agent_module(full_module, category)
            except Exception as e:
                logger.warning(f"Failed to import {full_module}: {e}")
    
    def _import_agent_module(self, module_path: str, category: str) -> None:
        """Import a module and find agent classes."""
        try:
            module = importlib.import_module(module_path)
        except Exception as e:
            logger.warning(f"Cannot import {module_path}: {e}")
            return
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseAgent) and obj != BaseAgent:
                if obj.__module__ == module_path:
                    agent_info = AgentInfo(
                        name=getattr(obj, "agent_name", name.replace("Agent", "").lower()),
                        class_name=name,
                        module=module_path,
                        category=category,
                        description=inspect.getdoc(obj) or "",
                        agent_class=obj
                    )
                    
                    self.discovered_agents[agent_info.name] = agent_info
                    logger.debug(f"Discovered agent: {agent_info.name} ({category})")
    
    def discover_agents(self) -> Dict[str, AgentInfo]:
        """Get all discovered agents."""
        return self.discovered_agents.copy()
    
    def get_agents_by_category(self, category: str) -> List[AgentInfo]:
        """Get agents by category."""
        return [
            info for info in self.discovered_agents.values()
            if info.category == category
        ]
    
    def load_agent(self, agent_name: str, **kwargs) -> Optional[BaseAgent]:
        """Load a specific agent by name."""
        if agent_name not in self.discovered_agents:
            logger.warning(f"Agent {agent_name} not found")
            return None
        
        info = self.discovered_agents[agent_name]
        
        try:
            return info.agent_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to instantiate {agent_name}: {e}")
            return None
    
    def load_category(
        self,
        category: str,
        **kwargs
    ) -> List[BaseAgent]:
        """Load all agents in a category."""
        agents = []
        
        for info in self.get_agents_by_category(category):
            try:
                agent = info.agent_class(**kwargs)
                agents.append(agent)
            except Exception as e:
                logger.warning(f"Failed to load {info.name}: {e}")
        
        return agents
    
    def load_all(self, **kwargs) -> List[BaseAgent]:
        """Load all discovered agents."""
        agents = []
        
        for info in self.discovered_agents.values():
            try:
                agent = info.agent_class(**kwargs)
                agents.append(agent)
            except Exception as e:
                logger.warning(f"Failed to load {info.name}: {e}")
        
        return agents
    
    def load_from_path(self, path: str, category: str = "custom") -> List[BaseAgent]:
        """Load agents from a custom path."""
        self._scan_path(path, category)
        
        return self.load_category(category)
    
    def reload(self) -> None:
        """Reload all agent modules."""
        self.discovered_agents.clear()
        
        for module_name in list(sys.modules.keys()):
            if module_name.startswith("agents."):
                del sys.modules[module_name]
        
        self._scan_base_paths()
    
    def validate_agent(self, agent_name: str) -> bool:
        """Validate an agent can be instantiated."""
        if agent_name not in self.discovered_agents:
            return False
        
        info = self.discovered_agents[agent_name]
        
        try:
            agent = info.agent_class()
            return hasattr(agent, "run") or hasattr(agent, "compute_signal")
        except Exception:
            return False
    
    def list_categories(self) -> List[str]:
        """List all available categories."""
        categories = set(info.category for info in self.discovered_agents.values())
        return sorted(list(categories))
    
    def get_agent_info(self, agent_name: str) -> Optional[AgentInfo]:
        """Get information about an agent."""
        return self.discovered_agents.get(agent_name)


class StrategyConfigLoader:
    """
    Load agent configurations from YAML/JSON files.
    
    Usage:
        loader = StrategyConfigLoader()
        config = loader.load("strategies/momentum.yaml")
        agents = loader.create_agents(config)
    """
    
    def __init__(self):
        self.plugin_manager = AgentPluginManager()
    
    def load(self, filepath: str) -> Dict[str, Any]:
        """Load strategy configuration from file."""
        import yaml
        
        with open(filepath, "r") as f:
            if filepath.endswith(".yaml") or filepath.endswith(".yml"):
                return yaml.safe_load(f)
            elif filepath.endswith(".json"):
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {filepath}")
    
    def create_agents(
        self,
        config: Dict[str, Any],
        **kwargs
    ) -> List[BaseAgent]:
        """Create agents from configuration."""
        agents = []
        
        agent_names = config.get("agents", [])
        
        for agent_name in agent_names:
            if isinstance(agent_name, str):
                agent = self.plugin_manager.load_agent(agent_name, **kwargs)
            elif isinstance(agent_name, dict):
                name = agent_name.get("name")
                params = agent_name.get("params", {})
                agent = self.plugin_manager.load_agent(name, **{**kwargs, **params})
            
            if agent:
                agents.append(agent)
        
        return agents
    
    def load_strategy(self, filepath: str, **kwargs) -> Dict[str, Any]:
        """Load a complete strategy."""
        config = self.load(filepath)
        
        agents = self.create_agents(config, **kwargs)
        
        return {
            "config": config,
            "agents": agents,
            "name": config.get("name", "Unnamed"),
            "description": config.get("description", "")
        }


import sys
import json
