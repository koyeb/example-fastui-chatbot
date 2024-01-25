import asyncio
from itertools import chain
from typing import AsyncIterable, Annotated
from decouple import config
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastui import prebuilt_html, FastUI, AnyComponent
from fastui import components as c
from fastui.events import PageEvent
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse


# Create the app object
app = FastAPI()


# Defines Forms
class ChatForm(BaseModel):
    chat: str = Field(title=' ', max_length=1000)


# Root endpoint
@app.get('/api/', response_model=FastUI, response_model_exclude_none=True)
def api_index(chat: str | None = None) -> list[AnyComponent]:
    if chat is not None:
        c.FireEvent(event=PageEvent(name='load'))
    return [
        c.PageTitle(text='FastUI Chatbot'),
        c.Page(
            components=[
                c.Heading(text='FastUI Chatbot'),
                c.Paragraph(text='This is a simple chatbot built with FastUI and MistralAI.'),
                c.ModelForm(model=ChatForm, submit_url=".", method='GOTO'),
                c.Div(
                    components=[
                        c.ServerLoad(
                            path=f"/sse/{chat}",
                            sse=True,
                            load_trigger=PageEvent(name='load'),
                            components=[],
                        )
                    ],
                    class_name='my-2 p-2 border rounded'),
            ],
        ),
        c.Footer(
            extra_text='Made with FastUI',
            links=[]
        )
    ]


# async
async def ai_response_generator(prompt: str) -> AsyncIterable[str]:
    # Mistral client
    client = MistralClient(api_key=config('MISTRAL_API_KEY'))  # Create the client
    system_message = "You are a helpful chatbot. You will help people with answers to their questions."
    # Output variables
    output = f"**User:** {prompt}\n\n"
    msg = ''
    # Mistral chat messages
    messages = [
        ChatMessage(role="system", content=system_message),
        ChatMessage(role="user", content=prompt)
    ]
    # Stream the chat
    output += f"**Chatbot:** "
    for chunk in client.chat_stream(model="mistral-small", messages=messages):
        if token := chunk.choices[0].delta.content or "":
            output += token
            m = FastUI(root=[c.Markdown(text=output)])
            msg = f'data: {m.model_dump_json(by_alias=True, exclude_none=True)}\n\n'
            yield msg
    # avoid the browser reconnecting
    while True:
        yield msg
        await asyncio.sleep(10)


# SSE endpoint
@app.get('/api/sse/{prompt}')
async def sse_ai_response(prompt: str) -> StreamingResponse:
    return StreamingResponse(ai_response_generator(prompt), media_type='text/event-stream')


# Prebuilt HTML
@app.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    """Simple HTML page which serves the React app, comes last as it matches all paths."""
    return HTMLResponse(prebuilt_html(title='FastUI Demo'))
