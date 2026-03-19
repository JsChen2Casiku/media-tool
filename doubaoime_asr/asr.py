from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import AsyncIterator, Callable, Optional

import websockets
from pydantic import BaseModel, Field
from websockets import ClientConnection

from .asr_pb2 import AsrRequest, AsrResponse as AsrResponsePb, FrameState
from .audio import AudioEncoder
from .config import ASRConfig, SessionConfig

AudioChunk = bytes


class ResponseType(Enum):
    TASK_STARTED = auto()
    SESSION_STARTED = auto()
    SESSION_FINISHED = auto()
    VAD_START = auto()
    INTERIM_RESULT = auto()
    FINAL_RESULT = auto()
    HEARTBEAT = auto()
    ERROR = auto()
    UNKNOWN = auto()


@dataclass
class ASRWord:
    word: str
    start_time: float
    end_time: float


@dataclass
class OIDecodingInfo:
    oi_former_word_num: int = 0
    oi_latter_word_num: int = 0
    oi_words: Optional[list] = None


@dataclass
class ASRAlternative:
    text: str
    start_time: float
    end_time: float
    words: list[ASRWord] = field(default_factory=list)
    semantic_related_to_prev: Optional[bool] = None
    oi_decoding_info: Optional[OIDecodingInfo] = None


@dataclass
class ASRResult:
    text: str
    start_time: float
    end_time: float
    confidence: float = 0.0
    alternatives: list[ASRAlternative] = field(default_factory=list)
    is_interim: bool = True
    is_vad_finished: bool = False
    index: int = 0


@dataclass
class ASRExtra:
    audio_duration: Optional[int] = None
    model_avg_rtf: Optional[float] = None
    model_send_first_response: Optional[int] = None
    speech_adaptation_version: Optional[str] = None
    model_total_process_time: Optional[int] = None
    packet_number: Optional[int] = None
    vad_start: Optional[bool] = None
    req_payload: Optional[dict] = None


@dataclass
class ASRResponse:
    type: ResponseType
    text: str = ""
    is_final: bool = False
    vad_start: bool = False
    vad_finished: bool = False
    packet_number: int = -1
    error_msg: str = ""
    raw_json: Optional[dict] = None
    results: list[ASRResult] = field(default_factory=list)
    extra: Optional[ASRExtra] = None


class ASRError(Exception):
    def __init__(self, message: str, response: Optional[ASRResponse] = None) -> None:
        super().__init__(message)
        self.response = response


