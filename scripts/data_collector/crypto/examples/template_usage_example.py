# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Example usage of configuration templates.

This example demonstrates how to use predefined configuration templates
and the template manager for cryptocurrency data collection.
"""

import logging
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from pathlib import Path

from config import (
    ConfigTemplateManager,
    load_template,
    list_templates,
    CryptoDataConfig
)


def setup_logging():
    """Setup logging for examples."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def example_list_templates():
    """Example of listing available templates."""
    print("=== Available Templates ===")
    
    templates = list_templates()
    print(f"Found {len(templates)} templates:")
    
    for template in templates:
        print(f"  - {template}")
    
    return templates


def example_load_templates():
    """Example of loading different templates."""
    print("\n=== Loading Templates ===")
    
    templates_to_try = ["default", "simple", "high_frequency", "production", "research"]
    
    for template_name in templates_to_try:
        try:
            config = load_template(template_name)
            print(f"\n{template_name.upper()} Template:")
            print(f"  Exchanges: {config.collection.exchanges}")
            print(f"  Timeframes: {config.collection.timeframes}")
            print(f"  Output dir: {config.collection.output_dir}")
            print(f"  Max workers: {config.collection.max_workers}")
            print(f"  Extended fields: {config.collection.enable_extended_fields}")
            print(f"  Risk metrics: {config.collection.enable_risk_metrics}")
            print(f"  Universe max symbols: {config.universe.max_symbols}")
            
        except Exception as e:
            print(f"  Error loading {template_name}: {str(e)}")


def example_template_manager():
    """Example of using the template manager."""
    print("\n=== Template Manager Usage ===")
    
    # Create template manager
    manager = ConfigTemplateManager()
    
    # List templates
    templates = manager.list_templates()
    print(f"Available templates: {templates}")
    
    # Get template information
    for template_name in templates[:3]:  # Show first 3 templates
        try:
            info = manager.get_template_info(template_name)
            print(f"\n{template_name.upper()} Template Info:")
            print(f"  Description: {info['description']}")
            print(f"  Exchanges: {info['exchanges']}")
            print(f"  Timeframes: {info['timeframes']}")
            print(f"  Max symbols: {info['max_symbols']}")
            print(f"  Extended fields: {info['enable_extended_fields']}")
            print(f"  File size: {info['size']} bytes")
            
        except Exception as e:
            print(f"  Error getting info for {template_name}: {str(e)}")


def example_template_comparison():
    """Example of comparing templates."""
    print("\n=== Template Comparison ===")
    
    manager = ConfigTemplateManager()
    
    try:
        # Compare simple vs production templates
        comparison = manager.compare_templates("simple", "production")
        
        print(f"Comparing {comparison['template1']} vs {comparison['template2']}:")
        print(f"Total differences: {comparison['total_differences']}")
        
        # Show first few differences
        differences = comparison['differences']
        for i, (path, diff) in enumerate(differences.items()):
            if i >= 5:  # Show only first 5 differences
                print(f"  ... and {len(differences) - 5} more differences")
                break
            
            print(f"  {path}:")
            if 'template1' in diff and 'template2' in diff:
                print(f"    {comparison['template1']}: {diff['template1']}")
                print(f"    {comparison['template2']}: {diff['template2']}")
            elif 'in_template1_only' in diff:
                print(f"    Only in {comparison['template1']}: {diff['in_template1_only']}")
            elif 'in_template2_only' in diff:
                print(f"    Only in {comparison['template2']}: {diff['in_template2_only']}")
        
    except Exception as e:
        print(f"Error comparing templates: {str(e)}")


def example_custom_template():
    """Example of creating custom templates."""
    print("\n=== Custom Template Creation ===")
    
    manager = ConfigTemplateManager()
    
    try:
        # Create custom template based on default
        custom_config = manager.create_custom_template(
            template_name="my_custom",
            base_template="default",
            **{
                'collection.exchanges': ['binance', 'okx'],
                'collection.timeframes': ['1h', '4h', '1d'],
                'collection.max_workers': 6,
                'collection.enable_extended_fields': True,
                'universe.max_symbols': 75,
                'logging.level': 'DEBUG'
            }
        )
        
        print("Custom Template Created:")
        print(f"  Exchanges: {custom_config.collection.exchanges}")
        print(f"  Timeframes: {custom_config.collection.timeframes}")
        print(f"  Max workers: {custom_config.collection.max_workers}")
        print(f"  Extended fields: {custom_config.collection.enable_extended_fields}")
        print(f"  Max symbols: {custom_config.universe.max_symbols}")
        print(f"  Log level: {custom_config.logging.level}")
        
        # Save custom template (commented out to avoid file creation)
        # manager.save_template(custom_config, "my_custom")
        # print("Custom template saved!")
        
    except Exception as e:
        print(f"Error creating custom template: {str(e)}")


