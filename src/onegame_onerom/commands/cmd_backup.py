import os
import shutil
import yaml
import click
import glob
from concurrent.futures import ThreadPoolExecutor
import logging

def config_logging(verbose, log_path=None):
    log_handlers = []
    log_level = logging.DEBUG

    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
        log_handlers.append(console_handler)

    if log_path:
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
        log_handlers.append(file_handler)

    logging.basicConfig(level=log_level, handlers=log_handlers)
    logger = logging.getLogger(__name__)
    return logger


def load_config(config_path, prefix="backup"):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get(prefix, {})


def copy_file(src_file, dest_file, label="Copied"):
    try:
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        shutil.copy2(src_file, dest_file)
        click.echo(f"{label} {src_file} -> {dest_file}")
    except Exception as e:
        click.echo(f"Error copying {src_file}: {e}", err=True)


@click.command()
@click.pass_context
@click.argument('config', type=click.Path(exists=True), default='backup.yml')
@click.option('-t', '--threads', default=8, help='Number of concurrent threads.', type=click.IntRange(min=1, max=None))
def cli(ctx, config, threads):
    """Backup files as per CONFIG."""
    cfg = load_config(config)
    src = cfg['src']
    dest = cfg['dest']
    filetypes = cfg.get('filetypes', {})
    click.echo(f"Backing up from {src} to {dest} using {config} with {threads} threads")

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
                futures.append(executor.submit(copy_file, src_file, dest_file, "Backing up"))

            for future in futures:
                future.result()
        except KeyboardInterrupt:
            click.echo("\nInterrupted by user. Cancelling pending tasks...", err=True)
            for future in futures:
                future.cancel()
            executor.shutdown(wait=False)
            click.echo("Stopped.", err=True)
            return
