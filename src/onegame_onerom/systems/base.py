import glob
import os
import shutil
import abc
import subprocess
import tempfile


class SystemProcessor(abc.ABC):

    def __init__(self, config, source_dir, dest_dir, options):
        self.config = config
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.options = options

    @abc.abstractmethod
    def find_inputs(self):
        pass

    @abc.abstractmethod
    def process(self):
        pass


# Generalized processor for copy-only systems
class CopyProcessor(SystemProcessor):
    def find_inputs(self):
        pattern = os.path.join(self.source_dir, self.config.get('file_pattern', '*'))
        return glob.glob(pattern)

    def process(self):
        inputs = self.find_inputs()
        verbose = self.options.get('verbose', False)
        dry_run = self.options.get('dry_run', False)
        if verbose:
            print(f"Found files: {len(inputs)}")
        for src_file in inputs:
            dest_file = os.path.join(self.dest_dir, os.path.basename(src_file))
            if verbose:
                print(f"Copying {src_file} to {dest_file}")
            if not dry_run:
                if os.path.exists(dest_file) and not self.options.get('force', False):
                    if verbose:
                        print(f"Destination file {dest_file} already exists, skipping.")
                    continue
                os.makedirs(self.dest_dir, exist_ok=True)
                shutil.copy2(src_file, dest_file)
            else:
                print(f"[DRY-RUN] Would copy {src_file} to {dest_file}")
        if verbose:
            print("Copy-only processing complete.")


# Generalized processor for CHD systems
class CHDProcessor(SystemProcessor):
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
        chdman_path = conversion.get('tool', 'chdman')
        options = conversion.get('options', {})

        for game in inputs:
            game_name = game['name']
            discs = game['discs']

            # Check if output exists and skip unless --force
            if not force and not dry_run:
                if any([os.path.exists(f) for f in [os.path.join(self.dest_dir, f"{game_name}.chd"), os.path.join(self.dest_dir, f"{game_name}.m3u")]]):
                    if verbose:
                        print(f"Output already exists for {game_name}, skipping. Use --force to overwrite.")
                    continue
            if verbose:
                print(f"Processing game: {game_name} with {len(discs)} disc(s)")
            converted_discs = []
            for disc in discs:
                zip_file = disc['file']
                disc_name = os.path.basename(zip_file)
                with tempfile.TemporaryDirectory() as temp_dir:
                    if verbose:
                        print(f"Extracting {zip_file} to {temp_dir}")
                    if not dry_run:
                        self.extract_zip(zip_file, temp_dir)
                    else:
                        print(f"[DRY-RUN] Would extract {zip_file} to {temp_dir}")

                    cue_files = glob.glob(os.path.join(temp_dir, '*.cue'))
                    if not cue_files and not dry_run:
                        print(f"No CUE file found in {zip_file}, skipping.")
                        continue

                    if dry_run:
                        input_arg = f"{disc_name}.cue"
                    else:
                        input_arg = cue_files[0]

                    if dry_run:
                        output_arg = os.path.join(self.dest_dir, f"{disc_name}.chd")
                    else:
                        output_arg = os.path.join(self.dest_dir, os.path.splitext(os.path.basename(cue_files[0]))[0] + ".chd")             

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

                    if verbose:
                        print(f"Running conversion command: {' '.join(cmd)}")

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
                                print("Conversion output:", stdout)
                                if stderr:
                                    print("Conversion errors:", stderr)
                            converted_discs.append(output_arg)
                        except Exception as e:
                            print(f"Error running conversion tool: {e}")
                    else:
                        print(f"[DRY-RUN] Would run: {' '.join(cmd)}")
            
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
                        print(f"Moving {src_file} to {dest_filepath}")
                    if not dry_run:
                        shutil.move(src_file, dest_filepath)
                    m3u_contents.append(dest_filename)

                m3u_contents = '\n'.join(m3u_contents)
                if not dry_run:
                    with open(m3u_path, 'w') as m3u:
                        m3u.write(m3u_contents)
                    if verbose:
                        print(f"Created M3U manifest at {m3u_path}")
                else:
                    print(f"[DRY-RUN] Would create m3u file: {m3u_path}")

            if verbose:
                print(f"Processed \"{game_name}\" with #{len(discs)} discs successfully.")

