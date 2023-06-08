# tmplayer

Minimalist music player for audio files with a pleasant UI.

![preview](./screenshots/preview.png)

## Installation

### PyPI

```
pip install tmplayer
```

### Manual

1. Clone the repository

```
git clone https://github.com/H4wk507/tmplayer.git
```

2. Go into the directory and install

```
cd tmplayer && pip install .
```

## Usage

Pass in directories/audio files as commandline arguments.

Example:

```
tmplayer ~/Music/Rap/ sample.mp3 ...
```

## Key bindings

- arrow keys: Navigate
- k and j: Move up and down
- enter: Play selected song
- space: Play/Pause
- n: Play the next song
- p: Play the previous song
- 1: Set default mode
- 2: Set loop mode
- 3: Set repeat mode
- r: Set random mode
- u: Increase volume by 5%
- d: Decrease volume by 5%
- q: Quit

## License

Licensed under the [MIT License](LICENSE).
