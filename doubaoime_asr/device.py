import hashlib
import secrets
import time
import uuid
from typing import Optional

import requests
from pydantic import BaseModel, ConfigDict, Field

from .constants import APP_CONFIG, DEFAULT_DEVICE_CONFIG, REGISTER_URL, SETTINGS_URL, USER_AGENT


class DeviceCredentials(BaseModel):
    device_id: Optional[str] = None
    install_id: Optional[str] = None
    cdid: Optional[str] = None
    openudid: Optional[str] = None
    clientudid: Optional[str] = None
    token: Optional[str] = ""


class DeviceRegisterHeaderField(BaseModel):
    device_id: int = 0
    install_id: int = 0
    aid: int
    app_name: str
    version_code: int
    version_name: str
    manifest_version_code: int
    update_version_code: int
    channel: str
    package: str
    device_platform: str
    os: str
    os_api: str
    os_version: str
    device_type: str
    device_brand: str
    device_model: str
    resolution: str
    dpi: str
    language: str
    timezone: int
    access: str
    rom: str
    rom_version: str
    openudid: str
    clientudid: str
    cdid: str
    region: str = "CN"
    tz_name: str = "Asia/Shanghai"
    tz_offset: int = 28800
    sim_region: str = "cn"
    carrier_region: str = "cn"
    cpu_abi: str = "arm64-v8a"
    build_serial: str = "unknown"
    not_request_sender: int = 0
    sig_hash: str = ""
    google_aid: str = ""
    mc: str = ""
    serial_number: str = ""

    @classmethod
    def default(
        cls,
        cdid: Optional[str] = None,
        openudid: Optional[str] = None,
        clientudid: Optional[str] = None,
    ) -> "DeviceRegisterHeaderField":
        return cls(
            **APP_CONFIG,
            **DEFAULT_DEVICE_CONFIG,
            cdid=cdid or _generate_cdid(),
            openudid=openudid or _generate_openudid(),
            clientudid=clientudid or _generate_clientudid(),
        )


class DeviceRegisterBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    magic_tag: str = "ss_app_log"
    header: DeviceRegisterHeaderField
    gen_time: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        serialization_alias="_gen_time",
    )

    @classmethod
    def new(cls, header: DeviceRegisterHeaderField):
        return cls(header=header)


class DeviceRegisterParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    device_platform: str
    os: str
    ssmix: str = "a"
    rticket: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        serialization_alias="_rticket",
    )
    cdid: str
    channel: str
    aid: str
    app_name: str
    version_code: str
    version_name: str
    manifest_version_code: str
    update_version_code: str
    resolution: str
    dpi: str
    device_type: str
    device_brand: str
    language: str
    os_api: str
    os_version: str
    ac: str = "wifi"

    @classmethod
    def default(cls, cdid: str) -> "DeviceRegisterParams":
        app_config = {
            **{k: APP_CONFIG[k] for k in ("channel", "app_name", "version_name")},
            "aid": str(APP_CONFIG["aid"]),
            "version_code": str(APP_CONFIG["version_code"]),
            "manifest_version_code": str(APP_CONFIG["manifest_version_code"]),
            "update_version_code": str(APP_CONFIG["update_version_code"]),
        }
        device_keys = (
            "device_platform",
            "os",
            "resolution",
            "dpi",
            "device_type",
            "device_brand",
            "language",
            "os_api",
            "os_version",
        )
        device_config = {k: DEFAULT_DEVICE_CONFIG[k] for k in device_keys}
        return cls(cdid=cdid, **app_config, **device_config)


class DeviceRegisterResponse(BaseModel):
    server_time: int
    device_id: int
    install_id: int


class SettingsParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    device_platform: str = "android"
    os: str = "android"
    ssmix: str = "a"
    rticket: str = Field(
        default_factory=lambda: str(int(time.time() * 1000)),
        serialization_alias="_rticket",
    )
    cdid: str
    channel: str
    aid: str
    app_name: str
    version_code: str
    version_name: str
    device_id: str

    @classmethod
    def default(cls, device_id: str, cdid: str) -> "SettingsParams":
        return cls(
            cdid=cdid,
            device_id=device_id,
            channel=APP_CONFIG["channel"],
            aid=str(APP_CONFIG["aid"]),
            app_name=APP_CONFIG["app_name"],
            version_code=str(APP_CONFIG["version_code"]),
            version_name=APP_CONFIG["version_name"],
        )


class _AsrConfig(BaseModel):
    app_key: str


class _Settings(BaseModel):
    asr_config: _AsrConfig


class _SettingsData(BaseModel):
    settings: _Settings


class SettingsResponse(BaseModel):
    data: _SettingsData
    message: str

    @property
    def app_key(self) -> str:
        return self.data.settings.asr_config.app_key


def _generate_openudid() -> str:
    return secrets.token_hex(8)


def _generate_cdid() -> str:
    return str(uuid.uuid4())


def _generate_clientudid() -> str:
    return str(uuid.uuid4())


def register_device() -> DeviceCredentials:
    cdid = _generate_cdid()
    openudid = _generate_openudid()
    clientudid = _generate_clientudid()

    header = DeviceRegisterHeaderField.default(cdid=cdid, openudid=openudid, clientudid=clientudid)
    body = DeviceRegisterBody.new(header)
    params = DeviceRegisterParams.default(cdid)
    response = requests.post(
        REGISTER_URL,
        params=params.model_dump(),
        json=body.model_dump(),
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    response_data = DeviceRegisterResponse(**response.json())

    if response_data.device_id and response_data.device_id != 0:
        return DeviceCredentials(
            device_id=str(response_data.device_id),
            install_id=str(response_data.install_id),
            cdid=cdid,
            openudid=openudid,
            clientudid=clientudid,
        )
    raise RuntimeError("设备注册失败，未获取到有效的 device_id。")


def get_asr_token(device_id: str, cdid: str | None) -> str:
    if cdid is None:
        cdid = _generate_cdid()

    params = SettingsParams.default(device_id, cdid)
    body_str = "body=null"
    x_ss_stub = hashlib.md5(body_str.encode()).hexdigest().upper()
    response = requests.post(
        SETTINGS_URL,
        params=params,
        data=body_str,
        headers={
            "User-Agent": USER_AGENT,
            "x-ss-stub": x_ss_stub,
        },
    )
    response.raise_for_status()
    return SettingsResponse(**response.json()).app_key
