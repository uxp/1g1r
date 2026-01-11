import click
import yaml
import os
import sys
import logging

logger = logging.getLogger(__name__)


def load_config(config_path, prefix="convert"):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get(prefix, {})


@click.command()
@click.argument('config', type=click.Path(exists=True), default='config.yaml')
@click.option('--dry-run', default=False, is_flag=True, help='Simulate actions without making changes')
@click.option('--force', default=False, is_flag=True, help='Force overwrite of existing files')
@click.option('-s', '--system', 'systems', multiple=True, help='Specific system(s) to process (repeatable)')
@click.pass_context
def cli(ctx, config, dry_run=False, force=False, systems=None):
    """Prepare ROMs and other game media files from archived formats into usable
    formats. For many classic systems, this is simply a copy-file operation from
    a 1G1R DAT collection to a different EmulationStation directory structure.
    For other systems, this may involve conversion from a BIN/CUE or ISO format
    to a CHD, or another usable format.
    """
    config = load_config(config)

    source_dir = config.get("source", "")
    dest_dir = config.get("dest", "")

    systems_config: dict[str, dict] = config.get('systems', {})

    # Filter systems if specific ones were requested via CLI
    if systems:
        systems_config = {k: v for k, v in systems_config.items() if k in systems}
        if not systems_config:
            logger.error(f"None of the specified systems {systems} were found in config.")
            return

    sorted_systems = {name: obj for name, obj in sorted(systems_config.items())}

    for system_slug, sys_conf in sorted_systems.items():
        system_name = sys_conf.get('name', None)
        if system_name is None:
            logger.error(f"No Processor name defined for slug '{system_slug}'. Aborting.")
            continue

        module_slug = system_slug.lower().replace('-', '_')

        try:
            module = __import__(f"onegame_onerom.systems.{module_slug}", fromlist=[f"{system_name}Processor"])
            processor_class = getattr(module, f'{system_name}Processor')
        except (ImportError, AttributeError) as e:
            logger.error(f"Error loading module for {system_name} ({system_slug}): {e}")
            continue

        # Join base source/dest with per-system config
        sys_source = os.path.join(source_dir, sys_conf.get('source'))
        sys_dest = os.path.join(dest_dir, system_slug)

        if not os.path.exists(sys_source):
            logger.warning(f"Source directory does not exist for {system_name}. Skipping.")
            continue
        if not os.path.exists(sys_dest):
            logger.info(f"Destination directory does not exist for {system_name}. Creating it.")
            if not dry_run:
                os.makedirs(sys_dest, exist_ok=True)

        processor_options = {'config': config, 'dry_run': dry_run, 'force': force, 'logger': logger}
        processor = processor_class(system_slug, sys_conf, sys_source, sys_dest, processor_options)
        logger.info(f"Running processing for {system_name}...")
        processor.process()


if __name__ == '__main__':
    cli()
