import aiohttp.web
import os

async def handle_root(_):
    return aiohttp.web.Response(text="✅ Server is alive")

async def handle_transcript(request: aiohttp.web.Request):
    filename = request.match_info["filename"]
    folder = os.path.join(os.getcwd(), "transcripts")
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return aiohttp.web.Response(status=404, text="Transcript not found.")
    return aiohttp.web.FileResponse(path)

def make_app():
    folder = os.path.join(os.getcwd(), "transcripts")
    os.makedirs(folder, exist_ok=True)  # <-- this creates it if missing

    app = aiohttp.web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_static("/transcripts", path=folder)
    app.router.add_get("/transcripts/{filename}", handle_transcript)
    return app