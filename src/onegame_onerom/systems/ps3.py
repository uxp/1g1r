import re
import glob
import os
import zipfile
import tempfile
import subprocess
import logging
from . import SystemProcessor


class Playstation3Processor(SystemProcessor):
    file_pattern = "*.zip"

    def __init__(self, config, source_dir, dest_dir, options):
        super().__init__(config, source_dir, dest_dir, options)
        self.logger = logging.getLogger(__name__)

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
            zip_ref.extractall(extract_to)

    def process(self):
        inputs = self.find_inputs()
        dry_run = self.options.get('dry_run', False)
        force = self.options.get('force', False)
        if len(inputs) == 0:
            self.logger.warning("No PS3 input files found, skipping processing.")
            return
        self.logger.info(f"Found PS3 games: {len(inputs)}")

        for game in inputs:
            game_name = game['name']
            discs = game['discs']
            output_file = os.path.join(self.dest_dir, f"{game_name}.iso")
            # Check if output exists and skip unless --force
            if os.path.exists(output_file) and not force and not dry_run:
                self.logger.warning(f"Output already exists for {output_file}, skipping. Use --force to overwrite.")
                continue
            self.logger.debug(f"Processing game: {game_name} with {len(discs)} disc(s)")
            with tempfile.TemporaryDirectory() as temp_dir:
                extracted_cues = []
                for disc in discs:
                    zip_file = disc['file']
                    self.logger.debug(f"Extracting {zip_file} to {temp_dir}")
                    if not dry_run:
                        self.extract_zip(zip_file, temp_dir)
                    else:
                        self.logger.info(f"[DRY-RUN] Would extract {zip_file} to {temp_dir}")

                # PS3 games should always be single ISOs. This m3u stuff is largely just copypaste
                # to deal with the copypasted find_inputs that groups by disk number.

                # Find all .ISO, .CUE files in temp_dir
                disc_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith('.cue') or f.lower().endswith('.iso')]
                disc_files.sort()  # Ensure order
                if len(disc_files) == 0 and not dry_run:
                    self.logger.warning(f"No Disc images found for {disc_files}")
                    continue

                # If multi-disc, create m3u manifest
                if len(disc_files) > 1 or (len(discs) > 1 and dry_run):
                    m3u_path = os.path.join(temp_dir, f"{game_name}.m3u")
                    m3u_contents = '\n'.join([os.path.basename(c) for c in disc_files])
                    if not dry_run:
                        with open(m3u_path, 'w') as m3u:
                            m3u.write(m3u_contents)
                    else:
                        self.logger.info(f"[DRY-RUN] Would create m3u file: {m3u_path}")
                    input_arg = m3u_path

                else:
                    if dry_run:
                        input_arg = f"{game_name}.iso"
                    else:
                        input_arg = disc_files[0]

                # Prepare command for ps3dec
                conversion = self.config.get('conversion', {})
                tool = conversion.get('tool', 'ps3dec')
                options = conversion.get('options', {})
                dkey_dir = conversion.get('dkeys', os.path.join(os.path.dirname(__file__), 'dkeys'))

                dkey_filepath = os.path.join(dkey_dir, f"{game_name}.dkey")
                if os.path.exists(dkey_filepath):
                    with open(dkey_filepath, 'r') as dkey_f:
                        dkey_contents = "".join(dkey_f.readline()).strip()
                else:
                    self.logger.warning(f"No DKEY file found for {game_name}, skipping.")
                    continue

                # Quote input and output args for shell
                cmd = [tool, 'd', 'key', dkey_contents, input_arg, output_file]

                for k, v in options.items():
                    raise "Options are not supported here"
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
                        self.logger.debug(f"Decoding output: {stdout}")
                        if stderr:
                            self.logger.warning(f"Decoding errors: {stderr}")
                    except Exception as e:
                        self.logger.error(f"Error running Decoding tool: {e}")
                else:
                    self.logger.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
            self.logger.debug(f"Processed \"{game_name}\" with #{len(discs)} discs successfully.")
