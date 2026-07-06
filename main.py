from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime, UTC , timezone

app = FastAPI(
    title="Cinema Ticket Booking API"
)

tickets_db = [
    {
        "id": 1,
        "movie_name": "Doctor Strange 3",
        "room_code": "IMAX-01",
        "quantity": 2,
        "status": "confirmed",
        "created_at": "2026-07-01T19:00:00Z"
    },
    {
        "id": 2,
        "movie_name": "Avatar 3",
        "room_code": "PREMIUM-02",
        "quantity": 1,
        "status": "confirmed",
        "created_at": "2026-07-01T20:15:00Z"
    }
]

class APIResponse(BaseModel):
    statusCode: int
    message: str
    data: Optional[Any]
    error: Optional[Any]
    timestamp: str
    path: str


class TicketCreate(BaseModel):
    movie_name: str = Field(..., min_length=1)
    room_code: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1, le=10)


def responseOTD(
    status_code: int,
    message: str,
    data: Any,
    error: Any,
    path: str
):
    return {
        "statusCode": status_code,
        "message": message,
        "data": data,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": path
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):

    detail = exc.detail

    if isinstance(detail, dict):
        message = detail.get("message")
        error = detail.get("error")
    else:
        message = str(detail)
        error = None

    return JSONResponse(
        status_code=exc.status_code,
        content= responseOTD(
            exc.status_code,
            message,
            None,
            error,
            request.url.path
        )
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    return JSONResponse(
        status_code=422,
        content=responseOTD(
            422,
            "Dữ liệu đầu vào không hợp lệ!",
            None,
            exc.errors(),
            request.url.path
        )
    )

@app.get(
    "/tickets",
    tags=["Ticket"],
    summary="Lấy danh sách vé",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK
)
def get_all_tickets(request: Request):

    return responseOTD(
        200,
        "Lấy danh sách vé thành công!",
        tickets_db,
        None,
        request.url.path
    )

@app.post(
    "/tickets",
    tags=["Ticket"],
    summary= "Đăng ký vé",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED
)
def create_ticket(ticket: TicketCreate, request: Request):

    for item in tickets_db:
        if (
            item["movie_name"].lower() == ticket.movie_name.lower()
            and item["room_code"].lower() == ticket.room_code.lower()
        ):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Lỗi: Vé xem phim tại phòng chiếu này đã được đặt!",
                    "error": "ERR-CINE-01: Ticket conflict for movie and room combination."
                }
            )

    new_ticket = {
        "id": len(tickets_db) + 1,
        "movie_name": ticket.movie_name,
        "room_code": ticket.room_code,
        "quantity": ticket.quantity,
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    tickets_db.append(new_ticket)

    return responseOTD(
        201,
        "Đặt vé thành công!",
        new_ticket,
        None,
        request.url.path
    )

@app.delete(
    "/tickets/{ticket_id}",
    tags=["Ticket"],
    summary="Hủy đăng ký vé",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK
)
def delete_ticket(ticket_id: int, request: Request):

    for ticket in tickets_db:
        if ticket["id"] == ticket_id:
            tickets_db.remove(ticket)

            return responseOTD(
                200,
                "Hủy vé thành công!",
                None,
                None,
                request.url.path
            )

    raise HTTPException(
        status_code=404,
        detail={
            "message": "Lỗi: Không tìm thấy mã vé yêu cầu!",
            "error": "ERR-CINE-02: Ticket ID does not exist."
        }
    )