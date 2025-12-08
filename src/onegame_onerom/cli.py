import argparse
import yaml
import os
import sys

SYSTEMS_PATH = os.path.join(os.path.dirname(__file__), 'systems')

def parse_args():
    parser = argparse.ArgumentParser(description='1G1R Deployment Tool')
    parser.add_argument('-s', '--source', required=True, help='Source directory containing input files')
    parser.add_argument('-d', '--dest', required=True, help='Target directory to output files')
    parser.add_argument('--config', required=True, help='Path to YAML configuration file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--dry-run', action='store_true', help='Simulate actions without making changes')
    return parser.parse_args()

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    args = parse_args()
    config = load_config(args.config)

    systems_config = config.get('systems', {})
    for system_name, sys_conf in systems_config.items():
        module_name = system_name.lower()
        try:
            module = __import__(f'onegame_onerom.systems.{module_name}', fromlist=[f'{system_name}Processor'])
            processor_class = getattr(module, f'{system_name}Processor')
        except (ImportError, AttributeError) as e:
            print(f"Error loading module for {system_name}: {e}")
            continue
        # Join base source/dest with per-system config
        sys_source = os.path.join(args.source, sys_conf.get('source'))
        sys_dest = os.path.join(args.dest, sys_conf.get('dest'))

        processor = processor_class(sys_conf, sys_source, sys_dest, vars(args))
        print(f"Running processing for {system_name}...")
        processor.process()

if __name__ == '__main__':
    main()
