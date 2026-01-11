# 1G1R Deployment Tool Systems package
# This provides a command-line interface for processing game files
# based on a YAML configuration file.
#
# Here's a list of compression formats that various systems support::
# https://forums.launchbox-app.com/topic/65171-guide-compression-to-use-for-most-popular-platform/
#
# - 3DO: chd (chdman)
# - 3DS: Mose emulator doesn't support compression for now. (Use NDSTokyoTrim for trimming rom) (Only Azahar emulator can compress and play .zcci files ".3ds to .zcci")
# - 32x: zip
# - Arcade (mame): zip + chd
# - Atomiswave: zip
# - CD-i Philips: chd (chdman + cdifile) (file from harryoke) (script doesn't support filename with apostrophe)
# - Dreamcast: chd (chdman) (you can't convert cdi format to chd)
# - GameBoy Advance (gba): zip
# - GameBoy Color (GBC): zip
# - GameCube: rvz (use dolphin emulator, import games, right click on games and convert file)
# - GameGear: zip
# - Genesis: zip
# - Nintendo (nes): zip
# - Nintendo 64: zip
# - Nintendo DS: zip
# - Nintendo Wii: rvz (use dolphin emulator from iso file, import games, right click on games and convert file) (if you have a wbfs, use wiibackupmanager to transfer them to iso)
# - Nintendo WiiU: wua (from Cemu 1.27 and later -> Tools -> Manage Titles -> right click on game)
# - Playstation: pbp (psx2psp, compress and combine multi-disc game) or chd (for better compression)
# - Playstation 2:  chd (chdman)
# - Playstation 3: emulator doesn't support compression for now
# - Playstation Portable (psp): cso (yacc or maxcso)
# - Playstation Vita: ???
# - Saturn: chd (chdman)
# - Sega CD: chd (chdman)
# - Super Nintendo: zip
# - TurboGrafx: zip
# - TurboGrafx-CD: chd (chdman)
# - Virtual Boy: zip
# - Xbox: emulator doesn't support compression for now (Use iso2god for trimming iso)
# - Xbox 360: emulator doesn't support compression for now (Use iso2god for trimming iso)
__template__ = """
from .base import CopyProcessor

class {{ SystemName }}Processor(CopyProcessor):
    pass

"""

import glob
import os
import shutil
import abc
import re
import subprocess
import tempfile
import logging
import zipfile
from concurrent.futures import ThreadPoolExecutor


def touch(fname, times=None):
    fhandle = open(fname, 'a')
    try:
        os.utime(fname, times)
    finally:
        fhandle.close()


class SystemProcessor(abc.ABC):
    name: str = None
    config: dict = None
    source_dir: str = None
    dest_dir: str = None
    options: dict = None
    file_pattern = "*"

    def __init__(self, name, config, source_dir, dest_dir, options):
        self.name = name
        self.config = config
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.options = options
        self.logger = logging.getLogger('.'.join([*__name__.split('.'), (name or 'unknown')]))

    @abc.abstractmethod
    def find_inputs(self):
        pass

    @abc.abstractmethod
    def process(self):
        pass


# For when we want to not do anything (yet?)
class NullProcessor(SystemProcessor):
    def __init__(self, name, config, source_dir, dest_dir, options):
        super().__init__(name, config, source_dir, dest_dir, options)
        self.name = name
        self.logger = logging.getLogger(__name__)

    def find_inputs(self):
        return []

    def process(self):
        self.logger.info(f"Skipped {self.name or 'Unknown'} System.")


# Generalized processor for copy-only systems
class CopyProcessor(SystemProcessor):
    def __init__(self, name, config, source_dir, dest_dir, options):
        super().__init__(name, config, source_dir, dest_dir, options)
        self.logger = logging.getLogger(__name__)

    def find_inputs(self):
        pattern = os.path.join(self.source_dir, self.file_pattern)
        return glob.glob(pattern)

    def process(self):
        inputs = self.find_inputs()
        dry_run = self.options.get('dry_run', False)
        threads = self.options.get('threads', 4)

        if len(inputs) == 0:
            self.logger.warning("No input files found, skipping processing.")
            return
        self.logger.info(f"Found files: {len(inputs)}")

        if dry_run:
            for src_file in inputs:
                dest_file = os.path.join(self.dest_dir, os.path.basename(src_file))
                self.logger.debug(f"[DRY-RUN] Would copy {src_file} to {dest_file}")
        else:
            with ThreadPoolExecutor(max_workers=threads) as executor:
                for src_file in inputs:
                    dest_file = os.path.join(self.dest_dir, os.path.basename(src_file))
                    executor.submit(self._copy_task, src_file, dest_file)

        self.logger.info("Copy-only processing complete.")

    def _copy_task(self, src_file, dest_file):
        self.logger.debug(f"Copying {src_file} to {dest_file}")
        if os.path.exists(dest_file) and not self.options.get('force', False):
            return
        os.makedirs(self.dest_dir, exist_ok=True)
        shutil.copy2(src_file, dest_file)


