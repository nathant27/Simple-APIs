from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, AnyUrl
import asyncio, tempfile, os, glob, mimetypes, shutil
from yt_dlp import YoutubeDL
from starlette.background import BackgroundTask

app = FastAPI(title="Youtube Video to Audio API")

class ExtractRequest(BaseModel):
    url: AnyUrl
    #audio_format: str = Body(..., regex="^(mp3|wav|m4a|flac|aac)$")

def _download_best_audio(tmpdir: str, url: str) -> tuple[str, str]:
    """
    Blocking: run in a thread. Returns (filepath, suggested_filename).
    We request 'bestaudio' only, with no post-processing to avoid re-encoding.
    """
    outtmpl = os.path.join(tmpdir, "%(title).200B-%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",   # pick the best audio-only format
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "restrictfilenames": False,
        "ignoreerrors": False,
        # No postprocessors -> no re-encode = “full quality”
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise RuntimeError("Failed to extract info for the provided URL.")
        # When downloading a single video, yt-dlp returns a dict for that video.
        # Build expected path: outtmpl pattern with title/id/ext; or just glob.
        downloaded = []
        for ext in ("m4a", "webm", "mp4", "opus", "mp3"):  # common cases
            downloaded.extend(glob.glob(os.path.join(tmpdir, f"*/*.{ext}")))
            downloaded.extend(glob.glob(os.path.join(tmpdir, f"*.{ext}")))
        if not downloaded:
            # fall back to any file in tmpdir
            downloaded = glob.glob(os.path.join(tmpdir, "*"))
        if not downloaded:
            raise RuntimeError("No downloaded file found.")
        # pick largest (safest when thumbnails/captions also present)
        downloaded.sort(key=lambda p: os.path.getsize(p), reverse=True)
        path = downloaded[0]

        # Suggest a clean filename for the client
        title = info.get("title") or "audio"
        ext = os.path.splitext(path)[1].lstrip(".") or "m4a"
        suggested = f"{title}.{ext}"
        # sanitize suggested just a bit
        suggested = suggested.replace("/", "-")
        return path, suggested

@app.post("/extract-audio")
async def extract_audio(payload: ExtractRequest = Body(...)):
    # Make a temp dir for this request
    tmpdir = tempfile.mkdtemp(prefix="yt_audio_")
    try:
        # yt-dlp is blocking; run it in a thread so we don't block the event loop
        path, suggested = await asyncio.to_thread(_download_best_audio, tmpdir, str(payload.url))

        # Best-effort content-type
        mime, _ = mimetypes.guess_type(path)
        if not mime or not mime.startswith("audio/"):
            # Most common YouTube audio-only containers
            if path.endswith(".m4a"):
                mime = "audio/mp4"
            elif path.endswith(".webm") or path.endswith(".opus"):
                mime = "audio/webm"
            else:
                mime = "application/octet-stream"

        # Stream the file to the client; cleanup temp dir after response is sent
        return FileResponse(
            path,
            media_type=mime,
            filename=suggested,
            background=BackgroundTask(shutil.rmtree, str(tmpdir), ignore_errors=True)
        )
    except Exception as e:
        # Cleanup tempdir on error as well
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Extraction failed: {e}")