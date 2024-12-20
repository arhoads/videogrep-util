import os
import subprocess
import importlib
import re
import argparse
import mimetypes

from videogrep import videogrep

EPISODE_PATTERN = re.compile(r'(?P<episode>S\d{1,2}E\d{1,2})')

EXTRA_COMMANDs = ['-map', '0:a:m:language:eng?']
# copied from moviepy. We only want to add in the audio channel mapping
def monkey_patched_moviepy(self, starttime = 0):
    import numpy as np
    from moviepy.compat import DEVNULL, PY3
    from moviepy.config import get_setting
    import subprocess as sp

    """ Opens the file, creates the pipe. """

    self.close_proc() # if any

    if starttime !=0 :
        offset = min(1,starttime)
        i_arg = ["-ss", "%.05f"%(starttime-offset),
                '-i', self.filename, '-vn',
                "-ss", "%.05f"%offset]
    else:
        i_arg = [ '-i', self.filename,  '-vn']


    cmd = ([get_setting("FFMPEG_BINARY")] + i_arg + EXTRA_COMMANDs +
           [ '-loglevel', 'error',
             '-f', self.f,
            '-acodec', self.acodec,
            '-ar', "%d"%self.fps,
            '-ac', '%d'%self.nchannels, '-'])

    popen_params = {"bufsize": self.buffersize,
                    "stdout": sp.PIPE,
                    "stderr": sp.PIPE,
                    "stdin": DEVNULL}

    if os.name == "nt":
        popen_params["creationflags"] = 0x08000000

    self.proc = sp.Popen( cmd, **popen_params)

    self.pos = np.round(self.fps*starttime)

def patch_moviepy():
    import moviepy

    if importlib.metadata.version('moviepy') == '1.0.3':
        moviepy.audio.io.readers.FFMPEG_AudioReader.initialize = monkey_patched_moviepy
    else:
        print("unable to patch moviepy. 1.0.3 is supported only.")

def prepare_video(args, fullpath, subtitleFile, toDelete):
    isFile = os.path.isfile(subtitleFile)

    if args.delete_all_srt:
        if isFile:
            toDelete.append(subtitleFile)
    elif not isFile:
        assert subtitleFile[-4:] == '.srt', 'subtitleFile must end in srt'
        command = [
            "ffmpeg",
            "-i", fullpath,
            "-map", "0:s:0",  # Select subtitle stream
            subtitleFile,
            "-y"  # Overwrite output file if it exists
        ]
        subprocess.run(command, check=True)
        if args.delete_generated:
            toDelete.append(subtitleFile)

def get_top_level_name(fullpath):
    split_path = fullpath.split(str(os.sep))
    
    # Look for the "Season X" folder first
    for i, component in enumerate(split_path):
        if "Season" in component:
            return split_path[i - 1]  # The folder before "Season X" is the show name

    return split_path[-1]

def process_file(args, file, toProcess, toDelete):
    if file is None:
        # os.path.join let's us be sloppy
        file = args.input

    filename = os.fsdecode(file)
    if not mimetypes.guess_type(filename)[0].startswith('video'):
        return

    fullpath = os.path.join(args.input, filename)

    withoutExtension, _ = os.path.splitext(filename)
    subtitleFile = os.path.join(args.input, f'{withoutExtension}.srt')

    prepare_video(args, fullpath, subtitleFile, toDelete)

    if args.delete_all_srt:
        return

    if not args.combine:
        outputName = get_top_level_name(args.input)
        match = EPISODE_PATTERN.search(withoutExtension)
        if match:
            notFullPath = withoutExtension.split(str(os.sep))[-1]
            outputName = f'{notFullPath[:match.end('episode')]} supercut.mp4'

        videogrep(fullpath, args.search, output=outputName, search_type=args.search_type)
    else:
        toProcess.append(fullpath)

def process_files(args):
    userInput = args.input
    searchTerm = args.search

    if not os.path.exists(userInput):
        print("invalid input")
        return

    toProcess = []
    toDelete = []

    directory = os.fsencode(userInput)
    
    if os.path.isdir(directory):
        for file in os.listdir(directory):
            process_file(args, file, toProcess, toDelete)
    else:
        process_file(args, None, toProcess, toDelete)

    if toProcess:
        videogrep(toProcess, searchTerm, output=f'{get_top_level_name(userInput)} {searchTerm} supercut.mp4', search_type=args.search_type)

    for file in toDelete:
        os.remove(file)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", help='search input')
    parser.add_argument("-st", "--search-type", default="sentence")
    parser.add_argument("-i", "--input")
    parser.add_argument("-d", "--delete-generated", action='store_true', default=False, help='delete str generated this run')
    parser.add_argument("-dall", "--delete-all-srt", action='store_true', default=False, help="delete srt even if not generated this run only")
    parser.add_argument("-c", "--combine", default=False, help='if true output is collated')
    parser.add_argument("-force", "--force-english", default=True, help='if true enable hack to select English audio channel')

    args = parser.parse_args()

    if args.force_english:
        patch_moviepy()

    process_files(args)

if __name__ == '__main__':
    main()
