import os
import shutil
import yaml
import click
import glob
import logging
from concurrent.futures import ThreadPoolExecutor


def load_config(config_path, prefix="backup"):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get(prefix, {})


def copy_file(src_file, dest_file, label="Copied", logger=None):
    logger = logger or logging.getLogger(__name__)
    try:
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        shutil.copy2(src_file, dest_file)
        logger.info(f"{label} {src_file} -> {dest_file}")
    except Exception as e:
        logger.error(f"Error copying {src_file}", exc_info=e)


@click.command()
@click.pass_context
@click.argument('config', type=click.Path(exists=True), default='config.yaml')
@click.option('--threads', default=8, help='Number of concurrent threads.')
def cli(ctx, config, threads):
    """Restore files as per CONFIG (swap src/dest)."""
    cfg = load_config(config)
    logger = ctx.obj.get('logger', logging.getLogger(__name__))
    src = cfg['dest']
    dest = cfg['src']
    filetypes = cfg.get('filetypes', {})
    logger.info(f"Restoring from {src} to {dest} using {config} with {threads} threads")

    tasks = []
    for subdir, patterns in filetypes.items():
        src_subdir = os.path.join(src, subdir)
        for pattern in patterns:
            for file in glob.glob(os.path.join(src_subdir, pattern), recursive=True):
                if os.path.isfile(file):
                    rel_path = os.path.relpath(file, src)
                    target_path = os.path.join(dest, rel_path)
                    tasks.append((file, target_path))

    futures = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        try:
            for src_file, dest_file in tasks:
                futures.append(executor.submit(copy_file, src_file, dest_file, "Restoring", logger))

            for future in futures:
                future.result()
        except KeyboardInterrupt:
            logger.error("\nInterrupted by user. Cancelling pending tasks...", err=True)
            for future in futures:
                future.cancel()
            executor.shutdown(wait=False)
            logger.info("Stopped.", err=True)
            return
