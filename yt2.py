from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, AnyUrl
import asyncio, tempfile, os, glob, mimetypes, shutil
from yt_dlp import YoutubeDL

app = FastAPI(title="Youtube Video to Audio API")

class AudioFormat(str, Enum):
    mp3 = "mp3"
    wav = "wav"
    m4a = "m4a"
    flac = "flac"
    aac = "aac"

class ExtractRequest(BaseModel):
    url: AnyUrl #Http url can be used to be more restrictive
    audio_format: AudioFormat

def _download_audio(tmpdir:str, url: str, audio_format: AudioFormat):
    outtmpl = os.path.join(tmpdir, "%(title).200B-%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best", #best audio priority, else best video+audio
        "noplaylist": True,
        "quiet": True,
        "restrictfilenames": False,
        "ignoreerrors": False
    } #no post processors to avoid re-encoding, but can be added later to convert video to audio if audio doesn't exist
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise RuntimeError("Failed to extract info for the provided URL.")
        downloaded = []
        for ext in AudioFormat:
            ext = ext.value

            downloaded.extend(glob.glob(os.path.join(tmpdir, f"*/*.{ext}")))
            downloaded.extend(glob.glob(os.path.join(tmpdir, f"*.{ext}")))
        if not downloaded:
            downloaded = glob.glob(os.path.join(tmpdir, "*"))
        if not downloaded:
            raise RuntimeError("No downloaded file found.")
        downloaded.sort(key=lambda p: os.path.getsize(p), reverse=True)
        path = downloaded[0]

        title = info.get("title") or "audio"
        ext = audio_format.value
        suggested = f"{title}.{ext}"
        suggested = suggested.replace("/", "-")
        return path, suggested

@app.get(/"extract/{url}")
def extract_audio(payload: ExtractRequest):
    tmpdir = tempfile.mkdtemp(prefix="yt_audio_")
    try:
        path, suggested = await asyncio.to_thread(_download_audio, tmpdir, payload.url, payload.audio_format)
        mime_type, _ = mimetypes.guess_type(suggested)
        return FileResponse(
            path,
            media_type=mime_type or "application/octet-stream",
            filename=suggested,
            background=shutil.rmtree(tmpdir, ignore_errors=True)
        )
    except Exception as e:
        shutil.rmtree(tmpdir)
        raise HTTPException(status_code=500, detail=str(e))

