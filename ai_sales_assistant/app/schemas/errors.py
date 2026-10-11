from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str | None = Field(default=None, examples=["customer"])
    message: str = Field(examples=["String should have at least 1 character"])
    type: str = Field(examples=["string_too_short"])


class ErrorBody(BaseModel):
    code: str = Field(examples=["validation_error"])
    message: str = Field(examples=["The request contains invalid data."])
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
