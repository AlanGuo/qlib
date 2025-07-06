# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Configuration template manager for cryptocurrency data collection.

This module provides utilities for managing and loading predefined
configuration templates for different use cases.
"""

import os
import sys
from pathlib import Path
_current_dir = Path(__file__).parent

from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from config.main_config import CryptoDataConfig


class ConfigTemplateManager:
    """
    Manager for configuration templates.
    
    This class provides utilities for discovering, loading, and managing
    predefined configuration templates.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize template manager.
        
        Parameters
        ----------
        template_dir : str, optional
            Directory containing template files
        """
        self.logger = logging.getLogger(__name__)
        
        if template_dir is None:
            # Default to templates directory relative to this file
            current_dir = Path(__file__).parent
            self.template_dir = current_dir / "templates"
        else:
            self.template_dir = Path(template_dir)
        
        self._templates_cache = {}
        self._discover_templates()
    
    def _discover_templates(self):
        """Discover available templates."""
        if not self.template_dir.exists():
            self.logger.warning(f"Template directory not found: {self.template_dir}")
            return
        
        self.available_templates = {}
        
        for template_file in self.template_dir.glob("*.yaml"):
            template_name = template_file.stem
            self.available_templates[template_name] = template_file
            self.logger.debug(f"Discovered template: {template_name}")
        
        for template_file in self.template_dir.glob("*.yml"):
            template_name = template_file.stem
            self.available_templates[template_name] = template_file
            self.logger.debug(f"Discovered template: {template_name}")
        
        self.logger.info(f"Discovered {len(self.available_templates)} templates")
    
    def list_templates(self) -> List[str]:
        """
        List available template names.
        
        Returns
        -------
        List[str]
            List of available template names
        """
        return list(self.available_templates.keys())
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        Get information about a template.
        
        Parameters
        ----------
        template_name : str
            Name of the template
        
        Returns
        -------
        Dict[str, Any]
            Template information
        """
        if template_name not in self.available_templates:
            raise ValueError(f"Template not found: {template_name}")
        
        template_path = self.available_templates[template_name]
        
        # Load template to extract metadata
        config = self.load_template(template_name)
        
        return {
            'name': template_name,
            'path': str(template_path),
            'size': template_path.stat().st_size,
            'exchanges': config.collection.exchanges,
            'timeframes': config.collection.timeframes,
            'universe_name': config.universe.name,
            'description': config.universe.description,
            'enable_extended_fields': config.collection.enable_extended_fields,
            'enable_risk_metrics': config.collection.enable_risk_metrics,
            'lookback_days': config.collection.lookback_days,
            'max_symbols': config.universe.max_symbols
        }
    
    def load_template(self, template_name: str) -> CryptoDataConfig:
        """
        Load a configuration template.
        
        Parameters
        ----------
        template_name : str
            Name of the template to load
        
        Returns
        -------
        CryptoDataConfig
            Loaded configuration
        """
        if template_name not in self.available_templates:
            raise ValueError(f"Template not found: {template_name}. Available: {self.list_templates()}")
        
        # Check cache first
        if template_name in self._templates_cache:
            self.logger.debug(f"Loading template from cache: {template_name}")
            return self._templates_cache[template_name]
        
        template_path = self.available_templates[template_name]
        
        try:
            config = CryptoDataConfig(str(template_path))
            self._templates_cache[template_name] = config
            self.logger.info(f"Loaded template: {template_name}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading template {template_name}: {str(e)}")
            raise
    
    def create_custom_template(
        self, 
        template_name: str, 
        base_template: str = "default",
        **overrides
    ) -> CryptoDataConfig:
        """
        Create a custom configuration based on a template.
        
        Parameters
        ----------
        template_name : str
            Name for the new template
        base_template : str, default "default"
            Base template to start from
        **overrides
            Configuration overrides
        
        Returns
        -------
        CryptoDataConfig
            Custom configuration
        """
        # Load base template
        base_config = self.load_template(base_template)
        
        # Apply overrides
        config_dict = base_config.to_dict()
        
        # Apply nested overrides
        for key, value in overrides.items():
            if '.' in key:
                # Handle nested keys like 'collection.exchanges'
                parts = key.split('.')
                current = config_dict
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                # Handle top-level keys
                if key in config_dict:
                    if isinstance(config_dict[key], dict) and isinstance(value, dict):
                        config_dict[key].update(value)
                    else:
                        config_dict[key] = value
        
        # Create new configuration
        custom_config = CryptoDataConfig()
        custom_config._update_from_dict(config_dict)
        
        self.logger.info(f"Created custom template: {template_name}")
        return custom_config
    
    def save_template(self, config: CryptoDataConfig, template_name: str):
        """
        Save a configuration as a template.
        
        Parameters
        ----------
        config : CryptoDataConfig
            Configuration to save
        template_name : str
            Name for the template
        """
        template_path = self.template_dir / f"{template_name}.yaml"
        
        # Ensure template directory exists
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        config.save_to_file(str(template_path), format="yaml")
        
        # Update available templates
        self.available_templates[template_name] = template_path
        self._templates_cache[template_name] = config
        
        self.logger.info(f"Saved template: {template_name}")
    
    def compare_templates(self, template1: str, template2: str) -> Dict[str, Any]:
        """
        Compare two templates.
        
        Parameters
        ----------
        template1 : str
            First template name
        template2 : str
            Second template name
        
        Returns
        -------
        Dict[str, Any]
            Comparison results
        """
        config1 = self.load_template(template1)
        config2 = self.load_template(template2)
        
        dict1 = config1.to_dict()
        dict2 = config2.to_dict()
        
        differences = {}
        
        def compare_dicts(d1, d2, path=""):
            for key in set(d1.keys()) | set(d2.keys()):
                current_path = f"{path}.{key}" if path else key
                
                if key not in d1:
                    differences[current_path] = {"in_template2_only": d2[key]}
                elif key not in d2:
                    differences[current_path] = {"in_template1_only": d1[key]}
                elif isinstance(d1[key], dict) and isinstance(d2[key], dict):
                    compare_dicts(d1[key], d2[key], current_path)
                elif d1[key] != d2[key]:
                    differences[current_path] = {
                        "template1": d1[key],
                        "template2": d2[key]
                    }
        
        compare_dicts(dict1, dict2)
        
        return {
            'template1': template1,
            'template2': template2,
            'differences': differences,
            'total_differences': len(differences)
        }
    
    def get_template_recommendations(self, requirements: Dict[str, Any]) -> List[str]:
        """
        Get template recommendations based on requirements.
        
        Parameters
        ----------
        requirements : Dict[str, Any]
            Requirements specification
        
        Returns
        -------
        List[str]
            Recommended template names
        """
        recommendations = []
        
        for template_name in self.available_templates:
            try:
                info = self.get_template_info(template_name)
                score = 0
                
                # Score based on requirements
                if 'exchanges' in requirements:
                    req_exchanges = set(requirements['exchanges'])
                    template_exchanges = set(info['exchanges'])
                    if req_exchanges.issubset(template_exchanges):
                        score += 10
                    elif req_exchanges & template_exchanges:
                        score += 5
                
                if 'timeframes' in requirements:
                    req_timeframes = set(requirements['timeframes'])
                    template_timeframes = set(info['timeframes'])
                    if req_timeframes.issubset(template_timeframes):
                        score += 10
                    elif req_timeframes & template_timeframes:
                        score += 5
                
                if 'extended_fields' in requirements:
                    if requirements['extended_fields'] == info['enable_extended_fields']:
                        score += 5
                
                if 'risk_metrics' in requirements:
                    if requirements['risk_metrics'] == info['enable_risk_metrics']:
                        score += 5
                
                if 'max_symbols' in requirements:
                    if info['max_symbols'] and info['max_symbols'] >= requirements['max_symbols']:
                        score += 5
                
                if score > 0:
                    recommendations.append((template_name, score))
                    
            except Exception as e:
                self.logger.warning(f"Error evaluating template {template_name}: {str(e)}")
        
        # Sort by score and return template names
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return [name for name, score in recommendations]
    
    def clear_cache(self):
        """Clear template cache."""
        self._templates_cache.clear()
        self.logger.info("Template cache cleared")


# Global template manager instance
_template_manager = None


def get_template_manager() -> ConfigTemplateManager:
    """Get global template manager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = ConfigTemplateManager()
    return _template_manager


def load_template(template_name: str) -> CryptoDataConfig:
    """
    Load a configuration template.
    
    Parameters
    ----------
    template_name : str
        Name of the template to load
    
    Returns
    -------
    CryptoDataConfig
        Loaded configuration
    """
    return get_template_manager().load_template(template_name)


def list_templates() -> List[str]:
    """
    List available template names.
    
    Returns
    -------
    List[str]
        List of available template names
    """
    return get_template_manager().list_templates()
