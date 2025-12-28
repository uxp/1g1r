import click
import yaml
import os
import sys
import logging


def load_config(config_path, prefix="convert"):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get(prefix, {})


@click.command()
@click.argument('config', type=click.Path(exists=True), default='config.yml')
@click.option('--dry-run', default=False, is_flag=True, help='Simulate actions without making changes')
@click.option('--force', default=False, is_flag=True, help='Force overwrite of existing files')
@click.option('--log', type=str, help='Path to log file (in addition to console output)')
@click.pass_context
def cli(ctx, config, dry_run=False, force=False, log=None):
    """Prepare ROMs and other game media files from archived formats into usable
    formats. For many classic systems, this is simply a copy-file operation from
    a 1G1R DAT collection to a different EmulationStation directory structure.
    For other systems, this may involve conversion from a BIN/CUE or ISO format
    to a CHD, or another usable format.
    """
    logger = ctx.obj.get('logger', logging.getLogger(__name__))
    config = load_config(config)

    source_dir = config.get("source", "")
    dest_dir = config.get("dest", "")

    systems_config = config.get('systems', {})
    for system_name, sys_conf in systems_config.items():
        module_name = sys_conf.get('slug', None)
        if module_name is None:
            logger.error(f"No slug defined for {system_name}. Aborting.")
            continue
        module_name = module_name.lower().replace('-', '_')

        try:
            module = __import__(f'onegame_onerom.systems.{module_name}', fromlist=[f'{system_name}Processor'])
            processor_class = getattr(module, f'{system_name}Processor')
        except (ImportError, AttributeError) as e:
            logger.error(f"Error loading module for {system_name}: {e}")
            continue
        # Join base source/dest with per-system config
        sys_source = os.path.join(source_dir, sys_conf.get('source'))
        sys_dest = os.path.join(dest_dir, sys_conf.get('slug'))

        if not os.path.exists(sys_source):
            logger.warning(f"Source directory does not exist for {system_name}. Skipping.")
            continue
        if not os.path.exists(sys_dest):
            logger.info(f"Destination directory does not exist for {system_name}. Creating it.")
            if not dry_run:
                os.makedirs(sys_dest, exist_ok=True)

        processor_options = {'config': config, 'dry_run': dry_run, 'force': force, 'logger': logger}
        processor = processor_class(sys_conf, sys_source, sys_dest, processor_options)
        logger.info(f"Running processing for {system_name}...")
        processor.process()


if __name__ == '__main__':
    cli()
