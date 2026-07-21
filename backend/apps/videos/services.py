import secrets
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings

KEY_URI_PLACEHOLDER = 'KEY_PLACEHOLDER'


class TranscodeError(Exception):
    pass


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise TranscodeError(result.stderr[-2000:] or 'ffmpeg failed with no stderr output')
    return result.stdout


def probe_duration(input_path) -> int:
    out = _run([
        settings.FFPROBE_BINARY, '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(input_path),
    ])
    try:
        return int(float(out.strip()))
    except ValueError:
        return 0


def transcode_to_hls(input_path, output_dir) -> dict:
    """Encodes input_path to AES-128-encrypted HLS (single quality, 720p max) in
    output_dir. The key URI baked into the manifest is a placeholder — ManifestView
    rewrites it per-request to a token-scoped URL, so the actual key never sits in
    a static, guessable location.
    # ponytail: single bitrate, not adaptive multi-rendition — add ABR variants if
    # bandwidth-adaptive playback is ever needed.
    Returns {aes_key: bytes, hls_relpath: str, duration_seconds: int, thumbnail_relpath: str}
    with paths relative to MEDIA_ROOT."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    media_root = Path(settings.MEDIA_ROOT)

    aes_key = secrets.token_bytes(16)
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as keyfile:
        keyfile.write(aes_key)
        keyfile_path = keyfile.name
    keyinfo_path = output_dir / 'keyinfo.txt'
    keyinfo_path.write_text(f'{KEY_URI_PLACEHOLDER}\n{keyfile_path}\n')

    manifest_path = output_dir / 'index.m3u8'
    thumb_path = output_dir / 'thumb.jpg'
    try:
        _run([
            settings.FFMPEG_BINARY, '-y', '-i', str(input_path),
            '-vf', "scale='min(1280,iw)':-2",
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-hls_time', '6', '-hls_playlist_type', 'vod',
            '-hls_key_info_file', str(keyinfo_path),
            '-hls_segment_filename', str(output_dir / 'seg_%03d.ts'),
            str(manifest_path),
        ])
        _run([
            settings.FFMPEG_BINARY, '-y', '-i', str(input_path),
            '-ss', '00:00:01', '-vframes', '1', str(thumb_path),
        ])
        duration = probe_duration(input_path)
    finally:
        Path(keyfile_path).unlink(missing_ok=True)
        keyinfo_path.unlink(missing_ok=True)

    return {
        'aes_key': aes_key,
        'hls_relpath': str(manifest_path.relative_to(media_root)).replace('\\', '/'),
        'duration_seconds': duration,
        'thumbnail_relpath': (
            str(thumb_path.relative_to(media_root)).replace('\\', '/')
            if thumb_path.exists() else ''
        ),
    }
