"""
Feature Registry - Pluggable feature discovery and management.

Provides:
- Registry for feature generators
- Lazy loading of features
- Feature dependency tracking
- Metadata storage
"""

from typing import Dict, List, Type, Optional, Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeatureMetadata:
    """Metadata for a registered feature."""

    name: str
    description: str
    category: str
    dependencies: List[str] = field(default_factory=list)
    lookback_required: int = 1
    provides: List[str] = field(default_factory=list)


class FeatureRegistry:
    """
    Registry for feature generators.

    Features are registered as classes that implement the FeatureGenerator interface.
    The registry handles:
    - Registration
    - Discovery
    - Dependency resolution
    - Lazy instantiation
    """

    _instance: Optional["FeatureRegistry"] = None
    _generators: Dict[str, Type["FeatureGenerator"]] = {}
    _metadata: Dict[str, FeatureMetadata] = {}
    _categories: Dict[str, List[str]] = {}

    def __new__(cls) -> "FeatureRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._generators = {}
            cls._instance._metadata = {}
            cls._instance._categories = {}
        return cls._instance

    @classmethod
    def register(
        cls,
        name: str,
        category: str = "general",
        description: str = "",
        dependencies: List[str] = None,
        lookback_required: int = 1,
        provides: List[str] = None,
    ) -> Callable:
        """
        Decorator to register a feature generator.

        Args:
            name: Feature name
            category: Feature category (e.g., 'trend', 'momentum', 'volatility')
            description: Human-readable description
            dependencies: List of required features
            lookback_required: Minimum lookback window needed
            provides: List of column names this feature provides

        Returns:
            Decorator function
        """

        def decorator(
            feature_class: Type["FeatureGenerator"],
        ) -> Type["FeatureGenerator"]:
            cls._generators[name] = feature_class

            metadata = FeatureMetadata(
                name=name,
                description=description,
                category=category,
                dependencies=dependencies or [],
                lookback_required=lookback_required,
                provides=provides or [name],
            )
            cls._metadata[name] = metadata

            if category not in cls._categories:
                cls._categories[category] = []
            cls._categories[category].append(name)

            logger.debug(f"Registered feature: {name} (category: {category})")
            return feature_class

        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[Type["FeatureGenerator"]]:
        """Get a feature generator class by name."""
        return cls._generators.get(name)

    @classmethod
    def get_metadata(cls, name: str) -> Optional[FeatureMetadata]:
        """Get metadata for a feature."""
        return cls._metadata.get(name)

    @classmethod
    def list_features(cls, category: Optional[str] = None) -> List[str]:
        """List all registered features, optionally filtered by category."""
        if category:
            return cls._categories.get(category, [])
        return list(cls._generators.keys())

    @classmethod
    def list_categories(cls) -> List[str]:
        """List all feature categories."""
        return list(cls._categories.keys())

    @classmethod
    def get_dependencies(cls, feature_names: List[str]) -> List[str]:
        """
        Get all dependencies for a list of features.

        Args:
            feature_names: List of feature names

        Returns:
            Sorted list of all dependencies (including transitive)
        """
        visited = set()
        to_visit = list(feature_names)

        while to_visit:
            name = to_visit.pop()
            if name in visited:
                continue
            visited.add(name)

            metadata = cls._metadata.get(name)
            if metadata:
                for dep in metadata.dependencies:
                    if dep not in visited:
                        to_visit.append(dep)

        return sorted(visited - set(feature_names))

    @classmethod
    def get_required_lookback(cls, feature_names: List[str]) -> int:
        """Get maximum lookback required among all features."""
        max_lookback = 1
        all_features = set(feature_names) | set(cls.get_dependencies(feature_names))

        for name in all_features:
            metadata = cls._metadata.get(name)
            if metadata:
                max_lookback = max(max_lookback, metadata.lookback_required)

        return max_lookback

    @classmethod
    def create_instance(cls, name: str, **kwargs) -> Optional["FeatureGenerator"]:
        """Create an instance of a feature generator."""
        feature_class = cls.get(name)
        if feature_class:
            return feature_class(**kwargs)
        return None

    @classmethod
    def create_instances(
        cls, feature_names: List[str], **common_kwargs
    ) -> Dict[str, "FeatureGenerator"]:
        """Create instances of multiple feature generators."""
        instances = {}
        all_features = set(feature_names) | set(cls.get_dependencies(feature_names))

        for name in all_features:
            instance = cls.create_instance(name, **common_kwargs)
            if instance:
                instances[name] = instance

        return instances

    @classmethod
    def clear(cls) -> None:
        """Clear all registered features (mainly for testing)."""
        cls._generators.clear()
        cls._metadata.clear()
        cls._categories.clear()


class FeatureGenerator(ABC):
    """
    Abstract base class for feature generators.

    All feature generators must implement this interface.
    """

    name: str = ""
    category: str = "general"

    @abstractmethod
    def compute(self, data: Any) -> Any:
        """
        Compute the feature(s).

        Args:
            data: Input data (typically pd.DataFrame with OHLCV)

        Returns:
            Feature(s) as pd.Series or pd.DataFrame
        """
        pass

    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Get list of required input columns/features."""
        pass

    @property
    @abstractmethod
    def lookback_required(self) -> int:
        """Minimum lookback window required."""
        pass

    def validate_input(self, data: Any) -> bool:
        """Validate input data before computation."""
        return data is not None and len(data) > 0


class CompositeFeatureGenerator(FeatureGenerator):
    """Feature generator that combines multiple generators."""

    def __init__(self, generators: List[FeatureGenerator]):
        self.generators = generators

    def compute(self, data: Any) -> Any:
        results = []
        for gen in self.generators:
            result = gen.compute(data)
            results.append(result)

        if all(isinstance(r, pd.Series) for r in results):
            import pandas as pd

            return pd.concat(results, axis=1)
        return results

    def get_dependencies(self) -> List[str]:
        deps = []
        for gen in self.generators:
            deps.extend(gen.get_dependencies())
        return list(set(deps))

    @property
    def lookback_required(self) -> int:
        return max(g.lookback_required for g in self.generators)


__all__ = [
    "FeatureRegistry",
    "FeatureMetadata",
    "FeatureGenerator",
    "CompositeFeatureGenerator",
]
