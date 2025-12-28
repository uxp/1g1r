import os
import re
import glob
import shutil
import tempfile
import subprocess
from .base import SystemProcessor


import logging

class WiiProcessor(SystemProcessor):
    def __init__(self, config, source_dir, dest_dir, options):
        super().__init__(config, source_dir, dest_dir, options)
        self.logger = logging.getLogger(__name__)

    def find_inputs(self):
        import re
        pattern = os.path.join(self.source_dir, self.config.get('file_pattern', '*.zip'))
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
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

    def process(self):
        inputs = self.find_inputs()
        verbose = self.options.get('verbose', False)
        dry_run = self.options.get('dry_run', False)
        force = self.options.get('force', False)
        conversion = self.config.get('conversion', {})
        tool_path = conversion.get('tool', 'dolphintool')
        options = conversion.get('options', {})

        if len(inputs) == 0:
            self.logger.warning("No Wii input files found, skipping processing.")
            return
        self.logger.info(f"Found Wii games: {len(inputs)}")

        for game in inputs:
            game_name = game['name']
            discs = game['discs']

            # Check if output exists and skip unless --force
            if not force and not dry_run:
                if any([os.path.exists(f) for f in [os.path.join(self.dest_dir, f"{game_name}.rvz"), os.path.join(self.dest_dir, f"{game_name}.m3u")]]):
                    self.logger.warning(f"Output already exists for {game_name}, skipping. Use --force to overwrite.")
                    continue
            self.logger.info(f"Processing game: {game_name} with {len(discs)} disc(s)")
            converted_discs = []
            for disc in discs:
                zip_file = disc['file']
                disc_name = os.path.basename(zip_file)
                with tempfile.TemporaryDirectory() as temp_dir:
                    if verbose:
                        self.logger.debug(f"Extracting {zip_file} to {temp_dir}")
                    if not dry_run:
                        self.extract_zip(zip_file, temp_dir)
                    else:
                        self.logger.info(f"[DRY-RUN] Would extract {zip_file} to {temp_dir}")

                    iso_files = glob.glob(os.path.join(temp_dir, '*.iso'))
                    if not iso_files and not dry_run:
                        self.logger.warning(f"No CUE file found in {zip_file}, skipping.")
                        continue

                    if dry_run:
                        input_arg = f"{disc_name}.iso"
                    else:
                        input_arg = iso_files[0]

                    if dry_run:
                        output_arg = os.path.join(self.dest_dir, f"{disc_name}.iso")
                    else:
                        output_arg = os.path.join(self.dest_dir, os.path.splitext(os.path.basename(iso_files[0]))[0] + ".rvz")
                
                    # Quote input and output args for shell
                    cmd = [tool_path, 'convert', f'--input={input_arg}', f'--output={output_arg}', '--format=rvz']
                    if force:
                        # force not supported in DolphinTool, so we skip this
                        pass
                    for k, v in options.items():
                        if isinstance(v, bool):
                            if v:
                                cmd.append(f'--{k}')
                        else:
                            cmd.append(f'--{k}={v}')

                    if verbose:
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
                            if verbose:
                                self.logger.debug(f"Conversion output: {stdout}")
                                if stderr:
                                    self.logger.warning(f"Conversion errors: {stderr}")
                            converted_discs.append(output_arg)
                        except Exception as e:
                            self.logger.error(f"Error running conversion tool: {e}")
                    else:
                        self.logger.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
            
            # TODO: Handle multi-disc manifest (M3U) creation if needed
            if len(converted_discs) > 1:
                m3u_path = os.path.join(self.dest_dir, f"{game_name}.m3u")
                m3u_contents = []
                disc_path = os.path.join(self.dest_dir, game_name)
                if not os.path.exists(disc_path) and not dry_run:
                    os.makedirs(disc_path, exist_ok=True)
                for src_file in converted_discs:
                    dest_filepath = os.path.join(disc_path, os.path.basename(src_file))
                    dest_filename = "/".join([game_name, os.path.basename(src_file)])
                    if verbose:
                        self.logger.debug(f"Moving {src_file} to {dest_filepath}")
                    if not dry_run:
                        shutil.move(src_file, dest_filepath)
                    m3u_contents.append(dest_filename)

                m3u_contents = '\n'.join(m3u_contents)
                if not dry_run:
                    with open(m3u_path, 'w') as m3u:
                        m3u.write(m3u_contents)
                    if verbose:
                        self.logger.info(f"Created M3U manifest at {m3u_path}")
                else:
                    self.logger.info(f"[DRY-RUN] Would create m3u file: {m3u_path}")

            if verbose:
                self.logger.info(f"Processed \"{game_name}\" with #{len(discs)} discs successfully.")