def example_template_recommendations():
    """Example of getting template recommendations."""
    print("\n=== Template Recommendations ===")
    
    manager = ConfigTemplateManager()
    
    # Example requirements
    requirements_examples = [
        {
            'name': 'High-frequency trading',
            'requirements': {
                'exchanges': ['binance'],
                'timeframes': ['1m', '5m'],
                'extended_fields': True,
                'risk_metrics': True
            }
        },
        {
            'name': 'Simple daily collection',
            'requirements': {
                'exchanges': ['binance'],
                'timeframes': ['1d'],
                'extended_fields': False,
                'max_symbols': 20
            }
        },
        {
            'name': 'Multi-exchange research',
            'requirements': {
                'exchanges': ['binance', 'okx'],
                'timeframes': ['1h', '1d'],
                'extended_fields': True,
                'risk_metrics': True,
                'max_symbols': 100
            }
        }
    ]
    
    for example in requirements_examples:
        try:
            recommendations = manager.get_template_recommendations(example['requirements'])
            print(f"\n{example['name']}:")
            print(f"  Requirements: {example['requirements']}")
            print(f"  Recommended templates: {recommendations[:3]}")  # Top 3 recommendations
            
        except Exception as e:
            print(f"Error getting recommendations for {example['name']}: {str(e)}")


def example_template_modification():
    """Example of modifying loaded templates."""
    print("\n=== Template Modification ===")
    
    try:
        # Load a template
        config = load_template("default")
        print("Original configuration:")
        print(f"  Exchanges: {config.collection.exchanges}")
        print(f"  Timeframes: {config.collection.timeframes}")
        print(f"  Output dir: {config.collection.output_dir}")
        
        # Modify the configuration
        config.collection.exchanges = ["binance", "okx"]
        config.collection.timeframes = ["1h", "4h", "1d"]
        config.collection.output_dir = "./my_modified_data"
        config.collection.enable_extended_fields = True
        config.universe.max_symbols = 50
        
        print("\nModified configuration:")
        print(f"  Exchanges: {config.collection.exchanges}")
        print(f"  Timeframes: {config.collection.timeframes}")
        print(f"  Output dir: {config.collection.output_dir}")
        print(f"  Extended fields: {config.collection.enable_extended_fields}")
        print(f"  Max symbols: {config.universe.max_symbols}")
        
        # Save modified configuration (commented out)
        # config.save_to_file("./my_modified_config.yaml", format="yaml")
        # print("Modified configuration saved!")
        
    except Exception as e:
        print(f"Error modifying template: {str(e)}")


def example_environment_override_with_template():
    """Example of using environment variables with templates."""
    print("\n=== Environment Override with Templates ===")
    
    import os
    
    try:
        # Set some environment variables
        os.environ['CRYPTO_EXCHANGES'] = 'binance,okx'
        os.environ['CRYPTO_TIMEFRAMES'] = '1h,1d'
        os.environ['CRYPTO_MAX_WORKERS'] = '8'
        
        # Load template (environment variables will be applied)
        config = load_template("default")
        
        print("Template with environment overrides:")
        print(f"  Exchanges: {config.collection.exchanges}")
        print(f"  Timeframes: {config.collection.timeframes}")
        print(f"  Max workers: {config.collection.max_workers}")
        
        # Clean up environment variables
        for var in ['CRYPTO_EXCHANGES', 'CRYPTO_TIMEFRAMES', 'CRYPTO_MAX_WORKERS']:
            if var in os.environ:
                del os.environ[var]
        
    except Exception as e:
        print(f"Error with environment override: {str(e)}")


def main():
    """Run all template usage examples."""
    setup_logging()
    
    print("Cryptocurrency Configuration Template Usage Examples")
    print("=" * 60)
    
    try:
        example_list_templates()
        example_load_templates()
        example_template_manager()
        example_template_comparison()
        example_custom_template()
        example_template_recommendations()
        example_template_modification()
        example_environment_override_with_template()
        
        print("\n" + "=" * 60)
        print("All template usage examples completed successfully!")
        
    except Exception as e:
        print(f"Error running template examples: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
