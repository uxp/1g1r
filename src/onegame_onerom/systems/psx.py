import glob
import os
from .base import SystemProcessor

class PlaystationProcessor(SystemProcessor):
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
        import tempfile
        import subprocess
        inputs = self.find_inputs()
        verbose = self.options.get('verbose', False)
        dry_run = self.options.get('dry_run', False)
        force = self.options.get('force', False)
        if verbose:
            print(f"Found PSX games: {len(inputs)}")

        if len(inputs) == 0:
            print("No PSX input files found, skipping processing.")
            return

        for game in inputs:
            game_name = game['name']
            discs = game['discs']
            output_file = os.path.join(self.dest_dir, f"{game_name}.pbp")
            # Check if output exists and skip unless --force
            if os.path.exists(output_file) and not force and not dry_run:
                print(f"Output already exists for {output_file}, skipping. Use --force to overwrite.")
                continue
            print(f"Processing game: {game_name} with {len(discs)} disc(s)")
            with tempfile.TemporaryDirectory() as temp_dir:
                extracted_cues = []
                for disc in discs:
                    zip_file = disc['file']
                    if verbose:
                        print(f"Extracting {zip_file} to {temp_dir}")
                    if not dry_run:
                        self.extract_zip(zip_file, temp_dir)
                    else:
                        print(f"[DRY-RUN] Would extract {zip_file} to {temp_dir}")
                # Find all .cue files in temp_dir
                cue_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith('.cue')]
                cue_files.sort()  # Ensure order
                if len(cue_files) == 0 and not dry_run:
                    print(f"No .cue files found for {game_name}")
                    continue
                # If multi-disc, create m3u manifest
                if len(cue_files) > 1 or (len(discs) > 1 and dry_run):
                    m3u_path = os.path.join(temp_dir, f"{game_name}.m3u")
                    m3u_contents = '\n'.join([os.path.basename(c) for c in cue_files])
                    if not dry_run:
                        with open(m3u_path, 'w') as m3u:
                            m3u.write(m3u_contents)
                    else:
                        print(f"[DRY-RUN] Would create m3u file: {m3u_path}")
                    input_arg = m3u_path
                else:
                    if dry_run:
                        input_arg = f"{game_name}.cue"
                    else:
                        input_arg = cue_files[0]
                # Prepare command for psxpackager
                conversion = self.config.get('conversion', {})
                tool = conversion.get('tool', 'psxpackager')
                options = conversion.get('options', {})
                # Quote input and output args for shell
                cmd = [tool, '--input', input_arg, '--output', self.dest_dir]
                if force:
                    cmd.append('-x')
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
                    except Exception as e:
                        print(f"Error running conversion tool: {e}")
                else:
                    print(f"[DRY-RUN] Would run: {' '.join(cmd)}")
            if verbose:
                print(f"Processed \"{game_name}\" with #{len(discs)} discs successfully.")
