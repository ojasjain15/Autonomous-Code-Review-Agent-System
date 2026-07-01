from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from celery.result import AsyncResult
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any
import os
from .celery_config import celery_app
from .core.github import GithubClient
from dotenv import load_dotenv
from datetime import datetime
from .logger_config import get_logger, cleanup_logging
import atexit

load_dotenv()

logger = get_logger("api_service", "api_service.log")
atexit.register(cleanup_logging)

class PRRequest(BaseModel):
    repo_url: HttpUrl = Field(..., description="GitHub repository URL")
    pr_number: int = Field(..., gt=0, description="Pull request number")
    github_token: Optional[str] = Field(
        None,
        description="GitHub access token",
        min_length=40,
        max_length=255
    )
    
    class Config:
        schema_extra = {
            "example": {
                "repo_url": "https://github.com/owner/repo",
                "pr_number": 123,
                "github_token": "optional_github_token"
            }
        }

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None

class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    last_updated: str

app = FastAPI(
    title="AI Code Review Agent",
    description="API for automated code review using AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(
        "Validation error occurred",
        extra={
            "error_details": exc.errors(),
            "client_host": request.client.host,
            "path": request.url.path
        }
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Invalid request parameters"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception occurred",
        extra={
            "error_type": type(exc).__name__,
            "error_details": str(exc),
            "client_host": request.client.host,
            "path": request.url.path
        },
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "message": "An unexpected error occurred"
        }
    )

@app.post(
    "/analyze-pr",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Analysis"]
)
async def analyze_pr(request: PRRequest) -> TaskResponse:
    logger.info(
        "Received PR analysis request",
        extra={
            "pr_number": request.pr_number,
            "repo_url": str(request.repo_url),
            "has_token": bool(request.github_token)
        }
    )
    
    try:
        task = celery_app.send_task(
            'app.tasks.analyze_pr',
            args=[str(request.repo_url), request.pr_number, request.github_token]
        )
        
        logger.info(
            "Created analysis task",
            extra={
                "task_id": task.id,
                "pr_number": request.pr_number
            }
        )
        
        return TaskResponse(
            task_id=task.id,
            status="pending",
            message="Analysis task created successfully"
        )
        
    except Exception as e:
        logger.error(
            "Failed to create analysis task",
            extra={
                "error_type": type(e).__name__,
                "error_details": str(e),
                "pr_number": request.pr_number
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analysis task: {str(e)}"
        )

@app.get(
    "/status/{task_id}",
    response_model=TaskStatus,
    tags=["Analysis"]
)
async def get_status(task_id: str) -> TaskStatus:
    logger.info("Checking task status", extra={"task_id": task_id})
    
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        status_response = TaskStatus(
            task_id=task_id,
            status=result.status,
            result=result.result if result.ready() else None,
            last_updated=datetime.now().isoformat()
        )
        
        logger.info(
            "Retrieved task status",
            extra={
                "task_id": task_id,
                "status": result.status,
                "is_ready": result.ready()
            }
        )
        
        return status_response
        
    except Exception as e:
        logger.error(
            "Failed to get task status",
            extra={
                "task_id": task_id,
                "error_type": type(e).__name__,
                "error_details": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found or error retrieving status: {str(e)}"
        )

@app.get(
    "/results/{task_id}",
    response_model=Dict[str, Any],
    tags=["Analysis"]
)
async def get_results(task_id: str) -> Dict[str, Any]:
    logger.info("Fetching task results", extra={"task_id": task_id})
    
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if not result.ready():
            logger.info(
                "Results not ready",
                extra={
                    "task_id": task_id,
                    "status": result.status
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Results not ready"
            )
            
        if result.failed():
            logger.error(
                "Task failed",
                extra={
                    "task_id": task_id,
                    "error_info": str(result.info)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Task failed"
            )
            
        logger.info(
            "Successfully retrieved results",
            extra={"task_id": task_id}
        )
        return result.result
        
    except Exception as e:
        logger.error(
            "Failed to get task results",
            extra={
                "task_id": task_id,
                "error_type": type(e).__name__,
                "error_details": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving results: {str(e)}"
        )

@app.get("/health", tags=["System"])
async def health_check():
    logger.debug("Health check requested")
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
