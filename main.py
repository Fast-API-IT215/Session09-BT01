from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

app = FastAPI(
    title="Team Task Manager API",
    description="Hệ thống API quản lý công việc nhóm - Rikkei Education Mini Project",
    version="1.0.0"
)

tasks_db: List[Dict[str, Any]] = [
    {
        "id": 1, 
        "title": "Thiet ke database Shop AI", 
        "description": "Xay dung bang va toi uu index", 
        "assignee": "QuyDev", 
        "priority": 1, 
        "status": "todo",
        "created_at": "2026-07-01T09:00:00Z"
    },
    {
        "id": 2, 
        "title": "Code bo API Authen", 
        "description": "Trien khai filter verify JWT token", 
        "assignee": "FixerQ", 
        "priority": 2, 
        "status": "done",
        "created_at": "2026-07-01T10:00:00Z"
    }
]

class TaskCreateSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=1)
    assignee: str = Field(..., min_length=1)
    priority: int = Field(..., ge=1, le=5)

    class Config:
        anystr_strip_whitespace = True

class TaskStatusUpdateSchema(BaseModel):
    status: str = Field(..., description="Trạng thái mới của công việc (ví dụ: todo, in_progress, done)")

def create_unified_response(
    status_code: int,
    message: str,
    data: Any = None,
    error: Optional[str] = None,
    path: str = ""
) -> JSONResponse:
    envelope = {
        "statusCode": status_code,
        "message": message,
        "data": data,
        "error": error,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "path": path
    }
    return JSONResponse(status_code=status_code, content=envelope)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return create_unified_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Lỗi: Dữ liệu đầu vào không hợp lệ hoặc sai định dạng quy định!",
        error="ERR-VAL-422: Validation error at Request Body fields constraint layout.",
        path=request.url.path
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return create_unified_response(
        status_code=exc.status_code,
        message=exc.detail.get("message") if isinstance(exc.detail, dict) else exc.detail,
        error=exc.detail.get("error") if isinstance(exc.detail, dict) else None,
        path=request.url.path
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return create_unified_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Lỗi hệ thống nghiêm trọng, vui lòng liên hệ quản trị viên!",
        error=f"ERR-SYS-500: Internal Server Error. {str(exc)}",
        path=request.url.path
    )

def calculate_team_metrics() -> Tuple[int, int, float]:
    total_tasks = len(tasks_db)
    if total_tasks == 0:
        return 0, 0, 0.0
    
    completed_tasks = sum(1 for task in tasks_db if task["status"] == "done")
    completion_rate_percentage = round((completed_tasks / total_tasks) * 100, 1)
    
    return total_tasks, completed_tasks, completion_rate_percentage

@app.get("/tasks")
async def get_all_tasks(request: Request, status: Optional[str] = None):
    filtered_tasks = tasks_db
    if status:
        filtered_tasks = [task for task in tasks_db if task["status"] == status]
        
    return create_unified_response(
        status_code=status.HTTP_200_OK,
        message="Lấy danh sách công việc thành công!",
        data=filtered_tasks,
        path=request.url.path
    )

@app.post("/tasks")
async def create_task(request: Request, task_in: TaskCreateSchema):
    for task in tasks_db:
        if task["title"].lower() == task_in.title.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Lỗi: Tiêu đề công việc này đã tồn tại trong nhóm!",
                    "error": "ERR-TASK-01: Task conflict: Title field duplicates an existing record."
                }
            )
            
    max_id = max([task["id"] for task in tasks_db]) if tasks_db else 0
    new_id = max_id + 1
    
    new_task = {
        "id": new_id,
        "title": task_in.title,
        "description": task_in.description,
        "assignee": task_in.assignee,
        "priority": task_in.priority,
        "status": "todo",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    tasks_db.append(new_task)
    
    return create_unified_response(
        status_code=status.HTTP_201_CREATED,
        message="Khởi tạo công việc mới thành công!",
        data=new_task,
        path=request.url.path
    )

@app.put("/tasks/{task_id}")
async def update_task_status(request: Request, task_id: int, status_in: TaskStatusUpdateSchema):
    target_task = None
    for task in tasks_db:
        if task["id"] == task_id:
            target_task = task
            break
            
    if not target_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"Không tìm thấy công việc có ID {task_id}!",
                "error": "ERR-TASK-03: Task not found with the provided identifier."
            }
        )
        
    if target_task["status"] == "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Lỗi: Không được phép cập nhật lùi trạng thái khi công việc đã hoàn thành!",
                "error": "ERR-TASK-04: Task status mutation blocked. Completed tasks are immutable."
            }
        )
        
    target_task["status"] = status_in.status
    
    return create_unified_response(
        status_code=status.HTTP_200_OK,
        message="Cập nhật tiến độ công việc thành công!",
        data=target_task,
        path=request.url.path
    )

@app.get("/tasks/analytics/dashboard")
async def get_dashboard_analytics(request: Request):
    total_tasks, completed_tasks, completion_rate_percentage = calculate_team_metrics()
    
    dashboard_data = {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate_percentage": completion_rate_percentage
    }
    
    return create_unified_response(
        status_code=status.HTTP_200_OK,
        message="Lấy số liệu thống kê hiệu suất nhóm thành công!",
        data=dashboard_data,
        path=request.url.path
    )