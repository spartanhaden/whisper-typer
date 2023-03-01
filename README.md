# whisper-typer

A small script that types what you say using whisper while holding a hotkey

## Usage

Install requirements:

```bash
pip3 install -r requirements.txt
```

Run the script:

```bash
python3 main.py
```

The script currently uses the `base.en` model and the `F16` key for push to talk. I also have only tested this on Linux, but it should work on Windows and Mac as well. Also the script will use the default audio input device.
