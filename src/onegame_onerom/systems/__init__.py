# 1G1R Deployment Tool package
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
# - Playstation Portable (psp): cso (yacc)
# - Saturn: chd (chdman)
# - Sega CD: chd (chdman)
# - Super Nintendo: zip
# - TurboGrafx: zip
# - TurboGrafx-CD: chd (chdman)
# - Virtual Boy: zip
# - Xbox: emulator doesn't support compression for now (Use iso2god for trimming iso)
# - Xbox 360: emulator doesn't support compression for now (Use iso2god for trimming iso) 