# Generalized processor for CHD systems
class CHDProcessor(SystemProcessor):
    file_pattern = "*.zip"

    def __init__(self, name, config, source_dir, dest_dir, options):
        super().__init__(name, config, source_dir, dest_dir, options)

    def find_inputs(self):
        pattern = os.path.join(self.source_dir, self.file_pattern)
        files = glob.glob(pattern)
        # Group files by game name, handling multi-disc
        game_map = {}
        disc_regex = re.compile(r'^(?P<name>.+?)\s*\(Disc\s*(?P<disc>\d+)\)(?:\s*\([^)]*\))*\.zip$', re.IGNORECASE)
        for f in files:
            base = os.path.basename(f)
            m = disc_regex.match(base)
            if m:
                name = m.group('name').strip()
                disc_num = int(m.group('disc'))
                if name not in game_map:
                    game_map[name] = {'name': name, 'discs': []}
                game_map[name]['discs'].append({'file': f, 'disc_num': disc_num})
            else:
                # Single disc game
                name = os.path.splitext(base)[0]
                game_map[name] = {'name': name, 'discs': [{'file': f, 'disc_num': 1}]}
        # Sort discs for each game
        for g in game_map.values():
            g['discs'].sort(key=lambda d: d['disc_num'])
        return list(game_map.values())

    def extract_zip(self, zip_path, extract_to):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            self.logger.debug(f"Extracting {zip_path} to {extract_to}")
            zip_ref.extractall(extract_to)

    def process(self):
        inputs = self.find_inputs()
        dry_run = self.options.get('dry_run', False)
        force = self.options.get('force', False)
        conversion = self.config.get('conversion', {})
        chdman_path = conversion.get('tool', 'chdman')
        options = conversion.get('options', {})

        if len(inputs) == 0:
            self.logger.warning("No input files found, skipping processing.")
            return
        self.logger.info(f"Found games: {len(inputs)}")

        for game in inputs:
            game_name = game['name']
            discs = game['discs']

            # Check if output exists and skip unless --force
            if not force and not dry_run:
                if any([os.path.exists(f) for f in [os.path.join(self.dest_dir, f"{game_name}.chd"), os.path.join(self.dest_dir, f"{game_name}.m3u")]]):
                    self.logger.warning(f"Output already exists for {game_name}, skipping. Use --force to overwrite.")
                    continue
            self.logger.info(f"Processing game: {game_name} with {len(discs)} disc(s)")
            converted_discs = []
            for disc in discs:
                zip_file = disc['file']
                disc_name = os.path.basename(zip_file)
                with tempfile.TemporaryDirectory() as temp_dir:
                    if not dry_run:
                        self.extract_zip(zip_file, temp_dir)
                    else:
                        self.logger.info(f"[DRY-RUN] Would extract {zip_file} to {temp_dir}")

                    cue_files = glob.glob(os.path.join(temp_dir, '*.cue'))
                    iso_files = glob.glob(os.path.join(temp_dir, '*.iso'))

                    if dry_run:
                        input_arg = f"{disc_name}.cue"
                        output_arg = os.path.join(self.dest_dir, f"{disc_name}.chd")
                    else:
                        if iso_files:
                            input_arg = iso_files[0]
                            output_arg = os.path.join(self.dest_dir, os.path.splitext(os.path.basename(iso_files[0]))[0] + ".chd")
                        elif cue_files:
                            input_arg = cue_files[0]
                            output_arg = os.path.join(self.dest_dir, os.path.splitext(os.path.basename(cue_files[0]))[0] + ".chd")
                        else:
                            self.logger.error(f"No CUE/ISO files found in {zip_file}, skipping.")
                            continue

                    # Quote input and output args for shell
                    cmd = [chdman_path, 'createcd', '--input', input_arg, '--output', output_arg]
                    if force:
                        cmd.append('--force')
                    for k, v in options.items():
                        if isinstance(v, bool):
                            if v:
                                cmd.append(f'--{k}')
                        else:
                            cmd.append(f'--{k}')
                            cmd.append(str(v))

                    self.logger.debug(f"Running conversion command: {' '.join(cmd)}")

                    if not dry_run:
                        try:
                            process = subprocess.Popen(
                                cmd,
                                cwd=temp_dir,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                            stdout, stderr = process.communicate()
                            self.logger.debug(f"Conversion output: {stdout}")
                            if stderr:
                                self.logger.warning(f"Conversion errors: {stderr}")
                            converted_discs.append(output_arg)
                        except Exception as e:
                            self.logger.error(f"Error running conversion tool: {e}")
                    else:
                        self.logger.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
            
            if len(converted_discs) > 1:
                m3u_path = os.path.join(self.dest_dir, f"{game_name}.m3u")
                m3u_contents = []
                disc_path = os.path.join(self.dest_dir, 'discs')
                if not os.path.exists(disc_path) and not dry_run:
                    os.makedirs(disc_path, exist_ok=True)
                touch(os.path.join(disc_path, "noload.txt"))
                for src_file in converted_discs:
                    dest_filepath = os.path.join(disc_path, os.path.basename(src_file))
                    dest_filename = "/".join(['discs', os.path.basename(src_file)])
                    self.logger.debug(f"Moving {src_file} to {dest_filepath}")
                    if not dry_run:
                        shutil.move(src_file, dest_filepath)
                    m3u_contents.append(dest_filename)

                m3u_contents = '\n'.join(m3u_contents)
                if not dry_run:
                    with open(m3u_path, 'w') as m3u:
                        m3u.write(m3u_contents)
                    self.logger.info(f"Created M3U manifest at {m3u_path}")
                else:
                    self.logger.info(f"[DRY-RUN] Would create m3u file: {m3u_path}")

            self.logger.info(f"Processed \"{game_name}\" with #{len(discs)} discs successfully.")