class _SessionState(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    final_text: str = ""
    is_finished: bool = False
    error: Optional[ASRResponse] = None


class DoubaoASR:
    def __init__(self, config: Optional[ASRConfig] = None):
        self.config = config or ASRConfig()
        self._encoder = AudioEncoder(self.config)

    async def __aenter__(self) -> "DoubaoASR":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    async def transcribe(
        self,
        audio: str | Path | bytes,
        *,
        realtime: bool = False,
        on_interim: Callable[[str], None] | None = None,
    ) -> str:
        final_text = ""
        async for response in self.transcribe_stream(audio, realtime=realtime):
            if response.type == ResponseType.INTERIM_RESULT and on_interim:
                on_interim(response.text)
            elif response.type == ResponseType.FINAL_RESULT:
                final_text = response.text
            elif response.type == ResponseType.ERROR:
                raise ASRError(response.error_msg, response)
        return final_text

    async def transcribe_stream(
        self,
        audio: str | Path | bytes,
        *,
        realtime: bool = False,
    ) -> AsyncIterator[ASRResponse]:
        if isinstance(audio, (str, Path)):
            pcm_data = self._encoder.convert_audio_to_pcm(
                audio,
                self.config.sample_rate,
                self.config.channels,
            )
        else:
            pcm_data = audio

        opus_frames = self._encoder.pcm_to_opus_frames(pcm_data)
        state = _SessionState()

        try:
            async with websockets.connect(
                self.config.ws_url,
                additional_headers=self.config.headers,
                open_timeout=self.config.connect_timeout,
            ) as ws:
                async for resp in self._initialize_session(ws, state):
                    yield resp

                response_queue: asyncio.Queue[Optional[ASRResponse]] = asyncio.Queue()
                send_task = asyncio.create_task(self._send_audio(ws, opus_frames, state, realtime))
                recv_task = asyncio.create_task(self._receive_responses(ws, state, response_queue))

                try:
                    while True:
                        try:
                            resp = await asyncio.wait_for(
                                response_queue.get(),
                                timeout=self.config.recv_timeout,
                            )
                            if resp is None:
                                break
                            if resp.type == ResponseType.HEARTBEAT:
                                continue
                            yield resp
                            if resp.type == ResponseType.ERROR:
                                break
                        except asyncio.TimeoutError:
                            break
                    await send_task
                finally:
                    send_task.cancel()
                    recv_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await send_task
                    with contextlib.suppress(asyncio.CancelledError):
                        await recv_task
        except websockets.exceptions.WebSocketException as exc:
            raise ASRError(f"WebSocket 错误: {exc}") from exc

    async def transcribe_realtime(
        self,
        audio_source: AsyncIterator[AudioChunk],
    ) -> AsyncIterator[ASRResponse]:
        state = _SessionState()
        try:
            async with websockets.connect(
                self.config.ws_url,
                additional_headers=self.config.headers,
                open_timeout=self.config.connect_timeout,
            ) as ws:
                async for resp in self._initialize_session(ws, state):
                    yield resp

                response_queue: asyncio.Queue[Optional[ASRResponse]] = asyncio.Queue()
                send_task = asyncio.create_task(self._send_audio_realtime(ws, audio_source, state))
                recv_task = asyncio.create_task(self._receive_responses(ws, state, response_queue))

                try:
                    while True:
                        resp = await response_queue.get()
                        if resp is None:
                            break
                        if resp.type == ResponseType.HEARTBEAT:
                            continue
                        yield resp
                        if resp.type == ResponseType.ERROR:
                            break
                    await send_task
                finally:
                    send_task.cancel()
                    recv_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await send_task
                    with contextlib.suppress(asyncio.CancelledError):
                        await recv_task
        except websockets.exceptions.WebSocketException as exc:
            raise ASRError(f"WebSocket 错误: {exc}") from exc

    async def _initialize_session(self, ws: ClientConnection, state: _SessionState) -> AsyncIterator[ASRResponse]:
        token = self.config.get_token()
        await ws.send(_build_start_task(state.request_id, token))
        parsed = _parse_response(await ws.recv())
        if parsed.type == ResponseType.ERROR:
            raise ASRError(f"StartTask 失败：{parsed.error_msg}", parsed)
        yield parsed

        await ws.send(_build_start_session(state.request_id, token, self.config.session_config()))
        parsed = _parse_response(await ws.recv())
        if parsed.type == ResponseType.ERROR:
            raise ASRError(f"StartSession 失败：{parsed.error_msg}", parsed)
        yield parsed

    async def _send_audio(
        self,
        ws: ClientConnection,
        opus_frames: list[bytes],
        state: _SessionState,
        realtime: bool,
    ):
        timestamp_ms = int(time.time() * 1000)
        frame_interval = self.config.frame_duration_ms / 1000.0

        for index, opus_frame in enumerate(opus_frames):
            if state.is_finished:
                break
            if index == 0:
                frame_state = FrameState.FRAME_STATE_FIRST
            elif index == len(opus_frames) - 1:
                frame_state = FrameState.FRAME_STATE_LAST
            else:
                frame_state = FrameState.FRAME_STATE_MIDDLE

            await ws.send(
                _build_asr_request(
                    opus_frame,
                    state.request_id,
                    frame_state,
                    timestamp_ms + index * self.config.frame_duration_ms,
                )
            )
            if realtime:
                await asyncio.sleep(frame_interval)

        await ws.send(_build_finish_session(state.request_id, self.config.get_token()))

    async def _send_audio_realtime(
        self,
        ws: ClientConnection,
        audio_source: AsyncIterator[AudioChunk],
        state: _SessionState,
    ):
        timestamp_ms = int(time.time() * 1000)
        frame_index = 0
        pcm_buffer = b""
        samples_per_frame = self.config.sample_rate * self.config.frame_duration_ms // 1000
        bytes_per_frame = samples_per_frame * 2

        async for chunk in audio_source:
            if state.is_finished:
                break
            pcm_buffer += chunk
            while len(pcm_buffer) >= bytes_per_frame:
                pcm_frame = pcm_buffer[:bytes_per_frame]
                pcm_buffer = pcm_buffer[bytes_per_frame:]
                opus_frame = self._encoder.encoder.encode(pcm_frame, samples_per_frame)
                frame_state = FrameState.FRAME_STATE_FIRST if frame_index == 0 else FrameState.FRAME_STATE_MIDDLE
                await ws.send(
                    _build_asr_request(
                        opus_frame,
                        state.request_id,
                        frame_state,
                        timestamp_ms + frame_index * self.config.frame_duration_ms,
                    )
                )
                frame_index += 1

        if pcm_buffer and not state.is_finished:
            if len(pcm_buffer) < bytes_per_frame:
                pcm_buffer += b"\x00" * (bytes_per_frame - len(pcm_buffer))
            opus_frame = self._encoder.encoder.encode(pcm_buffer, samples_per_frame)
            await ws.send(
                _build_asr_request(
                    opus_frame,
                    state.request_id,
                    FrameState.FRAME_STATE_LAST,
                    timestamp_ms + frame_index * self.config.frame_duration_ms,
                )
            )
        elif frame_index > 0 and not state.is_finished:
            silent_frame = b"\x00" * bytes_per_frame
            opus_frame = self._encoder.encoder.encode(silent_frame, samples_per_frame)
            await ws.send(
                _build_asr_request(
                    opus_frame,
                    state.request_id,
                    FrameState.FRAME_STATE_LAST,
                    timestamp_ms + frame_index * self.config.frame_duration_ms,
                )
            )

        if not state.is_finished:
            await ws.send(_build_finish_session(state.request_id, self.config.get_token()))

    async def _receive_responses(
        self,
        ws: ClientConnection,
        state: _SessionState,
        queue: asyncio.Queue[Optional[ASRResponse]],
    ):
        try:
            while not state.is_finished:
                resp = _parse_response(await ws.recv())
                if resp.type == ResponseType.ERROR:
                    state.error = resp
                    state.is_finished = True
                    await queue.put(resp)
                    break
                if resp.type == ResponseType.HEARTBEAT:
                    await queue.put(resp)
                elif resp.type == ResponseType.SESSION_FINISHED:
                    state.is_finished = True
                    await queue.put(resp)
                    break
                elif resp.type == ResponseType.FINAL_RESULT:
                    state.final_text = resp.text
                    await queue.put(resp)
                else:
                    await queue.put(resp)
        except websockets.exceptions.ConnectionClosed:
            state.is_finished = True
        finally:
            await queue.put(None)


def _build_start_task(request_id: str, token: str) -> bytes:
    request = AsrRequest()
    request.token = token
    request.service_name = "ASR"
    request.method_name = "StartTask"
    request.request_id = request_id
    return request.SerializeToString()


def _build_start_session(request_id: str, token: str, config: SessionConfig) -> bytes:
    request = AsrRequest()
    request.token = token
    request.service_name = "ASR"
    request.method_name = "StartSession"
    request.request_id = request_id
    request.payload = config.model_dump_json()
    return request.SerializeToString()


def _build_finish_session(request_id: str, token: str) -> bytes:
    request = AsrRequest()
    request.token = token
    request.service_name = "ASR"
    request.method_name = "FinishSession"
    request.request_id = request_id
    return request.SerializeToString()


def _build_asr_request(
    audio_data: bytes,
    request_id: str,
    frame_state: FrameState,
    timestamp_ms: int,
) -> bytes:
    request = AsrRequest()
    request.service_name = "ASR"
    request.method_name = "TaskRequest"
    request.payload = json.dumps({"extra": {}, "timestamp_ms": timestamp_ms})
    request.audio_data = audio_data
    request.request_id = request_id
    request.frame_state = frame_state
    return request.SerializeToString()


def _parse_word(data: dict) -> ASRWord:
    return ASRWord(
        word=data.get("word", ""),
        start_time=data.get("start_time", 0.0),
        end_time=data.get("end_time", 0.0),
    )


def _parse_oi_decoding_info(data: Optional[dict]) -> Optional[OIDecodingInfo]:
    if data is None:
        return None
    return OIDecodingInfo(
        oi_former_word_num=data.get("oi_former_word_num", 0),
        oi_latter_word_num=data.get("oi_latter_word_num", 0),
        oi_words=data.get("oi_words"),
    )


def _parse_alternative(data: dict) -> ASRAlternative:
    return ASRAlternative(
        text=data.get("text", ""),
        start_time=data.get("start_time", 0.0),
        end_time=data.get("end_time", 0.0),
        words=[_parse_word(item) for item in data.get("words", [])],
        semantic_related_to_prev=data.get("semantic_related_to_prev"),
        oi_decoding_info=_parse_oi_decoding_info(data.get("oi_decoding_info")),
    )


def _parse_result(data: dict) -> ASRResult:
    return ASRResult(
        text=data.get("text", ""),
        start_time=data.get("start_time", 0.0),
        end_time=data.get("end_time", 0.0),
        confidence=data.get("confidence", 0.0),
        alternatives=[_parse_alternative(item) for item in data.get("alternatives", [])],
        is_interim=data.get("is_interim", True),
        is_vad_finished=data.get("is_vad_finished", False),
        index=data.get("index", 0),
    )


def _parse_extra(data: dict) -> ASRExtra:
    return ASRExtra(
        audio_duration=data.get("audio_duration"),
        model_avg_rtf=data.get("model_avg_rtf"),
        model_send_first_response=data.get("model_send_first_response"),
        speech_adaptation_version=data.get("speech_adaptation_version"),
        model_total_process_time=data.get("model_total_process_time"),
        packet_number=data.get("packet_number"),
        vad_start=data.get("vad_start"),
        req_payload=data.get("req_payload"),
    )


def _parse_response(data: bytes) -> ASRResponse:
    pb = AsrResponsePb()
    pb.ParseFromString(data)

    if pb.message_type == "TaskStarted":
        return ASRResponse(type=ResponseType.TASK_STARTED)
    if pb.message_type == "SessionStarted":
        return ASRResponse(type=ResponseType.SESSION_STARTED)
    if pb.message_type == "SessionFinished":
        return ASRResponse(type=ResponseType.SESSION_FINISHED)
    if pb.message_type in ("TaskFailed", "SessionFailed"):
        return ASRResponse(type=ResponseType.ERROR, error_msg=pb.status_message)
    if not pb.result_json:
        return ASRResponse(type=ResponseType.UNKNOWN)

    try:
        json_data = json.loads(pb.result_json)
    except json.JSONDecodeError:
        return ASRResponse(type=ResponseType.UNKNOWN)

    results_raw = json_data.get("results")
    extra_raw = json_data.get("extra", {})
    parsed_extra = _parse_extra(extra_raw)

    if results_raw is None:
        return ASRResponse(
            type=ResponseType.HEARTBEAT,
            packet_number=extra_raw.get("packet_number", -1),
            raw_json=json_data,
            extra=parsed_extra,
        )

    parsed_results = [_parse_result(item) for item in results_raw]
    if extra_raw.get("vad_start"):
        return ASRResponse(
            type=ResponseType.VAD_START,
            vad_start=True,
            raw_json=json_data,
            results=parsed_results,
            extra=parsed_extra,
        )

    text = ""
    is_interim = True
    vad_finished = False
    nonstream_result = False
    for item in results_raw:
        if item.get("text"):
            text = item.get("text")
        if item.get("is_interim") is False:
            is_interim = False
        if item.get("is_vad_finished"):
            vad_finished = True
        if item.get("extra", {}).get("nonstream_result"):
            nonstream_result = True

    if nonstream_result or (not is_interim and vad_finished):
        return ASRResponse(
            type=ResponseType.FINAL_RESULT,
            text=text,
            is_final=True,
            vad_finished=vad_finished,
            raw_json=json_data,
            results=parsed_results,
            extra=parsed_extra,
        )

    return ASRResponse(
        type=ResponseType.INTERIM_RESULT,
        text=text,
        is_final=False,
        raw_json=json_data,
        results=parsed_results,
        extra=parsed_extra,
    )


async def transcribe(
    audio: str | Path | bytes,
    *,
    config: ASRConfig | None = None,
    on_interim: Callable[[str], None] | None = None,
    realtime: bool = False,
) -> str:
    async with DoubaoASR(config) as asr:
        return await asr.transcribe(audio, on_interim=on_interim, realtime=realtime)


async def transcribe_stream(
    audio: str | Path | bytes,
    *,
    config: ASRConfig | None = None,
    realtime: bool = False,
) -> AsyncIterator[ASRResponse]:
    async with DoubaoASR(config) as asr:
        async for resp in asr.transcribe_stream(audio, realtime=realtime):
            yield resp


async def transcribe_realtime(
    audio_source: AsyncIterator[AudioChunk],
    *,
    config: ASRConfig | None = None,
) -> AsyncIterator[ASRResponse]:
    async with DoubaoASR(config) as asr:
        async for resp in asr.transcribe_realtime(audio_source):
            yield resp
