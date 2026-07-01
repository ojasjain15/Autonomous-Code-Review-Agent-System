from typing import Dict, Optional, List
from celery import Task
from .celery_config import celery_app
from .core.github import GithubClient
from .core.agent import CodeAnalyzer
from .logger_config import get_logger
from datetime import datetime
from dataclasses import dataclass, asdict

logger = get_logger("pr_analysis", "pr_analysis.log")

class PRAnalysisTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Task failed",
            extra={
                "task_id": task_id,
                "error_type": type(exc).__name__,
                "error_details": str(exc),
                "args": args
            },
            exc_info=True
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            "Task is being retried",
            extra={
                "task_id": task_id,
                "error_type": type(exc).__name__,
                "error_details": str(exc),
                "args": args,
                "retry_count": self.request.retries
            }
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)

@dataclass
class AnalysisResult:
    name: str
    issues: List[Dict]
    analysis_time: float
    status: str
    error: Optional[str] = None

@dataclass
class AnalysisSummary:
    total_files: int
    total_issues: int
    critical_issues: int
    total_files_analysed: int
    analysis_start_time: str
    analysis_end_time: str
    failed_files: int = 0
    status: str = "success"
    error: Optional[str] = None

@celery_app.task(
    bind=True,
    base=PRAnalysisTask,
    max_retries=3,
    retry_backoff=True,
    rate_limit='10/m'
)
def analyze_pr(
    self,
    repo_url: str,
    pr_number: int,
    github_token: Optional[str] = None
) -> Dict:
    analysis_start_time = datetime.now()
    logger.info(
        "Starting PR analysis",
        extra={
            "pr_number": pr_number,
            "repo_url": repo_url,
            "task_id": self.request.id,
            "has_token": bool(github_token)
        }
    )
    
    results = {
        "files": [],
        "summary": asdict(AnalysisSummary(
            total_files=0,
            total_issues=0,
            critical_issues=0,
            total_files_analysed=0,
            analysis_start_time=analysis_start_time.isoformat(),
            analysis_end_time=datetime.now().isoformat(),
            failed_files=0,
            status="error",
            error=None
        ))
    }
    
    try:
        github_client = GithubClient(github_token)
        pr_files = github_client.get_pr_files(repo_url, pr_number)
        
        results["summary"].update({
            "total_files": len(pr_files),
            "status": "success",
            "error": None
        })

        for file in pr_files:
            try:
                logger.info(
                    "Starting file analysis",
                    extra={
                        "file_name": file["name"],
                        "pr_number": pr_number
                    }
                )
                start_time = datetime.now()
                code_analyzer = CodeAnalyzer()
                file_analysis = code_analyzer.analyze_code(file["content"])

                num_issues = len(file_analysis["issues"])
                results["summary"]["total_issues"] += num_issues
                
                critical_issues = sum(1 for issue in file_analysis["issues"] 
                                   if issue.get("severity") == "critical")
                results["summary"]["critical_issues"] += critical_issues

                file_result = AnalysisResult(
                    name=file["name"],
                    issues=file_analysis["issues"],
                    analysis_time=(datetime.now() - start_time).total_seconds(),
                    status="success"
                )
                
                results["files"].append(asdict(file_result))
                results["summary"]["total_files_analysed"] += 1
                
            except Exception as e:
                logger.error(
                    "File analysis failed",
                    extra={
                        "file_name": file["name"],
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                        "pr_number": pr_number
                    },
                    exc_info=True
                )
                results["summary"]["failed_files"] += 1
                
                file_result = AnalysisResult(
                    name=file["name"],
                    issues=[],
                    analysis_time=0,
                    status="error",
                    error=str(e)
                )
                results["files"].append(asdict(file_result))

        results["summary"]["analysis_end_time"] = datetime.now().isoformat()
        
    except Exception as e:
        error_message = str(e)
        if "404" in error_message and "Not Found" in error_message:
            error_message = f"Pull request #{pr_number} not found in repository {repo_url}"
        
        results["summary"].update({
            "status": "error",
            "error": error_message,
            "analysis_end_time": datetime.now().isoformat()
        })
        
        logger.error(
            "PR analysis failed",
            extra={
                "pr_number": pr_number,
                "repo_url": repo_url,
                "error_type": type(e).__name__,
                "error_details": error_message,
                "task_id": self.request.id,
                "retry_count": self.request.retries
            },
            exc_info=True
        )

    return results
