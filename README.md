A script that makes using [videogrep](https://github.com/antiboredom/videogrep) a little easier. 

videogrep-util adds the following QoL features:
* Extract embedded subtitles automatically if the loose `.srt` is missing that videogrep requires.
* Monkey patch in support to force the English audio track. videogrep uses moviepy and that library doesn't support audio track selection.
* Easily generate super cuts from a directory of video files split by episode or not. 
