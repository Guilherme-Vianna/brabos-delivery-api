from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.models.push_device import PushRole

FcmToken = Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=512)]


class PushDeviceRegister(BaseModel):
    fcm_token: FcmToken
    role: PushRole
